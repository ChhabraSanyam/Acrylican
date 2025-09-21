"""
Comprehensive test suite runner for the Artisan Promotion Platform.

This module provides utilities to run different categories of tests
and generate comprehensive reports.
"""

import pytest
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import json
import time
from datetime import datetime


class TestSuiteRunner:
    """Main test suite runner with categorized test execution."""
    
    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path) if base_path else Path(__file__).parent
        self.results = {}
        
    def run_unit_tests(self) -> Dict[str, Any]:
        """Run all unit tests."""
        print("🧪 Running Unit Tests...")
        start_time = time.time()
        
        result = pytest.main([
            "-m", "unit",
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov/unit",
            "--junit-xml=test-results/unit-tests.xml",
            "-v"
        ])
        
        duration = time.time() - start_time
        self.results['unit'] = {
            'exit_code': result,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }
        
        return self.results['unit']
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """Run all integration tests."""
        print("🔗 Running Integration Tests...")
        start_time = time.time()
        
        result = pytest.main([
            "-m", "integration",
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov/integration",
            "--junit-xml=test-results/integration-tests.xml",
            "-v"
        ])
        
        duration = time.time() - start_time
        self.results['integration'] = {
            'exit_code': result,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }
        
        return self.results['integration']
    
    def run_e2e_tests(self) -> Dict[str, Any]:
        """Run end-to-end tests."""
        print("🎯 Running End-to-End Tests...")
        start_time = time.time()
        
        result = pytest.main([
            "-m", "e2e",
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov/e2e",
            "--junit-xml=test-results/e2e-tests.xml",
            "-v",
            "--maxfail=5"  # Stop after 5 failures for E2E
        ])
        
        duration = time.time() - start_time
        self.results['e2e'] = {
            'exit_code': result,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }
        
        return self.results['e2e']
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests."""
        print("⚡ Running Performance Tests...")
        start_time = time.time()
        
        result = pytest.main([
            "-m", "performance",
            "--junit-xml=test-results/performance-tests.xml",
            "-v",
            "--tb=short"
        ])
        
        duration = time.time() - start_time
        self.results['performance'] = {
            'exit_code': result,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }
        
        return self.results['performance']
    
    def run_security_tests(self) -> Dict[str, Any]:
        """Run security tests."""
        print("🔒 Running Security Tests...")
        start_time = time.time()
        
        result = pytest.main([
            "-m", "security",
            "--junit-xml=test-results/security-tests.xml",
            "-v"
        ])
        
        duration = time.time() - start_time
        self.results['security'] = {
            'exit_code': result,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }
        
        return self.results['security']
    
    def run_platform_tests(self, platform: str = None) -> Dict[str, Any]:
        """Run platform-specific tests."""
        if platform:
            print(f"🌐 Running {platform.title()} Platform Tests...")
            marker = platform
        else:
            print("🌐 Running All Platform Tests...")
            marker = "platform"
        
        start_time = time.time()
        
        result = pytest.main([
            "-m", marker,
            "--junit-xml=f'test-results/{marker}-tests.xml'",
            "-v"
        ])
        
        duration = time.time() - start_time
        test_key = f'platform_{platform}' if platform else 'platform_all'
        self.results[test_key] = {
            'exit_code': result,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }
        
        return self.results[test_key]
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run the complete test suite."""
        print("🚀 Running Complete Test Suite...")
        start_time = time.time()
        
        # Create results directory
        os.makedirs("test-results", exist_ok=True)
        os.makedirs("htmlcov", exist_ok=True)
        
        # Run all test categories
        self.run_unit_tests()
        self.run_integration_tests()
        self.run_e2e_tests()
        self.run_performance_tests()
        self.run_security_tests()
        self.run_platform_tests()
        
        total_duration = time.time() - start_time
        
        # Generate summary report
        summary = self.generate_summary_report(total_duration)
        
        return summary
    
    def generate_summary_report(self, total_duration: float) -> Dict[str, Any]:
        """Generate a comprehensive test summary report."""
        summary = {
            'total_duration': total_duration,
            'timestamp': datetime.now().isoformat(),
            'results': self.results,
            'overall_status': 'PASSED' if all(
                result.get('exit_code', 1) == 0 
                for result in self.results.values()
            ) else 'FAILED'
        }
        
        # Save summary to file
        with open('test-results/test-summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Print summary
        self.print_summary_report(summary)
        
        return summary
    
    def print_summary_report(self, summary: Dict[str, Any]):
        """Print a formatted summary report."""
        print("\n" + "="*80)
        print("📊 TEST SUITE SUMMARY REPORT")
        print("="*80)
        print(f"Overall Status: {summary['overall_status']}")
        print(f"Total Duration: {summary['total_duration']:.2f} seconds")
        print(f"Timestamp: {summary['timestamp']}")
        print("\nTest Category Results:")
        print("-" * 40)
        
        for category, result in summary['results'].items():
            status = "✅ PASSED" if result['exit_code'] == 0 else "❌ FAILED"
            duration = result['duration']
            print(f"{category.upper():15} | {status} | {duration:6.2f}s")
        
        print("\n" + "="*80)
        
        if summary['overall_status'] == 'FAILED':
            print("❌ Some tests failed. Check individual test reports for details.")
            print("📁 Test reports available in: test-results/")
            print("📊 Coverage reports available in: htmlcov/")
        else:
            print("✅ All tests passed successfully!")
        
        print("="*80)


def run_quick_tests():
    """Run a quick subset of tests for development."""
    print("⚡ Running Quick Test Suite...")
    
    result = pytest.main([
        "-m", "not slow and not external",
        "--cov=app",
        "--cov-report=term-missing",
        "-x",  # Stop on first failure
        "-v"
    ])
    
    return result


def run_ci_tests():
    """Run tests suitable for CI/CD pipeline."""
    print("🔄 Running CI Test Suite...")
    
    result = pytest.main([
        "--cov=app",
        "--cov-report=term-missing",
        "--cov-report=xml:coverage.xml",
        "--junit-xml=test-results/ci-tests.xml",
        "--maxfail=10",
        "-v"
    ])
    
    return result


if __name__ == "__main__":
    runner = TestSuiteRunner()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "unit":
            runner.run_unit_tests()
        elif command == "integration":
            runner.run_integration_tests()
        elif command == "e2e":
            runner.run_e2e_tests()
        elif command == "performance":
            runner.run_performance_tests()
        elif command == "security":
            runner.run_security_tests()
        elif command == "platform":
            platform = sys.argv[2] if len(sys.argv) > 2 else None
            runner.run_platform_tests(platform)
        elif command == "quick":
            run_quick_tests()
        elif command == "ci":
            run_ci_tests()
        elif command == "all":
            runner.run_all_tests()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: unit, integration, e2e, performance, security, platform, quick, ci, all")
    else:
        # Default to running all tests
        runner.run_all_tests()