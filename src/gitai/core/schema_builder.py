# schema_builder.py
#
# Builds the final structured schema passed to the LLM for commit message generation.
#
# Design decisions:
# - Hints (type, scope, breaking change) are WEAK SIGNALS derived from heuristics.
#   They are not ground truth. The LLM is expected to validate and override them.
# - Raw diffs are included per file so the LLM has full semantic context as a fallback
#   when summaries are insufficient or miss internal logic changes.
# - A confidence field is attached to hints so the LLM knows how much to trust them.
# - Breaking change detection is intentionally conservative — it flags a signal,
#   not a conclusion. The LLM confirms from the diff.

import re
from typing import List, Dict
from collections import Counter


# ============================================================
# COMMIT TYPE INFERENCE
# Keyword-based heuristic. Intentionally simple — this is a
# soft signal for the LLM, not a deterministic classification.
# The LLM is expected to override this based on the actual diff.
# ============================================================

# Ordered from most specific to least specific.
# Note: order matters — earlier matches win.
# "test" before "fix" prevents "add test for fix" from returning "fix".
# However, ambiguous summaries will still produce unreliable results here.
# That's acceptable — confidence scoring handles this downstream.
COMMIT_TYPE_SIGNALS = [
    ("test",     ["test", "spec"]),
    ("fix",      ["fix", "bug", "patch", "correct"]),
    ("refactor", ["refactor", "restructure", "reorganize", "cleanup"]),
    ("feat",     ["add", "implement", "introduce", "create"]),
]

def infer_commit_type(changes: List[Dict], total_files: int, total_lines: int) -> tuple[str, str]:
    """
    Infer the likely commit type from change summaries.

    Uses keyword matching against COMMIT_TYPE_SIGNALS.
    Returns both the inferred type and a confidence level.

    Confidence is "high" only when a specific, unambiguous keyword
    matches (e.g. "refactor", "bug") AND the changeset is small enough
    for heuristic analysis to be reliable. Generic keywords like "add"
    produce "low" confidence since they appear in almost any change.
    Large changesets (>5 files or >50 lines) force low confidence.

    Args:
        changes: List of change dicts with a 'summary' field (list of strings)
        total_files: Total number of files changed
        total_lines: Total number of lines changed (insertions + deletions)

    Returns:
        tuple: (commit_type: str, confidence: str)
            commit_type — one of: 'test', 'fix', 'refactor', 'feat', 'chore'
            confidence  — one of: 'high', 'low'
    """
    summaries = " ".join(
        " ".join(c.get("summary", [])) for c in changes
    ).lower()

    # Low-confidence keywords: common words that appear in nearly any change.
    # If the final match was driven by these, we flag confidence as low.
    LOW_CONFIDENCE_KEYWORDS = {"add", "implement", "create"}

    # Size-based penalty: large changesets force low confidence
    # No simple regex script can accurately summarize a massive architectural shift
    size_penalty = total_files > 5 or total_lines > 50

    for commit_type, keywords in COMMIT_TYPE_SIGNALS:
        for keyword in keywords:
            if keyword in summaries:
                if size_penalty or keyword in LOW_CONFIDENCE_KEYWORDS:
                    return commit_type, "low"
                return commit_type, "high"

    # No strong signal found — default to chore with low confidence
    return "chore", "low"


# ============================================================
# SCOPE INFERENCE
# Directory-based scope detection. This is reliable enough
# to be a "high confidence" signal in most projects since
# scope typically maps directly to the module directory.
# ============================================================

def infer_scope(changes: List[Dict]) -> str:
    """
    Determine the dominant scope from changed file paths.

    Uses the 'scope' field (typically the parent directory of the file).
    Returns the most frequently occurring scope across all changes.

    This heuristic is generally reliable for conventional commit scopes
    since scope maps naturally to directory/module structure.

    Args:
        changes: List of change dicts with a 'scope' field

    Returns:
        str: Most common scope, or 'general' if none found
    """
    scopes = [c.get("scope", "general") for c in changes]
    most_common = Counter(scopes).most_common(1)
    return most_common[0][0] if most_common else "general"


# ============================================================
# BREAKING CHANGE DETECTION
# Conservative heuristic — intentionally produces false negatives
# over false positives. A "breaking_change_signal: true" means
# the LLM should inspect the diff and confirm, not auto-flag it.
#
# Current limitation: only catches "remove" + "api" co-occurrence.
# Misses: renamed signatures, changed return types, deleted exports,
# modified constructor params. This is a known gap — the LLM
# is responsible for catching what this heuristic misses.
# ============================================================

# Configuration files whose modification may indicate breaking changes
CONFIG_FILES = {"pyproject.toml", "package.json", "go.mod", "setup.py", "setup.cfg", "Cargo.toml", "pom.xml", "build.gradle"}

# Patterns for detecting export/API removal in diff lines
EXPORT_REMOVAL_PATTERNS = [
    r"export\s+",           # JS/TS: export removal
    r"module\.exports",     # Node.js: module.exports removal
    r"exports\.",           # Node.js: exports.something removal
    r"public\s+",           # Java/C#: public modifier removal
]


def detect_breaking_change(changes: List[Dict], parsed_files: List[Dict]) -> bool:
    """
    Signal whether the changes might include a breaking change.

    This is a heuristic that checks multiple signals:
    1. File deletions (removing entire files is often breaking)
    2. Export/API removals in removed lines (detected via signals or regex)
    3. Modification of configuration files (pyproject.toml, package.json, go.mod, etc.)
    4. Co-occurrence of "remove" and "api" in summaries (legacy heuristic)

    Do not treat this as a definitive flag. It is passed to the LLM
    as "breaking_change_signal" with the expectation that the LLM
    validates it against the actual diff content.

    Args:
        changes: List of change dicts from extract_summary() with 'summary', 'signals', 'type' fields
        parsed_files: List of parsed file dicts from parse_git_diff() with 'file', 'type', 'removed_lines'

    Returns:
        bool: True if a potential breaking change pattern is detected
    """
    # Build a lookup from file path to parsed file data
    parsed_lookup = {p["file"]: p for p in parsed_files}

    for change in changes:
        file_path = change.get("file", "")
        filename = file_path.split("/")[-1]  # basename

        # Signal 1: File deletion
        if change.get("type") == "deleted":
            return True

        # Signal 2: Config file modification
        if filename in CONFIG_FILES:
            return True

        # Signal 3: Export removal detected in signals
        signals = change.get("signals", [])
        for signal in signals:
            if signal.get("type") == "remove_export" and signal.get("impact") == "high":
                return True
            if signal.get("type") == "function_removal" and signal.get("impact") in ("medium", "high"):
                return True
            if signal.get("type") == "class_removal":
                return True

        # Signal 4: Export patterns in removed lines (fallback for files without signals)
        if file_path in parsed_lookup:
            removed_lines = parsed_lookup[file_path].get("removed_lines", [])
            for line in removed_lines:
                line = line.strip()
                for pattern in EXPORT_REMOVAL_PATTERNS:
                    if re.search(pattern, line):
                        return True

    # Legacy heuristic: co-occurrence of "remove" and "api" in summaries
    summaries = " ".join(
        " ".join(c.get("summary", [])) for c in changes
    ).lower()
    if "remove" in summaries and "api" in summaries:
        return True

    return False


# ============================================================
# SCHEMA BUILDER
# Assembles the final schema passed to the LLM.
#
# Structure:
#   meta    — aggregate stats (files, insertions, deletions)
#   changes — per-file summaries + raw diffs for full semantic context
#   hints   — weak heuristic signals with confidence for LLM guidance
#
# The raw diff is included in each file entry so the LLM can fall back
# to direct diff inspection when summaries are incomplete or misleading.
# ============================================================

def build_schema(
    parsed_files: List[Dict],
    file_summaries: List[Dict],
) -> Dict:
    """
    Build the structured schema for commit message generation.

    Merges semantic summaries with raw diff data and heuristic hints
    into a single JSON-serializable schema for prompt injection.

    The hints block is explicitly marked with a confidence level so
    the LLM knows how much weight to give each signal. Low confidence
    means the LLM should derive the correct value from the diff directly.

    Args:
        file_summaries: Output of extract_summary(). Each dict contains:
            - file (str): file path
            - type (str): change type (added, modified, deleted)
            - scope (str): parent directory / module
            - language (str): detected programming language
            - signals (List[Dict]): structured Signal Objects
            - summary (List[str]): human-readable change descriptions

        parsed_files: Output of parse_git_diff(). Each dict contains:
            - file (str): file path
            - meta (dict): insertions, deletions counts
            - raw_diff (str): raw unified diff for this file

    Returns:
        Dict with:
            meta:
                files_changed (int)
                insertions    (int)
                deletions     (int)
            changes (List[Dict]):
                Per-file entry with summary fields + raw_diff attached
            hints:
                suggested_type        (str)  — weak signal, LLM should validate
                suggested_scope       (str)  — generally reliable
                breaking_change_signal (bool) — heuristic flag, LLM must confirm
                confidence            (str)  — 'high' or 'low'
    """
    # ----- Meta aggregation -----
    total_insertions = sum(f.get("meta", {}).get("insertions", 0) for f in parsed_files)
    total_deletions = sum(f.get("meta", {}).get("deletions", 0) for f in parsed_files)
    total_lines = total_insertions + total_deletions

    meta = {
        "files_changed": len(file_summaries),
        "insertions": total_insertions,
        "deletions": total_deletions,
    }

    # ----- Merge raw diffs into summaries using path-based lookup -----
    # Build a dictionary keyed by file path to ensure correct matching
    # even if the order of parsed_files and file_summaries differs.
    parsed_lookup = {p["file"]: p for p in parsed_files}

    changes = []
    for summary in file_summaries:
        file_path = summary.get("file", "")
        parsed = parsed_lookup.get(file_path, {})
        entry = {**summary, "diff": parsed.get("raw_diff", "")}
        changes.append(entry)

    # ----- Hints -----
    # All hints are heuristic-derived weak signals.
    # suggested_type and confidence come from the same inference call
    # since confidence is a property of how the type was matched.
    # Confidence is penalized for large changesets (>5 files or >50 lines).
    suggested_type, confidence = infer_commit_type(file_summaries, len(file_summaries), total_lines)

    hints = {
        # Weak signal — keyword matched. LLM should validate against diff.
        "suggested_type": suggested_type,

        # Generally reliable — maps directly to directory structure.
        "suggested_scope": infer_scope(file_summaries),

        # Heuristic flag only. LLM must confirm from diff before using.
        "breaking_change_signal": detect_breaking_change(file_summaries, parsed_files),

        # Reflects how reliable suggested_type is.
        # "low" means the LLM should ignore suggested_type and infer from diff.
        # Forced low for large changesets (>5 files or >50 lines).
        "confidence": confidence,
    }

    return {
        "meta": meta,
        "changes": changes,
        "hints": hints,
    }
