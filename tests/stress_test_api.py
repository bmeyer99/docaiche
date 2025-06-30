#!/usr/bin/env python3
"""
Comprehensive API Stress Testing - 100 Pass Analysis
Tests all endpoints with varied parameters to identify runtime issues
"""

import json
import time
import requests
import random
import string
from datetime import datetime
from typing import Dict, Any, List
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class APIStressTester:
    def __init__(self, base_url: str = "http://localhost:4080/api/v1"):
        self.base_url = base_url
        self.session = requests.Session()
        self.errors = []
        self.warnings = []
        self.performance_issues = []
        self.lock = threading.Lock()
        
        # Test data variations
        self.search_queries = [
            "python async await", "react hooks tutorial", "fastapi authentication",
            "vue.js components", "javascript promises", "docker compose",
            "kubernetes deployment", "sql joins", "git rebase", "nginx configuration",
            "postgresql indexes", "redis caching", "mongodb aggregation", "elasticsearch queries",
            "test", "a", "documentation", "tutorial guide", "how to", "best practices",
            "error handling", "performance optimization", "security", "deployment",
            "testing", "debugging", "monitoring", "logging", "api design"
        ]
        
        self.technology_hints = [
            None, "python", "javascript", "react", "vue", "docker", "kubernetes", 
            "postgresql", "redis", "nginx", "fastapi", "nodejs", "typescript", "go"
        ]
        
        self.feedback_types = ["helpful", "not_helpful", "incorrect", "outdated"]
        self.signal_types = ["click", "hover", "scroll", "copy", "download"]
        
    def random_string(self, length=10):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    def log_error(self, category: str, endpoint: str, error: str, details: Dict = None):
        with self.lock:
            self.errors.append({
                "category": category,
                "endpoint": endpoint,
                "error": error,
                "details": details or {},
                "timestamp": datetime.now().isoformat()
            })
    
    def log_warning(self, category: str, endpoint: str, warning: str, details: Dict = None):
        with self.lock:
            self.warnings.append({
                "category": category,
                "endpoint": endpoint,
                "warning": warning,
                "details": details or {},
                "timestamp": datetime.now().isoformat()
            })
    
    def log_performance_issue(self, endpoint: str, duration: float, details: Dict = None):
        with self.lock:
            self.performance_issues.append({
                "endpoint": endpoint,
                "duration": duration,
                "details": details or {},
                "timestamp": datetime.now().isoformat()
            })
    
    def test_endpoint(self, method: str, endpoint: str, data: Dict = None, 
                     expected_status: int = 200, timeout: float = 30.0) -> Dict[str, Any]:
        """Test a single endpoint and return detailed results"""
        start_time = time.time()
        result = {
            "success": False,
            "status_code": None,
            "duration": 0,
            "response_size": 0,
            "error": None,
            "response_data": None
        }
        
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method == "GET":
                response = self.session.get(url, timeout=timeout)
            elif method == "POST":
                response = self.session.post(url, json=data, timeout=timeout)
            elif method == "DELETE":
                response = self.session.delete(url, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            duration = time.time() - start_time
            result.update({
                "status_code": response.status_code,
                "duration": duration,
                "response_size": len(response.content)
            })
            
            # Performance monitoring
            if duration > 10.0:  # Very slow
                self.log_performance_issue(endpoint, duration, {
                    "threshold": "very_slow", "method": method, "data_size": len(str(data)) if data else 0
                })
            elif duration > 5.0:  # Slow
                self.log_performance_issue(endpoint, duration, {
                    "threshold": "slow", "method": method, "data_size": len(str(data)) if data else 0
                })
            
            # Status code analysis
            if response.status_code == expected_status:
                result["success"] = True
                try:
                    result["response_data"] = response.json()
                except:
                    result["response_data"] = response.text
            else:
                self.log_error("status_mismatch", endpoint, 
                             f"Expected {expected_status}, got {response.status_code}",
                             {"response": response.text[:500]})
            
            # Response validation
            if response.status_code == 200:
                try:
                    json_data = response.json()
                    if not json_data:
                        self.log_warning("empty_response", endpoint, "Received empty JSON response")
                    
                    # Check for common API response patterns
                    if endpoint.startswith("/search") and "results" in json_data:
                        if "execution_time_ms" not in json_data:
                            self.log_warning("missing_field", endpoint, "Missing execution_time_ms field")
                        if json_data.get("execution_time_ms", 0) > 30000:  # 30+ seconds
                            self.log_performance_issue(endpoint, json_data.get("execution_time_ms", 0) / 1000)
                            
                except Exception as e:
                    if "application/json" in response.headers.get("content-type", ""):
                        self.log_error("json_parse", endpoint, f"Failed to parse JSON: {str(e)}")
            
        except requests.exceptions.Timeout:
            result["error"] = "timeout"
            self.log_error("timeout", endpoint, f"Request timeout after {timeout}s")
        except requests.exceptions.ConnectionError:
            result["error"] = "connection_error"
            self.log_error("connection", endpoint, "Connection error")
        except Exception as e:
            result["error"] = str(e)
            self.log_error("exception", endpoint, str(e), {"traceback": traceback.format_exc()})
        
        result["duration"] = time.time() - start_time
        return result
    
    def test_health_endpoints(self, pass_num: int):
        """Test health and monitoring endpoints"""
        endpoints = [
            ("GET", "/health", None, 200),
            ("GET", "/stats", None, 200),
            ("GET", "/analytics?timeRange=24h", None, 200),
            ("GET", "/analytics?timeRange=7d", None, 200),
            ("GET", "/analytics?timeRange=30d", None, 200),
            ("GET", "/analytics?timeRange=invalid", None, 200),  # Should handle gracefully
        ]
        
        for method, endpoint, data, expected in endpoints:
            self.test_endpoint(method, endpoint, data, expected)
    
    def test_search_endpoints(self, pass_num: int):
        """Test search endpoints with various queries"""
        # GET search tests
        for _ in range(3):  # Multiple queries per pass
            query = random.choice(self.search_queries)
            tech_hint = random.choice(self.technology_hints)
            limit = random.randint(1, 50)
            
            params = f"?q={query}&limit={limit}"
            if tech_hint:
                params += f"&technology_hint={tech_hint}"
            
            self.test_endpoint("GET", f"/search{params}", None, 200)
        
        # POST search tests
        for _ in range(3):
            query = random.choice(self.search_queries)
            data = {
                "query": query,
                "limit": random.randint(1, 100),
                "session_id": f"session_{self.random_string(8)}"
            }
            
            if random.choice([True, False]):
                data["technology_hint"] = random.choice([t for t in self.technology_hints if t])
            
            self.test_endpoint("POST", "/search", data, 200)
        
        # Edge case tests
        edge_cases = [
            {"query": "", "limit": 1},  # Empty query
            {"query": "a" * 1000, "limit": 1},  # Very long query
            {"query": "test", "limit": 0},  # Zero limit
            {"query": "test", "limit": 1000},  # Very high limit
            {"query": "test", "technology_hint": "x" * 100},  # Long tech hint
        ]
        
        for data in edge_cases:
            result = self.test_endpoint("POST", "/search", data, None)  # Don't expect specific status
            if result["status_code"] not in [200, 422, 400]:
                self.log_warning("unexpected_status", "/search", 
                               f"Edge case returned {result['status_code']}", {"data": data})
    
    def test_feedback_endpoints(self, pass_num: int):
        """Test feedback and signals endpoints"""
        # Feedback tests
        for _ in range(2):
            feedback_data = {
                "content_id": f"doc_{self.random_string(10)}",
                "feedback_type": random.choice(self.feedback_types),
                "rating": random.randint(1, 5),
                "comment": f"Test feedback {self.random_string(20)}"
            }
            self.test_endpoint("POST", "/feedback", feedback_data, 202)
        
        # Signal tests
        for _ in range(2):
            signal_data = {
                "query_id": f"q_{self.random_string(8)}",
                "session_id": f"s_{self.random_string(8)}",
                "signal_type": random.choice(self.signal_types),
                "content_id": f"doc_{self.random_string(10)}",
                "result_position": random.randint(0, 20)
            }
            self.test_endpoint("POST", "/signals", signal_data, 202)
    
    def test_config_endpoints(self, pass_num: int):
        """Test configuration endpoints"""
        self.test_endpoint("GET", "/config", None, 200)
        self.test_endpoint("GET", "/collections", None, 200)
        
        # Config update test
        config_data = {
            "key": f"test.key_{pass_num}",
            "value": f"test_value_{self.random_string(10)}",
            "description": f"Test config from pass {pass_num}"
        }
        self.test_endpoint("POST", "/config", config_data, 202)
    
    def test_provider_endpoints(self, pass_num: int):
        """Test provider management endpoints"""
        self.test_endpoint("GET", "/providers", None, 200)
        self.test_endpoint("GET", "/provider-registry-status", None, 200)
        
        # Provider tests
        providers = ["ollama", "openai", "openrouter", "anthropic", "litellm"]
        provider = random.choice(providers)
        
        test_configs = {
            "ollama": {"base_url": "http://localhost:11434/api"},
            "openai": {"base_url": "https://api.openai.com/v1", "api_key": "test-key"},
            "openrouter": {"api_key": "test-key", "base_url": "https://openrouter.ai/api/v1"},
            "anthropic": {"api_key": "test-key", "base_url": "https://api.anthropic.com"},
            "litellm": {"base_url": "http://localhost:4000", "api_key": ""}
        }
        
        config = test_configs.get(provider, {"base_url": "http://localhost:8000"})
        self.test_endpoint("POST", f"/providers/{provider}/test", config, 200)
    
    def test_admin_endpoints(self, pass_num: int):
        """Test admin endpoints"""
        endpoints = [
            ("GET", "/admin/search-content?limit=10", None, 200),
            ("GET", "/admin/activity/recent?limit=5", None, 200),
            ("GET", "/admin/activity/searches?limit=5", None, 200),
            ("GET", "/admin/activity/errors?limit=5", None, 200),
            ("GET", "/admin/dashboard", None, 200),
        ]
        
        for method, endpoint, data, expected in endpoints:
            self.test_endpoint(method, endpoint, data, expected)
    
    def test_ingestion_endpoints(self, pass_num: int):
        """Test ingestion endpoints"""
        # File upload simulation
        test_content = f"Test document content for pass {pass_num}\n" + self.random_string(100)
        files = {'file': (f'test_{pass_num}.txt', test_content, 'text/plain')}
        
        try:
            response = self.session.post(f"{self.base_url}/ingestion/upload", files=files, timeout=10)
            if response.status_code != 200:
                self.log_warning("upload_issue", "/ingestion/upload", 
                               f"Upload returned {response.status_code}")
        except Exception as e:
            self.log_error("upload_error", "/ingestion/upload", str(e))
    
    def test_enrichment_endpoints(self, pass_num: int):
        """Test enrichment endpoints (expected to return 503)"""
        endpoints = [
            ("POST", "/enrichment/enrich", {"content_id": f"doc_{pass_num}", "priority": "normal"}, 503),
            ("GET", f"/enrichment/status/doc_{pass_num}", None, 503),
            ("POST", "/enrichment/gap-analysis", {"query": random.choice(self.search_queries)}, 503),
            ("GET", "/enrichment/metrics", None, 503),
            ("GET", "/enrichment/health", None, 503),
        ]
        
        for method, endpoint, data, expected in endpoints:
            self.test_endpoint(method, endpoint, data, expected)
    
    def run_single_pass(self, pass_num: int):
        """Run a complete test pass"""
        print(f"{Colors.BLUE}Pass {pass_num}/100{Colors.ENDC}", end=" ", flush=True)
        
        try:
            self.test_health_endpoints(pass_num)
            self.test_search_endpoints(pass_num)
            self.test_feedback_endpoints(pass_num)
            self.test_config_endpoints(pass_num)
            self.test_provider_endpoints(pass_num)
            self.test_admin_endpoints(pass_num)
            self.test_ingestion_endpoints(pass_num)
            self.test_enrichment_endpoints(pass_num)
            
            print(f"{Colors.GREEN}✓{Colors.ENDC}", end="", flush=True)
            
        except Exception as e:
            self.log_error("pass_failure", f"pass_{pass_num}", str(e), 
                          {"traceback": traceback.format_exc()})
            print(f"{Colors.RED}✗{Colors.ENDC}", end="", flush=True)
        
        # Add small delay to prevent overwhelming the server
        time.sleep(0.1)
    
    def run_stress_test(self, passes: int = 100, concurrent: bool = False):
        """Run comprehensive stress test"""
        print(f"{Colors.BOLD}API Stress Testing - {passes} Passes{Colors.ENDC}")
        print(f"Base URL: {self.base_url}")
        print(f"Started at: {datetime.now().isoformat()}")
        print()
        
        start_time = time.time()
        
        if concurrent:
            # Run some passes concurrently to test race conditions
            print("Running concurrent stress test...")
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(self.run_single_pass, i+1) for i in range(passes)]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        print(f"{Colors.RED}Concurrent error: {e}{Colors.ENDC}")
        else:
            # Sequential testing
            for i in range(passes):
                self.run_single_pass(i + 1)
                if (i + 1) % 10 == 0:
                    print(f" ({i+1}/100)")
                elif (i + 1) % 5 == 0:
                    print(" |", end="", flush=True)
        
        total_time = time.time() - start_time
        print(f"\n\n{Colors.BOLD}Stress Test Complete{Colors.ENDC}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Average time per pass: {total_time/passes:.2f}s")
        
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive analysis report"""
        print(f"\n{Colors.BOLD}=== COMPREHENSIVE ANALYSIS REPORT ==={Colors.ENDC}")
        
        # Error Analysis
        if self.errors:
            print(f"\n{Colors.RED}🚨 ERRORS FOUND ({len(self.errors)}){Colors.ENDC}")
            error_categories = {}
            for error in self.errors:
                cat = error["category"]
                error_categories[cat] = error_categories.get(cat, 0) + 1
            
            for category, count in sorted(error_categories.items()):
                print(f"  {category}: {count} occurrences")
                
            # Show sample errors
            print(f"\n{Colors.RED}Sample Errors:{Colors.ENDC}")
            for error in self.errors[:5]:  # Show first 5
                print(f"  [{error['category']}] {error['endpoint']}: {error['error']}")
        else:
            print(f"\n{Colors.GREEN}✅ NO ERRORS FOUND{Colors.ENDC}")
        
        # Warning Analysis
        if self.warnings:
            print(f"\n{Colors.YELLOW}⚠️  WARNINGS FOUND ({len(self.warnings)}){Colors.ENDC}")
            warning_categories = {}
            for warning in self.warnings:
                cat = warning["category"]
                warning_categories[cat] = warning_categories.get(cat, 0) + 1
            
            for category, count in sorted(warning_categories.items()):
                print(f"  {category}: {count} occurrences")
        else:
            print(f"\n{Colors.GREEN}✅ NO WARNINGS FOUND{Colors.ENDC}")
        
        # Performance Analysis
        if self.performance_issues:
            print(f"\n{Colors.YELLOW}🐌 PERFORMANCE ISSUES ({len(self.performance_issues)}){Colors.ENDC}")
            slow_endpoints = {}
            for issue in self.performance_issues:
                endpoint = issue["endpoint"]
                slow_endpoints[endpoint] = slow_endpoints.get(endpoint, [])
                slow_endpoints[endpoint].append(issue["duration"])
            
            for endpoint, durations in sorted(slow_endpoints.items()):
                avg_duration = sum(durations) / len(durations)
                max_duration = max(durations)
                print(f"  {endpoint}: avg={avg_duration:.2f}s, max={max_duration:.2f}s ({len(durations)} slow calls)")
        else:
            print(f"\n{Colors.GREEN}⚡ NO PERFORMANCE ISSUES{Colors.ENDC}")
        
        # Recommendations
        print(f"\n{Colors.BOLD}📋 RECOMMENDATIONS{Colors.ENDC}")
        recommendations = []
        
        if any(e["category"] == "timeout" for e in self.errors):
            recommendations.append("• Investigate timeout issues - consider increasing timeout values or optimizing slow endpoints")
        
        if any(e["category"] == "json_parse" for e in self.errors):
            recommendations.append("• Fix JSON parsing errors - ensure all JSON responses are properly formatted")
        
        if any(w["category"] == "missing_field" for w in self.warnings):
            recommendations.append("• Add missing response fields for better API consistency")
        
        if self.performance_issues:
            slow_count = len([p for p in self.performance_issues if p["duration"] > 5])
            if slow_count > 0:
                recommendations.append(f"• Optimize {slow_count} slow endpoints (>5s response time)")
        
        if any(e["category"] == "status_mismatch" for e in self.errors):
            recommendations.append("• Review unexpected status codes - may indicate error handling issues")
        
        if not recommendations:
            recommendations.append("🎉 System appears stable under stress testing!")
        
        for rec in recommendations:
            print(f"  {rec}")
        
        # Final assessment
        error_count = len(self.errors)
        warning_count = len(self.warnings)
        perf_count = len(self.performance_issues)
        
        if error_count == 0 and warning_count == 0 and perf_count == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}🏆 EXCELLENT: System passed 100-pass stress test with no issues!{Colors.ENDC}")
        elif error_count == 0 and warning_count < 5 and perf_count < 10:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✅ GOOD: System is stable with minor issues to address{Colors.ENDC}")
        elif error_count < 5 and warning_count < 20:
            print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  FAIR: System needs attention but is functional{Colors.ENDC}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}🚨 NEEDS WORK: System has significant issues requiring fixes{Colors.ENDC}")
        
        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "performance_issues": self.performance_issues,
            "recommendations": recommendations
        }

def main():
    tester = APIStressTester()
    
    # Run sequential stress test
    print("🔥 Starting comprehensive 100-pass API stress test...")
    report = tester.run_stress_test(passes=100, concurrent=False)
    
    # Save detailed report
    with open("/home/lab/docaiche/STRESS_TEST_REPORT.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n📄 Detailed report saved to: STRESS_TEST_REPORT.json")

if __name__ == "__main__":
    main()