#!/usr/bin/env python3
"""
Test script to verify the improved confirm() function and retry logic.
This tests the input validation and user interaction flow.
"""

import sys
import os
from unittest.mock import patch, MagicMock
from io import StringIO

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from gitai.cli.cli import confirm


def test_confirm_accepts_yes_variants():
    """Test that confirm() accepts y/yes variants."""
    print("\n" + "="*60)
    print("Testing confirm() with yes variants")
    print("="*60)
    
    test_cases = [
        ("y", True),
        ("Y", True),
        ("yes", True),
        ("Yes", True),
        ("YES", True),
        ("  y  ", True),  # with whitespace
        ("  yes  ", True),
    ]
    
    for user_input, expected in test_cases:
        with patch('builtins.input', return_value=user_input):
            result = confirm()
            assert result == expected, f"Failed for input '{user_input}': expected {expected}, got {result}"
            print(f"  ✅ Input '{user_input}' -> {result}")
    
    print("  ✅ All yes variant tests passed!")


def test_confirm_accepts_no_variants():
    """Test that confirm() accepts n/no variants."""
    print("\n" + "="*60)
    print("Testing confirm() with no variants")
    print("="*60)
    
    test_cases = [
        ("n", False),
        ("N", False),
        ("no", False),
        ("No", False),
        ("NO", False),
        ("  n  ", False),  # with whitespace
        ("  no  ", False),
    ]
    
    for user_input, expected in test_cases:
        with patch('builtins.input', return_value=user_input):
            result = confirm()
            assert result == expected, f"Failed for input '{user_input}': expected {expected}, got {result}"
            print(f"  ✅ Input '{user_input}' -> {result}")
    
    print("  ✅ All no variant tests passed!")


def test_confirm_rejects_invalid_input():
    """Test that confirm() re-prompts for invalid input."""
    print("\n" + "="*60)
    print("Testing confirm() with invalid inputs")
    print("="*60)
    
    # Simulate user entering invalid inputs first, then a valid one
    test_sequences = [
        (["maybe", "y"], True),
        (["nope", "n"], False),
        (["123", "yes"], True),
        (["", "y"], True),
        (["maybe", "nope", "y"], True),
    ]
    
    for inputs, expected in test_sequences:
        with patch('builtins.input', side_effect=inputs) as mock_input:
            # Capture print output to verify error messages
            captured_output = StringIO()
            with patch('sys.stdout', captured_output):
                result = confirm()
            
            assert result == expected, f"Failed for inputs {inputs}: expected {expected}, got {result}"
            
            # Check that error message was printed for invalid inputs
            output = captured_output.getvalue()
            if len(inputs) > 1:  # Only check if there were invalid inputs
                assert "Invalid input" in output, f"Expected error message for invalid input, got: {output}"
            
            print(f"  ✅ Inputs {inputs} -> {result} (with re-prompting)")
    
    print("  ✅ All invalid input tests passed!")


def test_confirm_handles_keyboard_interrupt():
    """Test that confirm() handles keyboard interrupt gracefully."""
    print("\n" + "="*60)
    print("Testing confirm() with keyboard interrupt")
    print("="*60)
    
    with patch('builtins.input', side_effect=KeyboardInterrupt):
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            result = confirm()
        
        assert result == False, f"Expected False on keyboard interrupt, got {result}"
        output = captured_output.getvalue()
        assert "cancelled by user" in output.lower(), "Expected cancellation message"
        print("  ✅ Keyboard interrupt handled correctly")
    
    print("  ✅ Keyboard interrupt test passed!")


def test_confirm_custom_prompt():
    """Test that confirm() uses custom prompt."""
    print("\n" + "="*60)
    print("Testing confirm() with custom prompt")
    print("="*60)
    
    custom_prompt = "Do you want to continue? (y/n): "
    with patch('builtins.input', return_value="y") as mock_input:
        confirm(prompt=custom_prompt)
        mock_input.assert_called_once_with(custom_prompt)
        print(f"  ✅ Custom prompt '{custom_prompt}' used correctly")
    
    print("  ✅ Custom prompt test passed!")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("GitAI Confirm Function Validation Tests")
    print("="*60)
    
    tests = [
        ("Yes variants", test_confirm_accepts_yes_variants),
        ("No variants", test_confirm_accepts_no_variants),
        ("Invalid inputs", test_confirm_rejects_invalid_input),
        ("Keyboard interrupt", test_confirm_handles_keyboard_interrupt),
        ("Custom prompt", test_confirm_custom_prompt),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n  ❌ {name} test FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)