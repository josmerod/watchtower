#!/usr/bin/env python3
"""
Project validation script for Watchtower.

This script checks for common issues and ensures the project follows best practices.
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Dict, Tuple, Set


class ProjectValidator:
    """Validator for Watchtower project structure and code quality."""

    def __init__(self):
        self.project_root = Path(".")
        self.issues = []
        self.warnings = []
        self.stats = {
            'python_files': 0,
            'total_lines': 0,
            'sys_path_insertions': 0,
            'missing_type_hints': 0,
            'missing_docstrings': 0,
        }

    def log_issue(self, level: str, file_path: str, message: str):
        """Log an issue or warning."""
        entry = f"{level}: {file_path} - {message}"
        if level == "ERROR":
            self.issues.append(entry)
        else:
            self.warnings.append(entry)

    def find_python_files(self) -> List[Path]:
        """Find all Python files in the project."""
        python_files = []
        
        # Include source files
        for pattern in ["src/**/*.py", "tests/**/*.py", "*.py"]:
            python_files.extend(self.project_root.glob(pattern))
        
        # Exclude certain directories
        excluded_dirs = {".venv", "__pycache__", ".pytest_cache", "build", "dist"}
        
        filtered_files = []
        for file_path in python_files:
            if not any(part in excluded_dirs for part in file_path.parts):
                filtered_files.append(file_path)
        
        return filtered_files

    def check_sys_path_insertions(self, python_files: List[Path]):
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                    self.stats['sys_path_insertions'] += 1
            except Exception as e:
                self.log_issue("ERROR", str(file_path), f"Could not read file: {e}")

    def check_imports(self, python_files: List[Path]):
        """Check for import issues."""
        print("🔍 Checking import patterns...")
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for relative imports outside src/
                if not str(file_path).startswith("src/"):
                    if re.search(r'from src\.\w+', content):
                        self.log_issue("INFO", str(file_path), "Uses src imports (good after dev install)")
                
                # Check for circular imports (basic check)
                lines = content.splitlines()
                import_lines = [line.strip() for line in lines if line.strip().startswith(('import ', 'from '))]
                
                if len(import_lines) > 20:
                    self.log_issue("WARNING", str(file_path), f"Many imports ({len(import_lines)}), consider refactoring")
                
            except Exception as e:
                self.log_issue("ERROR", str(file_path), f"Could not analyze imports: {e}")

    def check_code_structure(self, python_files: List[Path]):
        """Check code structure and quality."""
        print("🔍 Checking code structure...")
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.stats['total_lines'] += len(content.splitlines())
                self.stats['python_files'] += 1
                
                # Parse AST for more detailed analysis
                try:
                    tree = ast.parse(content)
                    
                    # Check for type hints in functions
                    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
                    for func in functions:
                        if not func.returns and func.name != "__init__":
                            if not func.name.startswith("_"):  # Skip private methods
                                self.stats['missing_type_hints'] += 1
                    
                    # Check for docstrings
                    classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
                    for cls in classes:
                        if not ast.get_docstring(cls):
                            self.stats['missing_docstrings'] += 1
                            self.log_issue("WARNING", str(file_path), f"Class {cls.name} missing docstring")
                
                except SyntaxError as e:
                    self.log_issue("ERROR", str(file_path), f"Syntax error: {e}")
                
            except Exception as e:
                self.log_issue("ERROR", str(file_path), f"Could not analyze structure: {e}")

    def check_project_files(self):
        """Check for required project files."""
        print("🔍 Checking project structure...")
        
        required_files = [
            "pyproject.toml",
            "README.md",
            "requirements.txt",
            ".cursorrules",
        ]
        
        for file_name in required_files:
            file_path = self.project_root / file_name
            if not file_path.exists():
                self.log_issue("WARNING", file_name, "Required file missing")
        
        # Check src structure
        src_dirs = [
            "src/config",
            "src/etl", 
            "src/models",
            "src/utils",
            "src/watchers",
            "src/web",
        ]
        
        for dir_name in src_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                self.log_issue("WARNING", dir_name, "Expected directory missing")

    def check_configuration(self):
        """Check configuration files."""
        print("🔍 Checking configuration...")
        
        # Check pyproject.toml
        pyproject_path = self.project_root / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if '[tool.ruff]' not in content:
                self.log_issue("WARNING", "pyproject.toml", "Missing Ruff configuration")
            
            if '[tool.pytest.ini_options]' not in content:
                self.log_issue("WARNING", "pyproject.toml", "Missing pytest configuration")

    def print_summary(self):
        """Print validation summary."""
        print("\n" + "="*60)
        print("📊 VALIDATION SUMMARY")
        print("="*60)
        
        print(f"Python files analyzed: {self.stats['python_files']}")
        print(f"Total lines of code: {self.stats['total_lines']}")
        print(f"Functions missing type hints: {self.stats['missing_type_hints']}")
        print(f"Classes missing docstrings: {self.stats['missing_docstrings']}")
        
        print(f"\n🚨 Issues found: {len(self.issues)}")
        for issue in self.issues:
            print(f"  {issue}")
        
        print(f"\n⚠️ Warnings: {len(self.warnings)}")
        for warning in self.warnings[:10]:  # Show first 10 warnings
            print(f"  {warning}")
        
        if len(self.warnings) > 10:
            print(f"  ... and {len(self.warnings) - 10} more warnings")
        
        print("\n" + "="*60)
        
        if self.stats['sys_path_insertions'] > 0:
            print("💡 RECOMMENDATION: Run 'python fix_imports.py' to clean up sys.path insertions")
        
        if len(self.issues) == 0:
            print("✅ No critical issues found!")
        else:
            print("❌ Critical issues found - please review and fix")
        
        print("\n🔧 To improve code quality:")
        print("1. Run 'python install_dev.py' for proper package setup")
        print("2. Run 'ruff format .' for code formatting")
        print("3. Run 'ruff check .' for linting")
        print("4. Run 'mypy src/' for type checking")
        print("5. Add type hints and docstrings where missing")

    def validate(self):
        """Run full project validation."""
        print("🔍 Starting Watchtower project validation...")
        print("="*60)
        
        # Find all Python files
        python_files = self.find_python_files()
        print(f"Found {len(python_files)} Python files")
        
        # Run checks
        self.check_project_files()
        self.check_configuration()
        self.check_sys_path_insertions(python_files)
        self.check_imports(python_files)
        self.check_code_structure(python_files)
        
        # Print summary
        self.print_summary()


def main():
    """Main validation function."""
    validator = ProjectValidator()
    validator.validate()


if __name__ == "__main__":
    main() 