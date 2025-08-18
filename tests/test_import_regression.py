#!/usr/bin/env python3
"""
Test script to prevent import regression.
This test ensures that no unused imports are introduced in the future.
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Set, Dict, Tuple
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.import_analyzer import ImportAnalyzer


class TestImportRegression:
    """Test class to prevent import regression."""
    
    @pytest.fixture(scope="class")
    def analyzer(self):
        """Create import analyzer instance."""
        return ImportAnalyzer()
    
    def test_no_unused_imports_in_core_services(self, analyzer):
        """Test that core services have no unused imports."""
        analyzer.run_analysis()
        
        # Define core service files that should have clean imports
        core_services = [
            "services/ai_service.py",
            "services/ai_parser.py", 
            "services/email_generator.py",
            "services/linkedin_scraper.py",
            "services/product_hunt_scraper.py",
            "services/notion_manager.py",
            "services/openai_client_manager.py",
            "services/caching_service.py",
            "services/parallel_processor.py"
        ]
        
        unused_in_core = {}
        for service_file in core_services:
            service_path = Path(service_file)
            if service_path in analyzer.unused_imports:
                unused_in_core[service_file] = analyzer.unused_imports[service_path]
        
        if unused_in_core:
            error_msg = "Unused imports found in core services:\n"
            for file_path, unused_imports in unused_in_core.items():
                error_msg += f"\n{file_path}:\n"
                for imp in unused_imports:
                    if imp['type'] == 'import':
                        error_msg += f"  Line {imp['line']}: import {imp['module']}\n"
                    else:
                        error_msg += f"  Line {imp['line']}: from {imp['module']} import {imp['original_name']}\n"
            
            pytest.fail(error_msg)
    
    def test_no_unused_imports_in_utils(self, analyzer):
        """Test that utility modules have no unused imports."""
        analyzer.run_analysis()
        
        # Define utility files that should have clean imports
        util_files = [
            "utils/base_service.py",
            "utils/configuration_service.py",
            "utils/error_handling_enhanced.py",
            "utils/rate_limiting.py",
            "utils/validation_framework.py",
            "utils/webdriver_manager.py"
        ]
        
        unused_in_utils = {}
        for util_file in util_files:
            util_path = Path(util_file)
            if util_path in analyzer.unused_imports:
                unused_in_utils[util_file] = analyzer.unused_imports[util_path]
        
        if unused_in_utils:
            error_msg = "Unused imports found in utility modules:\n"
            for file_path, unused_imports in unused_in_utils.items():
                error_msg += f"\n{file_path}:\n"
                for imp in unused_imports:
                    if imp['type'] == 'import':
                        error_msg += f"  Line {imp['line']}: import {imp['module']}\n"
                    else:
                        error_msg += f"  Line {imp['line']}: from {imp['module']} import {imp['original_name']}\n"
            
            pytest.fail(error_msg)
    
    def test_no_circular_dependencies(self, analyzer):
        """Test that there are no circular dependencies."""
        analyzer.run_analysis()
        
        if analyzer.circular_dependencies:
            error_msg = "Circular dependencies found:\n"
            for i, cycle in enumerate(analyzer.circular_dependencies, 1):
                error_msg += f"\nCycle {i}:\n"
                for file_path in cycle:
                    if isinstance(file_path, Path):
                        rel_path = file_path.relative_to(analyzer.project_root)
                        error_msg += f"  -> {rel_path}\n"
                    else:
                        error_msg += f"  -> {file_path}\n"
            
            pytest.fail(error_msg)
    
    def test_all_python_files_have_valid_syntax(self):
        """Test that all Python files have valid syntax."""
        project_root = Path(__file__).parent.parent
        python_files = []
        
        for root, dirs, files in os.walk(project_root):
            # Skip common directories that don't need analysis
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.pytest_cache', 'venv', '.venv', 'import_cleanup_backups'}]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        syntax_errors = []
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                ast.parse(content)
            except SyntaxError as e:
                syntax_errors.append((file_path, str(e)))
            except Exception as e:
                # Skip files that can't be read (e.g., binary files)
                continue
        
        if syntax_errors:
            error_msg = "Syntax errors found in Python files:\n"
            for file_path, error in syntax_errors:
                rel_path = file_path.relative_to(project_root)
                error_msg += f"\n{rel_path}: {error}\n"
            
            pytest.fail(error_msg)
    
    def test_import_organization_standards(self):
        """Test that imports follow organization standards."""
        project_root = Path(__file__).parent.parent
        
        # Define files to check for import organization
        files_to_check = [
            "services/ai_service.py",
            "services/ai_parser.py",
            "services/email_generator.py",
            "utils/base_service.py",
            "utils/configuration_service.py"
        ]
        
        organization_violations = []
        
        for file_path in files_to_check:
            full_path = project_root / file_path
            if not full_path.exists():
                continue
            
            violations = self._check_import_organization(full_path)
            if violations:
                organization_violations.extend([(file_path, v) for v in violations])
        
        if organization_violations:
            error_msg = "Import organization violations found:\n"
            for file_path, violation in organization_violations:
                error_msg += f"\n{file_path}: {violation}\n"
            
            pytest.fail(error_msg)
    
    def _check_import_organization(self, file_path: Path) -> List[str]:
        """Check import organization in a file."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            imports = []
            
            # Extract imports with line numbers
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    imports.append((node.lineno, node))
            
            # Sort by line number
            imports.sort(key=lambda x: x[0])
            
            # Check for proper grouping (standard library, third-party, local)
            import_groups = self._categorize_imports(imports)
            
            # Check if groups are properly separated
            if len(import_groups['standard']) > 0 and len(import_groups['third_party']) > 0:
                last_standard = max(imp[0] for imp in import_groups['standard'])
                first_third_party = min(imp[0] for imp in import_groups['third_party'])
                if first_third_party <= last_standard:
                    violations.append("Standard library imports should come before third-party imports")
            
            if len(import_groups['third_party']) > 0 and len(import_groups['local']) > 0:
                last_third_party = max(imp[0] for imp in import_groups['third_party'])
                first_local = min(imp[0] for imp in import_groups['local'])
                if first_local <= last_third_party:
                    violations.append("Third-party imports should come before local imports")
            
        except Exception as e:
            violations.append(f"Error checking import organization: {e}")
        
        return violations
    
    def _categorize_imports(self, imports: List[Tuple[int, ast.AST]]) -> Dict[str, List[Tuple[int, ast.AST]]]:
        """Categorize imports into standard library, third-party, and local."""
        import_groups = {
            'standard': [],
            'third_party': [],
            'local': []
        }
        
        # Standard library modules (common ones)
        standard_modules = {
            'os', 'sys', 'json', 'time', 'datetime', 'pathlib', 'typing', 'enum',
            'dataclasses', 'abc', 'functools', 'itertools', 'collections', 'logging',
            'urllib', 're', 'ast', 'threading', 'queue', 'tempfile', 'io', 'hashlib'
        }
        
        # Local modules (project-specific)
        local_prefixes = {'controllers', 'services', 'models', 'utils', 'tests'}
        
        for line_no, node in imports:
            if isinstance(node, ast.Import):
                module_name = node.names[0].name.split('.')[0]
            elif isinstance(node, ast.ImportFrom):
                module_name = (node.module or '').split('.')[0]
            else:
                continue
            
            if module_name in standard_modules:
                import_groups['standard'].append((line_no, node))
            elif any(module_name.startswith(prefix) for prefix in local_prefixes):
                import_groups['local'].append((line_no, node))
            else:
                import_groups['third_party'].append((line_no, node))
        
        return import_groups


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])