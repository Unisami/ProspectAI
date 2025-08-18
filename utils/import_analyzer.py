#!/usr/bin/env python3
"""
Import analyzer script to identify unused imports and circular dependencies.
This script analyzes all Python files in the project and provides recommendations
for import optimization.
"""

import ast
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional


class ImportAnalyzer:
    """Analyzes Python imports for optimization opportunities."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.python_files = []
        self.imports_by_file = {}
        self.used_names_by_file = {}
        self.circular_dependencies = []
        self.unused_imports = {}
        
    def find_python_files(self) -> List[Path]:
        """Find all Python files in the project."""
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            # Skip common directories that don't need analysis
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.pytest_cache', 'venv', '.venv'}]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        return python_files
    
    def parse_file_imports(self, file_path: Path) -> Tuple[List[Dict], Set[str]]:
        """Parse imports and used names from a Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            imports = []
            used_names = set()
            
            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({
                            'type': 'import',
                            'module': alias.name,
                            'name': alias.asname or alias.name.split('.')[0],
                            'line': node.lineno
                        })
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        imports.append({
                            'type': 'from_import',
                            'module': module,
                            'name': alias.asname or alias.name,
                            'original_name': alias.name,
                            'line': node.lineno
                        })
                elif isinstance(node, ast.Name):
                    used_names.add(node.id)
                elif isinstance(node, ast.Attribute):
                    # Handle attribute access like module.function
                    if isinstance(node.value, ast.Name):
                        used_names.add(node.value.id)
            
            return imports, used_names
            
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return [], set()
    
    def analyze_unused_imports(self):
        """Identify unused imports in each file."""
        for file_path in self.python_files:
            imports, used_names = self.parse_file_imports(file_path)
            self.imports_by_file[file_path] = imports
            self.used_names_by_file[file_path] = used_names
            
            unused = []
            for imp in imports:
                import_name = imp['name']
                
                # Skip certain imports that might be used implicitly
                if self._is_implicit_import(imp, file_path):
                    continue
                
                if import_name not in used_names:
                    unused.append(imp)
            
            if unused:
                self.unused_imports[file_path] = unused
    
    def _is_implicit_import(self, imp: Dict, file_path: Path) -> bool:
        """Check if import might be used implicitly (e.g., in __init__.py, decorators, etc.)."""
        # Skip analysis for __init__.py files as they often have re-exports
        if file_path.name == '__init__.py':
            return True
        
        # Skip common implicit imports
        implicit_modules = {
            'typing', 'dataclasses', 'abc', 'enum', 'functools',
            'pytest', 'unittest', 'mock'
        }
        
        if imp['module'] in implicit_modules or imp['name'] in implicit_modules:
            return True
        
        # Skip if it's a decorator or might be used in type hints
        if imp['name'].lower() in {'dataclass', 'abstractmethod', 'property', 'classmethod', 'staticmethod'}:
            return True
        
        return False
    
    def detect_circular_dependencies(self):
        """Detect circular import dependencies."""
        # Build dependency graph
        dependency_graph = defaultdict(set)
        
        for file_path, imports in self.imports_by_file.items():
            for imp in imports:
                module_name = imp['module']
                
                # Convert module name to file path if it's a local import
                if self._is_local_import(module_name):
                    target_file = self._module_to_file_path(module_name)
                    if target_file and target_file in self.imports_by_file:
                        dependency_graph[file_path].add(target_file)
        
        # Find cycles using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(node, path):
            if node in rec_stack:
                # Found a cycle
                try:
                    cycle_start = path.index(node)
                    cycle = path[cycle_start:] + [node]
                    return cycle
                except ValueError:
                    return [node]
            
            if node in visited:
                return None
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in dependency_graph.get(node, set()):
                cycle = has_cycle(neighbor, path + [node])
                if cycle:
                    return cycle
            
            rec_stack.remove(node)
            return None
        
        # Convert to list to avoid dictionary size change during iteration
        nodes_to_check = list(dependency_graph.keys())
        for file_path in nodes_to_check:
            if file_path not in visited:
                cycle = has_cycle(file_path, [])
                if cycle:
                    self.circular_dependencies.append(cycle)
    
    def _is_local_import(self, module_name: str) -> bool:
        """Check if module is a local import."""
        # Simple heuristic: if it starts with project components
        local_prefixes = ['controllers', 'services', 'models', 'utils', 'tests']
        return any(module_name.startswith(prefix) for prefix in local_prefixes)
    
    def _module_to_file_path(self, module_name: str) -> Optional[Path]:
        """Convert module name to file path."""
        parts = module_name.split('.')
        potential_path = self.project_root / '/'.join(parts)
        
        # Try .py file
        py_file = potential_path.with_suffix('.py')
        if py_file.exists():
            return py_file
        
        # Try __init__.py in directory
        init_file = potential_path / '__init__.py'
        if init_file.exists():
            return init_file
        
        return None
    
    def generate_report(self) -> str:
        """Generate a comprehensive import analysis report."""
        report = []
        report.append("# Import Analysis Report")
        report.append("=" * 50)
        report.append("")
        
        # Summary
        total_files = len(self.python_files)
        files_with_unused = len(self.unused_imports)
        total_unused = sum(len(unused) for unused in self.unused_imports.values())
        
        report.append(f"## Summary")
        report.append(f"- Total Python files analyzed: {total_files}")
        report.append(f"- Files with unused imports: {files_with_unused}")
        report.append(f"- Total unused imports: {total_unused}")
        report.append(f"- Circular dependencies found: {len(self.circular_dependencies)}")
        report.append("")
        
        # Unused imports by file
        if self.unused_imports:
            report.append("## Unused Imports")
            report.append("-" * 30)
            for file_path, unused in self.unused_imports.items():
                rel_path = file_path.relative_to(self.project_root)
                report.append(f"\n### {rel_path}")
                for imp in unused:
                    if imp['type'] == 'import':
                        report.append(f"  Line {imp['line']}: import {imp['module']}")
                    else:
                        report.append(f"  Line {imp['line']}: from {imp['module']} import {imp['original_name']}")
        
        # Circular dependencies
        if self.circular_dependencies:
            report.append("\n## Circular Dependencies")
            report.append("-" * 30)
            for i, cycle in enumerate(self.circular_dependencies, 1):
                report.append(f"\n### Cycle {i}:")
                for file_path in cycle:
                    rel_path = file_path.relative_to(self.project_root)
                    report.append(f"  -> {rel_path}")
        
        return "\n".join(report)
    
    def run_analysis(self):
        """Run complete import analysis."""
        print("Finding Python files...")
        self.python_files = self.find_python_files()
        print(f"Found {len(self.python_files)} Python files")
        
        print("Analyzing unused imports...")
        self.analyze_unused_imports()
        
        print("Detecting circular dependencies...")
        self.detect_circular_dependencies()
        
        print("Analysis complete!")


def main():
    """Main function to run import analysis."""
    analyzer = ImportAnalyzer()
    analyzer.run_analysis()
    
    # Generate and save report
    report = analyzer.generate_report()
    
    # Save report to file
    report_path = Path("import_analysis_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\nReport saved to: {report_path}")
    print("\nReport preview:")
    print("=" * 50)
    print(report[:1000] + "..." if len(report) > 1000 else report)


if __name__ == "__main__":
    main()