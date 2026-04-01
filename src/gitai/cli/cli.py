import json
import os
import subprocess

from gitai.core.parser import parse_git_diff
from gitai.core.extractor import extract_summary
from gitai.core.schema_builder import build_schema
from gitai.core.llm import get_llm_report
from gitai.utils.config import load_config
from gitai.utils.log import setup_logger

logger = setup_logger(__name__, "test") 
def get_staged_diff():
    return os.popen("git diff --cached").read()


def confirm(prompt="Proceed? (y/n): "):
    return input(prompt).lower().strip() == "y"


def main():
    print("🔍 Generating commit message...\n")

    config = load_config()

    diff_text = get_staged_diff()

    if not diff_text.strip():
        print("❌ No staged changes found. Use `git add .` first.")
        return

    # 1. Parse
    parsed_files = parse_git_diff(diff_text)

    # 2. Extract summaries
    file_summaries = [extract_summary(f) for f in parsed_files]

    # 3. Build schema
    schema = build_schema(file_summaries, parsed_files)
    logger.debug(json.dumps(schema, indent=2))

    # 4. LLM prediction
    result = get_llm_report(schema, config)

    message = result.get("message", "").strip()

    if not message:
        print("❌ Failed to generate commit message.")
        return

    print("✨ Suggested Commit Message:\n")
    print(message)
    print("\n" + "-" * 50)

    # 5. Auto commit or confirm
    if config.get("auto_commit"):
        subprocess.run(["git", "commit", "-m", message])
        print("✅ Commit created.")
        return

    if confirm("👉 Use this commit message? (y/n): "):
        subprocess.run(["git", "commit", "-m", message])
        print("✅ Commit created.")
    else:
        print("❌ Commit cancelled.")