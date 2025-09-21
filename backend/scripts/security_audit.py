#!/usr/bin/env python3
"""
Security audit script for the Artisan Promotion Platform.

This script performs automated security checks including:
- Dependency vulnerability scanning
- Configuration security review
- Code security analysis
- Database security checks
- API security testing
"""

import os
import sys
import json
import subprocess
import requests
from typing import Dict, List, Any
from pathlib import Path
import logging

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SecurityAuditor:
    """Performs comprehensive security audits."""
    
    def __init__(self):
        self.results = {
            "dependencies": [],
            "configuration": [],
            "code_analysis": [],
            "api_security": [],
            "database": [],
            "overall_score": 0
        }
        self.base_dir = Path(__file__).parent.parent
    
    def run_full_audit(self) -> Dict[str, Any]:
        """Run complete security audit."""
        logger.info("Starting comprehensive security audit...")
        
        try:
            self.check_dependencies()
            self.check_configuration()
            self.analyze_code_security()
            self.check_api_security()
            self.check_database_security()
            self.calculate_overall_score()
            
            logger.info("Security audit completed")
            return self.results
            
        except Exception as e:
            logger.error(f"Security audit failed: {e}")
            return {"error": str(e)}
    
    def check_dependencies(self):
        """Check for vulnerable dependencies."""
        logger.info("Checking dependencies for vulnerabilities...")
        
        try:
            # Check if safety is installed
            result = subprocess.run(
                ["pip", "show", "safety"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.warning("Safety not installed. Installing...")
                subprocess.run(["pip", "install", "safety"], check=True)
            
            # Run safety check
            result = subprocess.run(
                ["safety", "check", "--json"],
                capture_output=True,
                text=True,
                cwd=self.base_dir
            )
            
            if result.returncode == 0:
                self.results["dependencies"].append({
                    "status": "pass",
                    "message": "No known vulnerabilities found in dependencies"
                })
            else:
                try:
                    vulnerabilities = json.loads(result.stdout)
                    self.results["dependencies"].extend([
                        {
                            "status": "fail",
                            "package": vuln.get("package"),
                            "vulnerability": vuln.get("vulnerability"),
                            "severity": vuln.get("severity", "unknown")
                        }
                        for vuln in vulnerabilities
                    ])
                except json.JSONDecodeError:
                    self.results["dependencies"].append({
                        "status": "error",
                        "message": "Failed to parse safety output"
                    })
                    
        except subprocess.CalledProcessError as e:
            self.results["dependencies"].append({
                "status": "error",
                "message": f"Failed to run dependency check: {e}"
            })
        except Exception as e:
            self.results["dependencies"].append({
                "status": "error",
                "message": f"Dependency check error: {e}"
            })
    
    def check_configuration(self):
        """Check security configuration."""
        logger.info("Checking security configuration...")
        
        checks = [
            self._check_jwt_secret(),
            self._check_database_config(),
            self._check_cors_config(),
            self._check_environment_config(),
            self._check_file_upload_config(),
            self._check_rate_limiting_config()
        ]
        
        self.results["configuration"].extend(checks)
    
    def _check_jwt_secret(self) -> Dict[str, Any]:
        """Check JWT secret configuration."""
        if settings.jwt_secret_key == "your-secret-key-here-change-in-production":
            return {
                "status": "fail",
                "check": "JWT Secret",
                "message": "Using default JWT secret key - CRITICAL SECURITY RISK",
                "severity": "critical"
            }
        elif len(settings.jwt_secret_key) < 32:
            return {
                "status": "fail",
                "check": "JWT Secret",
                "message": "JWT secret key too short (should be at least 32 characters)",
                "severity": "high"
            }
        else:
            return {
                "status": "pass",
                "check": "JWT Secret",
                "message": "JWT secret key properly configured"
            }
    
    def _check_database_config(self) -> Dict[str, Any]:
        """Check database configuration."""
        if "sqlite" in settings.database_url.lower():
            return {
                "status": "warning",
                "check": "Database",
                "message": "Using SQLite - not recommended for production",
                "severity": "medium"
            }
        elif "password" not in settings.database_url.lower():
            return {
                "status": "fail",
                "check": "Database",
                "message": "Database connection without password",
                "severity": "high"
            }
        else:
            return {
                "status": "pass",
                "check": "Database",
                "message": "Database configuration appears secure"
            }
    
    def _check_cors_config(self) -> Dict[str, Any]:
        """Check CORS configuration."""
        if "*" in settings.cors_origins:
            return {
                "status": "fail",
                "check": "CORS",
                "message": "CORS allows all origins - security risk",
                "severity": "high"
            }
        elif len(settings.cors_origins) == 0:
            return {
                "status": "warning",
                "check": "CORS",
                "message": "No CORS origins configured",
                "severity": "low"
            }
        else:
            return {
                "status": "pass",
                "check": "CORS",
                "message": f"CORS properly configured for {len(settings.cors_origins)} origins"
            }
    
    def _check_environment_config(self) -> Dict[str, Any]:
        """Check environment configuration."""
        if settings.environment == "development" and os.getenv("PRODUCTION"):
            return {
                "status": "fail",
                "check": "Environment",
                "message": "Development mode in production environment",
                "severity": "critical"
            }
        elif settings.environment == "production":
            return {
                "status": "pass",
                "check": "Environment",
                "message": "Production environment properly configured"
            }
        else:
            return {
                "status": "pass",
                "check": "Environment",
                "message": f"Environment set to {settings.environment}"
            }
    
    def _check_file_upload_config(self) -> Dict[str, Any]:
        """Check file upload configuration."""
        max_size_mb = settings.max_file_size / (1024 * 1024)
        
        if max_size_mb > 50:
            return {
                "status": "warning",
                "check": "File Upload",
                "message": f"Large file upload limit ({max_size_mb}MB) may cause DoS",
                "severity": "medium"
            }
        elif len(settings.allowed_image_types) == 0:
            return {
                "status": "fail",
                "check": "File Upload",
                "message": "No file type restrictions configured",
                "severity": "high"
            }
        else:
            return {
                "status": "pass",
                "check": "File Upload",
                "message": f"File upload properly configured ({max_size_mb}MB limit)"
            }
    
    def _check_rate_limiting_config(self) -> Dict[str, Any]:
        """Check rate limiting configuration."""
        if not hasattr(settings, 'rate_limit_enabled') or not settings.rate_limit_enabled:
            return {
                "status": "fail",
                "check": "Rate Limiting",
                "message": "Rate limiting not enabled",
                "severity": "high"
            }
        else:
            return {
                "status": "pass",
                "check": "Rate Limiting",
                "message": "Rate limiting properly configured"
            }
    
    def analyze_code_security(self):
        """Analyze code for security issues."""
        logger.info("Analyzing code security...")
        
        try:
            # Check if bandit is installed
            result = subprocess.run(
                ["pip", "show", "bandit"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.warning("Bandit not installed. Installing...")
                subprocess.run(["pip", "install", "bandit"], check=True)
            
            # Run bandit security analysis
            result = subprocess.run(
                ["bandit", "-r", "app/", "-f", "json"],
                capture_output=True,
                text=True,
                cwd=self.base_dir
            )
            
            if result.stdout:
                try:
                    bandit_results = json.loads(result.stdout)
                    
                    for issue in bandit_results.get("results", []):
                        self.results["code_analysis"].append({
                            "status": "fail" if issue["issue_severity"] in ["HIGH", "MEDIUM"] else "warning",
                            "file": issue["filename"],
                            "line": issue["line_number"],
                            "issue": issue["issue_text"],
                            "severity": issue["issue_severity"].lower(),
                            "confidence": issue["issue_confidence"].lower()
                        })
                    
                    if not bandit_results.get("results"):
                        self.results["code_analysis"].append({
                            "status": "pass",
                            "message": "No security issues found in code analysis"
                        })
                        
                except json.JSONDecodeError:
                    self.results["code_analysis"].append({
                        "status": "error",
                        "message": "Failed to parse bandit output"
                    })
            else:
                self.results["code_analysis"].append({
                    "status": "pass",
                    "message": "No security issues found in code analysis"
                })
                
        except subprocess.CalledProcessError as e:
            self.results["code_analysis"].append({
                "status": "error",
                "message": f"Code analysis failed: {e}"
            })
        except Exception as e:
            self.results["code_analysis"].append({
                "status": "error",
                "message": f"Code analysis error: {e}"
            })
    
    def check_api_security(self):
        """Check API security."""
        logger.info("Checking API security...")
        
        # This would typically test against a running instance
        # For now, we'll do static checks
        
        checks = [
            self._check_authentication_endpoints(),
            self._check_input_validation(),
            self._check_error_handling(),
            self._check_security_headers()
        ]
        
        self.results["api_security"].extend(checks)
    
    def _check_authentication_endpoints(self) -> Dict[str, Any]:
        """Check authentication endpoint security."""
        # Check if auth routes exist and are properly protected
        auth_file = self.base_dir / "app" / "routers" / "auth.py"
        
        if not auth_file.exists():
            return {
                "status": "fail",
                "check": "Authentication Endpoints",
                "message": "Authentication router not found",
                "severity": "critical"
            }
        
        # Read auth file and check for security measures
        with open(auth_file, 'r') as f:
            content = f.read()
        
        security_features = [
            ("password hashing", "hash_password" in content or "bcrypt" in content),
            ("JWT tokens", "jwt" in content.lower() or "token" in content),
            ("rate limiting", "rate" in content.lower() or "limit" in content),
            ("input validation", "validate" in content or "pydantic" in content)
        ]
        
        missing_features = [feature for feature, present in security_features if not present]
        
        if missing_features:
            return {
                "status": "warning",
                "check": "Authentication Endpoints",
                "message": f"Missing security features: {', '.join(missing_features)}",
                "severity": "medium"
            }
        else:
            return {
                "status": "pass",
                "check": "Authentication Endpoints",
                "message": "Authentication endpoints have proper security measures"
            }
    
    def _check_input_validation(self) -> Dict[str, Any]:
        """Check input validation implementation."""
        security_file = self.base_dir / "app" / "security.py"
        
        if not security_file.exists():
            return {
                "status": "fail",
                "check": "Input Validation",
                "message": "Security module not found",
                "severity": "high"
            }
        
        with open(security_file, 'r') as f:
            content = f.read()
        
        validation_features = [
            "InputSanitizer" in content,
            "sanitize_string" in content,
            "XSS_PATTERNS" in content,
            "SQL_PATTERNS" in content
        ]
        
        if all(validation_features):
            return {
                "status": "pass",
                "check": "Input Validation",
                "message": "Comprehensive input validation implemented"
            }
        else:
            return {
                "status": "warning",
                "check": "Input Validation",
                "message": "Input validation partially implemented",
                "severity": "medium"
            }
    
    def _check_error_handling(self) -> Dict[str, Any]:
        """Check error handling security."""
        main_file = self.base_dir / "app" / "main.py"
        
        if not main_file.exists():
            return {
                "status": "fail",
                "check": "Error Handling",
                "message": "Main application file not found",
                "severity": "high"
            }
        
        with open(main_file, 'r') as f:
            content = f.read()
        
        # Check for debug mode in production
        if 'debug=True' in content and settings.environment == "production":
            return {
                "status": "fail",
                "check": "Error Handling",
                "message": "Debug mode enabled in production",
                "severity": "high"
            }
        else:
            return {
                "status": "pass",
                "check": "Error Handling",
                "message": "Error handling properly configured"
            }
    
    def _check_security_headers(self) -> Dict[str, Any]:
        """Check security headers implementation."""
        middleware_file = self.base_dir / "app" / "middleware.py"
        
        if not middleware_file.exists():
            return {
                "status": "fail",
                "check": "Security Headers",
                "message": "Security middleware not found",
                "severity": "high"
            }
        
        with open(middleware_file, 'r') as f:
            content = f.read()
        
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Content-Security-Policy",
            "Strict-Transport-Security"
        ]
        
        missing_headers = [header for header in required_headers if header not in content]
        
        if missing_headers:
            return {
                "status": "warning",
                "check": "Security Headers",
                "message": f"Missing security headers: {', '.join(missing_headers)}",
                "severity": "medium"
            }
        else:
            return {
                "status": "pass",
                "check": "Security Headers",
                "message": "All required security headers implemented"
            }
    
    def check_database_security(self):
        """Check database security configuration."""
        logger.info("Checking database security...")
        
        checks = [
            self._check_database_connection(),
            self._check_sql_injection_protection(),
            self._check_data_encryption()
        ]
        
        self.results["database"].extend(checks)
    
    def _check_database_connection(self) -> Dict[str, Any]:
        """Check database connection security."""
        db_url = settings.database_url
        
        if db_url.startswith("sqlite"):
            return {
                "status": "warning",
                "check": "Database Connection",
                "message": "Using SQLite - ensure file permissions are secure",
                "severity": "low"
            }
        elif "sslmode" not in db_url and "postgresql" in db_url:
            return {
                "status": "warning",
                "check": "Database Connection",
                "message": "PostgreSQL connection without SSL",
                "severity": "medium"
            }
        else:
            return {
                "status": "pass",
                "check": "Database Connection",
                "message": "Database connection appears secure"
            }
    
    def _check_sql_injection_protection(self) -> Dict[str, Any]:
        """Check SQL injection protection."""
        # Check if SQLAlchemy ORM is used (provides protection)
        models_file = self.base_dir / "app" / "models.py"
        
        if not models_file.exists():
            return {
                "status": "fail",
                "check": "SQL Injection Protection",
                "message": "Models file not found",
                "severity": "high"
            }
        
        with open(models_file, 'r') as f:
            content = f.read()
        
        if "sqlalchemy" in content.lower() and "Base" in content:
            return {
                "status": "pass",
                "check": "SQL Injection Protection",
                "message": "Using SQLAlchemy ORM for SQL injection protection"
            }
        else:
            return {
                "status": "warning",
                "check": "SQL Injection Protection",
                "message": "Verify SQL injection protection implementation",
                "severity": "medium"
            }
    
    def _check_data_encryption(self) -> Dict[str, Any]:
        """Check data encryption implementation."""
        security_file = self.base_dir / "app" / "security.py"
        
        if not security_file.exists():
            return {
                "status": "fail",
                "check": "Data Encryption",
                "message": "Security module not found",
                "severity": "high"
            }
        
        with open(security_file, 'r') as f:
            content = f.read()
        
        if "TokenEncryption" in content and "Fernet" in content:
            return {
                "status": "pass",
                "check": "Data Encryption",
                "message": "Token encryption implemented"
            }
        else:
            return {
                "status": "warning",
                "check": "Data Encryption",
                "message": "Data encryption not fully implemented",
                "severity": "medium"
            }
    
    def calculate_overall_score(self):
        """Calculate overall security score."""
        total_checks = 0
        passed_checks = 0
        critical_failures = 0
        
        for category in ["dependencies", "configuration", "code_analysis", "api_security", "database"]:
            for check in self.results[category]:
                total_checks += 1
                if check.get("status") == "pass":
                    passed_checks += 1
                elif check.get("severity") == "critical":
                    critical_failures += 1
        
        if total_checks == 0:
            score = 0
        else:
            base_score = (passed_checks / total_checks) * 100
            # Penalize critical failures heavily
            penalty = critical_failures * 20
            score = max(0, base_score - penalty)
        
        self.results["overall_score"] = round(score, 1)
        
        # Add summary
        self.results["summary"] = {
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "critical_failures": critical_failures,
            "score": self.results["overall_score"],
            "grade": self._get_security_grade(score)
        }
    
    def _get_security_grade(self, score: float) -> str:
        """Get security grade based on score."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def generate_report(self) -> str:
        """Generate human-readable security report."""
        report = []
        report.append("=" * 60)
        report.append("ARTISAN PROMOTION PLATFORM - SECURITY AUDIT REPORT")
        report.append("=" * 60)
        report.append("")
        
        # Summary
        summary = self.results.get("summary", {})
        report.append(f"Overall Security Score: {summary.get('score', 0)}/100 (Grade: {summary.get('grade', 'F')})")
        report.append(f"Total Checks: {summary.get('total_checks', 0)}")
        report.append(f"Passed Checks: {summary.get('passed_checks', 0)}")
        report.append(f"Critical Failures: {summary.get('critical_failures', 0)}")
        report.append("")
        
        # Detailed results
        categories = [
            ("Dependencies", "dependencies"),
            ("Configuration", "configuration"),
            ("Code Analysis", "code_analysis"),
            ("API Security", "api_security"),
            ("Database Security", "database")
        ]
        
        for category_name, category_key in categories:
            report.append(f"{category_name}:")
            report.append("-" * len(category_name))
            
            checks = self.results.get(category_key, [])
            if not checks:
                report.append("  No checks performed")
            else:
                for check in checks:
                    status = check.get("status", "unknown").upper()
                    message = check.get("message", "No message")
                    severity = check.get("severity", "")
                    
                    if severity:
                        report.append(f"  [{status}] {message} (Severity: {severity})")
                    else:
                        report.append(f"  [{status}] {message}")
            
            report.append("")
        
        return "\n".join(report)


def main():
    """Run security audit."""
    auditor = SecurityAuditor()
    results = auditor.run_full_audit()
    
    # Generate and print report
    report = auditor.generate_report()
    print(report)
    
    # Save results to file
    output_file = Path(__file__).parent.parent / "security_audit_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nDetailed results saved to: {output_file}")
    
    # Exit with error code if critical failures
    critical_failures = results.get("summary", {}).get("critical_failures", 0)
    if critical_failures > 0:
        print(f"\nWARNING: {critical_failures} critical security issues found!")
        sys.exit(1)
    
    score = results.get("overall_score", 0)
    if score < 70:
        print(f"\nWARNING: Security score ({score}) below acceptable threshold!")
        sys.exit(1)
    
    print("\nSecurity audit completed successfully!")


if __name__ == "__main__":
    main()