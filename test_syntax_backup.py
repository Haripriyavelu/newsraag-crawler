#!/usr/bin/env python3
"""
Simple syntax test for main.py
"""
import ast
import sys

def test_main_py_syntax():
    """Test that main.py has valid Python syntax."""
    try:
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST to check for syntax errors
        ast.parse(content)
        print("SUCCESS: main.py has valid Python syntax")
        return True
        
    except SyntaxError as e:
        print("SYNTAX ERROR in main.py:")
        print(f"   Line {e.lineno}: {e.text}")
        print(f"   Error: {e.msg}")
        return False
    except Exception as e:
        print(f"ERROR reading main.py: {e}")
        return False

if __name__ == "__main__":
    success = test_main_py_syntax()
    sys.exit(0 if success else 1)