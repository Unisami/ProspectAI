#!/usr/bin/env python3
"""

import ast
import sys
from pathlib import Path
from typing import (
    List,
    Set,
    Dict,
    Tuple
)

from utils.import_analyzer import ImportAnalyzer


Import cleaner script to automatically remove unused imports.
This script removes unused imports identified by the import analyzer.
"""


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class ImportCleaner:
    """Automatically removes unused imports from Python files."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.analyzer = ImportAnalyzer(project_root)
        self.cleaned_files = []
        self.backup_dir = Path("import_cleanup_backups")
        
    def create_backup(self, file_path: Path):
        """Create backup of file before cleaning."""
        if not self.backup_dir.exists():
            self.backup_dir.mkdir()
        
        backup_path = self.backup_dir / file_path.name
        counter = 1
        while backup_path.exists():
            name_parts = file_path.stem, counter, file_path.suffix
            backup_path = self.backup_dir / f"{name_parts[0]}_backup_{name_parts[1]}{name_parts[2]}"
            counter += 1
        
        with open(file_path, 'r', encoding='utf-8') as src:
            with open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
        
        return backup_path
    
    def remove_unused_imports(self, file_path: Path, unused_imports: List[Dict]) -> bool:
        """Remove unused imports from a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Sort unused imports by line number in descending order
            # This ensures we remove from bottom to top, preserving line numbers
            unused_imports.sort(key=lambda x: x['line'], reverse=True)
            
            lines_to_remove = set()
            
            for imp in unused_imports:
                line_idx = imp['line'] - 1  # Convert to 0-based index
                if 0 <= line_idx < len(lines):
                    line_content = lines[line_idx].strip()
                    
                    # Check if this is a multi-import line (e.g., "from x import a, b, c")
                    if self._is_multi_import_line(line_content, imp):
                        # Handle multi-import by removing just the specific import
                        lines[line_idx] = self._remove_from_multi_import(lines[line_idx], imp)
                    else:
                        # Mark entire line for removal
                        lines_to_remove.add(line_idx)
            
            # Remove marked lines
            cleaned_lines = [line for i, line in enumerate(lines) if i not in lines_to_remove]
            
            # Remove consecutive empty lines that might result from import removal
            cleaned_lines = self._clean_empty_lines(cleaned_lines)
            
            # Write cleaned content back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(cleaned_lines)
            
            return True
            
        except Exception as e:
            print(f"Error cleaning {file_path}: {e}")
            return False
    
    def _is_multi_import_line(self, line_content: str, imp: Dict) -> bool:
        """Check if line contains multiple imports."""
        if imp['type'] == 'from_import':
            # Look for comma-separated imports
            import_part = line_content.split('import', 1)
            if len(import_part) > 1:
                imports = import_part[1].strip()
                return ',' in imports
        return False
    
    def _remove_from_multi_import(self, line: str, imp: Dict) -> str:
        """Remove specific import from a multi-import line."""
        if imp['type'] != 'from_import':
            return line
        
        # Parse the import line
        parts = line.split('import', 1)
        if len(parts) != 2:
            return line
        
        prefix = parts[0] + 'import'
        imports_part = parts[1]
        
        # Split imports and remove the target import
        imports = [i.strip() for i in imports_part.split(',')]
        target_name = imp['original_name']
        
        # Remove the target import
        filtered_imports = [i for i in imports if not (
            i == target_name or 
            i.startswith(f"{target_name} as ") or
            i.strip() == target_name
        )]
        
        if not filtered_imports:
            # If no imports left, return empty string to remove line
            return ""
        
        # Reconstruct the line
        return f"{prefix} {', '.join(filtered_imports)}\n"
    
    def _clean_empty_lines(self, lines: List[str]) -> List[str]:
        """Remove excessive empty lines, keeping at most 2 consecutive empty lines."""
        cleaned = []
        empty_count = 0
        
        for line in lines:
            if line.strip() == "":
                empty_count += 1
                if empty_count <= 2:  # Allow up to 2 consecutive empty lines
                    cleaned.append(line)
            else:
                empty_count = 0
                cleaned.append(line)
        
        return cleaned
    
    def clean_all_files(self, create_backups: bool = True) -> Dict[str, int]:
        """Clean unused imports from all files."""
        print("Running import analysis...")
        self.analyzer.run_analysis()
        
        results = {
            'files_processed': 0,
            'files_cleaned': 0,
            'imports_removed': 0,
            'errors': 0
        }
        
        if not self.analyzer.unused_imports:
            print("No unused imports found!")
            return results
        
        print(f"Found unused imports in {len(self.analyzer.unused_imports)} files")
        
        for file_path, unused_imports in self.analyzer.unused_imports.items():
            results['files_processed'] += 1
            
            # Skip certain files that might have special import requirements
            if self._should_skip_file(file_path):
                print(f"Skipping {file_path.relative_to(self.project_root)} (special file)")
                continue
            
            print(f"Cleaning {file_path.relative_to(self.project_root)} ({len(unused_imports)} unused imports)")
            
            # Create backup if requested
            if create_backups:
                backup_path = self.create_backup(file_path)
                print(f"  Backup created: {backup_path}")
            
            # Clean the file
            if self.remove_unused_imports(file_path, unused_imports):
                results['files_cleaned'] += 1
                results['imports_removed'] += len(unused_imports)
                self.cleaned_files.append(file_path)
                print(f"  ✓ Cleaned {len(unused_imports)} unused imports")
            else:
                results['errors'] += 1
                print(f"  ✗ Error cleaning file")
        
        return results
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during cleaning."""
        # Skip __init__.py files as they often have re-exports
        if file_path.name == '__init__.py':
            return True
        
        # Skip files that might have special import requirements
        skip_patterns = [
            'test_*',  # Test files might have imports for fixtures
            '*_test.py',
            'conftest.py',
            'setup.py',
            '__main__.py'
        ]
        
        for pattern in skip_patterns:
            if file_path.match(pattern):
                return True
        
        return False
    
    def verify_syntax(self) -> List[Path]:
        """Verify syntax of all cleaned files."""
        syntax_errors = []
        
        for file_path in self.cleaned_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                ast.parse(content)
            except SyntaxError as e:
                syntax_errors.append(file_path)
                print(f"Syntax error in {file_path}: {e}")
        
        return syntax_errors
    
    def generate_cleanup_report(self, results: Dict[str, int]) -> str:
        """Generate cleanup report."""
        report = []
        report.append("# Import Cleanup Report")
        report.append("=" * 50)
        report.append("")
        report.append(f"Files processed: {results['files_processed']}")
        report.append(f"Files cleaned: {results['files_cleaned']}")
        report.append(f"Imports removed: {results['imports_removed']}")
        report.append(f"Errors: {results['errors']}")
        report.append("")
        
        if self.cleaned_files:
            report.append("## Cleaned Files:")
            for file_path in self.cleaned_files:
                rel_path = file_path.relative_to(self.project_root)
                report.append(f"- {rel_path}")
        
        return "\n".join(report)


def main():
    """Main function to run import cleanup."""
    cleaner = ImportCleaner()
    
    print("Starting import cleanup...")
    print("This will create backups before making changes.")
    
    # Run cleanup
    results = cleaner.clean_all_files(create_backups=True)
    
    # Verify syntax
    print("\nVerifying syntax of cleaned files...")
    syntax_errors = cleaner.verify_syntax()
    
    if syntax_errors:
        print(f"⚠️  Syntax errors found in {len(syntax_errors)} files:")
        for file_path in syntax_errors:
            print(f"  - {file_path.relative_to(cleaner.project_root)}")
        print("Please review these files manually.")
    else:
        print("✓ All cleaned files have valid syntax")
    
    # Generate report
    report = cleaner.generate_cleanup_report(results)
    
    # Save report
    report_path = Path("import_cleanup_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\nCleanup complete! Report saved to: {report_path}")
    print("\nSummary:")
    print(f"- Files processed: {results['files_processed']}")
    print(f"- Files cleaned: {results['files_cleaned']}")
    print(f"- Imports removed: {results['imports_removed']}")
    print(f"- Errors: {results['errors']}")
    
    if results['files_cleaned'] > 0:
        print(f"\nBackups created in: {cleaner.backup_dir}")
        print("Run your tests to ensure everything still works correctly.")


if __name__ == "__main__":
    main()
