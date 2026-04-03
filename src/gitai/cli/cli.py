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


def confirm(prompt: str = "👉 Use this commit message? (y/n): ") -> bool:
    """
    Ask user for confirmation with proper input validation.
    
    Args:
        prompt: The prompt to display
        
    Returns:
        bool: True if user confirms (y/yes), False if user declines (n/no)
    """
    while True:
        try:
            response = input(prompt).lower().strip()
            
            # Accept y/yes for confirmation
            if response in ("y", "yes"):
                return True
            
            # Accept n/no for rejection
            if response in ("n", "no"):
                return False
            
            # Invalid input - re-prompt with guidance
            print("⚠️  Invalid input. Please enter 'y' or 'yes' to confirm, or 'n' or 'no' to decline.")
            
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


def push_changes() -> bool:
    """
    Push committed changes to remote repository.
    
    Returns:
        bool: True if push was successful
    """
    try:
        # First, check if a remote is configured
        result = subprocess.run(
            ["git", "remote", "-v"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0 or not result.stdout.strip():
            print("❌ No remote repository configured.")
            print("💡 Add a remote with: git remote add origin <url>")
            return False
        
        # Get current branch name
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print("❌ Failed to determine current branch.")
            return False
        
        branch = result.stdout.strip()
        
        # Attempt to push
        print(f"🔄 Pushing to remote (branch: {branch})...")
        result = subprocess.run(
            ["git", "push", "origin", branch],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            print(f"❌ Push failed: {error_msg}")
            
            # Provide helpful suggestions based on error
            if "couldn't find remote ref" in error_msg.lower() or "does not appear to be a git repository" in error_msg.lower():
                print("💡 Make sure the remote repository exists and you have push access.")
                print("💡 You may need to set the upstream: git push --set-upstream origin " + branch)
            elif "authentication failed" in error_msg.lower() or "permission denied" in error_msg.lower():
                print("💡 Authentication failed. Check your SSH keys or credentials.")
            elif "connection timed out" in error_msg.lower() or "could not resolve host" in error_msg.lower():
                print("💡 Network error. Check your internet connection and remote URL.")
            
            return False
        
        print("✅ Push successful!")
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Push timed out")
        return False
    except FileNotFoundError:
        print("❌ Git is not installed or not in PATH")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during push: {str(e)}")
        print(f"❌ Unexpected error during push: {str(e)}")
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
        
        # Get LLM report with proper retry and confirmation flow
        result: Optional[dict] = None
        message: Optional[str] = None
        commit_messages = []
        max_retries = config.get("retry", 3)
        
        for attempt in range(max_retries):
            try:
                # Show retry indicator only for actual retries (attempt > 0)
                if attempt > 0:
                    print(f"\n🔄 Retry {attempt}/{max_retries - 1}")
                
                # Call LLM API
                try:
                    result = get_llm_report(schema, config)
                except LLMError as e:
                    # Custom exception - handle with our error handler
                    handle_gitai_error(e)
                    # If it's a rate limit or network error, we might want to retry
                    if attempt < max_retries - 1:
                        print(f"⚠️  Will retry...")
                        continue
                    else:
                        return
                except Exception as e:
                    logger.error(f"LLM call failed (attempt {attempt + 1}): {str(e)}")
                    if attempt < max_retries - 1:
                        print(f"⚠️  LLM call failed, will retry...")
                        continue
                    else:
                        print("❌ Failed to generate commit message after all retries.")
                        return
                
                # Extract and validate message
                message = result.get("message", "").strip()
                
                if not message:
                    print("⚠️  Generated empty message, will retry...")
                    continue
                
                # Store successful message
                commit_messages.append(message)
                
                # Show the generated message to user
                print("\n✨ Suggested Commit Message:\n")
                print(message)
                print("\n" + "-" * 50)
                
                # Auto commit or ask for confirmation
                if config.get("auto_commit"):
                    if commit_changes(message):
                        # Auto push if enabled
                        if config.get("auto_push"):
                            push_changes()
                        return
                    # If auto-commit fails, fall through to manual confirmation
                    print("⚠️  Auto-commit failed, falling back to manual confirmation.")
                
                # Ask user for confirmation
                if confirm():
                    if commit_changes(message):
                        # Auto push if enabled
                        if config.get("auto_push"):
                            push_changes()
                        return
                
                # User declined - ask if they want to try again
                if attempt < max_retries - 1:
                    print("\n💡 You can retry to generate a different commit message.")
                    if not confirm("👉 Generate a new commit message? (y/n): "):
                        # User doesn't want to retry
                        break
                else:
                    # No more retries available
                    print("\n❌ Maximum retries reached.")
                    break
                    
            except Exception as e:
                logger.error(f"Unexpected error during LLM call (attempt {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    print(f"⚠️  Unexpected error, will retry...")
                    continue
                else:
                    print("❌ Failed to generate commit message after all retries.")
                    return
        
        # If we have commit messages but user declined all, offer to choose from previous attempts
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
                            # Auto push if enabled
                            if config.get("auto_push"):
                                push_changes()
                            return
                    else:
                        print(f"⚠️  Please enter a number between 0 and {len(commit_messages)}")
                except ValueError:
                    print("⚠️  Please enter a valid number")
                except (EOFError, KeyboardInterrupt):
                    print("\n\n👋 Operation cancelled by user.")
                    return
        elif len(commit_messages) == 1:
            # Only one message was generated and user declined
            print("❌ Commit cancelled.")
        else:
            # No messages were generated
            print("❌ Failed to generate any commit message.")
            
    except KeyboardInterrupt:
        print("\n\n👋 Operation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception("Unexpected error in main():")
        print(f"\n❌ An unexpected error occurred: {str(e)}")
        print("💡 Please check the logs for more details.")
        sys.exit(1)