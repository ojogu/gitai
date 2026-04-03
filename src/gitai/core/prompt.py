# prompt.py
#
# This module constructs prompts for LLM-based commit message generation.
# It builds both system and user prompts, incorporating schema data, user
# preferences, and dynamic context cues to guide the LLM's output.

import json


# ============================================================
# SYSTEM PROMPT BUILDER
# Defines the AI's role and behavioral guidelines
# ============================================================

def build_system_prompt():
    """
    Build the system prompt that defines the LLM's role and behavior.
    
    This prompt establishes the AI as an expert software engineer focused on
    writing clear, meaningful commit messages. It provides guidelines for:
    - How to interpret the input data (changes, hints, metadata)
    - How to handle heuristic hints (as suggestions, not rules)
    - Output format and style expectations
    
    Returns:
        str: The complete system prompt text to be sent with every LLM request
    """
    return """You are an expert software engineer writing clear, concise Git commit messages.

You will receive:
- Changed files with semantic summaries, structured signals, and raw unified diff
- Aggregate metadata (files changed, insertions, deletions)
- Heuristic hints (suggested type, scope, breaking change signal, confidence)

**Critical: The Raw Diff is your source of truth.**
- Hints are weak signals — treat as suggestions, not ground truth.
- If confidence is "low," analyze the diff to determine true intent.
- Validate hints against the diff: if hint suggests 'feat' but diff shows bug fix, use 'fix'.

Focus:
- Identify the "Why" — why were these changes made?
- Summarize intent, not line-by-line description.
- Use surrounding code context to understand scope.

Output rules:
- Use present tense.
- Be specific and direct.
- Output ONLY the commit message."""


# ============================================================
# DYNAMIC CONTEXT BUILDER
# Adds conditional guidance based on change characteristics
# ============================================================

def build_addons(schema: dict) -> str:
    """
    Generate dynamic context notes based on schema signals.
    
    This function examines the schema for specific conditions (large changesets,
    breaking change signals, low confidence hints, etc.) and adds contextual
    notes to guide the LLM's analysis.
    
    Args:
        schema (dict): The structured schema containing:
            - meta: Metadata like files_changed count
            - hints: Heuristic hints including confidence, suggested_type,
              and breaking_change_signal
    
    Returns:
        str: Newline-separated context notes to append to the prompt.
    """
    addons = []

    meta = schema.get("meta", {})
    hints = schema.get("hints", {})

    files_changed = meta.get("files_changed", 0)
    confidence = hints.get("confidence", "high")
    suggested_type = hints.get("suggested_type")
    breaking_signal = hints.get("breaking_change_signal", False)

    if files_changed > 5:
        addons.append(
            "Note: This is a large changeset across multiple files. Identify the single dominant "
            "architectural intent that ties these changes together."
        )

    if breaking_signal:
        addons.append(
            "Critical: Potential breaking change detected. Verify if public APIs or interfaces were altered."
        )

    if confidence == "low":
        addons.append(
            "Warning: The suggested type is a guess. Analyze the diff logic to determine the true intent."
        )

    if suggested_type == "test":
        addons.append(
            "Note: These changes appear to be validation-focused. If they only affect tests, "
            "ensure the type is 'test'."
        )

    if suggested_type == "refactor":
        addons.append(
            "Note: This appears to be a refactor. Confirm there are no functional changes "
            "or new features introduced before using the 'refactor' type."
        )

    return "\n".join(addons)


# ============================================================
# USER PROMPT BUILDER
# Constructs the main prompt with schema data and user preferences
# ============================================================

def build_user_prompt(schema: dict, config: dict) -> str:
    """
    Build the user prompt that sends change data to the LLM.
    
    Args:
        schema (dict): Structured change data from schema_builder
        config (dict): User configuration options (style, max_title_length, etc.)
    
    Returns:
        str: The complete user prompt text.
    """
    # Serialize schema to JSON.
    schema_json = json.dumps(schema, indent=2)

    base_prompt = ""

    # Build format-specific instructions based on style preference
    if config.get("style") == "conventional":
        max_title = config.get("max_title_length", 72)
        base_prompt = f"""Generate a Conventional Commit message.

Rules:
- Format: <type>(<scope>): <short description>
- Title: Maximum {max_title} characters.
- Intent: Explain the change in behavior, not the code.
- Types: feat, fix, refactor, test, docs, chore, style, ci, perf.
"""

        if config.get("include_body", True):
            base_prompt += """
Body (concise):
- 2-3 bullet points maximum for non-trivial changes.
- Each bullet: one sentence, max 15 words.
- Explain "Why" and side effects.
"""

        base_prompt += """
Breaking Changes:
- If confirmed from diff, append '!' to type.
- Example: feat!(auth): remove legacy login endpoint
"""

    else:
        base_prompt = """Generate a clear, concise git commit message.

Rules:
- Focus on primary intent.
- Avoid implementation details.
- Keep title punchy and informative.
"""

    # Gather dynamic context notes and custom instructions
    addons = build_addons(schema)
    custom = config.get("custom_instructions", "")

    # Assemble the final prompt
    final_prompt = f"""{base_prompt}

### INPUT DATA:
{schema_json}
"""

    if addons:
        final_prompt += f"\n### DYNAMIC GUIDANCE:\n{addons}\n"

    if custom:
        final_prompt += f"\n### USER PREFERENCES:\n{custom}\n"

    return final_prompt.strip()