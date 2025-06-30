#!/usr/bin/env python3
"""Validate database connections and models."""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

class DatabaseValidator:
    def __init__(self):
        self.models: Dict[str, List[str]] = {}
        self.db_operations: Dict[str, List[str]] = {}
        self.connection_patterns: List[Dict] = []
        
    def extract_models(self, file_path: Path) -> List[str]:
        """Extract SQLAlchemy models from a file."""
        models = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Find SQLAlchemy model definitions
            model_pattern = r'class\s+(\w+)\s*\([^)]*(?:Base|Model|db\.Model)[^)]*\)'
            matches = re.findall(model_pattern, content)
            models.extend(matches)
            
            # Also find Pydantic models that might be DB schemas
            pydantic_pattern = r'class\s+(\w+)\s*\([^)]*(?:BaseModel|Schema)[^)]*\):'
            pydantic_matches = re.findall(pydantic_pattern, content)
            for match in pydantic_matches:
                if 'DB' in match or 'Model' in match or match.endswith('Schema'):
                    models.append(f"{match} (Pydantic)")
                    
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            
        return models
    
    def extract_db_operations(self, file_path: Path) -> List[str]:
        """Extract database operations from a file."""
        operations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Common database operation patterns
            op_patterns = [
                r'session\.(add|commit|rollback|query|delete|merge)\s*\(',
                r'db\.(session|create_all|drop_all)\s*\(',
                r'(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP)\s+',
                r'\.filter\s*\(',
                r'\.filter_by\s*\(',
                r'\.order_by\s*\(',
                r'\.join\s*\(',
                r'execute\s*\(["\']*(SELECT|INSERT|UPDATE|DELETE)',
            ]
            
            for pattern in op_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                operations.extend(matches)
                
        except Exception as e:
            print(f"Error extracting operations from {file_path}: {e}")
            
        return operations
    
    def extract_connection_patterns(self, file_path: Path) -> List[Dict]:
        """Extract database connection patterns."""
        patterns = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Connection string patterns
            conn_patterns = [
                (r'sqlite:///', 'SQLite'),
                (r'postgresql://', 'PostgreSQL'),
                (r'mysql://', 'MySQL'),
                (r'create_engine\s*\(', 'SQLAlchemy Engine'),
                (r'AsyncSession', 'Async Session'),
                (r'Session\s*\(', 'Session Factory'),
                (r'DATABASE_URL', 'Database URL Config'),
            ]
            
            for pattern, conn_type in conn_patterns:
                if re.search(pattern, content):
                    patterns.append({
                        'file': str(file_path),
                        'type': conn_type
                    })
                    
        except Exception as e:
            print(f"Error extracting connections from {file_path}: {e}")
            
        return patterns
    
    def validate_database(self):
        """Validate database setup and usage."""
        src_dir = Path("src")
        
        # Find relevant files
        db_files = list(src_dir.rglob("*model*.py"))
        db_files.extend(src_dir.rglob("*database*.py"))
        db_files.extend(src_dir.rglob("*schema*.py"))
        db_files.extend(src_dir.rglob("*repository*.py"))
        
        # Extract information
        for file_path in db_files:
            relative_path = str(file_path.relative_to(src_dir))
            
            # Extract models
            models = self.extract_models(file_path)
            if models:
                self.models[relative_path] = models
                
            # Extract operations
            operations = self.extract_db_operations(file_path)
            if operations:
                self.db_operations[relative_path] = operations
                
            # Extract connections
            patterns = self.extract_connection_patterns(file_path)
            self.connection_patterns.extend(patterns)
    
    def report(self):
        """Generate validation report."""
        print("=== Database Validation Report ===\n")
        
        # Summary
        total_models = sum(len(models) for models in self.models.values())
        print(f"Total database models found: {total_models}")
        print(f"Files with models: {len(self.models)}")
        print(f"Files with DB operations: {len(self.db_operations)}\n")
        
        # List models
        print("Database Models:")
        for file_path, models in sorted(self.models.items()):
            print(f"\n  {file_path}:")
            for model in models:
                print(f"    - {model}")
                
        # Connection patterns
        print("\n\nDatabase Connection Patterns:")
        conn_types = {}
        for pattern in self.connection_patterns:
            conn_type = pattern['type']
            conn_types[conn_type] = conn_types.get(conn_type, 0) + 1
            
        for conn_type, count in sorted(conn_types.items()):
            print(f"  - {conn_type}: {count} occurrences")
            
        # Database operations summary
        print("\n\nDatabase Operations Summary:")
        op_counts = {}
        for operations in self.db_operations.values():
            for op in operations:
                op_name = op.upper() if isinstance(op, str) else str(op)
                op_counts[op_name] = op_counts.get(op_name, 0) + 1
                
        for op, count in sorted(op_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  - {op}: {count} occurrences")
            
        # Check for potential issues
        print("\n\nPotential Issues:")
        
        # Check for raw SQL
        raw_sql_files = []
        for file_path, operations in self.db_operations.items():
            if any(op in ['SELECT', 'INSERT', 'UPDATE', 'DELETE'] for op in operations):
                raw_sql_files.append(file_path)
                
        if raw_sql_files:
            print(f"\n  Files with raw SQL ({len(raw_sql_files)}):")
            for file_path in raw_sql_files[:5]:
                print(f"    - {file_path}")
            if len(raw_sql_files) > 5:
                print(f"    ... and {len(raw_sql_files) - 5} more")
        
        # Check for missing models
        model_names = set()
        for models in self.models.values():
            for model in models:
                model_name = model.split()[0]  # Remove "(Pydantic)" suffix if present
                model_names.add(model_name)
                
        print(f"\n  Total unique model names: {len(model_names)}")

if __name__ == "__main__":
    validator = DatabaseValidator()
    validator.validate_database()
    validator.report()