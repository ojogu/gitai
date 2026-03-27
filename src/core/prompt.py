# prompt_builder.py
import json


def build_system_prompt():
    return """You are an expert software engineer.

You write clear, concise, and meaningful Git commit messages based on structured code changes.

You will receive:
- A list of changed files, each with a semantic summary and the raw unified diff
- Aggregate metadata (files changed, insertions, deletions)
- Heuristic hints (suggested type, scope, breaking change signal)

How to use the hints:
- Hints are weak signals derived from keyword matching — treat them as a starting point, not ground truth
- Validate each hint against the actual diff and summaries before using it
- Override any hint that conflicts with what you observe in the changes
- "breaking_change_signal: true" means a heuristic detected a possible breaking change — confirm it yourself

Your focus:
- Understand developer intent from the actual changes
- Summarize at a high level — what changed and why, not how
- Avoid low-level implementation details

Output rules:
- Use present tense
- Be specific and direct
- Do not explain the commit message
- Output only the commit message
"""


def build_addons(schema: dict) -> str:
    # Dynamic context injected based on schema signals.
    # These are soft guidance cues, not strict rules.
    addons = []

    meta = schema.get("meta", {})
    hints = schema.get("hints", {})

    files_changed = meta.get("files_changed", 0)
    confidence = hints.get("confidence", "high")
    suggested_type = hints.get("suggested_type")
    breaking_signal = hints.get("breaking_change_signal", False)

    if files_changed > 5:
        addons.append(
            "Note: This is a large changeset. Focus on the dominant intent across all files."
        )

    if breaking_signal:
        addons.append(
            "Note: A heuristic flagged a possible breaking change. "
            "Inspect the diff carefully — confirm before marking it breaking."
        )

    if confidence == "low":
        addons.append(
            "Note: Hint confidence is low — the suggested type and scope are weak guesses. "
            "Derive the correct type from the diff directly."
        )

    if suggested_type == "test":
        addons.append(
            "Note: Changes appear to be test-related. Confirm against the diff."
        )

    if suggested_type == "refactor":
        addons.append(
            "Note: Changes may be a refactor with no behavior change. Confirm against the diff."
        )

    return "\n".join(addons)


def build_user_prompt(schema: dict, config: dict) -> str:
    schema_json = json.dumps(schema, indent=2)

    base_prompt = ""

    if config.get("style") == "conventional":
        max_title = config.get("max_title_length", 72)
        base_prompt = f"""Generate a git commit message from the structured changes below.

Rules:
- Format: <type>(<scope>): <message>
- Title must be under {max_title} characters
- Validate the suggested type and scope from hints against the actual diff — correct them if wrong
- Focus on WHAT changed and WHY, not implementation details
- Keep it concise but meaningful
"""

        if config.get("include_body", True):
            base_prompt += """
Optional body:
- Include 1–3 bullet points if the change is non-trivial or affects multiple concerns
- Each bullet should add information not already clear from the title
"""

        base_prompt += """
Special cases:
- If you confirm a breaking change from the diff, add "!" after the type: e.g. feat!(...):
- Do not mark breaking based on the hint alone — verify it
- If multiple significant changes exist, prioritize the one with the highest impact
"""

    else:
        base_prompt = """Generate a concise and meaningful git commit message.

Rules:
- Do NOT use conventional commit prefixes (feat:, fix:, etc.)
- Keep it short and clear
- Focus on intent, not implementation details
"""

    addons = build_addons(schema)
    custom = config.get("custom_instructions", "")

    final_prompt = f"""{base_prompt}
Structured changes:
{schema_json}
"""

    if addons:
        final_prompt += f"\n{addons}\n"

    if custom:
        final_prompt += f"\nAdditional instructions:\n{custom}\n"

    return final_prompt.strip()