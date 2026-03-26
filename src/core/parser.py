# parser.py
# 
# This module parses raw git diff output into structured data.
# It uses the 'unidiff' library to handle unified diff format and
# extracts file-level changes with line-by-line details.

from unidiff import PatchSet
from typing import List, Dict, Any
from core.extractor import extract_summary


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
    
    Example:
        >>> diff_text = subprocess.run(['git', 'diff'], capture_output=True).stdout
        >>> file_changes = parse_git_diff(diff_text)
        >>> summaries = extract_summary(file_changes)
    """
    # Parse the unified diff format using unidiff library
    # PatchSet handles hunk headers, line numbers, and context automatically
    patch = PatchSet(diff_text.splitlines())
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

        # Extract line-by-line changes from each hunk
        # Hunks contain the actual code changes with +/- prefixes
        for hunk in patched_file:
            for line in hunk:
                # Only process added or removed lines (skip context lines)
                if line.is_added:
                    # Remove trailing newline before storing
                    file_change["added_lines"].append(line.value.rstrip("\n"))
                elif line.is_removed:
                    file_change["removed_lines"].append(line.value.rstrip("\n"))

        files.append(file_change)

    return files
