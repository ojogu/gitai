# schema_builder.py
# 
# This module builds a high-level schema from parsed file changes and summaries.
# It aggregates metadata, infers commit type hints, and detects breaking changes
# to provide a structured overview suitable for generating commit messages.

from typing import List, Dict
from collections import Counter


# ============================================================
# COMMIT TYPE INFERENCE
# Heuristics to guess the type of commit based on change summaries
# ============================================================

def infer_commit_type(changes: List[Dict]) -> str:
    """
    Determine the likely commit type based on the content of changes.
    
    Analyzes the text in change summaries to guess the appropriate
    commit type (following Conventional Commits specification).
    
    Args:
        changes: List of change dictionaries with 'summary' field
        
    Returns:
        str: One of 'test', 'fix', 'refactor', 'feat', or 'chore'
    """
    # Combine all summary text and convert to lowercase for matching
    summaries = " ".join(
        " ".join(c.get("summary", [])) for c in changes
    ).lower()

    # Check for specific keywords in order of specificity
    if "test" in summaries:
        return "test"
    if "fix" in summaries or "bug" in summaries:
        return "fix"
    if "refactor" in summaries:
        return "refactor"
    if "add" in summaries or "implement" in summaries:
        return "feat"

    return "chore"


# ============================================================
# SCOPE INFERENCE
# Determines the dominant scope/module from changed files
# ============================================================

def infer_scope(changes: List[Dict]) -> str:
    """
    Find the most common scope among all changed files.
    
    Uses the 'scope' field from each change (typically the parent directory)
    and returns the most frequently occurring one.
    
    Args:
        changes: List of change dictionaries with 'scope' field
        
    Returns:
        str: The most common scope, or 'general' if none found
    """
    # Extract scope from each change (default to 'general' if missing)
    scopes = [c.get("scope", "general") for c in changes]
    
    # Find the most common scope using Counter
    most_common = Counter(scopes).most_common(1)
    return most_common[0][0] if most_common else "general"


# ============================================================
# BREAKING CHANGE DETECTION
# Heuristic to detect potentially breaking API changes
# ============================================================

def detect_breaking_change(changes: List[Dict]) -> bool:
    """
    Detect if the changes might include a breaking change.
    
    Uses a simple heuristic: looks for 'remove' and 'api' keywords
    in the same set of changes. This can be improved with more
    sophisticated detection (e.g., checking for API signature changes).
    
    Args:
        changes: List of change dictionaries with 'summary' field
        
    Returns:
        bool: True if breaking change is likely, False otherwise
    """
    summaries = " ".join(
        " ".join(c.get("summary", [])) for c in changes
    ).lower()

    # Heuristic: removing something related to 'api' suggests breaking change
    # Note: This is a basic check and can be improved later
    return "remove" in summaries and "api" in summaries


# ============================================================
# MAIN SCHEMA BUILDER
# Aggregates all information into a structured schema
# ============================================================

def build_schema(
    file_summaries: List[Dict],
    parsed_files: List[Dict]
) -> Dict:
    """
    Build a comprehensive schema from file summaries and parsed diff data.
    
    Combines semantic summaries (from extract_summary) with raw diff
    metadata (insertions/deletions) to create a structured overview
    suitable for commit message generation.
    
    This is typically the final step before generating a commit message:
        parsed_files -> file_summaries -> schema -> LLM -> commit message
    
    Args:
        file_summaries: List of summaries from extract_summary()
            Each dict should contain: file, type, scope, summary
        parsed_files: List of parsed file changes from parse_git_diff()
            Each dict should contain: meta with insertions/deletions
            
    Returns:
        Dict: Complete schema containing:
            - meta: Aggregate statistics
                - files_changed (int): Number of files modified
                - insertions (int): Total lines added
                - deletions (int): Total lines removed
            - changes: List of file summaries
            - hints: Suggested commit metadata
                - suggested_type (str): 'test', 'fix', 'refactor', 'feat', or 'chore'
                - suggested_scope (str): Dominant module/directory
                - breaking_change (bool): True if breaking change detected
                
    Example:
        >>> parsed = parse_git_diff(diff_text)
        >>> summaries = extract_summary(parsed)
        >>> schema = build_schema(summaries, parsed)
        >>> # Use schema to generate commit message
    """
    # ----- Meta aggregation -----
    # Sum up insertions and deletions across all files
    total_insertions = sum(f.get("meta", {}).get("insertions", 0) for f in parsed_files)
    total_deletions = sum(f.get("meta", {}).get("deletions", 0) for f in parsed_files)

    meta = {
        "files_changed": len(file_summaries),
        "insertions": total_insertions,
        "deletions": total_deletions
    }

    # ----- Generate hints for commit message -----
    # Use heuristics to suggest type, scope, and breaking changes
    hints = {
        "suggested_type": infer_commit_type(file_summaries),
        "suggested_scope": infer_scope(file_summaries),
        "breaking_change": detect_breaking_change(file_summaries),
    }

    # ----- Assemble final schema -----
    schema = {
        "meta": meta,
        "changes": file_summaries,
        "hints": hints
    }

    return schema
