#!/usr/bin/env python3
"""Validate imports and module dependencies in the backend code."""

import ast
import os
import sys
from pathlib import Path
from typing import Set, Dict, List, Tuple

class ImportValidator:
    def __init__(self, src_dir: str):
        self.src_dir = Path(src_dir)
        self.imports: Dict[str, Set[str]] = {}
        self.missing_imports: List[Tuple[str, str, str]] = []
        self.circular_imports: List[Tuple[str, str]] = []
        
    def analyze_file(self, file_path: Path) -> Set[str]:
        """Extract imports from a Python file."""
        imports = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=str(file_path))
                
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
                        
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            
        return imports
    
    def check_import_exists(self, module_name: str, from_file: str) -> bool:
        """Check if an import can be resolved."""
        # Check if it's a standard library module
        if module_name in sys.stdlib_module_names:
            return True
            
        # Check if it's an installed package
        try:
            __import__(module_name.split('.')[0])
            return True
        except ImportError:
            pass
            
        # Check if it's a local module
        if module_name.startswith('src.'):
            module_path = module_name.replace('.', '/')
            if (self.src_dir.parent / f"{module_path}.py").exists():
                return True
            if (self.src_dir.parent / module_path / "__init__.py").exists():
                return True
                
        return False
    
    def validate_imports(self):
        """Validate all imports in the project."""
        python_files = list(self.src_dir.rglob("*.py"))
        
        # First pass: collect all imports
        for file_path in python_files:
            relative_path = file_path.relative_to(self.src_dir.parent)
            module_name = str(relative_path).replace('/', '.').replace('.py', '')
            self.imports[module_name] = self.analyze_file(file_path)
            
        # Second pass: check for missing imports
        for file_path in python_files:
            relative_path = file_path.relative_to(self.src_dir.parent)
            module_name = str(relative_path).replace('/', '.').replace('.py', '')
            
            for imported in self.imports.get(module_name, set()):
                if not self.check_import_exists(imported, str(file_path)):
                    self.missing_imports.append((str(file_path), imported, module_name))
                    
        # Check for circular imports (simplified check)
        for module1, imports1 in self.imports.items():
            for module2 in imports1:
                if module2 in self.imports:
                    if module1 in self.imports[module2]:
                        if (module2, module1) not in self.circular_imports:
                            self.circular_imports.append((module1, module2))
    
    def report(self):
        """Generate validation report."""
        print("=== Import Validation Report ===\n")
        
        print(f"Total Python files analyzed: {len(self.imports)}")
        print(f"Total unique imports: {sum(len(imps) for imps in self.imports.values())}\n")
        
        if self.missing_imports:
            print(f"Missing/Unresolved Imports ({len(self.missing_imports)}):")
            for file_path, import_name, module in self.missing_imports[:20]:  # Show first 20
                print(f"  - {module}: Cannot import '{import_name}'")
            if len(self.missing_imports) > 20:
                print(f"  ... and {len(self.missing_imports) - 20} more")
        else:
            print("✓ All imports resolved successfully")
            
        print()
        
        if self.circular_imports:
            print(f"Potential Circular Imports ({len(self.circular_imports)}):")
            for module1, module2 in self.circular_imports[:10]:  # Show first 10
                print(f"  - {module1} <-> {module2}")
            if len(self.circular_imports) > 10:
                print(f"  ... and {len(self.circular_imports) - 10} more")
        else:
            print("✓ No circular imports detected")

if __name__ == "__main__":
    validator = ImportValidator("src")
    validator.validate_imports()
    validator.report()