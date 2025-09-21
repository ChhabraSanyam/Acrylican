#!/usr/bin/env python3
"""
Comprehensive test runner for the Artisan Promotion Platform.

This script runs the complete test suite for both backend and frontend,
generates coverage reports, and provides a comprehensive summary.
"""

import os
import sys
import subprocess
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


class ComprehensiveTestRunner:
    """Main test runner for the entire platform."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.backend_path = self.project_root / "backend"
        self.frontend_path = self.project_root / "frontend"
        self.results = {}
        self.start_time = time.time()
    
    def run_backend_tests(self) -> Dict[str, Any]:
        """Run all backend tests."""
        print("🔧 Running Backend Tests...")
        print("=" * 50)
        
        backend_results = {}
        
        # Change to backend directory
        os.chdir(self.backend_path)
        
        # Create results directory
        os.makedirs("test-results", exist_ok=True)
        
        # Run unit tests
        print("📋 Running Unit Tests...")
        unit_result = self._run_command([
            "python", "-m", "pytest",
            "-m", "unit",
            "--cov=app",
            "--cov-report=xml:test-results/coverage-unit.xml",
            "--cov-report=html:htmlcov/unit",
            "--junit-xml=test-results/unit-tests.xml",
            "--tb=short",
            "-v"
        ])
        backend_results['unit'] = unit_result
        
        # Run integration tests
        print("🔗 Running Integration Tests...")
        integration_result = self._run_command([
            "python", "-m", "pytest",
            "-m", "integration",
            "--cov=app",
            "--cov-report=xml:test-results/coverage-integration.xml",
            "--cov-report=html:htmlcov/integration",
            "--junit-xml=test-results/integration-tests.xml",
            "--tb=short",
            "-v"
        ])
        backend_results['integration'] = integration_result
        
        # Run E2E tests
        print("🎯 Running E2E Tests...")
        e2e_result = self._run_command([
            "python", "-m", "pytest",
            "-m", "e2e",
            "--junit-xml=test-results/e2e-tests.xml",
            "--tb=short",
            "--maxfail=5",
            "-v"
        ])
        backend_results['e2e'] = e2e_result
        
        # Run performance tests
        print("⚡ Running Performance Tests...")
        perf_result = self._run_command([
            "python", "-m", "pytest",
            "-m", "performance",
            "--junit-xml=test-results/performance-tests.xml",
            "--tb=short",
            "-v"
        ])
        backend_results['performance'] = perf_result
        
        # Run security tests
        print("🔒 Running Security Tests...")
        security_result = self._run_command([
            "python", "-m", "pytest",
            "-m", "security",
            "--junit-xml=test-results/security-tests.xml",
            "--tb=short",
            "-v"
        ])
        backend_results['security'] = security_result
        
        # Generate comprehensive coverage report
        print("📊 Generating Comprehensive Coverage Report...")
        coverage_result = self._run_command([
            "python", "-m", "pytest",
            "--cov=app",
            "--cov-report=xml:test-results/coverage-comprehensive.xml",
            "--cov-report=html:htmlcov/comprehensive",
            "--cov-report=term-missing",
            "--tb=no",
            "-q"
        ])
        backend_results['coverage'] = coverage_result
        
        return backend_results
    
    def run_frontend_tests(self) -> Dict[str, Any]:
        """Run all frontend tests."""
        print("\n🎨 Running Frontend Tests...")
        print("=" * 50)
        
        frontend_results = {}
        
        # Change to frontend directory
        os.chdir(self.frontend_path)
        
        # Run linting
        print("🔍 Running ESLint...")
        lint_result = self._run_command(["npm", "run", "lint"])
        frontend_results['lint'] = lint_result
        
        # Run type checking
        print("📝 Running Type Check...")
        typecheck_result = self._run_command(["npm", "run", "type-check"])
        frontend_results['typecheck'] = typecheck_result
        
        # Run tests with coverage
        print("🧪 Running Frontend Tests with Coverage...")
        test_result = self._run_command(["npm", "run", "test:coverage"])
        frontend_results['tests'] = test_result
        
        return frontend_results
    
    def run_security_scans(self) -> Dict[str, Any]:
        """Run security scans."""
        print("\n🛡️ Running Security Scans...")
        print("=" * 50)
        
        security_results = {}
        
        # Change to backend directory for security scans
        os.chdir(self.backend_path)
        
        # Run Bandit security scan
        print("🔍 Running Bandit Security Scan...")
        bandit_result = self._run_command([
            "bandit", "-r", "app/", "-f", "json", "-o", "test-results/bandit-report.json"
        ], ignore_errors=True)
        security_results['bandit'] = bandit_result
        
        # Run Safety check
        print("🔒 Running Safety Dependency Check...")
        safety_result = self._run_command([
            "safety", "check", "--json", "--output", "test-results/safety-report.json"
        ], ignore_errors=True)
        security_results['safety'] = safety_result
        
        return security_results
    
    def run_build_tests(self) -> Dict[str, Any]:
        """Run build and deployment tests."""
        print("\n🏗️ Running Build Tests...")
        print("=" * 50)
        
        build_results = {}
        
        # Change to project root
        os.chdir(self.project_root)
        
        # Test backend build
        print("🔧 Testing Backend Build...")
        backend_build_result = self._run_command([
            "docker", "build", "-t", "artisan-platform-backend:test", "backend/"
        ])
        build_results['backend_build'] = backend_build_result
        
        # Test frontend build
        print("🎨 Testing Frontend Build...")
        frontend_build_result = self._run_command([
            "docker", "build", "-t", "artisan-platform-frontend:test", "frontend/"
        ])
        build_results['frontend_build'] = frontend_build_result
        
        return build_results
    
    def _run_command(self, command: List[str], ignore_errors: bool = False) -> Dict[str, Any]:
        """Run a command and capture results."""
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            duration = time.time() - start_time
            
            return {
                'command': ' '.join(command),
                'returncode': result.returncode,
                'duration': duration,
                'success': result.returncode == 0 or ignore_errors,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        
        except subprocess.TimeoutExpired:
            return {
                'command': ' '.join(command),
                'returncode': -1,
                'duration': time.time() - start_time,
                'success': False,
                'stdout': '',
                'stderr': 'Command timed out after 10 minutes'
            }
        
        except Exception as e:
            return {
                'command': ' '.join(command),
                'returncode': -1,
                'duration': time.time() - start_time,
                'success': False,
                'stdout': '',
                'stderr': str(e)
            }
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate a comprehensive summary report."""
        total_duration = time.time() - self.start_time
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_duration': total_duration,
            'results': self.results,
            'overall_success': self._calculate_overall_success(),
            'statistics': self._calculate_statistics()
        }
        
        return summary
    
    def _calculate_overall_success(self) -> bool:
        """Calculate overall success status."""
        for category, tests in self.results.items():
            if isinstance(tests, dict):
                for test_name, result in tests.items():
                    if not result.get('success', False):
                        return False
        return True
    
    def _calculate_statistics(self) -> Dict[str, Any]:
        """Calculate test statistics."""
        stats = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'categories': {}
        }
        
        for category, tests in self.results.items():
            if isinstance(tests, dict):
                category_stats = {'total': 0, 'passed': 0, 'failed': 0}
                
                for test_name, result in tests.items():
                    stats['total_tests'] += 1
                    category_stats['total'] += 1
                    
                    if result.get('success', False):
                        stats['passed_tests'] += 1
                        category_stats['passed'] += 1
                    else:
                        stats['failed_tests'] += 1
                        category_stats['failed'] += 1
                
                stats['categories'][category] = category_stats
        
        return stats
    
    def print_summary_report(self, summary: Dict[str, Any]):
        """Print a formatted summary report."""
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE TEST SUITE SUMMARY")
        print("=" * 80)
        
        # Overall status
        status_emoji = "✅" if summary['overall_success'] else "❌"
        print(f"{status_emoji} Overall Status: {'PASSED' if summary['overall_success'] else 'FAILED'}")
        print(f"⏱️  Total Duration: {summary['total_duration']:.2f} seconds")
        print(f"📅 Timestamp: {summary['timestamp']}")
        
        # Statistics
        stats = summary['statistics']
        print(f"\n📈 Test Statistics:")
        print(f"   Total Tests: {stats['total_tests']}")
        print(f"   Passed: {stats['passed_tests']} ✅")
        print(f"   Failed: {stats['failed_tests']} ❌")
        
        if stats['total_tests'] > 0:
            success_rate = (stats['passed_tests'] / stats['total_tests']) * 100
            print(f"   Success Rate: {success_rate:.1f}%")
        
        # Category breakdown
        print(f"\n📋 Category Breakdown:")
        for category, category_stats in stats['categories'].items():
            status = "✅" if category_stats['failed'] == 0 else "❌"
            print(f"   {status} {category.upper()}: {category_stats['passed']}/{category_stats['total']} passed")
        
        # Detailed results
        print(f"\n📝 Detailed Results:")
        for category, tests in summary['results'].items():
            print(f"\n   {category.upper()}:")
            if isinstance(tests, dict):
                for test_name, result in tests.items():
                    status = "✅" if result.get('success', False) else "❌"
                    duration = result.get('duration', 0)
                    print(f"     {status} {test_name}: {duration:.2f}s")
                    
                    if not result.get('success', False) and result.get('stderr'):
                        print(f"        Error: {result['stderr'][:100]}...")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        if not summary['overall_success']:
            print("   - Review failed tests and fix issues")
            print("   - Check error logs for detailed information")
            print("   - Run individual test categories to isolate problems")
        else:
            print("   - All tests passed! Great job! 🎉")
            print("   - Consider adding more tests for better coverage")
            print("   - Review performance test results for optimization opportunities")
        
        # File locations
        print(f"\n📁 Report Locations:")
        print("   - Backend coverage: backend/htmlcov/comprehensive/index.html")
        print("   - Frontend coverage: frontend/coverage/lcov-report/index.html")
        print("   - Test results: backend/test-results/")
        print("   - Security reports: backend/test-results/")
        
        print("=" * 80)
    
    def save_summary_report(self, summary: Dict[str, Any]):
        """Save summary report to file."""
        os.chdir(self.project_root)
        
        # Save JSON report
        with open('test-summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Save markdown report
        self._save_markdown_report(summary)
        
        print(f"📄 Summary reports saved:")
        print(f"   - JSON: test-summary.json")
        print(f"   - Markdown: test-summary.md")
    
    def _save_markdown_report(self, summary: Dict[str, Any]):
        """Save summary report as markdown."""
        md_content = f"""# Test Suite Summary Report

**Generated:** {summary['timestamp']}  
**Duration:** {summary['total_duration']:.2f} seconds  
**Status:** {'✅ PASSED' if summary['overall_success'] else '❌ FAILED'}

## Statistics

- **Total Tests:** {summary['statistics']['total_tests']}
- **Passed:** {summary['statistics']['passed_tests']} ✅
- **Failed:** {summary['statistics']['failed_tests']} ❌
- **Success Rate:** {(summary['statistics']['passed_tests'] / max(summary['statistics']['total_tests'], 1)) * 100:.1f}%

## Category Results

"""
        
        for category, category_stats in summary['statistics']['categories'].items():
            status = "✅ PASSED" if category_stats['failed'] == 0 else "❌ FAILED"
            md_content += f"### {category.upper()}\n\n"
            md_content += f"**Status:** {status}  \n"
            md_content += f"**Results:** {category_stats['passed']}/{category_stats['total']} passed\n\n"
        
        md_content += "## Detailed Results\n\n"
        
        for category, tests in summary['results'].items():
            md_content += f"### {category.upper()}\n\n"
            if isinstance(tests, dict):
                for test_name, result in tests.items():
                    status = "✅" if result.get('success', False) else "❌"
                    duration = result.get('duration', 0)
                    md_content += f"- {status} **{test_name}**: {duration:.2f}s\n"
        
        md_content += "\n## Report Locations\n\n"
        md_content += "- Backend coverage: `backend/htmlcov/comprehensive/index.html`\n"
        md_content += "- Frontend coverage: `frontend/coverage/lcov-report/index.html`\n"
        md_content += "- Test results: `backend/test-results/`\n"
        md_content += "- Security reports: `backend/test-results/`\n"
        
        with open('test-summary.md', 'w') as f:
            f.write(md_content)
    
    def run_all_tests(self):
        """Run the complete test suite."""
        print("🚀 Starting Comprehensive Test Suite")
        print("=" * 80)
        
        # Run all test categories
        self.results['backend'] = self.run_backend_tests()
        self.results['frontend'] = self.run_frontend_tests()
        self.results['security'] = self.run_security_scans()
        self.results['build'] = self.run_build_tests()
        
        # Generate and display summary
        summary = self.generate_summary_report()
        self.print_summary_report(summary)
        self.save_summary_report(summary)
        
        # Exit with appropriate code
        sys.exit(0 if summary['overall_success'] else 1)


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        runner = ComprehensiveTestRunner()
        
        if command == "backend":
            runner.results['backend'] = runner.run_backend_tests()
        elif command == "frontend":
            runner.results['frontend'] = runner.run_frontend_tests()
        elif command == "security":
            runner.results['security'] = runner.run_security_scans()
        elif command == "build":
            runner.results['build'] = runner.run_build_tests()
        elif command == "all":
            runner.run_all_tests()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: backend, frontend, security, build, all")
            sys.exit(1)
    else:
        # Default to running all tests
        runner = ComprehensiveTestRunner()
        runner.run_all_tests()


if __name__ == "__main__":
    main()