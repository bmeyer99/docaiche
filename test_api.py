#!/usr/bin/env python3
"""
Docaiche API Testing Script
Test all API endpoints with proper JSON handling and detailed reporting
"""

import json
import time
import requests
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import sys
import argparse

# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class APITester:
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.passed = 0
        self.failed = 0
        self.session = requests.Session()
        
    def print_header(self, text: str):
        print(f"\n{Colors.BLUE}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BLUE}{text}{Colors.ENDC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
        
    def print_test(self, text: str):
        print(f"\n{Colors.YELLOW}Testing: {text}{Colors.ENDC}")
        
    def print_success(self, text: str):
        print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")
        self.passed += 1
        
    def print_error(self, text: str):
        print(f"{Colors.RED}✗ {text}{Colors.ENDC}")
        self.failed += 1
        
    def test_endpoint(self, method: str, endpoint: str, 
                     data: Optional[Dict] = None, 
                     expected_status: int = 200,
                     description: str = "") -> Tuple[bool, Any]:
        """Test a single endpoint"""
        self.print_test(description or f"{method} {endpoint}")
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                response = self.session.get(url)
            elif method == "POST":
                response = self.session.post(url, json=data)
            elif method == "DELETE":
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            if response.status_code == expected_status:
                self.print_success(f"Status: {response.status_code} (Expected: {expected_status})")
                
                # Try to parse JSON response
                try:
                    json_response = response.json()
                    print(json.dumps(json_response, indent=2)[:500] + "..." if len(json.dumps(json_response)) > 500 else json.dumps(json_response, indent=2))
                except:
                    print(response.text[:200] + "..." if len(response.text) > 200 else response.text)
                    
                return True, response
            else:
                self.print_error(f"Status: {response.status_code} (Expected: {expected_status})")
                print(f"Response: {response.text[:200]}...")
                return False, response
                
        except Exception as e:
            self.print_error(f"Exception: {str(e)}")
            return False, None
            
        finally:
            # Rate limiting delay
            time.sleep(0.5)
            
    def run_all_tests(self):
        """Run all API endpoint tests"""
        print(f"{Colors.BOLD}Docaiche API Testing Suite{Colors.ENDC}")
        print(f"Base URL: {self.base_url}")
        print(f"Started at: {datetime.now().isoformat()}")
        
        # 1. Health & Monitoring
        self.print_header("HEALTH & MONITORING ENDPOINTS")
        
        self.test_endpoint("GET", "/health", 
                          description="Health Check")
        
        self.test_endpoint("GET", "/stats", 
                          description="System Statistics")
        
        self.test_endpoint("GET", "/analytics?timeRange=24h", 
                          description="Analytics (24h)")
        
        # 2. Search Endpoints
        self.print_header("SEARCH ENDPOINTS")
        
        self.test_endpoint("GET", "/search?q=python%20async&limit=5", 
                          description="Search Documents (GET)")
        
        self.test_endpoint("POST", "/search", 
                          data={
                              "query": "fastapi tutorial",
                              "technology_hint": "python",
                              "limit": 10
                          },
                          description="Search Documents (POST)")
        
        self.test_endpoint("POST", "/feedback",
                          data={
                              "content_id": "doc_001",
                              "feedback_type": "helpful",
                              "rating": 5,
                              "comment": "Very helpful"
                          },
                          expected_status=202,
                          description="Submit Feedback")
        
        self.test_endpoint("POST", "/signals",
                          data={
                              "query_id": "q123",
                              "session_id": "s456",
                              "signal_type": "click",
                              "content_id": "doc_001",
                              "result_position": 0
                          },
                          expected_status=202,
                          description="Submit Signal")
        
        # 3. Configuration Endpoints
        self.print_header("CONFIGURATION ENDPOINTS")
        
        self.test_endpoint("GET", "/config",
                          description="Get Configuration")
        
        self.test_endpoint("GET", "/collections",
                          description="Get Collections")
        
        self.test_endpoint("POST", "/config",
                          data={
                              "key": "app.debug",
                              "value": False,
                              "description": "Disable debug mode"
                          },
                          expected_status=202,
                          description="Update Configuration")
        
        # 4. Provider Management
        self.print_header("PROVIDER MANAGEMENT ENDPOINTS")
        
        self.test_endpoint("GET", "/providers",
                          description="List Providers")
        
        self.test_endpoint("POST", "/providers/ollama/test",
                          data={
                              "base_url": "http://localhost:11434/api"
                          },
                          description="Test Ollama Provider")
        
        self.test_endpoint("POST", "/providers/openai/test",
                          data={
                              "base_url": "https://api.openai.com/v1",
                              "api_key": "sk-test-key"
                          },
                          description="Test OpenAI Provider")
        
        # 5. Admin Endpoints
        self.print_header("ADMIN ENDPOINTS")
        
        self.test_endpoint("GET", "/admin/search-content?limit=10",
                          description="Admin Search Content")
        
        self.test_endpoint("GET", "/admin/activity/recent?limit=5",
                          description="Get Recent Activity")
        
        self.test_endpoint("GET", "/admin/activity/searches?limit=5",
                          description="Get Recent Searches")
        
        self.test_endpoint("GET", "/admin/activity/errors?limit=5",
                          description="Get Recent Errors")
        
        self.test_endpoint("GET", "/admin/dashboard",
                          description="Get Dashboard Data")
        
        # 6. Ingestion Endpoints
        self.print_header("INGESTION ENDPOINTS")
        
        # Create test file for upload
        test_content = "This is test content for document upload"
        files = {'file': ('test.txt', test_content, 'text/plain')}
        
        self.print_test("Upload Document")
        try:
            response = self.session.post(f"{self.base_url}/ingestion/upload", files=files)
            if response.status_code == 200:
                self.print_success(f"Status: {response.status_code}")
                print(response.json())
            else:
                self.print_error(f"Status: {response.status_code}")
        except Exception as e:
            self.print_error(f"Upload failed: {str(e)}")
        
        # 7. Enrichment Endpoints (might fail if service not available)
        self.print_header("ENRICHMENT ENDPOINTS")
        
        self.test_endpoint("POST", "/enrichment/enrich",
                          data={
                              "content_id": "doc_001",
                              "priority": "normal"
                          },
                          expected_status=503,  # Expected if service unavailable
                          description="Enrich Content")
        
        self.test_endpoint("GET", "/enrichment/status/doc_001",
                          expected_status=503,
                          description="Get Enrichment Status")
        
        self.test_endpoint("POST", "/enrichment/gap-analysis",
                          data={
                              "query": "kubernetes deployment"
                          },
                          expected_status=503,
                          description="Gap Analysis")
        
        self.test_endpoint("GET", "/enrichment/metrics",
                          expected_status=503,
                          description="Get Enrichment Metrics")
        
        self.test_endpoint("GET", "/enrichment/health",
                          expected_status=503,
                          description="Enrichment Health Check")
        
        # Summary
        self.print_header("TEST SUMMARY")
        total = self.passed + self.failed
        print(f"{Colors.GREEN}Passed: {self.passed}{Colors.ENDC}")
        print(f"{Colors.RED}Failed: {self.failed}{Colors.ENDC}")
        print(f"Total: {total}")
        print(f"Success Rate: {(self.passed/total*100):.1f}%" if total > 0 else "N/A")
        
        return self.failed == 0

def main():
    parser = argparse.ArgumentParser(description='Test Docaiche API endpoints')
    parser.add_argument('--base-url', default='http://localhost:8000/api/v1',
                       help='Base URL for the API (default: http://localhost:8000/api/v1)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    tester = APITester(args.base_url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()