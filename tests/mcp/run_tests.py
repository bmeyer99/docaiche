#!/usr/bin/env python3
"""
MCP Test Suite Runner
====================

Comprehensive test runner for MCP implementation with coverage reporting,
performance analysis, and security validation.
"""

import sys
import os
import argparse
import subprocess
import json
from pathlib import Path
from datetime import datetime


class MCPTestRunner:
    """Test runner for MCP test suite."""
    
    def __init__(self, project_root=None):
        self.project_root = Path(project_root or os.getcwd())
        self.test_dir = self.project_root / "tests" / "mcp"
        self.results_dir = self.project_root / "test_results" / "mcp"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
    def run_unit_tests(self, verbose=False):
        """Run unit tests."""
        print("\n" + "="*60)
        print("Running MCP Unit Tests")
        print("="*60)
        
        cmd = [
            "pytest",
            "-m", "unit",
            str(self.test_dir),
            f"--junit-xml={self.results_dir}/unit_results.xml",
            f"--html={self.results_dir}/unit_report.html",
            "--self-contained-html"
        ]
        
        if verbose:
            cmd.append("-vv")
            
        return subprocess.run(cmd).returncode
    
    def run_integration_tests(self, verbose=False):
        """Run integration tests."""
        print("\n" + "="*60)
        print("Running MCP Integration Tests")
        print("="*60)
        
        cmd = [
            "pytest",
            "-m", "integration",
            str(self.test_dir),
            f"--junit-xml={self.results_dir}/integration_results.xml",
            f"--html={self.results_dir}/integration_report.html",
            "--self-contained-html"
        ]
        
        if verbose:
            cmd.append("-vv")
            
        return subprocess.run(cmd).returncode
    
    def run_security_tests(self, verbose=False):
        """Run security tests."""
        print("\n" + "="*60)
        print("Running MCP Security Tests")
        print("="*60)
        
        cmd = [
            "pytest",
            "-m", "security",
            str(self.test_dir),
            f"--junit-xml={self.results_dir}/security_results.xml",
            f"--html={self.results_dir}/security_report.html",
            "--self-contained-html"
        ]
        
        if verbose:
            cmd.append("-vv")
            
        return subprocess.run(cmd).returncode
    
    def run_system_tests(self, verbose=False):
        """Run system tests."""
        print("\n" + "="*60)
        print("Running MCP System Tests")
        print("="*60)
        
        cmd = [
            "pytest",
            "-m", "system",
            str(self.test_dir),
            f"--junit-xml={self.results_dir}/system_results.xml",
            f"--html={self.results_dir}/system_report.html",
            "--self-contained-html"
        ]
        
        if verbose:
            cmd.append("-vv")
            
        return subprocess.run(cmd).returncode
    
    def run_all_tests(self, verbose=False, parallel=False):
        """Run all tests with coverage."""
        print("\n" + "="*60)
        print("Running Complete MCP Test Suite")
        print("="*60)
        
        cmd = [
            "pytest",
            str(self.test_dir),
            f"--junit-xml={self.results_dir}/all_results.xml",
            f"--html={self.results_dir}/test_report.html",
            "--self-contained-html",
            "--cov=src/mcp",
            f"--cov-report=html:{self.results_dir}/coverage",
            "--cov-report=json",
            "--cov-report=term"
        ]
        
        if verbose:
            cmd.append("-vv")
            
        if parallel:
            cmd.extend(["-n", "auto"])
            
        return subprocess.run(cmd).returncode
    
    def run_performance_tests(self, verbose=False):
        """Run performance tests."""
        print("\n" + "="*60)
        print("Running MCP Performance Tests")
        print("="*60)
        
        cmd = [
            "pytest",
            "-m", "performance",
            str(self.test_dir),
            f"--junit-xml={self.results_dir}/performance_results.xml",
            "--benchmark-only",
            "--benchmark-json=" + str(self.results_dir / "benchmark.json")
        ]
        
        if verbose:
            cmd.append("-vv")
            
        return subprocess.run(cmd).returncode
    
    def analyze_coverage(self):
        """Analyze test coverage."""
        print("\n" + "="*60)
        print("Analyzing Test Coverage")
        print("="*60)
        
        coverage_file = self.results_dir.parent / ".coverage"
        if not coverage_file.exists():
            print("No coverage data found. Run tests first.")
            return
        
        # Generate coverage report
        subprocess.run([
            "coverage",
            "report",
            "--include=src/mcp/*",
            "--sort=cover"
        ])
        
        # Load coverage JSON
        subprocess.run([
            "coverage",
            "json",
            "-o",
            str(self.results_dir / "coverage.json")
        ])
        
        with open(self.results_dir / "coverage.json") as f:
            coverage_data = json.load(f)
            
        total_coverage = coverage_data["totals"]["percent_covered"]
        print(f"\nTotal Coverage: {total_coverage:.1f}%")
        
        # Check coverage thresholds
        if total_coverage < 80:
            print("⚠️  Warning: Coverage below 80% threshold")
            return 1
        else:
            print("✅ Coverage meets requirements")
            return 0
    
    def run_linting(self):
        """Run code quality checks."""
        print("\n" + "="*60)
        print("Running Code Quality Checks")
        print("="*60)
        
        # Run pylint
        print("\nRunning pylint...")
        pylint_result = subprocess.run([
            "pylint",
            "src/mcp",
            "--rcfile=.pylintrc",
            f"--output={self.results_dir}/pylint_report.txt"
        ]).returncode
        
        # Run flake8
        print("\nRunning flake8...")
        flake8_result = subprocess.run([
            "flake8",
            "src/mcp",
            "--config=.flake8",
            f"--output-file={self.results_dir}/flake8_report.txt"
        ]).returncode
        
        # Run mypy
        print("\nRunning mypy...")
        mypy_result = subprocess.run([
            "mypy",
            "src/mcp",
            "--config-file=mypy.ini",
            f"--junit-xml={self.results_dir}/mypy_results.xml"
        ]).returncode
        
        return max(pylint_result, flake8_result, mypy_result)
    
    def generate_report(self):
        """Generate comprehensive test report."""
        print("\n" + "="*60)
        print("Generating Test Report")
        print("="*60)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "test_results": {},
            "coverage": {},
            "quality": {}
        }
        
        # Collect test results
        for result_file in self.results_dir.glob("*_results.xml"):
            test_type = result_file.stem.replace("_results", "")
            # Parse JUnit XML (simplified)
            report["test_results"][test_type] = {
                "file": str(result_file),
                "status": "completed"
            }
        
        # Add coverage data
        coverage_json = self.results_dir / "coverage.json"
        if coverage_json.exists():
            with open(coverage_json) as f:
                report["coverage"] = json.load(f)["totals"]
        
        # Save report
        report_file = self.results_dir / "test_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
            
        print(f"Report saved to: {report_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("Test Summary")
        print("="*60)
        print(f"Timestamp: {report['timestamp']}")
        print(f"Test Types Run: {', '.join(report['test_results'].keys())}")
        if report["coverage"]:
            print(f"Coverage: {report['coverage']['percent_covered']:.1f}%")
        print("="*60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="MCP Test Suite Runner"
    )
    parser.add_argument(
        "--type",
        choices=["all", "unit", "integration", "system", "security", "performance"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Run tests in parallel"
    )
    parser.add_argument(
        "--lint",
        action="store_true",
        help="Run linting checks"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Analyze coverage after tests"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate comprehensive report"
    )
    
    args = parser.parse_args()
    
    # Create test runner
    runner = MCPTestRunner()
    
    # Run requested tests
    exit_code = 0
    
    if args.lint:
        exit_code = max(exit_code, runner.run_linting())
    
    if args.type == "all":
        exit_code = max(exit_code, runner.run_all_tests(
            verbose=args.verbose,
            parallel=args.parallel
        ))
    elif args.type == "unit":
        exit_code = max(exit_code, runner.run_unit_tests(args.verbose))
    elif args.type == "integration":
        exit_code = max(exit_code, runner.run_integration_tests(args.verbose))
    elif args.type == "system":
        exit_code = max(exit_code, runner.run_system_tests(args.verbose))
    elif args.type == "security":
        exit_code = max(exit_code, runner.run_security_tests(args.verbose))
    elif args.type == "performance":
        exit_code = max(exit_code, runner.run_performance_tests(args.verbose))
    
    if args.coverage:
        exit_code = max(exit_code, runner.analyze_coverage())
    
    if args.report:
        runner.generate_report()
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())