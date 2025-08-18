#!/usr/bin/env python3
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import (
    List,
    Dict,
    Tuple,
    Set
)
from collections import defaultdict


Import organizer script to standardize import organization.
This script organizes imports according to PEP 8 standards:
1. Standard library imports
2. Third-party imports  
3. Local application imports
"""



class ImportOrganizer:
    """Organizes imports according to PEP 8 standards."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.standard_modules = self._get_standard_modules()
        self.local_prefixes = {'controllers', 'services', 'models', 'utils', 'tests'}
        self.organized_files = []
        
    def _get_standard_modules(self) -> Set[str]:
        """Get set of standard library module names."""
        return {
            # Core modules
            'os', 'sys', 'json', 'time', 'datetime', 'pathlib', 'typing', 'enum',
            'dataclasses', 'abc', 'functools', 'itertools', 'collections', 'logging',
            'urllib', 're', 'ast', 'threading', 'queue', 'tempfile', 'io', 'copy',
            'pickle', 'csv', 'xml', 'html', 'http', 'email', 'base64', 'hashlib',
            'uuid', 'random', 'math', 'statistics', 'decimal', 'fractions',
            'contextlib', 'warnings', 'traceback', 'inspect', 'importlib',
            'pkgutil', 'modulefinder', 'runpy', 'argparse', 'getopt', 'shlex',
            'configparser', 'fileinput', 'linecache', 'glob', 'fnmatch', 'shutil',
            'subprocess', 'socket', 'ssl', 'select', 'selectors', 'signal',
            'mmap', 'ctypes', 'struct', 'codecs', 'unicodedata', 'stringprep',
            'readline', 'rlcompleter', 'sqlite3', 'zlib', 'gzip', 'bz2', 'lzma',
            'zipfile', 'tarfile', 'getpass', 'platform', 'errno', 'stat',
            'filecmp', 'tempfile', 'glob', 'fnmatch', 'linecache', 'shutil',
            'macpath', 'ntpath', 'posixpath', 'genericpath', 'sched', 'mutex',
            'gettext', 'locale', 'calendar', 'mailcap', 'mailbox', 'mimetypes',
            'uu', 'binascii', 'quopri', 'pty', 'tty', 'pipes', 'posix', 'pwd',
            'spwd', 'grp', 'crypt', 'dl', 'termios', 'resource', 'nis', 'syslog',
            'commands', 'popen2', 'asyncore', 'asynchat', 'formatter', 'operator',
            'weakref', 'gc', 'types', 'new', 'user', 'site', 'future_builtins'
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
    
    def parse_imports(self, file_path: Path) -> Tuple[List[str], Dict[str, List[str]], List[str]]:
        """Parse imports from a file and categorize them."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            lines = content.splitlines()
            
            # Find all import statements
            import_nodes = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    import_nodes.append(node)
            
            # Sort by line number
            import_nodes.sort(key=lambda x: x.lineno)
            
            # Categorize imports
            categorized_imports = {
                'standard': [],
                'third_party': [],
                'local': []
            }
            
            # Track import lines to remove
            import_lines = set()
            
            for node in import_nodes:
                start_line = node.lineno - 1
                import_lines.add(start_line)
                
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        category = self.categorize_import(alias.name)
                        import_text = f"import {alias.name}"
                        if alias.asname:
                            import_text += f" as {alias.asname}"
                        categorized_imports[category].append(import_text)
                
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    category = self.categorize_import(module)
                    
                    # Handle different import styles
                    names = []
                    for alias in node.names:
                        if alias.asname:
                            names.append(f"{alias.name} as {alias.asname}")
                        else:
                            names.append(alias.name)
                    
                    if len(names) == 1:
                        import_text = f"from {module} import {names[0]}"
                    else:
                        # Multi-line import
                        import_text = f"from {module} import (\n    " + ",\n    ".join(names) + "\n)"
                    
                    categorized_imports[category].append(import_text)
            
            # Get non-import lines
            non_import_lines = []
            for i, line in enumerate(lines):
                if i not in import_lines:
                    non_import_lines.append(line)
            
            return lines, categorized_imports, non_import_lines
            
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return [], {}, []
    
    def organize_file_imports(self, file_path: Path) -> bool:
        """Organize imports in a single file."""
        try:
            original_lines, categorized_imports, non_import_lines = self.parse_imports(file_path)
            
            if not any(categorized_imports.values()):
                return True  # No imports to organize
            
            # Build organized content
            organized_lines = []
            
            # Add file header (docstring, encoding, etc.)
            header_lines = []
            in_header = True
            for line in non_import_lines:
                if in_header and (line.strip().startswith('"""') or 
                                line.strip().startswith("'''") or
                                line.strip().startswith('#') or
                                line.strip() == '' or
                                'coding:' in line or 'encoding:' in line):
                    header_lines.append(line)
                else:
                    in_header = False
                    break
            
            # Add header
            organized_lines.extend(header_lines)
            
            # Add organized imports
            if categorized_imports['standard']:
                if organized_lines and organized_lines[-1].strip():
                    organized_lines.append('')
                organized_lines.extend(categorized_imports['standard'])
            
            if categorized_imports['third_party']:
                if organized_lines and organized_lines[-1].strip():
                    organized_lines.append('')
                organized_lines.extend(categorized_imports['third_party'])
            
            if categorized_imports['local']:
                if organized_lines and organized_lines[-1].strip():
                    organized_lines.append('')
                organized_lines.extend(categorized_imports['local'])
            
            # Add rest of the file
            rest_lines = non_import_lines[len(header_lines):]
            if rest_lines:
                if organized_lines and organized_lines[-1].strip():
                    organized_lines.append('')
                    organized_lines.append('')
                organized_lines.extend(rest_lines)
            
            # Write organized content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(organized_lines))
                if organized_lines and not organized_lines[-1].endswith('\n'):
                    f.write('\n')
            
            return True
            
        except Exception as e:
            print(f"Error organizing {file_path}: {e}")
            return False
    
    def organize_all_files(self, file_patterns: List[str] = None) -> Dict[str, int]:
        """Organize imports in all specified files."""
        if file_patterns is None:
            file_patterns = [
                "services/*.py",
                "utils/*.py", 
                "controllers/*.py",
                "models/*.py",
                "cli.py",
                "main.py"
            ]
        
        results = {
            'files_processed': 0,
            'files_organized': 0,
            'errors': 0
        }
        
        files_to_process = []
        for pattern in file_patterns:
            if '*' in pattern:
                # Handle glob patterns
                pattern_path = Path(pattern)
                if pattern_path.is_absolute():
                    files_to_process.extend(pattern_path.parent.glob(pattern_path.name))
                else:
                    files_to_process.extend(self.project_root.glob(pattern))
            else:
                # Handle specific files
                file_path = self.project_root / pattern
                if file_path.exists():
                    files_to_process.append(file_path)
        
        for file_path in files_to_process:
            if not file_path.is_file() or not file_path.suffix == '.py':
                continue
            
            # Skip certain files
            if self._should_skip_file(file_path):
                continue
            
            results['files_processed'] += 1
            print(f"Organizing imports in {file_path.relative_to(self.project_root)}")
            
            if self.organize_file_imports(file_path):
                results['files_organized'] += 1
                self.organized_files.append(file_path)
                print(f"  ✓ Organized")
            else:
                results['errors'] += 1
                print(f"  ✗ Error")
        
        return results
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during organization."""
        # Skip __init__.py files as they often have special import requirements
        if file_path.name == '__init__.py':
            return True
        
        # Skip test files for now as they might have special import patterns
        if file_path.name.startswith('test_') or file_path.name.endswith('_test.py'):
            return True
        
        # Skip setup and configuration files
        skip_files = {'setup.py', 'conftest.py', '__main__.py'}
        if file_path.name in skip_files:
            return True
        
        return False
    
    def verify_syntax(self) -> List[Path]:
        """Verify syntax of all organized files."""
        syntax_errors = []
        
        for file_path in self.organized_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                ast.parse(content)
            except SyntaxError as e:
                syntax_errors.append(file_path)
                print(f"Syntax error in {file_path}: {e}")
        
        return syntax_errors
    
    def generate_report(self, results: Dict[str, int]) -> str:
        """Generate organization report."""
        report = []
        report.append("# Import Organization Report")
        report.append("=" * 50)
        report.append("")
        report.append(f"Files processed: {results['files_processed']}")
        report.append(f"Files organized: {results['files_organized']}")
        report.append(f"Errors: {results['errors']}")
        report.append("")
        
        if self.organized_files:
            report.append("## Organized Files:")
            for file_path in self.organized_files:
                rel_path = file_path.relative_to(self.project_root)
                report.append(f"- {rel_path}")
        
        return "\n".join(report)


def main():
    """Main function to run import organization."""
    organizer = ImportOrganizer()
    
    print("Starting import organization...")
    print("This will reorganize imports according to PEP 8 standards.")
    
    # Run organization
    results = organizer.organize_all_files()
    
    # Verify syntax
    print("\nVerifying syntax of organized files...")
    syntax_errors = organizer.verify_syntax()
    
    if syntax_errors:
        print(f"⚠️  Syntax errors found in {len(syntax_errors)} files:")
        for file_path in syntax_errors:
            print(f"  - {file_path.relative_to(organizer.project_root)}")
        print("Please review these files manually.")
    else:
        print("✓ All organized files have valid syntax")
    
    # Generate report
    report = organizer.generate_report(results)
    
    # Save report
    report_path = Path("import_organization_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\nOrganization complete! Report saved to: {report_path}")
    print("\nSummary:")
    print(f"- Files processed: {results['files_processed']}")
    print(f"- Files organized: {results['files_organized']}")
    print(f"- Errors: {results['errors']}")


if __name__ == "__main__":
    main()
