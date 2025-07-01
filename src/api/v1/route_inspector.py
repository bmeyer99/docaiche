"""
Route Inspector for FastAPI Application
Dynamically extracts all registered routes for monitoring purposes
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, APIRouter
from fastapi.routing import APIRoute

logger = logging.getLogger(__name__)


class RouteInspector:
    """Inspector for extracting route information from FastAPI applications."""
    
    def __init__(self, app: Optional[FastAPI] = None):
        """
        Initialize the route inspector.
        
        Args:
            app: FastAPI application instance
        """
        self.app = app
        
    def get_all_routes(self, app: Optional[FastAPI] = None) -> List[Dict[str, Any]]:
        """
        Extract all routes from the FastAPI application.
        
        Args:
            app: FastAPI application instance (uses self.app if not provided)
            
        Returns:
            List of route information dictionaries
        """
        target_app = app or self.app
        if not target_app:
            raise ValueError("No FastAPI application provided")
            
        routes = []
        
        # Process all routes in the application
        for route in target_app.routes:
            if isinstance(route, APIRoute):
                route_info = self._extract_route_info(route)
                routes.append(route_info)
                
        return sorted(routes, key=lambda x: (x['path'], x['methods'][0] if x['methods'] else ''))
    
    def _extract_route_info(self, route: APIRoute) -> Dict[str, Any]:
        """
        Extract detailed information from a route.
        
        Args:
            route: FastAPI route instance
            
        Returns:
            Dictionary containing route information
        """
        # Get route tags
        tags = list(route.tags) if route.tags else []
        
        # Get route methods
        methods = list(route.methods) if route.methods else []
        
        # Extract endpoint function information
        endpoint_name = route.endpoint.__name__ if route.endpoint else "unknown"
        endpoint_module = route.endpoint.__module__ if route.endpoint else "unknown"
        
        # Build route info
        route_info = {
            "path": route.path,
            "name": route.name,
            "methods": methods,
            "tags": tags,
            "summary": route.summary or "",
            "description": route.description or "",
            "endpoint_name": endpoint_name,
            "endpoint_module": endpoint_module,
            "deprecated": route.deprecated or False,
            "include_in_schema": route.include_in_schema,
            "response_model": route.response_model.__name__ if route.response_model else None,
        }
        
        # Add dependency information if available
        if hasattr(route, 'dependencies') and route.dependencies:
            route_info["has_dependencies"] = True
            route_info["dependency_count"] = len(route.dependencies)
        else:
            route_info["has_dependencies"] = False
            route_info["dependency_count"] = 0
            
        return route_info
    
    def get_routes_by_tag(self, tag: str, app: Optional[FastAPI] = None) -> List[Dict[str, Any]]:
        """
        Get all routes with a specific tag.
        
        Args:
            tag: Tag to filter by
            app: FastAPI application instance
            
        Returns:
            List of routes with the specified tag
        """
        all_routes = self.get_all_routes(app)
        return [route for route in all_routes if tag in route.get('tags', [])]
    
    def get_routes_by_method(self, method: str, app: Optional[FastAPI] = None) -> List[Dict[str, Any]]:
        """
        Get all routes with a specific HTTP method.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            app: FastAPI application instance
            
        Returns:
            List of routes with the specified method
        """
        all_routes = self.get_all_routes(app)
        method_upper = method.upper()
        return [route for route in all_routes if method_upper in route.get('methods', [])]
    
    def get_route_stats(self, app: Optional[FastAPI] = None) -> Dict[str, Any]:
        """
        Get statistics about the routes.
        
        Args:
            app: FastAPI application instance
            
        Returns:
            Dictionary containing route statistics
        """
        all_routes = self.get_all_routes(app)
        
        # Count routes by method
        method_counts = {}
        for route in all_routes:
            for method in route.get('methods', []):
                method_counts[method] = method_counts.get(method, 0) + 1
        
        # Count routes by tag
        tag_counts = {}
        for route in all_routes:
            for tag in route.get('tags', []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Count deprecated routes
        deprecated_count = sum(1 for route in all_routes if route.get('deprecated', False))
        
        # Count routes with dependencies
        dependency_count = sum(1 for route in all_routes if route.get('has_dependencies', False))
        
        return {
            "total_routes": len(all_routes),
            "routes_by_method": method_counts,
            "routes_by_tag": tag_counts,
            "deprecated_routes": deprecated_count,
            "routes_with_dependencies": dependency_count,
            "unique_paths": len(set(route['path'] for route in all_routes)),
        }
    
    def format_routes_table(self, routes: Optional[List[Dict[str, Any]]] = None, app: Optional[FastAPI] = None) -> str:
        """
        Format routes as a readable table.
        
        Args:
            routes: List of routes (uses all routes if not provided)
            app: FastAPI application instance
            
        Returns:
            Formatted table string
        """
        if routes is None:
            routes = self.get_all_routes(app)
        
        if not routes:
            return "No routes found."
        
        # Build table header
        lines = []
        lines.append("=" * 120)
        lines.append(f"{'Method':<8} {'Path':<40} {'Name':<30} {'Tags':<20} {'Module':<20}")
        lines.append("=" * 120)
        
        # Add route rows
        for route in routes:
            methods = ', '.join(route.get('methods', []))
            path = route.get('path', '')
            name = route.get('name', '')
            tags = ', '.join(route.get('tags', []))
            module = route.get('endpoint_module', '').split('.')[-1]  # Just the last part
            
            # Truncate long values
            if len(path) > 38:
                path = path[:35] + "..."
            if len(name) > 28:
                name = name[:25] + "..."
            if len(tags) > 18:
                tags = tags[:15] + "..."
            if len(module) > 18:
                module = module[:15] + "..."
            
            lines.append(f"{methods:<8} {path:<40} {name:<30} {tags:<20} {module:<20}")
        
        lines.append("=" * 120)
        
        return "\n".join(lines)


# Utility function to inspect routes from an existing app
def inspect_app_routes(app: FastAPI) -> Dict[str, Any]:
    """
    Convenience function to inspect routes from a FastAPI app.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        Dictionary containing routes and statistics
    """
    inspector = RouteInspector(app)
    
    return {
        "routes": inspector.get_all_routes(),
        "stats": inspector.get_route_stats(),
        "formatted_table": inspector.format_routes_table()
    }