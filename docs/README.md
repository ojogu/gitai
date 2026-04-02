# gitAI High-Fidelity Context System — Post-Mortem & Architecture Documentation

## Overview

This document describes the architectural transition from "vague string summaries" to a "high-fidelity context" system in gitAI. This optimization marks a fundamental shift from building a **deterministic script** (which tries to do the thinking) to an **intelligent pipeline** (where the script prepares the "evidence" for the LLM).

The goal was to eliminate abstraction layers that caused generic, uninformative commit messages, and instead provide the LLM with raw data (diffs), structured metadata (signals), and heuristic hints with confidence scores.

## Problem Statement

The previous system had a critical flaw: `extract_summary()` returned plain string summaries like `["add function", "update logic"]`. These strings were too abstract — the LLM had no way to know *which* function was added or *what* logic was updated. The result was commit messages that were vague and often incorrect.

### Root Cause Analysis

1. **Abstraction Layer**: String summaries discarded concrete information (entity names, line numbers, context).
2. **No Confidence Signals**: All summaries were treated equally, regardless of reliability.
3. **Misaligned Data**: `zip()` was used to merge parsed files with summaries, risking mismatches if ordering differed.
4. **Weak Breaking Change Detection**: Only checked for "remove" + "api" co-occurrence.

## Solution Architecture

The new system is built on four pillars:

### 1. Hunk-Aware Parser (`parser.py`)

**What Changed**: The parser now extracts structured hunk data with 3 lines of context around each change, and preserves the raw diff per file.

**New Data Structure**:
```python
{
    "file": "src/foo.py",
    "type": "modified",
    "added_lines": [...],           # flattened (backward compat)
    "removed_lines": [...],         # flattened (backward compat)
    "hunks": [
        {
            "start_line": 42,
            "source_length": 10,
            "target_start": 45,
            "target_length": 12,
            "context_before": ["line 40", "line 41", "line 42"],
            "changes": [
                {"type": "add", "line": "new code", "line_num": 43},
                {"type": "remove", "line": "old code", "line_num": 43}
            ],
            "context_after": ["line 46", "line 47", "line 48"]
        }
    ],
    "raw_diff": "...unified diff text...",
    "meta": {"insertions": 5, "deletions": 3}
}
```

**Decisions**:
- **3 lines of context**: Enough to understand surrounding code without bloating the prompt.
- **Raw diff per file**: Ensures the LLM always has the ground truth, even if summaries are incomplete.
- **Backward compatibility**: Kept `added_lines` and `removed_lines` as flattened lists for legacy consumers.

**Tradeoffs**:
- Larger output per file (hunks + raw_diff), but necessary for LLM accuracy.
- Line numbers for added lines are estimated (unidiff doesn't provide them directly).

### 2. Structured Signal Extractor (`extractor.py`)

**What Changed**: Instead of returning `{"summary": ["add function", "update logic"]}`, the extractor now returns `{"signals": [{"type": "function_addition", "entity": "my_func", "impact": "medium", "language": "python"}]}`.

**Signal Object Schema**:
```python
{
    "type": str,        # e.g., "function_addition", "test_update", "logic_update"
    "entity": str|None, # e.g., function name, class name, module name
    "impact": str,      # "low", "medium", "high"
    "language": str     # "python", "javascript", "go", etc.
}
```

**New Features**:
- **Language Detection**: From file extension (supports 15+ languages).
- **Python-Specific Pass**: Detects async, decorator, and import changes.
- **Export/API Detection**: Flags changes to public surface area (used for breaking change detection).

**Decisions**:
- **Impact Levels**: `high` for file additions/deletions and export changes; `medium` for function/class changes; `low` for imports and logic updates.
- **Legacy `summary` field**: Kept as a list of strings for backward compatibility, but `signals` is the primary data source.
- **Deduplication**: Limited to 5 summaries (strings) to keep output concise.

**Tradeoffs**:
- More data per change, but enables finer-grained confidence scoring.
- Export detection is conservative — many false negatives, few false positives.

### 3. Stereoscopic Schema Builder (`schema_builder.py`)

**What Changed**: Replaced `zip()` with a dictionary lookup keyed by file path. Added enhanced breaking change detection and size-based confidence penalty.

**Key Changes**:

#### File-Path Mapping
```python
# OLD (risky):
for summary, parsed in zip(file_summaries, parsed_files):
    entry = {**summary, "diff": parsed.get("raw_diff", "")}

# NEW (safe):
parsed_lookup = {p["file"]: p for p in parsed_files}
for summary in file_summaries:
    parsed = parsed_lookup.get(summary.get("file", ""), {})
    entry = {**summary, "diff": parsed.get("raw_diff", "")}
```

#### Breaking Change Detection
Now checks:
1. File deletions (any deleted file is a potential breaking change).
2. Export/API removals (via signals or regex on removed lines).
3. Config file modifications (`pyproject.toml`, `package.json`, `go.mod`, etc.).
4. Legacy "remove" + "api" co-occurrence.

#### Confidence Scoring
```python
# Confidence is "high" only when:
# 1. A specific, unambiguous keyword matches (e.g., "refactor", "bug")
# 2. The changeset is small (<5 files AND <50 lines)

size_penalty = total_files > 5 or total_lines > 50
if size_penalty or keyword in LOW_CONFIDENCE_KEYWORDS:
    confidence = "low"
```

**Decisions**:
- **Conservative breaking change detection**: Intentionally produces false negatives over false positives. The LLM is responsible for catching what the heuristic misses.
- **Size penalty**: No simple regex script can accurately summarize a massive architectural shift. If >5 files or >50 lines, confidence is forced to "low" and the LLM must derive intent from the diff directly.

**Tradeoffs**:
- Some legitimate breaking changes may be missed (e.g., renamed function signatures, changed return types). This is acceptable — the LLM validates from the diff.

### 4. Validation Prompt Strategy (`prompt.py`)

**What Changed**: Updated system prompt to emphasize "Raw Diff is source of truth" and added specific validation instructions based on confidence and breaking change signals.

**System Prompt Key Additions**:
- "**Critical: The Raw Diff is your source of truth.**"
- "The structured signals (type, entity, impact) provide location context but may have false positives."
- "If confidence is 'low,' the suggested type is a guess — analyze the diff logic to determine the true intent."

**Dynamic Addons**:
- **Low Confidence**: "Warning: The suggested type is a guess. Analyze the diff logic to determine the true intent."
- **Breaking Change**: "Critical: Potential breaking change detected. Verify if public APIs or interfaces were altered."

**Decisions**:
- **LLM as Architect**: The LLM is no longer a "generator" that trusts hints — it's an "architect" that validates hints against raw data.
- **Explicit Instructions**: Rather than subtle guidance, we use direct warnings ("Warning:", "Critical:").

**Tradeoffs**:
- Longer prompts (more tokens), but necessary to guide the LLM correctly.
- Increased `max_tokens` from 500 to 1024 to accommodate the larger prompt and allow full commit messages.

## Bug Fixes

### 1. `AttributeError: 'Hunk' object has no attribute 'header'`

**Cause**: The `unidiff` library's `Hunk` object doesn't have a `header` attribute. The code tried to access `hunk.header` to get the hunk header line.

**Fix**: Removed the invalid access. Hunk headers are implicitly included when iterating over hunk lines, and the hunk metadata (`source_start`, `source_length`, `target_start`, `target_length`) is available directly on the `Hunk` object.

### 2. Truncated Commit Messages

**Cause**: `max_tokens` was set to 500, which was insufficient for commit messages with a title and body (especially with the larger prompt from the new system).

**Fix**: Increased `max_tokens` to 1024.

## Schema Changes

### `parse_git_diff()` Output
- Added: `hunks` (list of structured hunk objects), `raw_diff` (string)
- Unchanged: `file`, `type`, `added_lines`, `removed_lines`, `meta`

### `extract_summary()` Output
- Added: `language` (string), `signals` (list of Signal Objects)
- Unchanged: `file`, `type`, `scope`, `summary` (legacy strings)

### `build_schema()` Output
- Changed: `changes` now built via path-based lookup instead of `zip()`
- Unchanged: `meta`, `hints` structure (but `confidence` now includes size penalty)

## Migration Guide

### For Users of `extract_summary()`
If you consume the `summary` field (list of strings), no changes needed — it's still present. To use the new structured signals, access `signals` instead:

```python
# OLD:
for change in file_summaries:
    print(change["summary"])  # ["add function", "update logic"]

# NEW:
for change in file_summaries:
    for signal in change["signals"]:
        print(f"{signal['type']}: {signal['entity']} (impact: {signal['impact']})")
```

### For Users of `parse_git_diff()`
No breaking changes. The new `hunks` and `raw_diff` fields are additive.

### For `schema_builder.py` Consumers
No changes needed. The schema structure is the same, but `hints.confidence` may be "low" more often due to the size penalty.

## Core Architectural Lessons

This transition taught us five fundamental lessons about building AI-assisted developer tools:

### 1. Context Over Content (The "Hunk" Lesson)
Previously, the system focused on *content*—the raw added and removed lines. This optimization shifted the focus to *context*.
* **The Insight:** An LLM cannot accurately describe a change if it doesn't know where it happened. By including **Hunks** (the 3 lines of surrounding code), you provide the "neighborhood" of the change.
* **System Impact:** This allows the AI to distinguish between a variable change in a `global` scope versus a change inside a `private` method, leading to significantly more accurate "Scope" detection in Conventional Commits.

### 2. Intent-Based Metadata (The "Signal" Lesson)
The old system tried to summarize code into human sentences like "updated logic." This was a "Lossy Compression" that robbed the LLM of its reasoning power.
* **The Insight:** Use Python to identify **Signals** (is this a test file? is it a config change? did a keyword like 'delete' appear?) rather than **Conclusions**.
* **System Impact:** Your `schema_builder` now sends "Hints" and "Tags." This acts as a "Heads-Up Display" for the LLM, pointing its "eyes" toward specific parts of the diff without telling it what to think.

### 3. The "Trust but Verify" Loop (The "Confidence" Lesson)
One of the biggest breakthroughs here is the **Confidence Score**. It manages the relationship between your heuristic script and the generative AI.
* **The Insight:** Heuristics (Regex) are fast but dumb. LLMs are slow but smart. By tagging a hint as `low confidence`, you are effectively "deputizing" the LLM to take over the heavy lifting.
* **System Impact:** This prevents **Hallucination Cascades**. When the script is unsure, the prompt now explicitly tells the LLM to ignore the hint and perform a deep semantic analysis of the diff.

### 4. Breaking Change Heuristics
You learned that "Breaking Changes" are a high-stakes detection problem that requires a multi-layered approach.
* **The Insight:** You don't need a perfect parser to detect breaking changes; you need a **Sensitive Alarm**. Even a simple keyword match for `remove` + `api` is enough to trigger a "High Alert" in the prompt.
* **System Impact:** The LLM is now the "Final Auditor." The script flags the possibility, and the LLM confirms it. This is why we added the `!` rule to the prompt—it's the visible output of that verified audit.

### 5. Prompt Engineering as "Role Definition"
We refactored `prompt.py` to move away from a simple "Write this" instruction to a "Expert Persona" definition.
* **The Insight:** An LLM performs better when it understands the **Hierarchy of Truth**.
* **System Impact:** We clearly defined the data priority:
    1.  **Raw Diff** (The Ground Truth)
    2.  **User Preferences** (The Constraint)
    3.  **Heuristic Hints** (The Suggestion)

---

## Comparison: Before vs. After Optimization

| Feature | Old System (Translator) | New System (Curator) |
| :--- | :--- | :--- |
| **Data Format** | Flat lists of lines | Structured Hunks with context |
| **Logic** | Script tries to write the summary | Script flags "Signals" for the LLM |
| **Reliability** | Assumes script is always right | Explicitly flags "Low Confidence" areas |
| **Commit Type** | Keyword matching on summaries | Heuristic suggestion + LLM verification |
| **Breaking Changes** | Ignored or missed | Flagged for manual LLM audit |

---

## Future Considerations

1. **Breaking Change Detection**: Could be improved by analyzing function signatures (parameters, return types) across versions, not just removal.
2. **Language-Specific Analysis**: Currently only Python has special handling. Could add JavaScript/TypeScript, Go, etc.
3. **Token Budget**: The larger prompt + larger responses increase API costs. Consider making `max_tokens` configurable.
4. **Confidence Calibration**: Could add a "medium" confidence level for cases between high and low.
5. **Signal Deduplication**: Currently signals can have duplicates (e.g., both `function_addition` and `add_export` for the same function). Could merge related signals.
