# exceptions.py
#
# This module defines custom exception classes for the gitAI application.
# These exceptions provide consistent error handling with user-friendly messages
# and detailed context for debugging.


class GitAIError(Exception):
    """
    Base exception for all gitAI-specific errors.
    
    All custom exceptions inherit from this base class to allow
    centralized error handling.
    """
    
    def __init__(self, message: str, details: dict = None, suggestion: str = None):
        self.message = message
        self.details = details or {}
        self.suggestion = suggestion
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Convert exception to a dictionary for logging."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "suggestion": self.suggestion
        }


class ConfigurationError(GitAIError):
    """
    Raised when there's an issue with configuration.
    
    Examples:
        - Missing required configuration values
        - Invalid configuration format
        - Configuration file not found
    """
    
    def __init__(self, message: str, details: dict = None, suggestion: str = None):
        default_suggestion = "Check your config.json and .env files for required settings."
        super().__init__(message, details, suggestion or default_suggestion)


class GitError(GitAIError):
    """
    Raised when git operations fail.
    
    Examples:
        - Not in a git repository
        - No staged changes
        - Git command execution failure
    """
    
    def __init__(self, message: str, details: dict = None, suggestion: str = None):
        default_suggestion = "Make sure you're in a git repository and have staged changes with `git add .`"
        super().__init__(message, details, suggestion or default_suggestion)


class LLMError(GitAIError):
    """
    Raised when LLM API operations fail.
    
    Examples:
        - API authentication failure
        - Network connectivity issues
        - Invalid API response
        - Rate limiting
    """
    
    def __init__(self, message: str, details: dict = None, suggestion: str = None):
        default_suggestion = "Check your API key and network connection. Verify LLM_MODEL and AI_KEY are set correctly."
        super().__init__(message, details, suggestion or default_suggestion)


class ValidationError(GitAIError):
    """
    Raised when input validation fails.
    
    Examples:
        - Invalid input format
        - Missing required fields
        - Data type mismatches
    """
    
    def __init__(self, message: str, details: dict = None, suggestion: str = None):
        default_suggestion = "Please check your input and try again."
        super().__init__(message, details, suggestion or default_suggestion)


class ParseError(GitAIError):
    """
    Raised when parsing git diff or other data fails.
    
    Examples:
        - Malformed diff output
        - Unexpected data format
        - Missing expected fields
    """
    
    def __init__(self, message: str, details: dict = None, suggestion: str = None):
        default_suggestion = "The diff output may be malformed. Try staging changes again."
        super().__init__(message, details, suggestion or default_suggestion)


class FileNotFoundError(GitAIError):
    """
    Raised when a required file is not found.
    
    Examples:
        - Config file missing
        - Required source file not found
    """
    
    def __init__(self, message: str, details: dict = None, suggestion: str = None):
        default_suggestion = "Make sure the file exists and you have read permissions."
        super().__init__(message, details, suggestion or default_suggestion)


class APIAuthenticationError(LLMError):
    """
    Raised when API authentication fails.
    
    This is a specific type of LLMError for authentication issues.
    """
    
    def __init__(self, message: str, details: dict = None, suggestion: str = None):
        default_suggestion = "Your API key may be invalid or expired. Check your .env file and verify your API key is correct."
        super().__init__(message, details, suggestion or default_suggestion)


class NetworkError(LLMError):
    """
    Raised when network connectivity issues occur.
    
    This is a specific type of LLMError for network problems.
    """
    
    def __init__(self, message: str, details: dict = None, suggestion: str = None):
        default_suggestion = "Check your internet connection and try again."
        super().__init__(message, details, suggestion or default_suggestion)


class RateLimitError(LLMError):
    """
    Raised when API rate limits are exceeded.
    
    This is a specific type of LLMError for rate limiting.
    """
    
    def __init__(self, message: str, details: dict = None, suggestion: str = None):
        default_suggestion = "You've exceeded the API rate limit. Please wait a moment and try again."
        super().__init__(message, details, suggestion or default_suggestion)