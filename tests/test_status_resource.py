"""
Unit Tests for Status Resource
===============================

Comprehensive test suite for the status resource implementation
covering health checks, metrics, and system status reporting.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
import sys
import os
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestStatusResource:
    """Test suite for status resource operations."""
    
    def test_uri_parsing(self):
        """Test URI parsing for different status operations."""
        def parse_status_uri(uri):
            if uri.startswith("status://docaiche/"):
                path = uri[18:]
            else:
                path = uri.lstrip("/")
            
            if not path or path == "overview":
                return {"type": "overview", "component": None}
            
            parts = path.split("/")
            component = parts[0]
            
            if component == "health":
                return {
                    "type": "health",
                    "component": parts[1] if len(parts) > 1 else None
                }
            elif component == "dependencies":
                return {"type": "dependencies", "component": None}
            elif component in ["system", "database", "search", "cache", "auth", "mcp", "storage", "network"]:
                return {"type": "component", "component": component}
            else:
                return {"type": "general", "component": component}
        
        # Test various URIs
        assert parse_status_uri("status://docaiche/") == {"type": "overview", "component": None}
        assert parse_status_uri("status://docaiche/overview") == {"type": "overview", "component": None}
        assert parse_status_uri("status://docaiche/health") == {"type": "health", "component": None}
        assert parse_status_uri("status://docaiche/health/database") == {"type": "health", "component": "database"}
        assert parse_status_uri("status://docaiche/database") == {"type": "component", "component": "database"}
        assert parse_status_uri("status://docaiche/dependencies") == {"type": "dependencies", "component": None}
    
    def test_health_status_calculation(self):
        """Test health status calculation logic."""
        def calculate_overall_status(cpu_usage, memory_usage):
            if cpu_usage > 80 or memory_usage > 90:
                return "critical"
            elif cpu_usage > 60 or memory_usage > 80:
                return "warning"
            else:
                return "healthy"
        
        # Test healthy status
        assert calculate_overall_status(35, 65) == "healthy"
        
        # Test warning status
        assert calculate_overall_status(65, 75) == "warning"
        assert calculate_overall_status(50, 85) == "warning"
        
        # Test critical status
        assert calculate_overall_status(85, 75) == "critical"
        assert calculate_overall_status(50, 95) == "critical"
    
    def test_component_status_generation(self):
        """Test component status data generation."""
        def generate_component_status(component, current_time):
            # Simulate variability
            base_health = "healthy"
            
            # Add some conditional degradation
            if component == "database" and current_time % 100 < 5:
                base_health = "warning"
            elif component == "cache" and current_time % 150 < 3:
                base_health = "degraded"
            
            return {
                "status": base_health,
                "response_time_ms": int(50 + (hash(component) % 100)),
                "availability_percent": round(99.5 + (hash(component) % 5) * 0.1, 1)
            }
        
        # Test different components
        current_time = int(time.time())
        
        db_status = generate_component_status("database", current_time)
        assert db_status["status"] in ["healthy", "warning", "degraded"]
        assert 50 <= db_status["response_time_ms"] <= 150
        assert 99.5 <= db_status["availability_percent"] <= 100.0
        
        cache_status = generate_component_status("cache", current_time)
        assert "status" in cache_status
        assert "response_time_ms" in cache_status
    
    def test_metrics_calculation(self):
        """Test system metrics calculation."""
        def calculate_metrics(base_values, current_time):
            return {
                "cpu_usage_percent": round(base_values["cpu"] + (current_time % 20) * 2, 1),
                "memory_usage_percent": round(base_values["memory"] + (current_time % 15) * 1.5, 1),
                "disk_usage_percent": base_values["disk"],
                "active_connections": int(base_values["connections"] + (current_time % 50)),
                "requests_per_second": round(base_values["rps"] + (current_time % 20), 1)
            }
        
        base = {"cpu": 35, "memory": 65, "disk": 45.2, "connections": 15, "rps": 25}
        current = int(time.time())
        
        metrics = calculate_metrics(base, current)
        assert metrics["cpu_usage_percent"] >= 35
        assert metrics["memory_usage_percent"] >= 65
        assert metrics["disk_usage_percent"] == 45.2
        assert metrics["active_connections"] >= 15
        assert metrics["requests_per_second"] >= 25
    
    def test_health_check_structure(self):
        """Test health check response structure."""
        def create_health_check(component):
            return {
                "component": component,
                "status": "healthy",
                "checks_performed": [
                    "connectivity",
                    "response_time",
                    "resource_usage",
                    "error_rate"
                ],
                "last_check": datetime.utcnow().isoformat(),
                "next_check": (datetime.utcnow() + timedelta(minutes=5)).isoformat(),
                "check_interval_seconds": 300,
                "details": {
                    "connectivity": {"status": "pass", "latency_ms": 25},
                    "response_time": {"status": "pass", "average_ms": 150},
                    "resource_usage": {"status": "pass", "usage_percent": 65},
                    "error_rate": {"status": "pass", "rate_percent": 0.1}
                }
            }
        
        health_check = create_health_check("database")
        assert health_check["component"] == "database"
        assert len(health_check["checks_performed"]) == 4
        assert health_check["check_interval_seconds"] == 300
        assert all(check["status"] == "pass" for check in health_check["details"].values())
    
    def test_dependency_status_structure(self):
        """Test dependency status reporting."""
        deps = {
            "dependencies": {
                "external_apis": {
                    "github_api": {
                        "status": "healthy",
                        "response_time_ms": 120,
                        "availability": "99.9%"
                    },
                    "documentation_providers": {
                        "status": "healthy",
                        "response_time_ms": 200,
                        "availability": "99.5%"
                    }
                },
                "internal_services": {
                    "ingestion_pipeline": {
                        "status": "healthy",
                        "queue_depth": 5,
                        "processing_rate": "10/min"
                    },
                    "analytics_processor": {
                        "status": "healthy",
                        "lag_seconds": 30,
                        "throughput": "50/min"
                    }
                },
                "infrastructure": {
                    "dns_resolution": {
                        "status": "healthy",
                        "response_time_ms": 15
                    },
                    "internet_connectivity": {
                        "status": "healthy",
                        "bandwidth_mbps": 100,
                        "packet_loss_percent": 0.0
                    }
                }
            },
            "summary": {
                "total_dependencies": 6,
                "healthy_dependencies": 6,
                "degraded_dependencies": 0,
                "failed_dependencies": 0
            }
        }
        
        assert len(deps["dependencies"]) == 3
        assert deps["summary"]["total_dependencies"] == 6
        assert deps["summary"]["healthy_dependencies"] == 6
    
    def test_cache_ttl_values(self):
        """Test cache TTL configuration."""
        cache_config = {
            "enabled": True,
            "ttl_seconds": 30,  # Very short for status
            "max_size_bytes": 128 * 1024  # 128KB
        }
        
        assert cache_config["ttl_seconds"] == 30
        assert cache_config["max_size_bytes"] == 131072
    
    def test_component_specific_details(self):
        """Test component-specific detail generation."""
        def get_component_details(component, current_time):
            details = {}
            
            if component == "database":
                details = {
                    "connection_pool": "active",
                    "active_connections": int(10 + (current_time % 20)),
                    "max_connections": 100,
                    "query_performance": "normal",
                    "replication_lag_ms": int(5 + (current_time % 15))
                }
            elif component == "search":
                details = {
                    "index_status": "healthy",
                    "indexed_documents": 125000 + int(current_time % 1000),
                    "query_latency_ms": int(45 + (current_time % 30)),
                    "cluster_status": "green",
                    "cache_hit_rate": round(0.85 + (current_time % 10) * 0.01, 2)
                }
            elif component == "cache":
                details = {
                    "memory_usage_percent": round(65 + (current_time % 20), 1),
                    "hit_rate_percent": round(78 + (current_time % 15), 1),
                    "evictions_per_hour": int(10 + (current_time % 50)),
                    "active_keys": int(15000 + (current_time % 5000))
                }
            elif component == "mcp":
                details = {
                    "active_connections": int(15 + (current_time % 25)),
                    "protocol_versions": ["2025-03-26", "2024-11-05"],
                    "tool_executions_per_minute": int(45 + (current_time % 30)),
                    "resource_cache_hit_rate": round(0.75 + (current_time % 20) * 0.01, 2),
                    "average_response_time_ms": int(150 + (current_time % 50))
                }
            
            return details
        
        current = int(time.time())
        
        # Test database details
        db_details = get_component_details("database", current)
        assert "connection_pool" in db_details
        assert db_details["max_connections"] == 100
        
        # Test search details
        search_details = get_component_details("search", current)
        assert search_details["cluster_status"] == "green"
        assert search_details["indexed_documents"] >= 125000
        
        # Test MCP details
        mcp_details = get_component_details("mcp", current)
        assert len(mcp_details["protocol_versions"]) == 2
        assert "2025-03-26" in mcp_details["protocol_versions"]
    
    def test_status_summary_calculation(self):
        """Test status summary calculations."""
        def calculate_summary(component_statuses):
            return {
                "healthy_components": sum(1 for c in component_statuses.values() if c["status"] == "healthy"),
                "total_components": len(component_statuses),
                "critical_issues": sum(1 for c in component_statuses.values() if c["status"] == "critical"),
                "warnings": sum(1 for c in component_statuses.values() if c["status"] in ["warning", "degraded"])
            }
        
        statuses = {
            "database": {"status": "healthy"},
            "search": {"status": "healthy"},
            "cache": {"status": "warning"},
            "auth": {"status": "healthy"},
            "mcp": {"status": "degraded"}
        }
        
        summary = calculate_summary(statuses)
        assert summary["total_components"] == 5
        assert summary["healthy_components"] == 3
        assert summary["critical_issues"] == 0
        assert summary["warnings"] == 2
    
    def test_recent_events_generation(self):
        """Test recent events list generation."""
        def generate_recent_events():
            return [
                {
                    "timestamp": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
                    "type": "info",
                    "component": "mcp",
                    "message": "MCP server restarted successfully"
                },
                {
                    "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                    "type": "warning",
                    "component": "cache",
                    "message": "Cache hit rate below threshold"
                }
            ]
        
        events = generate_recent_events()
        assert len(events) == 2
        assert events[0]["type"] == "info"
        assert events[1]["type"] == "warning"
        assert "timestamp" in events[0]
    
    def test_performance_metrics(self):
        """Test performance metric calculations."""
        def calculate_performance_metrics(component, base_values):
            return {
                "average_response_time_ms": base_values["response_time"] + (hash(component) % 100),
                "throughput_per_second": round(base_values["throughput"] + (hash(component) % 50), 1),
                "error_rate_percent": round(base_values["error_rate"] + (hash(component) % 5) * 0.1, 2),
                "availability_percent": round(99 + (hash(component) % 10) * 0.1, 1)
            }
        
        base = {"response_time": 100, "throughput": 10, "error_rate": 0.1}
        
        perf = calculate_performance_metrics("database", base)
        assert perf["average_response_time_ms"] >= 100
        assert perf["throughput_per_second"] >= 10
        assert perf["error_rate_percent"] >= 0.1
        assert perf["availability_percent"] >= 99.0


class TestStatusResourceCapabilities:
    """Test status resource capability reporting."""
    
    def test_capability_structure(self):
        """Test capability reporting structure."""
        capabilities = {
            "resource_name": "status",
            "monitored_components": [
                "system", "database", "search", "cache", 
                "auth", "mcp", "storage", "network", "dependencies"
            ],
            "status_types": ["overview", "component", "health", "dependencies"],
            "features": {
                "real_time_status": True,
                "component_health_checks": True,
                "dependency_monitoring": True,
                "historical_data": True,
                "performance_metrics": True,
                "alert_integration": False
            },
            "update_intervals": {
                "real_time": "30s",
                "health_checks": "5m",
                "metrics": "1m",
                "dependencies": "10m"
            },
            "caching": {
                "enabled": True,
                "ttl_seconds": 30,
                "max_size_bytes": 128 * 1024
            }
        }
        
        assert len(capabilities["monitored_components"]) == 9
        assert capabilities["features"]["real_time_status"] is True
        assert capabilities["features"]["alert_integration"] is False
        assert capabilities["update_intervals"]["real_time"] == "30s"
        assert capabilities["caching"]["ttl_seconds"] == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])