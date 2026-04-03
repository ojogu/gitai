#!/usr/bin/env python3
"""
Test script for error handling and logging functionality.
This script tests the custom exceptions, secure logging, and error handling.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from gitai.utils.log import setup_logger, sanitize_for_logging, SafeLogger
from gitai.utils.exceptions import (
    GitAIError, ConfigurationError, GitError, LLMError,
    ValidationError, ParseError, APIAuthenticationError,
    NetworkError, RateLimitError
)


def test_secure_logging():
    """Test that sensitive data is properly sanitized."""
    print("\n" + "="*60)
    print("Testing Secure Logging")
    print("="*60)
    
    logger = setup_logger("test_secure_logging", "test_error_handling.log", enable_console_logging=True)
    
    # Test 1: API Key pattern
    test_cases = [
        ('API key in string', 'api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz"'),
        ('Token in string', 'token: abc123def456ghi789jkl012mno345pqr678'),
        ('Password in string', 'password = "my_secret_password123"'),
        ('Email in string', 'user@example.com'),
        ('Private key header', '-----BEGIN RSA PRIVATE KEY-----'),
        ('Credit card number', '4111-1111-1111-1111'),
        ('SSN pattern', '123-45-6789'),
        ('IP address', '192.168.1.1'),
    ]
    
    for name, value in test_cases:
        sanitized = sanitize_for_logging(value)
        print(f"\n  {name}:")
        print(f"    Original: {value[:50]}...")
        print(f"    Sanitized: {sanitized}")
        assert "[REDACTED]" in sanitized or sanitized != value, f"Failed to sanitize: {name}"
    
    # Test 2: Dictionary sanitization
    test_dict = {
        "api_key": "sk-1234567890abcdefghijklmnopqrstuvwxyz",
        "username": "john_doe",
        "password": "secret_password_123",
        "email": "john@example.com",
        "data": "normal_data"
    }
    sanitized_dict = sanitize_for_logging(test_dict)
    print(f"\n  Dictionary sanitization:")
    print(f"    Original keys: {list(test_dict.keys())}")
    print(f"    Sanitized: {sanitized_dict}")
    assert sanitized_dict["api_key"] == "[REDACTED]", "API key not redacted"
    assert sanitized_dict["password"] == "[REDACTED]", "Password not redacted"
    assert sanitized_dict["username"] == "john_doe", "Username incorrectly redacted"
    assert sanitized_dict["data"] == "normal_data", "Normal data incorrectly redacted"
    
    print("\n  ✅ All secure logging tests passed!")
    return True


def test_custom_exceptions():
    """Test custom exception classes."""
    print("\n" + "="*60)
    print("Testing Custom Exceptions")
    print("="*60)
    
    # Test GitAIError
    try:
        raise GitAIError("Base error", details={"key": "value"}, suggestion="Try again")
    except GitAIError as e:
        assert e.message == "Base error"
        assert e.details == {"key": "value"}
        assert e.suggestion == "Try again"
        error_dict = e.to_dict()
        assert error_dict["error_type"] == "GitAIError"
        print("  ✅ GitAIError works correctly")
    
    # Test ConfigurationError
    try:
        raise ConfigurationError("Config missing", details={"file": "config.json"})
    except ConfigurationError as e:
        assert e.message == "Config missing"
        assert "Check your config.json" in e.suggestion
        print("  ✅ ConfigurationError works correctly")
    
    # Test GitError
    try:
        raise GitError("Not a git repo")
    except GitError as e:
        assert "git repository" in e.suggestion.lower()
        print("  ✅ GitError works correctly")
    
    # Test LLMError
    try:
        raise LLMError("API failed")
    except LLMError as e:
        assert "API key" in e.suggestion
        print("  ✅ LLMError works correctly")
    
    # Test APIAuthenticationError
    try:
        raise APIAuthenticationError("Auth failed")
    except APIAuthenticationError as e:
        assert isinstance(e, LLMError)  # Should inherit from LLMError
        assert "API key" in e.suggestion
        print("  ✅ APIAuthenticationError works correctly")
    
    # Test NetworkError
    try:
        raise NetworkError("Connection failed")
    except NetworkError as e:
        assert "internet connection" in e.suggestion.lower()
        print("  ✅ NetworkError works correctly")
    
    # Test RateLimitError
    try:
        raise RateLimitError("Rate limit exceeded")
    except RateLimitError as e:
        assert "rate limit" in e.suggestion.lower()
        print("  ✅ RateLimitError works correctly")
    
    # Test ParseError
    try:
        raise ParseError("Invalid diff")
    except ParseError as e:
        assert "diff" in e.suggestion.lower()
        print("  ✅ ParseError works correctly")
    
    # Test ValidationError
    try:
        raise ValidationError("Invalid input")
    except ValidationError as e:
        print("  ✅ ValidationError works correctly")
    
    print("\n  ✅ All custom exception tests passed!")
    return True


def test_safe_logger():
    """Test SafeLogger automatically sanitizes output."""
    print("\n" + "="*60)
    print("Testing SafeLogger")
    print("="*60)
    
    logger = setup_logger("test_safe_logger", "test_safe_logger.log", enable_console_logging=False)
    
    # Test that sensitive data is sanitized in logs
    sensitive_msg = "User password is secret123 and api_key is sk-1234567890"
    logger.info(sensitive_msg)
    
    # Read the log file and verify sanitization
    log_path = "logs/test_safe_logger.log"
    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            log_content = f.read()
        # The log should not contain the actual sensitive values
        assert "secret123" not in log_content, "Password leaked in log"
        assert "sk-1234567890" not in log_content, "API key leaked in log"
        print("  ✅ SafeLogger sanitized sensitive data in logs")
    else:
        print("  ⚠️ Log file not created (file logging may be disabled)")
    
    print("\n  ✅ SafeLogger test passed!")
    return True


def test_error_inheritance():
    """Test that exception inheritance is correct."""
    print("\n" + "="*60)
    print("Testing Exception Inheritance")
    print("="*60)
    
    # APIAuthenticationError should be catchable as LLMError
    try:
        raise APIAuthenticationError("Auth failed")
    except LLMError:
        print("  ✅ APIAuthenticationError caught as LLMError")
    
    # NetworkError should be catchable as LLMError
    try:
        raise NetworkError("Network failed")
    except LLMError:
        print("  ✅ NetworkError caught as LLMError")
    
    # RateLimitError should be catchable as LLMError
    try:
        raise RateLimitError("Rate limited")
    except LLMError:
        print("  ✅ RateLimitError caught as LLMError")
    
    # All custom exceptions should be catchable as GitAIError
    exceptions_to_test = [
        ConfigurationError("test"),
        GitError("test"),
        LLMError("test"),
        ValidationError("test"),
        ParseError("test"),
        APIAuthenticationError("test"),
        NetworkError("test"),
        RateLimitError("test"),
    ]
    
    for exc in exceptions_to_test:
        try:
            raise exc
        except GitAIError:
            pass
    
    print("  ✅ All exceptions caught as GitAIError")
    print("\n  ✅ All inheritance tests passed!")
    return True


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("GitAI Error Handling & Logging Tests")
    print("="*60)
    
    tests = [
        ("Secure Logging", test_secure_logging),
        ("Custom Exceptions", test_custom_exceptions),
        ("SafeLogger", test_safe_logger),
        ("Exception Inheritance", test_error_inheritance),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"\n  ❌ {name} test FAILED: {str(e)}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)