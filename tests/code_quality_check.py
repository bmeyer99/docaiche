#!/usr/bin/env python3
"""
Simple code quality checker for Python files.
Checks for common issues without external dependencies.
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Tuple

class CodeQualityChecker:
    def __init__(self):
        self.issues = []
        
    def check_file(self, filepath: str) -> List[Tuple[int, str]]:
        """Check a single Python file for quality issues."""
        issues = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines()
        
        # Check for syntax
        try:
            ast.parse(content)
        except SyntaxError as e:
            issues.append((e.lineno, f"Syntax error: {e.msg}"))
            return issues
        
        # Line-by-line checks
        for i, line in enumerate(lines, 1):
            # Line too long
            if len(line) > 100:
                issues.append((i, f"Line too long ({len(line)} > 100 characters)"))
            
            # Trailing whitespace
            if line.rstrip() != line:
                issues.append((i, "Trailing whitespace"))
            
            # TODO/FIXME comments
            if "TODO" in line or "FIXME" in line:
                issues.append((i, "TODO/FIXME comment found"))
            
            # Bare except
            if re.match(r'^\s*except\s*:', line):
                issues.append((i, "Bare except clause (use specific exceptions)"))
            
            # Print statements (should use logging)
            if re.match(r'^\s*print\s*\(', line):
                issues.append((i, "Print statement found (use logging instead)"))
        
        # AST-based checks
        tree = ast.parse(content)
        
        # Check for missing docstrings
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if not ast.get_docstring(node):
                    issues.append((node.lineno, f"Missing docstring for {node.name}"))
        
        return issues

def main():
    checker = CodeQualityChecker()
    
    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk("src"):
        # Skip __pycache__ directories
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))
    
    print(f"Checking {len(python_files)} Python files...\n")
    
    total_issues = 0
    files_with_issues = 0
    
    for filepath in sorted(python_files):
        issues = checker.check_file(filepath)
        if issues:
            files_with_issues += 1
            print(f"\n{filepath}:")
            for line_no, issue in sorted(issues):
                print(f"  Line {line_no}: {issue}")
                total_issues += 1
    
    print(f"\n{'='*50}")
    print(f"Summary: {total_issues} issues found in {files_with_issues}/{len(python_files)} files")
    
    # Also check for security issues
    print(f"\n{'='*50}")
    print("Security checks:")
    
    security_issues = 0
    for filepath in python_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for hardcoded secrets
        if re.search(r'(password|secret|key|token)\s*=\s*["\'][^"\']+["\']', content, re.IGNORECASE):
            print(f"  {filepath}: Possible hardcoded secret")
            security_issues += 1
            
        # Check for SQL injection risks
        if re.search(r'\.execute\s*\(\s*["\'].*%s', content):
            print(f"  {filepath}: Possible SQL injection risk (use parameterized queries)")
            security_issues += 1
    
    if security_issues == 0:
        print("  No obvious security issues found")
    
    return total_issues + security_issues

if __name__ == "__main__":
    exit(main())