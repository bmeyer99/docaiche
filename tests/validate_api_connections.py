#!/usr/bin/env python3
"""Validate API endpoint connections to backend services."""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

class APIConnectionValidator:
    def __init__(self):
        self.endpoints: Dict[str, List[Dict]] = {}
        self.service_calls: Dict[str, Set[str]] = {}
        self.dependencies: Dict[str, Set[str]] = {}
        
    def extract_endpoints(self, file_path: Path) -> List[Dict]:
        """Extract API endpoints from a file."""
        endpoints = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Find FastAPI route decorators
            route_pattern = r'@(?:router|app)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
            matches = re.findall(route_pattern, content, re.MULTILINE)
            
            for method, path in matches:
                endpoints.append({
                    'method': method.upper(),
                    'path': path,
                    'file': str(file_path)
                })
                
            # Also look for APIRouter prefix
            prefix_pattern = r'APIRouter\s*\([^)]*prefix\s*=\s*["\']([^"\']+)["\']'
            prefix_matches = re.findall(prefix_pattern, content)
            
            if prefix_matches and endpoints:
                prefix = prefix_matches[0]
                for endpoint in endpoints:
                    if not endpoint['path'].startswith(prefix):
                        endpoint['path'] = prefix + endpoint['path']
                        
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            
        return endpoints
    
    def extract_service_dependencies(self, file_path: Path) -> Set[str]:
        """Extract service dependencies from endpoint files."""
        dependencies = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Look for dependency injection patterns
            dep_patterns = [
                r'(\w+Service)\s*=\s*Depends',
                r'(\w+Repository)\s*=\s*Depends',
                r'(\w+Manager)\s*=\s*Depends',
                r'get_(\w+)_service\s*\(',
                r'get_(\w+)_repository\s*\(',
            ]
            
            for pattern in dep_patterns:
                matches = re.findall(pattern, content)
                dependencies.update(matches)
                
            # Look for direct service imports
            import_pattern = r'from\s+src\.(?:services|repositories|managers)\s+import\s+(\w+)'
            import_matches = re.findall(import_pattern, content)
            dependencies.update(import_matches)
            
        except Exception as e:
            print(f"Error extracting dependencies from {file_path}: {e}")
            
        return dependencies
    
    def validate_connections(self):
        """Validate all API endpoint connections."""
        src_dir = Path("src")
        
        # Find all endpoint files
        endpoint_files = []
        for pattern in ["*endpoints.py", "*api.py", "*router.py"]:
            endpoint_files.extend(src_dir.rglob(pattern))
            
        # Extract endpoints and dependencies
        for file_path in endpoint_files:
            endpoints = self.extract_endpoints(file_path)
            if endpoints:
                module_name = str(file_path.relative_to(src_dir)).replace('/', '.')
                self.endpoints[module_name] = endpoints
                self.dependencies[module_name] = self.extract_service_dependencies(file_path)
                
        # Check service files exist
        service_files = list(src_dir.rglob("*service*.py"))
        service_files.extend(src_dir.rglob("*repository*.py"))
        service_files.extend(src_dir.rglob("*manager*.py"))
        
        available_services = set()
        for service_file in service_files:
            service_name = service_file.stem
            available_services.add(service_name)
            
        return available_services
    
    def report(self):
        """Generate validation report."""
        print("=== API Connection Validation Report ===\n")
        
        # Summary
        total_endpoints = sum(len(eps) for eps in self.endpoints.values())
        print(f"Total API endpoints found: {total_endpoints}")
        print(f"Total endpoint modules: {len(self.endpoints)}")
        print(f"Total service dependencies: {sum(len(deps) for deps in self.dependencies.values())}\n")
        
        # List endpoints by module
        print("API Endpoints by Module:")
        for module, endpoints in sorted(self.endpoints.items()):
            print(f"\n  {module} ({len(endpoints)} endpoints):")
            for ep in endpoints[:5]:  # Show first 5
                print(f"    - {ep['method']} {ep['path']}")
            if len(endpoints) > 5:
                print(f"    ... and {len(endpoints) - 5} more")
                
        # Check for disconnected endpoints
        print("\n\nEndpoint Service Dependencies:")
        disconnected = []
        for module, deps in self.dependencies.items():
            if deps:
                print(f"\n  {module} depends on:")
                for dep in sorted(deps):
                    print(f"    - {dep}")
            elif module in self.endpoints:
                disconnected.append(module)
                
        if disconnected:
            print(f"\n\nWarning: Endpoints with no service dependencies ({len(disconnected)}):")
            for module in disconnected:
                print(f"  - {module}")
                
        # Check for common patterns
        print("\n\nAPI Path Patterns:")
        path_prefixes = {}
        for endpoints in self.endpoints.values():
            for ep in endpoints:
                prefix = ep['path'].split('/')[1] if ep['path'].startswith('/') else ep['path'].split('/')[0]
                if prefix:
                    path_prefixes[prefix] = path_prefixes.get(prefix, 0) + 1
                    
        for prefix, count in sorted(path_prefixes.items(), key=lambda x: x[1], reverse=True):
            if count > 1:
                print(f"  - /{prefix}/*: {count} endpoints")

if __name__ == "__main__":
    validator = APIConnectionValidator()
    validator.validate_connections()
    validator.report()