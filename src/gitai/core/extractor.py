# extractor.py
# 
# This module extracts semantic summaries from git file changes.
# It analyzes added/removed lines to identify what types of changes
# were made (e.g., new functions, classes, imports, test updates).
# 
# The extractor uses regex patterns to detect code patterns across
# multiple programming languages in a language-agnostic way.
# 
# Returns structured Signal Objects instead of plain strings:
# {
#     "type": "function_addition" | "function_removal" | "class_addition" | ...
#     "entity": "function_name" | "class_name" | None,
#     "impact": "low" | "medium" | "high",
#     "language": "python" | "javascript" | "go" | "other"
# }

import os
import re
from typing import Dict, List, Union, Optional


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

# Language detection from file extension
LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".go": "go",
    ".rb": "ruby",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".rs": "rust",
    ".php": "php",
    ".cs": "csharp",
    ".swift": "swift",
    ".kt": "kotlin",
}

# Python-specific patterns for async, decorator, import changes
PYTHON_ASYNC_PATTERNS = [
    r"async\s+def\s+(\w+)",           # async def function_name
    r"async\s+with\s+",               # async with statement
    r"async\s+for\s+",                # async for statement
    r"await\s+",                      # await expression
]

PYTHON_DECORATOR_PATTERNS = [
    r"@\w+",                          # @decorator
]

PYTHON_IMPORT_PATTERNS = [
    r"^import\s+(\w+)",               # import module
    r"^from\s+([\w.]+)\s+import",     # from module import ...
]

# Export/API patterns for breaking change detection
EXPORT_PATTERNS = [
    r"export\s+",                     # JS/TS: export const/function/class
    r"module\.exports",               # Node.js: module.exports
    r"exports\.",                     # Node.js: exports.something
    r"public\s+",                     # Java/C#: public modifier
    r"def\s+\w+",                     # Python: function definitions (potential API)
    r"class\s+\w+",                   # Python: class definitions (potential API)
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


def detect_language(file_path: str) -> str:
    """
    Detect programming language from file extension.
    
    Args:
        file_path: Path to the source file
        
    Returns:
        Language identifier (e.g., "python", "javascript", "go", "other")
    """
    _, ext = os.path.splitext(file_path)
    return LANGUAGE_MAP.get(ext.lower(), "other")


def detect_python_specific(lines: List[str], is_added: bool) -> List[Dict]:
    """
    Detect Python-specific changes: async, decorators, imports.
    
    Args:
        lines: List of code lines to analyze
        is_added: True if these are added lines, False if removed
        
    Returns:
        List of signal objects for Python-specific changes
    """
    signals = []
    signal_type_prefix = "add" if is_added else "remove"
    
    for line in lines:
        line = line.strip()
        
        # Check for async changes
        for pattern in PYTHON_ASYNC_PATTERNS:
            match = re.search(pattern, line)
            if match:
                entity = match.group(1) if match.groups() else "async_block"
                signals.append({
                    "type": f"{signal_type_prefix}_async",
                    "entity": entity,
                    "impact": "medium",
                    "language": "python"
                })
                break  # One signal per line
        
        # Check for decorator changes
        for pattern in PYTHON_DECORATOR_PATTERNS:
            match = re.search(pattern, line)
            if match:
                decorator_name = match.group(0)[1:]  # Remove @ prefix
                signals.append({
                    "type": f"{signal_type_prefix}_decorator",
                    "entity": decorator_name,
                    "impact": "medium",
                    "language": "python"
                })
                break
        
        # Check for import changes
        for pattern in PYTHON_IMPORT_PATTERNS:
            match = re.search(pattern, line)
            if match:
                module_name = match.group(1) if match.groups() else "module"
                signals.append({
                    "type": f"{signal_type_prefix}_dependency",
                    "entity": module_name,
                    "impact": "low",
                    "language": "python"
                })
                break
    
    return signals


def detect_export_changes(lines: List[str], is_added: bool, language: str) -> List[Dict]:
    """
    Detect changes to exported/public API surface.
    
    Args:
        lines: List of code lines to analyze
        is_added: True if these are added lines, False if removed
        language: Programming language identifier
        
    Returns:
        List of signal objects for export/API changes
    """
    signals = []
    signal_type_prefix = "add" if is_added else "remove"
    
    for line in lines:
        line = line.strip()
        
        # Check for export patterns
        for pattern in EXPORT_PATTERNS:
            match = re.search(pattern, line)
            if match:
                # Extract entity name if possible
                entity = None
                if match.groups():
                    entity = match.group(1)
                
                signals.append({
                    "type": f"{signal_type_prefix}_export",
                    "entity": entity,
                    "impact": "high",  # Export changes are high impact
                    "language": language
                })
                break
    
    return signals


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
    - Python-specific changes (async, decorators)
    - Export/API surface changes
    
    This function returns structured Signal Objects instead of plain strings.
    
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
            - language: Detected programming language
            - signals: List of structured Signal Objects
            - summary: List of human-readable change descriptions (legacy)
    """
    # Handle list of file changes by processing each one
    if isinstance(file_change, list):
        return [extract_summary(change) for change in file_change]

    file_path = file_change["file"]
    added = file_change.get("added_lines", [])
    removed = file_change.get("removed_lines", [])
    change_type = file_change["type"]

    # Detect language from file extension
    language = detect_language(file_path)
    
    # Initialize signals list (structured) and summary list (legacy strings)
    signals: List[Dict] = []
    summaries: List[str] = []

    # ----- File-level heuristics -----
    filename = os.path.basename(file_path)

    # Track complete file additions and deletions
    if change_type == "added":
        signals.append({
            "type": "file_addition",
            "entity": filename,
            "impact": "high",
            "language": language
        })
        summaries.append(f"add {filename} file")

    if change_type == "deleted":
        signals.append({
            "type": "file_deletion",
            "entity": filename,
            "impact": "high",
            "language": language
        })
        summaries.append(f"remove {filename} file")

    # Flag changes to test files
    if is_test_file(file_path):
        signals.append({
            "type": "test_update",
            "entity": None,
            "impact": "low",
            "language": language
        })
        summaries.append("add or update tests")

    # ----- Analyze added lines for new constructs -----
    for line in added:
        line = line.strip()

        # Detect new function definitions
        funcs = match_patterns(line, FUNCTION_PATTERNS)
        for f in funcs:
            signals.append({
                "type": "function_addition",
                "entity": f,
                "impact": "medium",
                "language": language
            })
            summaries.append(f"add {f} function")

        # Detect new class/type definitions
        classes = match_patterns(line, CLASS_PATTERNS)
        for c in classes:
            signals.append({
                "type": "class_addition",
                "entity": c,
                "impact": "medium",
                "language": language
            })
            summaries.append(f"add {c} class")

        # Detect new dependencies/imports
        if any(re.search(p, line) for p in IMPORT_PATTERNS):
            signals.append({
                "type": "dependency_addition",
                "entity": None,
                "impact": "low",
                "language": language
            })
            summaries.append("add dependencies")

    # ----- Analyze removed lines for deleted constructs -----
    for line in removed:
        line = line.strip()

        # Detect removed function definitions
        funcs = match_patterns(line, FUNCTION_PATTERNS)
        for f in funcs:
            signals.append({
                "type": "function_removal",
                "entity": f,
                "impact": "medium",
                "language": language
            })
            summaries.append(f"remove {f} function")

        # Detect removed class definitions
        classes = match_patterns(line, CLASS_PATTERNS)
        for c in classes:
            signals.append({
                "type": "class_removal",
                "entity": c,
                "impact": "medium",
                "language": language
            })
            summaries.append(f"remove {c} class")

    # ----- Language-specific analysis -----
    # Python-specific: async, decorators, imports
    if language == "python":
        signals.extend(detect_python_specific(added, is_added=True))
        signals.extend(detect_python_specific(removed, is_added=False))

    # Export/API changes (all languages)
    signals.extend(detect_export_changes(added, is_added=True, language=language))
    signals.extend(detect_export_changes(removed, is_added=False, language=language))

    # ----- Heuristic: detect modifications -----
    # If we have both added and removed lines, it's likely a modification
    # rather than pure addition/deletion
    if added and removed:
        signals.append({
            "type": "logic_update",
            "entity": None,
            "impact": "low",
            "language": language
        })
        summaries.append("update existing logic")

    # ----- Fallback: generic update message -----
    # Ensure we always return at least some signal
    if not signals:
        signals.append({
            "type": "file_update",
            "entity": None,
            "impact": "low",
            "language": language
        })
        summaries.append("update file")

    # ----- Post-processing -----
    # Remove duplicate summaries and limit to top 5 most important changes
    # to keep summaries concise and focused
    summaries = list(set(summaries))[:5]

    return {
        "file": file_path,
        "type": change_type,
        "scope": infer_scope(file_path),
        "language": language,
        "signals": signals,
        "summary": summaries  # Legacy field for backward compatibility
    }
