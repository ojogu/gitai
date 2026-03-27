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

def infer_commit_type(changes: List[Dict]) -> tuple[str, str]:
    """
    Infer the likely commit type from change summaries.

    Uses keyword matching against COMMIT_TYPE_SIGNALS.
    Returns both the inferred type and a confidence level.

    Confidence is "high" only when a specific, unambiguous keyword
    matches (e.g. "refactor", "bug"). Generic keywords like "add"
    produce "low" confidence since they appear in almost any change.

    Args:
        changes: List of change dicts with a 'summary' field (list of strings)

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

    for commit_type, keywords in COMMIT_TYPE_SIGNALS:
        for keyword in keywords:
            if keyword in summaries:
                confidence = "low" if keyword in LOW_CONFIDENCE_KEYWORDS else "high"
                return commit_type, confidence

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

def detect_breaking_change(changes: List[Dict]) -> bool:
    """
    Signal whether the changes might include a breaking change.

    This is a weak heuristic — it detects one common breaking change
    pattern (removing something API-related) but will miss many others.

    Do not treat this as a definitive flag. It is passed to the LLM
    as "breaking_change_signal" with the expectation that the LLM
    validates it against the actual diff content.

    Args:
        changes: List of change dicts with a 'summary' field

    Returns:
        bool: True if a potential breaking change pattern is detected
    """
    summaries = " ".join(
        " ".join(c.get("summary", [])) for c in changes
    ).lower()

    # Heuristic: co-occurrence of "remove" and "api" suggests a breaking change.
    # This will miss renames, signature changes, deleted exports, etc.
    return "remove" in summaries and "api" in summaries


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
    file_summaries: List[Dict],
    parsed_files: List[Dict]
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
            - summary (List[str]): human-readable change descriptions

        parsed_files: Output of parse_git_diff(). Each dict contains:
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

    meta = {
        "files_changed": len(file_summaries),
        "insertions": total_insertions,
        "deletions": total_deletions,
    }

    # ----- Merge raw diffs into summaries -----
    # Raw diff is attached so the LLM has full context per file.
    # Summaries alone may miss internal logic changes, renames, or
    # subtle refactors that only the diff can reveal.
    changes = []
    for summary, parsed in zip(file_summaries, parsed_files):
        entry = {**summary, "diff": parsed.get("raw_diff", "")}
        changes.append(entry)

    # ----- Hints -----
    # All hints are heuristic-derived weak signals.
    # suggested_type and confidence come from the same inference call
    # since confidence is a property of how the type was matched.
    suggested_type, confidence = infer_commit_type(file_summaries)

    hints = {
        # Weak signal — keyword matched. LLM should validate against diff.
        "suggested_type": suggested_type,

        # Generally reliable — maps directly to directory structure.
        "suggested_scope": infer_scope(file_summaries),

        # Heuristic flag only. LLM must confirm from diff before using.
        "breaking_change_signal": detect_breaking_change(file_summaries),

        # Reflects how reliable suggested_type is.
        # "low" means the LLM should ignore suggested_type and infer from diff.
        "confidence": confidence,
    }

    return {
        "meta": meta,
        "changes": changes,
        "hints": hints,
    }