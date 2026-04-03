# parser.py
# 
# This module parses raw git diff output into structured data.
# It uses the 'unidiff' library to handle unified diff format and
# extracts file-level changes with line-by-line details.

from unidiff import PatchSet
from typing import List, Dict, Any
from gitai.core.extractor import extract_summary
from gitai.utils.log import setup_logger, sanitize_for_logging
from gitai.utils.exceptions import ParseError

logger = setup_logger(__name__, "parse.log")
# ============================================================
# MAIN PARSER FUNCTION
# Converts git diff text into structured dictionaries
# ============================================================

def parse_git_diff(diff_text: str) -> List[Dict[str, Any]]:
    """
    Parse a git diff string into structured file changes.
    
    Converts raw git diff output (from `git diff` or `git diff --cached`)
    into a structured list of dictionaries containing:
    - File path and change type
    - Added and removed lines
    - Change statistics (insertions/deletions)
    
    This is typically used as a preprocessing step before calling
    extract_summary() to generate semantic summaries of the changes.
    
    Args:
        diff_text (str): Raw output from `git diff` or `git diff --cached`
            Should be in unified diff format.
        
    Returns:
        List[Dict]: List of file-level change dictionaries, each containing:
            - file (str): Path to the changed file
            - type (str): Change type ('added', 'modified', or 'deleted')
            - added_lines (List[str]): Lines that were added
            - removed_lines (List[str]): Lines that were removed
            - meta (Dict): Metadata including:
                - insertions (int): Total number of added lines
                - deletions (int): Total number of removed lines
    
    Raises:
        ParseError: If the diff text cannot be parsed
        
    Example:
        >>> diff_text = subprocess.run(['git', 'diff'], capture_output=True).stdout
        >>> file_changes = parse_git_diff(diff_text)
        >>> summaries = extract_summary(file_changes)
    """
    # Validate input
    if not diff_text or not diff_text.strip():
        raise ParseError(
            "Empty diff text provided",
            details={"input_length": len(diff_text) if diff_text else 0}
        )
    
    try:
        # Parse the unified diff format using unidiff library
        # PatchSet handles hunk headers, line numbers, and context automatically
        patch = PatchSet(diff_text.splitlines())
    except Exception as e:
        raise ParseError(
            f"Failed to parse git diff: {str(e)}",
            details={"error_type": type(e).__name__, "diff_length": len(diff_text)},
            suggestion="Ensure the diff output is valid unified diff format."
        )
    
    files = []

    # Iterate through each file that has changes
    for patched_file in patch:
        # Determine the type of change for this file
        # unidiff provides flags for new and deleted files
        if patched_file.is_added_file:
            change_type = "added"
        elif patched_file.is_removed_file:
            change_type = "deleted"
        else:
            change_type = "modified"

        # Initialize the file change record
        file_change = {
            "file": patched_file.path,
            "type": change_type,
            "added_lines": [],
            "removed_lines": [],
            "meta": {
                "insertions": patched_file.added,   # Total insertions in file
                "deletions": patched_file.removed    # Total deletions in file
            }
        }

        # Extract line-by-line changes and hunk context from each hunk
        # Hunks contain the actual code changes with +/- prefixes
        file_change["hunks"] = []
        raw_diff_lines = []
        
        for hunk in patched_file:
            # Build structured hunk data with context
            hunk_data = {
                "start_line": hunk.source_start,
                "source_length": hunk.source_length,
                "target_start": hunk.target_start,
                "target_length": hunk.target_length,
                "context_before": [],
                "changes": [],
                "context_after": []
            }
            
            # Collect all lines from the hunk
            hunk_lines = []
            for line in hunk:
                line_value = line.value.rstrip("\n")
                hunk_lines.append({
                    "type": "context" if not line.is_added and not line.is_removed else ("add" if line.is_added else "remove"),
                    "value": line_value,
                    "line_number": line.line_number if hasattr(line, 'line_number') else None,
                    "is_added": line.is_added,
                    "is_removed": line.is_removed,
                })
                raw_diff_lines.append(str(line))
            
            # Extract context before changes (up to 3 lines)
            change_start_idx = None
            for i, hunk_line in enumerate(hunk_lines):
                if hunk_line["type"] in ("add", "remove"):
                    change_start_idx = i
                    break
            
            if change_start_idx is not None:
                # Context before: up to 3 lines before first change
                context_before_start = max(0, change_start_idx - 3)
                hunk_data["context_before"] = [
                    hunk_lines[j]["value"] for j in range(context_before_start, change_start_idx)
                ]
                
                # Context after: up to 3 lines after last change
                change_end_idx = None
                for i in range(len(hunk_lines) - 1, -1, -1):
                    if hunk_lines[i]["type"] in ("add", "remove"):
                        change_end_idx = i
                        break
                
                if change_end_idx is not None:
                    context_after_end = min(len(hunk_lines), change_end_idx + 4)
                    hunk_data["context_after"] = [
                        hunk_lines[j]["value"] for j in range(change_end_idx + 1, context_after_end)
                    ]
                
                # Extract changes with line numbers
                for i, hunk_line in enumerate(hunk_lines):
                    if hunk_line["type"] in ("add", "remove"):
                        # For removed lines, use the line_number from unidiff
                        # For added lines, estimate based on position
                        if hunk_line["is_removed"]:
                            line_num = hunk_line["line_number"]
                        else:
                            # For added lines, estimate from context
                            line_num = hunk_data["start_line"] + change_start_idx - len(hunk_data["context_before"]) + i
                        hunk_data["changes"].append({
                            "type": hunk_line["type"],
                            "line": hunk_line["value"],
                            "line_num": line_num
                        })
            
            file_change["hunks"].append(hunk_data)
            
            # Process added/removed lines for backward compatibility
            for hunk_line in hunk_lines:
                if hunk_line["is_added"]:
                    file_change["added_lines"].append(hunk_line["value"])
                elif hunk_line["is_removed"]:
                    file_change["removed_lines"].append(hunk_line["value"])
        
        # Store raw diff for this file
        file_change["raw_diff"] = "\n".join(raw_diff_lines)

        files.append(file_change)
    
    # Log summary statistics instead of full file contents (security)
    total_insertions = sum(f["meta"]["insertions"] for f in files)
    total_deletions = sum(f["meta"]["deletions"] for f in files)
    logger.info(f"Parsed {len(files)} file(s), {total_insertions} insertions, {total_deletions} deletions")
    
    return files
