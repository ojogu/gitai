import json
import os
import subprocess
import sys
from typing import Optional

from gitai.core.parser import parse_git_diff
from gitai.core.extractor import extract_summary
from gitai.core.schema_builder import build_schema
from gitai.core.llm import get_llm_report
from gitai.utils.config import load_config
from gitai.utils.log import setup_logger, sanitize_for_logging
from gitai.utils.exceptions import (
    GitAIError, GitError, ConfigurationError, 
    LLMError, ParseError, NetworkError,
    APIAuthenticationError, RateLimitError
)

logger = setup_logger(__name__, "cli.log")


def get_staged_diff() -> str:
    """
    Get the git diff of staged changes.
    
    Returns:
        str: The git diff output
        
    Raises:
        GitError: If not in a git repository or git command fails
    """
    try:
        # Check if we're in a git repository
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            raise GitError(
                "Not a git repository",
                details={"error": result.stderr.strip()},
                suggestion="Initialize a git repository with `git init` or navigate to a git project."
            )
        
        # Get staged diff
        result = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            raise GitError(
                "Failed to get staged changes",
                details={"error": result.stderr.strip()},
                suggestion="Make sure you have staged changes with `git add .`"
            )
        
        return result.stdout
        
    except subprocess.TimeoutExpired:
        raise GitError(
            "Git command timed out",
            suggestion="The repository may be too large. Try staging fewer files."
        )
    except FileNotFoundError:
        raise GitError(
            "Git is not installed or not in PATH",
            suggestion="Install git from https://git-scm.com/"
        )
    except Exception as e:
        if isinstance(e, GitError):
            raise
        raise GitError(
            f"Unexpected error while getting git diff: {str(e)}",
            details={"exception_type": type(e).__name__}
        )


def confirm(prompt: str = "Proceed? (y/n): ") -> bool:
    """
    Ask user for confirmation.
    
    Args:
        prompt: The prompt to display
        
    Returns:
        bool: True if user confirms, False otherwise
    """
    try:
        response = input(prompt).lower().strip()
        return response == "y" or response == "yes"
    except (EOFError, KeyboardInterrupt):
        print("\n\n👋 Operation cancelled by user.")
        return False


def handle_gitai_error(error: GitAIError) -> None:
    """
    Handle a GitAIError with user-friendly output.
    
    Args:
        error: The GitAIError to handle
    """
    logger.error(f"Error: {error.message}", extra={"error_details": error.to_dict()})
    
    # Display error to user
    print(f"\n❌ {error.message}")
    
    if error.details:
        # Log details but don't expose them to user unless debugging
        logger.debug(f"Error details: {sanitize_for_logging(error.details)}")
    
    if error.suggestion:
        print(f"💡 {error.suggestion}")


def commit_changes(message: str) -> bool:
    """
    Commit changes with the given message.
    
    Args:
        message: The commit message
        
    Returns:
        bool: True if commit was successful
    """
    try:
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.error(f"Commit failed: {result.stderr}")
            print(f"❌ Failed to create commit: {result.stderr.strip()}")
            return False
        
        print("✅ Commit created successfully!")
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Commit timed out")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during commit: {str(e)}")
        print(f"❌ Unexpected error during commit: {str(e)}")
        return False


def main() -> None:
    """Main entry point for the CLI."""
    print("🔍 Generating commit message...\n")
    
    try:
        # Load configuration
        try:
            config = load_config()
        except ConfigurationError as e:
            handle_gitai_error(e)
            return
        except Exception as e:
            logger.error(f"Failed to load config: {str(e)}")
            print("❌ Failed to load configuration.")
            return
        
        # Get staged diff
        try:
            diff_text = get_staged_diff()
        except GitError as e:
            handle_gitai_error(e)
            return
        
        if not diff_text.strip():
            print("❌ No staged changes found. Use `git add .` first.")
            return
        
        logger.info(f"Found staged changes ({len(diff_text)} characters)")
        
        # Parse diff
        try:
            parsed_files = parse_git_diff(diff_text)
        except ParseError as e:
            handle_gitai_error(e)
            return
        except Exception as e:
            logger.error(f"Failed to parse diff: {str(e)}")
            print("❌ Failed to parse git diff.")
            return
        
        if not parsed_files:
            print("❌ No file changes detected in the diff.")
            return
        
        logger.info(f"Parsed {len(parsed_files)} file(s)")
        
        # Extract summaries
        try:
            file_summaries = [extract_summary(f) for f in parsed_files]
        except Exception as e:
            logger.error(f"Failed to extract summaries: {str(e)}")
            print("❌ Failed to extract change summaries.")
            return
        
        # Build schema
        try:
            schema = build_schema(file_summaries, parsed_files)
            logger.debug(f"Built schema: {sanitize_for_logging(schema)}")
        except Exception as e:
            logger.error(f"Failed to build schema: {str(e)}")
            print("❌ Failed to build change schema.")
            return
        
        # Get LLM report
        result: Optional[dict] = None
        message: Optional[str] = None
        
        max_retries = config.get("retry", 3)
        commit_messages = []
        
        for attempt in range(max_retries):
            try:
                if attempt == 0:
                    # First attempt - need to generate initial message
                    try:
                        result = get_llm_report(schema, config)
                    except LLMError as e:
                        handle_gitai_error(e)
                        return
                    except Exception as e:
                        logger.error(f"LLM call failed (attempt {attempt + 1}): {str(e)}")
                        if attempt < max_retries - 1:
                            print(f"⚠️ LLM call failed, will retry...")
                            continue
                        else:
                            print("❌ Failed to generate commit message after all retries.")
                            return
                    
                    message = result.get("message", "").strip()
                else:
                    # Retry
                    print(f"\n🔄 Retry {attempt}/{max_retries - 1}")
                    try:
                        result = get_llm_report(schema, config)
                    except LLMError as e:
                        handle_gitai_error(e)
                        return
                    except Exception as e:
                        logger.error(f"LLM call failed (attempt {attempt + 1}): {str(e)}")
                        if attempt < max_retries - 1:
                            print(f"⚠️ LLM call failed, will retry...")
                            continue
                        else:
                            print("❌ Failed to generate commit message after all retries.")
                            return
                    
                    message = result.get("message", "").strip()
                
                if not message:
                    print("⚠️ Generated empty message, will retry...")
                    continue
                
                commit_messages.append(message)
                
                if attempt > 0:
                    print("✨ Suggested Commit Message:\n")
                    print(message)
                    print("\n" + "-" * 50)
                
            except Exception as e:
                logger.error(f"Unexpected error during LLM call (attempt {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    print(f"⚠️ Unexpected error, will retry...")
                    continue
                else:
                    print("❌ Failed to generate commit message after all retries.")
                    return
        
        if not commit_messages:
            print("❌ Failed to generate any commit message.")
            return
        
        # Use the last generated message for confirmation
        message = commit_messages[-1]
        
        # Auto commit or confirm
        if config.get("auto_commit"):
            if commit_changes(message):
                return
            # If auto-commit fails, fall through to manual confirmation
            print("⚠️ Auto-commit failed, falling back to manual confirmation.")
        
        # Ask user for confirmation
        if confirm("👉 Use this commit message? (y/n): "):
            if commit_changes(message):
                return
        
        # If user declined and we have multiple messages, let them choose
        if len(commit_messages) > 1:
            print("\n📋 Available commit messages from all attempts:")
            for i, msg in enumerate(commit_messages, 1):
                print(f"\n{i}. {msg}")
            print(f"\n0. Exit without committing")
            
            while True:
                try:
                    choice = input("\n👉 Choose a commit message (0-{0}): ".format(len(commit_messages))).strip()
                    if choice == "0":
                        print("❌ Commit cancelled.")
                        return
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(commit_messages):
                        selected_message = commit_messages[choice_num - 1]
                        if commit_changes(selected_message):
                            return
                    else:
                        print(f"⚠️ Please enter a number between 0 and {len(commit_messages)}")
                except ValueError:
                    print("⚠️ Please enter a valid number")
                except (EOFError, KeyboardInterrupt):
                    print("\n\n👋 Operation cancelled by user.")
                    return
        else:
            print("❌ Maximum retries reached. Commit cancelled.")
            
    except KeyboardInterrupt:
        print("\n\n👋 Operation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception("Unexpected error in main():")
        print(f"\n❌ An unexpected error occurred: {str(e)}")
        print("💡 Please check the logs for more details.")
        sys.exit(1)