#!/usr/bin/env python3
"""
Import validation script to check import organization and standards.
This script can be run as part of CI/CD to ensure import standards are maintained.
"""

import ast
import sys
from pathlib import Path
from typing import List, Set


class ImportValidator:
    """Validates import organization and standards."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.standard_modules = self._get_standard_modules()
        self.local_prefixes = {'controllers', 'services', 'models', 'utils', 'tests'}
        self.violations = []
        
    def _get_standard_modules(self) -> Set[str]:
        """Get set of standard library module names."""
        return {
            'os', 'sys', 'json', 'time', 'datetime', 'pathlib', 'typing', 'enum',
            'dataclasses', 'abc', 'functools', 'itertools', 'collections', 'logging',
            'urllib', 're', 'ast', 'threading', 'queue', 'tempfile', 'io', 'copy',
            'pickle', 'csv', 'xml', 'html', 'http', 'email', 'base64', 'hashlib',
            'uuid', 'random', 'math', 'statistics', 'decimal', 'fractions',
            'contextlib', 'warnings', 'traceback', 'inspect', 'importlib'
        }
    
    def categorize_import(self, module_name: str) -> str:
        """Categorize an import as standard, third-party, or local."""
        if not module_name:
            return 'local'
        
        root_module = module_name.split('.')[0]
        
        if root_module in self.standard_modules:
            return 'standard'
        elif any(root_module.startswith(prefix) for prefix in self.local_prefixes):
            return 'local'
        else:
            return 'third_party'
    
    def validate_file_imports(self, file_path: Path) -> List[str]:
        """Validate import organization in a single file."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            imports = []
            
            # Extract imports with line numbers and categories
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        category = self.categorize_import(alias.name)
                        imports.append((node.lineno, category, alias.name))
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    category = self.categorize_import(module)
                    imports.append((node.lineno, category, module))
            
            # Sort by line number
            imports.sort(key=lambda x: x[0])
            
            # Check import order
            last_category_line = {'standard': 0, 'third_party': 0, 'local': 0}
            
            for line_no, category, module in imports:
                # Update last seen line for this category
                last_category_line[category] = line_no
                
                # Check if imports are in correct order
                if category == 'third_party':
                    if last_category_line['local'] > 0 and last_category_line['local'] < line_no:
                        violations.append(f"Line {line_no}: Third-party import '{module}' should come before local imports")
                elif category == 'standard':
                    if last_category_line['third_party'] > 0 and last_category_line['third_party'] < line_no:
                        violations.append(f"Line {line_no}: Standard library import '{module}' should come before third-party imports")
                    if last_category_line['local'] > 0 and last_category_line['local'] < line_no:
                        violations.append(f"Line {line_no}: Standard library import '{module}' should come before local imports")
            
            # Check for unused imports (basic check)
            # This is a simplified check - the full analyzer does more thorough checking
            used_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    used_names.add(node.id)
                elif isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name):
                        used_names.add(node.value.id)
            
            # Check if imported names are used (simplified)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        import_name = alias.asname or alias.name.split('.')[0]
                        if import_name not in used_names and not self._is_implicit_import(alias.name, file_path):
                            violations.append(f"Line {node.lineno}: Unused import '{alias.name}'")
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        import_name = alias.asname or alias.name
                        if import_name not in used_names and not self._is_implicit_import(alias.name, file_path):
                            violations.append(f"Line {node.lineno}: Unused import '{alias.name}' from '{node.module}'")
            
        except Exception as e:
            violations.append(f"Error parsing file: {e}")
        
        return violations
    
    def _is_implicit_import(self, import_name: str, file_path: Path) -> bool:
        """Check if import might be used implicitly."""
        # Skip analysis for __init__.py files
        if file_path.name == '__init__.py':
            return True
        
        # Skip common implicit imports
        implicit_names = {
            'typing', 'dataclasses', 'abc', 'enum', 'functools',
            'pytest', 'unittest', 'mock', 'dataclass', 'abstractmethod'
        }
        
        return import_name.lower() in implicit_names
    
    def validate_project(self, file_patterns: List[str] = None) -> bool:
        """Validate imports across the entire project."""
        if file_patterns is None:
            file_patterns = [
                "services/*.py",
                "utils/*.py", 
                "controllers/*.py",
                "models/*.py",
                "cli.py",
                "main.py"
            ]
        
        files_to_check = []
        for pattern in file_patterns:
            if '*' in pattern:
                files_to_check.extend(self.project_root.glob(pattern))
            else:
                file_path = self.project_root / pattern
                if file_path.exists():
                    files_to_check.append(file_path)
        
        all_valid = True
        
        for file_path in files_to_check:
            if not file_path.is_file() or file_path.suffix != '.py':
                continue
            
            # Skip certain files
            if self._should_skip_file(file_path):
                continue
            
            violations = self.validate_file_imports(file_path)
            if violations:
                all_valid = False
                rel_path = file_path.relative_to(self.project_root)
                print(f"\n❌ {rel_path}:")
                for violation in violations:
                    print(f"  {violation}")
                self.violations.extend([(str(rel_path), v) for v in violations])
        
        return all_valid
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during validation."""
        # Skip __init__.py files
        if file_path.name == '__init__.py':
            return True
        
        # Skip test files (they have different import patterns)
        if file_path.name.startswith('test_') or file_path.name.endswith('_test.py'):
            return True
        
        # Skip setup and configuration files
        skip_files = {'setup.py', 'conftest.py', '__main__.py'}
        if file_path.name in skip_files:
            return True
        
        return False
    
    def generate_report(self) -> str:
        """Generate validation report."""
        if not self.violations:
            return "✅ All imports are properly organized and valid!"
        
        report = []
        report.append("# Import Validation Report")
        report.append("=" * 50)
        report.append(f"\nTotal violations found: {len(self.violations)}\n")
        
        # Group violations by file
        violations_by_file = {}
        for file_path, violation in self.violations:
            if file_path not in violations_by_file:
                violations_by_file[file_path] = []
            violations_by_file[file_path].append(violation)
        
        for file_path, violations in violations_by_file.items():
            report.append(f"## {file_path}")
            for violation in violations:
                report.append(f"- {violation}")
            report.append("")
        
        return "\n".join(report)


def main():
    """Main function to run import validation."""
    validator = ImportValidator()
    
    print("🔍 Validating import organization and standards...")
    
    is_valid = validator.validate_project()
    
    if is_valid:
        print("\n✅ All imports are properly organized and valid!")
        return 0
    else:
        print(f"\n❌ Found {len(validator.violations)} import violations")
        
        # Save detailed report
        report = validator.generate_report()
        report_path = Path("import_validation_report.txt")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"📄 Detailed report saved to: {report_path}")
        return 1


if __name__ == "__main__":
    sys.exit(main())