# extractor.py
# 
# This module extracts semantic summaries from git file changes.
# It analyzes added/removed lines to identify what types of changes
# were made (e.g., new functions, classes, imports, test updates).
# 
# The extractor uses regex patterns to detect code patterns across
# multiple programming languages in a language-agnostic way.

import os
import re
from typing import Dict, List, Union


# ============================================================
# PATTERN REGISTRIES
# These regex patterns detect common code constructs across
# different programming languages. Each registry targets a
# specific type of code entity.
# ============================================================

# Detects function/method definitions in various languages
# Supports: Python (def), JavaScript/TypeScript (function, arrow functions),
# Go (func), and other C-style languages
FUNCTION_PATTERNS = [
    r"def\s+(\w+)\(",           # Python: def function_name(
    r"function\s+(\w+)\(",     # JS/TS: function functionName(
    r"func\s+(\w+)\(",          # Go: func functionName(
    r"(\w+)\s*=\s*\(?.*\)?\s*=>",  # JS arrow: const name = (...) => ...
]

# Detects class/type definitions
CLASS_PATTERNS = [
    r"class\s+(\w+)",          # Python/JS/Java: class ClassName
    r"type\s+(\w+)\s+struct",  # Go: type Name struct
]

# Detects import/require statements for dependency tracking
IMPORT_PATTERNS = [
    r"^import\s+",             # Python/Java: import module
    r"^from\s+",               # Python: from module import ...
    r"require\(",              # Node.js: require('module')
]

# Patterns to identify test files (used for filtering)
TEST_PATTERNS = [
    r"test_",                  # test_*.py, test*.py
    r"\.test\.",               # component.test.js
    r"\.spec\.",               # component.spec.ts
]


# ============================================================
# HELPER FUNCTIONS
# Utility functions for pattern matching and file analysis
# ============================================================

def match_patterns(line: str, patterns: List[str]) -> List[str]:
    """
    Check a single line against multiple regex patterns.
    
    Args:
        line: The source code line to check
        patterns: List of regex patterns to match against
        
    Returns:
        List of matched identifiers (function names, class names, etc.)
        Returns ["match"] for patterns without capture groups
    """
    matches = []
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            # Extract captured group if present, otherwise just flag as match
            if match.groups():
                matches.append(match.group(1))
            else:
                matches.append("match")
    return matches


def infer_scope(file_path: str) -> str:
    """
    Extract the directory scope from a file path.
    
    This helps categorize changes by their module/directory.
    E.g., 'src/core/parser.py' returns 'core'
    
    Args:
        file_path: Full path to the source file
        
    Returns:
        The parent directory name, or 'general' if unavailable
    """
    parts = file_path.split("/")
    if len(parts) > 1:
        return parts[-2]  # Parent directory
    return "general"


def is_test_file(file_path: str) -> bool:
    """
    Check if a file appears to be a test file based on naming conventions.
    
    Args:
        file_path: Path to check
        
    Returns:
        True if the file appears to be a test file
    """
    return any(re.search(p, file_path) for p in TEST_PATTERNS)


# ============================================================
# MAIN EXTRACTOR FUNCTION
# Core logic for generating semantic summaries from file changes
# ============================================================

def extract_summary(file_change: Union[List[Dict], Dict]) -> Union[List[Dict], Dict]:
    """
    Generate a semantic summary of changes made to one or more files.
    
    Analyzes added and removed lines to identify:
    - New/deleted functions and classes
    - Dependency changes (imports/requires)
    - Test file modifications
    - File-level operations (add/delete)
    
    This function is flexible and handles both single dict and list of dicts:
        - Single: extract_summary(change) -> Dict
        - Multiple: extract_summary([change1, change2]) -> List[Dict]
    
    Args:
        file_change: Either:
            - A single dict with one file's changes
            - A list of dicts with multiple files' changes
            
            Each dict should contain:
            - file: Path to the changed file
            - type: Change type ('added', 'modified', 'deleted')
            - added_lines: List of newly added lines
            - removed_lines: List of deleted lines
            
    Returns:
        - If input is a single dict: returns a single dict
        - If input is a list of dicts: returns a list of dicts
        
        Each result dict contains:
            - file: Original file path
            - type: Change type
            - scope: Inferred directory/module scope
            - summary: List of human-readable change descriptions
    """
    # Handle list of file changes by processing each one
    if isinstance(file_change, list):
        return [extract_summary(change) for change in file_change]

    file_path = file_change["file"]
    added = file_change.get("added_lines", [])
    removed = file_change.get("removed_lines", [])
    change_type = file_change["type"]

    summaries = []

    # ----- File-level heuristics -----
    filename = os.path.basename(file_path)

    # Track complete file additions and deletions
    if change_type == "added":
        summaries.append(f"add {filename} file")

    if change_type == "deleted":
        summaries.append(f"remove {filename} file")

    # Flag changes to test files
    if is_test_file(file_path):
        summaries.append("add or update tests")

    # ----- Analyze added lines for new constructs -----
    for line in added:
        line = line.strip()

        # Detect new function definitions
        funcs = match_patterns(line, FUNCTION_PATTERNS)
        for f in funcs:
            summaries.append(f"add {f} function")

        # Detect new class/type definitions
        classes = match_patterns(line, CLASS_PATTERNS)
        for c in classes:
            summaries.append(f"add {c} class")

        # Detect new dependencies/imports
        if any(re.search(p, line) for p in IMPORT_PATTERNS):
            summaries.append("add dependencies")

    # ----- Analyze removed lines for deleted constructs -----
    for line in removed:
        line = line.strip()

        # Detect removed function definitions
        funcs = match_patterns(line, FUNCTION_PATTERNS)
        for f in funcs:
            summaries.append(f"remove {f} function")

        # Detect removed class definitions
        classes = match_patterns(line, CLASS_PATTERNS)
        for c in classes:
            summaries.append(f"remove {c} class")

    # ----- Heuristic: detect modifications -----
    # If we have both added and removed lines, it's likely a modification
    # rather than pure addition/deletion
    if added and removed:
        summaries.append("update existing logic")

    # ----- Fallback: generic update message -----
    # Ensure we always return at least some summary
    if not summaries:
        summaries.append("update file")

    # ----- Post-processing -----
    # Remove duplicates and limit to top 5 most important changes
    # to keep summaries concise and focused
    summaries = list(set(summaries))[:5]

    return {
        "file": file_path,
        "type": change_type,
        "scope": infer_scope(file_path),
        "summary": summaries
    }
