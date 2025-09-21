#!/usr/bin/env python3
"""
Validation script to check if the project structure is set up correctly.
"""

import os
import sys
from pathlib import Path

def check_file_exists(file_path, description):
    """Check if a file exists and print status."""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} (missing)")
        return False

def check_directory_exists(dir_path, description):
    """Check if a directory exists and print status."""
    if os.path.isdir(dir_path):
        print(f"✅ {description}: {dir_path}")
        return True
    else:
        print(f"❌ {description}: {dir_path} (missing)")
        return False

def main():
    """Main validation function."""
    print("🔍 Validating Artisan Promotion Platform project structure...\n")
    
    all_good = True
    
    # Check root files
    root_files = [
        ("docker-compose.yml", "Docker Compose configuration"),
        ("README.md", "Project README"),
        (".gitignore", "Git ignore file"),
        ("Makefile", "Development Makefile"),
    ]
    
    for file_path, description in root_files:
        if not check_file_exists(file_path, description):
            all_good = False
    
    print()
    
    # Check backend structure
    print("📁 Backend structure:")
    backend_items = [
        ("backend/", "Backend directory", "dir"),
        ("backend/app/", "Backend app directory", "dir"),
        ("backend/app/__init__.py", "Backend app init", "file"),
        ("backend/app/main.py", "Backend main module", "file"),
        ("backend/tests/", "Backend tests directory", "dir"),
        ("backend/tests/__init__.py", "Backend tests init", "file"),
        ("backend/tests/test_main.py", "Backend test file", "file"),
        ("backend/migrations/", "Backend migrations directory", "dir"),
        ("backend/requirements.txt", "Backend requirements", "file"),
        ("backend/Dockerfile", "Backend Dockerfile", "file"),
        ("backend/.env.example", "Backend env example", "file"),
    ]
    
    for item_path, description, item_type in backend_items:
        if item_type == "dir":
            if not check_directory_exists(item_path, description):
                all_good = False
        else:
            if not check_file_exists(item_path, description):
                all_good = False
    
    print()
    
    # Check frontend structure
    print("📁 Frontend structure:")
    frontend_items = [
        ("frontend/", "Frontend directory", "dir"),
        ("frontend/src/", "Frontend src directory", "dir"),
        ("frontend/src/App.tsx", "Frontend App component", "file"),
        ("frontend/src/index.tsx", "Frontend index", "file"),
        ("frontend/src/index.css", "Frontend CSS", "file"),
        ("frontend/public/", "Frontend public directory", "dir"),
        ("frontend/public/index.html", "Frontend HTML template", "file"),
        ("frontend/package.json", "Frontend package.json", "file"),
        ("frontend/tsconfig.json", "Frontend TypeScript config", "file"),
        ("frontend/tailwind.config.js", "Frontend Tailwind config", "file"),
        ("frontend/Dockerfile", "Frontend Dockerfile", "file"),
        ("frontend/.env.example", "Frontend env example", "file"),
    ]
    
    for item_path, description, item_type in frontend_items:
        if item_type == "dir":
            if not check_directory_exists(item_path, description):
                all_good = False
        else:
            if not check_file_exists(item_path, description):
                all_good = False
    
    print()
    
    # Check scripts
    print("📁 Scripts:")
    script_items = [
        ("scripts/", "Scripts directory", "dir"),
        ("scripts/dev-setup.sh", "Development setup script", "file"),
    ]
    
    for item_path, description, item_type in script_items:
        if item_type == "dir":
            if not check_directory_exists(item_path, description):
                all_good = False
        else:
            if not check_file_exists(item_path, description):
                all_good = False
    
    print()
    
    if all_good:
        print("🎉 All project structure validation checks passed!")
        print("\n📋 Next steps:")
        print("1. Run 'make setup' or './scripts/dev-setup.sh' to start development environment")
        print("2. Update .env files with your API keys")
        print("3. Access frontend at http://localhost:3000")
        print("4. Access backend at http://localhost:8000")
        return 0
    else:
        print("❌ Some validation checks failed. Please review the missing items above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())