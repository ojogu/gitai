# Logging and Error Handling Guide

## Overview

The gitAI application now includes comprehensive logging and error handling to ensure a better developer experience while maintaining security by preventing sensitive information leakage.

## Key Features

### 1. Secure Logging System

- **Automatic Sanitization**: All logs are automatically scanned for sensitive data (API keys, passwords, tokens, emails, etc.) and redacted
- **SafeLogger**: A wrapper around Python's logging.Logger that sanitizes all output
- **Pattern-Based Detection**: Uses regex patterns to detect various formats of sensitive information
- **Dictionary Sanitization**: Automatically redacts values for sensitive keys

### 2. Custom Exception Hierarchy

All exceptions inherit from `GitAIError` for consistent error handling:

```
GitAIError (base)
├── ConfigurationError - Config file issues
├── GitError - Git operation failures
├── LLMError - LLM API issues
│   ├── APIAuthenticationError - Auth failures
│   ├── NetworkError - Connection issues
│   └── RateLimitError - Rate limiting
├── ValidationError - Input validation failures
├── ParseError - Diff parsing failures
└── FileNotFoundError - Missing files
```

### 3. Centralized Error Handling

- User-friendly error messages with actionable suggestions
- Detailed error context for debugging (logged, not shown to users)
- Consistent error formatting across the application

## Usage Examples

### Using the SafeLogger

```python
from gitai.utils.log import setup_logger

# Create a logger (automatically sanitizes output)
logger = setup_logger(__name__, "app.log")

# All of these will be automatically sanitized
logger.info("User password is secret123")  # Logs: "User [REDACTED]"
logger.debug(f"API key: {api_key}")  # Logs: "API key: [REDACTED]"
```

### Raising Custom Exceptions

```python
from gitai.utils.exceptions import ConfigurationError, GitError

# Raise with context and suggestion
raise ConfigurationError(
    "Config file not found",
    details={"path": "config.json"},
    suggestion="Create a config.json file in the project root."
)

# Catch all gitAI errors
try:
    # ... some operation
except GitAIError as e:
    print(f"Error: {e.message}")
    print(f"Suggestion: {e.suggestion}")
```

### Sanitizing Data for Logging

```python
from gitai.utils.log import sanitize_for_logging

sensitive_data = {
    "api_key": "sk-1234567890abcdefghijklmnopqrstuvwxyz",
    "username": "john_doe"
}

safe_data = sanitize_for_logging(sensitive_data)
# Result: {"api_key": "[REDACTED]", "username": "john_doe"}
```

## Sensitive Data Patterns

The system detects and redacts:

- **API Keys**: Various formats including `api_key = "value"`, `api_key is value`
- **Tokens**: Auth tokens, access tokens, bearer tokens
- **Passwords**: Any format containing password/passwd/pwd
- **Email Addresses**: Standard email format
- **Private Keys**: RSA, OpenSSH private key headers
- **Credit Cards**: Basic credit card number patterns
- **SSN**: Social Security Number patterns
- **IP Addresses**: IPv4 addresses
- **Common API Key Prefixes**: Stripe (`sk_live_`), AWS (`AKIA`), GitHub (`ghp_`)

## Configuration

### Log Levels

Set the logging level when creating a logger:

```python
import logging

# Debug level (most verbose)
logger = setup_logger(__name__, "app.log", level=logging.DEBUG)

# Info level (production recommended)
logger = setup_logger(__name__, "app.log", level=logging.INFO)

# Warning level (errors only)
logger = setup_logger(__name__, "app.log", level=logging.WARNING)
```

### File vs Console Logging

Control where logs are written:

```python
# File only (no console)
logger = setup_logger(__name__, "app.log", enable_console_logging=False)

# Console only (no file)
logger = setup_logger(__name__, "app.log", enable_file_logging=False)

# Both (default)
logger = setup_logger(__name__, "app.log")
```

## Testing

Run the test suite to verify error handling and logging:

```bash
python src/test/test_error_handling.py
```

This tests:
- Secure logging and sanitization
- Custom exception classes
- SafeLogger functionality
- Exception inheritance

## Best Practices

1. **Always use SafeLogger**: Never use raw Python logging in gitAI code
2. **Provide context in exceptions**: Include details and suggestions
3. **Catch specific exceptions**: Catch the most specific exception type first
4. **Log at appropriate levels**: DEBUG for development, INFO for production
5. **Never log sensitive data directly**: Even with sanitization, avoid logging sensitive info
6. **Use sanitization for debug output**: When printing data structures, use `sanitize_for_logging()`

## Architecture

### Module Structure

```
src/gitai/utils/
├── __init__.py          # Exports all utilities
├── log.py              # Logging with sanitization
├── exceptions.py       # Custom exception classes
└── config.py           # Configuration loading
```

### Log Files

Logs are stored in the `logs/` directory:

- `cli.log` - CLI operations
- `parse.log` - Diff parsing
- `app.log` - Configuration and general app events
- `test.log` - Legacy test logs

## Security Considerations

1. **No sensitive data in logs**: All logs are automatically sanitized
2. **Disabled verbose LLM logging**: Prevents API keys from being logged by litellm
3. **Sanitized error details**: Error details are logged but not exposed to users
4. **Safe exception messages**: Exception messages don't include sensitive values

## Migration Guide

If you have existing code that uses standard logging:

### Before
```python
import logging
logger = logging.getLogger(__name__)
logger.info(f"User data: {user_data}")  # May leak sensitive info
```

### After
```python
from gitai.utils.log import setup_logger
logger = setup_logger(__name__, "app.log")
logger.info(f"User data: {user_data}")  # Automatically sanitized
```

## Troubleshooting

### Logs still contain sensitive data

If you find sensitive data in logs:

1. Check that you're using `setup_logger()` not raw `logging.getLogger()`
2. Verify the sensitive pattern matches your data format
3. Add additional patterns to `SENSITIVE_PATTERNS` in `log.py`
4. Use `sanitize_for_logging()` explicitly for complex data structures

### Exceptions not being caught

Make sure you're catching the right exception type:

```python
# Catch specific exception
try:
    # ...
except ConfigurationError as e:
    handle_config_error(e)

# Catch all gitAI errors
try:
    # ...
except GitAIError as e:
    handle_gitai_error(e)
```

## Contributing

When adding new logging or error handling:

1. Use the existing exception hierarchy
2. Add new exception types only if needed
3. Test that sensitive data is properly sanitized
4. Follow the existing patterns in the codebase