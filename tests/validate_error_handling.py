#!/usr/bin/env python3
"""Validate error handling and exception flows."""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

class ErrorHandlingValidator:
    def __init__(self):
        self.exceptions: Dict[str, List[str]] = {}
        self.error_handlers: Dict[str, List[str]] = {}
        self.unhandled_operations: Dict[str, List[str]] = {}
        
    def extract_exceptions(self, file_path: Path) -> List[str]:
        """Extract custom exception definitions."""
        exceptions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Find exception class definitions
            exc_pattern = r'class\s+(\w*(?:Exception|Error)\w*)\s*\([^)]*(?:Exception|Error|BaseException)[^)]*\)'
            matches = re.findall(exc_pattern, content)
            exceptions.extend(matches)
            
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            
        return exceptions
    
    def extract_error_handlers(self, file_path: Path) -> Dict[str, List[str]]:
        """Extract error handling patterns."""
        handlers = {
            'try_except': [],
            'exception_handlers': [],
            'error_responses': [],
            'logging': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Find try-except blocks
            try_except_pattern = r'except\s+(\w+(?:Exception|Error)?)\s*(?:as\s+\w+)?:'
            matches = re.findall(try_except_pattern, content)
            handlers['try_except'].extend(matches)
            
            # Find FastAPI exception handlers
            handler_pattern = r'@app\.exception_handler\s*\((\w+)\)'
            matches = re.findall(handler_pattern, content)
            handlers['exception_handlers'].extend(matches)
            
            # Find error response patterns
            error_resp_pattern = r'(?:HTTPException|APIException|JsonResponse)\s*\([^)]*status_code\s*=\s*(\d+)'
            matches = re.findall(error_resp_pattern, content)
            handlers['error_responses'].extend(matches)
            
            # Find logging patterns
            log_pattern = r'(?:logger|logging)\.(error|exception|warning|critical)\s*\('
            matches = re.findall(log_pattern, content)
            handlers['logging'].extend(matches)
            
        except Exception as e:
            print(f"Error extracting handlers from {file_path}: {e}")
            
        return handlers
    
    def find_risky_operations(self, file_path: Path) -> List[str]:
        """Find potentially risky operations without error handling."""
        risky_ops = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Patterns for risky operations
            risky_patterns = [
                r'open\s*\(',
                r'requests\.(get|post|put|delete)\s*\(',
                r'aiohttp\.(get|post|put|delete)\s*\(',
                r'async with\s+\w+\s*\(',
                r'await\s+\w+\.(query|execute|fetch|save)\s*\(',
                r'json\.loads\s*\(',
                r'int\s*\(',
                r'float\s*\(',
            ]
            
            in_try_block = False
            for i, line in enumerate(lines):
                # Simple try block detection
                if 'try:' in line:
                    in_try_block = True
                elif 'except' in line and in_try_block:
                    in_try_block = False
                    
                if not in_try_block:
                    for pattern in risky_patterns:
                        if re.search(pattern, line):
                            risky_ops.append(f"Line {i+1}: {line.strip()}")
                            
        except Exception as e:
            print(f"Error finding risky operations in {file_path}: {e}")
            
        return risky_ops[:10]  # Limit to first 10
    
    def validate_error_handling(self):
        """Validate error handling across the codebase."""
        src_dir = Path("src")
        
        # Find all Python files
        python_files = list(src_dir.rglob("*.py"))
        
        for file_path in python_files:
            relative_path = str(file_path.relative_to(src_dir))
            
            # Extract exceptions
            exceptions = self.extract_exceptions(file_path)
            if exceptions:
                self.exceptions[relative_path] = exceptions
                
            # Extract handlers
            handlers = self.extract_error_handlers(file_path)
            if any(handlers.values()):
                self.error_handlers[relative_path] = handlers
                
            # Find risky operations
            risky_ops = self.find_risky_operations(file_path)
            if risky_ops:
                self.unhandled_operations[relative_path] = risky_ops
    
    def report(self):
        """Generate validation report."""
        print("=== Error Handling Validation Report ===\n")
        
        # Summary
        total_exceptions = sum(len(excs) for excs in self.exceptions.values())
        total_handlers = sum(
            sum(len(h) for h in handlers.values()) 
            for handlers in self.error_handlers.values()
        )
        
        print(f"Total custom exceptions: {total_exceptions}")
        print(f"Files with error handling: {len(self.error_handlers)}")
        print(f"Files with risky unhandled operations: {len(self.unhandled_operations)}\n")
        
        # List custom exceptions
        print("Custom Exceptions Defined:")
        all_exceptions = set()
        for file_path, exceptions in self.exceptions.items():
            for exc in exceptions:
                all_exceptions.add(exc)
                
        for exc in sorted(all_exceptions):
            print(f"  - {exc}")
            
        # Error handling summary
        print("\n\nError Handling Patterns:")
        handler_counts = {
            'try_except': 0,
            'exception_handlers': 0,
            'error_responses': 0,
            'logging': 0
        }
        
        for handlers in self.error_handlers.values():
            for handler_type, occurrences in handlers.items():
                handler_counts[handler_type] += len(occurrences)
                
        for handler_type, count in handler_counts.items():
            print(f"  - {handler_type}: {count} occurrences")
            
        # HTTP status codes used
        print("\n\nHTTP Error Status Codes Used:")
        status_codes = {}
        for handlers in self.error_handlers.values():
            for code in handlers.get('error_responses', []):
                status_codes[code] = status_codes.get(code, 0) + 1
                
        for code, count in sorted(status_codes.items()):
            print(f"  - {code}: {count} times")
            
        # Files with poor error handling
        print("\n\nFiles with Potentially Risky Unhandled Operations:")
        for file_path in sorted(self.unhandled_operations.keys())[:10]:
            ops_count = len(self.unhandled_operations[file_path])
            print(f"  - {file_path}: {ops_count} risky operations")
            
        # Exception hierarchy check
        print("\n\nException Hierarchy:")
        base_exceptions = ['BaseException', 'Exception', 'Error']
        custom_bases = set()
        
        for exc in all_exceptions:
            for base in base_exceptions:
                if base in exc and exc != base:
                    custom_bases.add(exc)
                    
        if custom_bases:
            print("  Custom base exceptions that others might inherit from:")
            for base in sorted(custom_bases):
                print(f"    - {base}")

if __name__ == "__main__":
    validator = ErrorHandlingValidator()
    validator.validate_error_handling()
    validator.report()