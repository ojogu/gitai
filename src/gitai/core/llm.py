import json
import os
import re
import litellm
from dotenv import load_dotenv
from .prompt import build_system_prompt, build_user_prompt

# Enable verbose logging (optional)
litellm.set_verbose = True

load_dotenv()

SYSTEM_PROMPT = build_system_prompt()





def get_llm_report(schema: dict, config: dict) -> dict:
    """
    Send schema to LLM via litellm and return parsed dict.

    Args:
        schema (dict): Structured schema from schema_builder
        config (dict): User config (style, length, etc.)

    Returns:
        dict: Parsed LLM response
    """

    model = os.getenv("LLM_MODEL")
    api_key = os.getenv("AI_KEY")

    if not model:
        raise ValueError("LLM_MODEL not set in environment variables")

    # Build dynamic user prompt (correct usage)
    user_prompt = build_user_prompt(schema, config)

    kwargs = {
        "model": model,
        "api_key":api_key,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 500,
    }

    try:
        response = litellm.completion(**kwargs)
    except Exception as e:
        raise RuntimeError(f"LLM API call failed: {str(e)}")

    raw = response.choices[0].message.content.strip()

    #  Try parsing JSON response
    try:
        result = _extract_json(raw)
    except (json.JSONDecodeError, ValueError):
        #  Fallback: treat as plain text commit message
        result = {
            "message": raw,
            "raw": raw
        }

    return result