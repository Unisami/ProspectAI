# Contributing to ProspectAI

Thank you for your interest in contributing to ProspectAI! This document provides guidelines and information for contributors.

## 🎯 Project Overview

ProspectAI is an intelligent job prospecting automation system that discovers companies, extracts team information, and generates personalized outreach emails using AI. We welcome contributions that improve functionality, performance, documentation, and user experience.

## 🚀 Quick Start for Contributors

### Prerequisites

- Python 3.13 or higher
- Git
- Basic understanding of web scraping, APIs, and AI integration

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/outreach-for-job.git
   cd outreach-for-job
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your test API keys
   ```

5. **Validate Setup**
   ```bash
   python cli.py validate-config
   python -c "import cli; print('✓ Setup successful')"
   ```

## 🛠️ Development Workflow

### 1. **Before You Start**

- Check existing [issues](https://github.com/YOUR_USERNAME/outreach-for-job/issues) and [discussions](https://github.com/YOUR_USERNAME/outreach-for-job/discussions)
- Create an issue for new features or bugs
- Comment on issues you'd like to work on

### 2. **Development Process**

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write code following our [style guidelines](#code-style)
   - Add tests for new functionality
   - Update documentation as needed

3. **Test Your Changes**
   ```bash
   # Run core functionality tests
   python scripts/test_full_pipeline.py
   
   # Run specific component tests
   python scripts/test_email_pipeline.py
   
   # Validate imports and dependencies
   python utils/validate_imports.py
   
   # Run CLI tests
   python cli.py --dry-run discover --limit 1
   ```

4. **Commit and Push**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   git push origin feature/your-feature-name
   ```

5. **Create Pull Request**
   - Use the PR template
   - Link related issues
   - Provide clear description of changes

### 3. **Review Process**

- Maintainers will review your PR
- Address feedback and update as needed
- Once approved, your changes will be merged

## 📋 Contribution Areas

### 🔥 High Priority Areas

1. **AI Provider Integration**
   - Add new AI providers (Cohere, Mistral, etc.)
   - Improve prompt engineering
   - Optimize token usage and costs

2. **Data Sources**
   - Add new company discovery sources
   - Improve team extraction accuracy
   - Enhance LinkedIn profile discovery

3. **Email Generation**
   - Create new email templates
   - Improve personalization algorithms
   - Add A/B testing capabilities

4. **Performance Optimization**
   - Reduce processing time
   - Improve memory usage
   - Optimize API calls

### 🌟 Medium Priority Areas

1. **User Interface**
   - Improve CLI experience
   - Add web interface
   - Create dashboard improvements

2. **Integrations**
   - CRM integrations (Salesforce, HubSpot)
   - Email platforms (Mailchimp, SendGrid)
   - Social media platforms

3. **Analytics & Reporting**
   - Advanced analytics dashboard
   - Performance metrics
   - ROI tracking

### 💡 Documentation & Community

1. **Documentation**
   - Tutorial videos
   - Use case examples
   - API documentation improvements

2. **Testing**
   - Add unit tests
   - Integration test improvements
   - Performance benchmarks

3. **Localization**
   - Multi-language support
   - Regional email templates
   - Cultural adaptation

## 🎨 Code Style Guidelines

### Python Style

- **PEP 8** compliance with 88-character line limit
- **Type hints** for all functions and methods
- **Docstrings** for all public functions
- **Black** for code formatting
- **Flake8** for linting

```python
def process_company(
    company_data: CompanyData,
    config: Config,
    enable_ai: bool = True
) -> List[Prospect]:
    """Process a company to extract prospects.
    
    Args:
        company_data: Company information to process
        config: Application configuration
        enable_ai: Whether to use AI enhancement
        
    Returns:
        List of extracted prospects
        
    Raises:
        ProcessingError: If company processing fails
    """
    # Implementation here
    pass
```

### Code Organization

- **Services** - Business logic in `services/`
- **Models** - Data models in `models/`
- **Controllers** - Orchestration in `controllers/`
- **Utils** - Utilities in `utils/`
- **Tests** - All tests in `tests/`

### Error Handling

```python
from utils.error_handling import get_error_handler

def risky_operation():
    error_handler = get_error_handler()
    try:
        # Risky code here
        pass
    except Exception as e:
        error_info = error_handler.handle_error(
            error=e,
            service="my_service",
            operation="operation_name",
            context={"additional": "context"}
        )
        logger.error(f"Operation failed: {error_info.error_id}")
        raise
```

## 🧪 Testing Guidelines

### Test Categories

1. **Unit Tests** - Test individual functions
2. **Integration Tests** - Test component interactions
3. **End-to-End Tests** - Test complete workflows
4. **Performance Tests** - Test speed and resource usage

### Writing Tests

```python
import pytest
from unittest.mock import Mock, patch
from services.ai_service import AIService

class TestAIService:
    def setup_method(self):
        self.config = Mock()
        self.ai_service = AIService(self.config)
    
    @patch('services.ai_service.openai')
    def test_generate_response(self, mock_openai):
        # Arrange
        mock_openai.ChatCompletion.create.return_value = {
            'choices': [{'message': {'content': 'test response'}}]
        }
        
        # Act
        result = self.ai_service.generate_response("test prompt")
        
        # Assert
        assert result == "test response"
        mock_openai.ChatCompletion.create.assert_called_once()
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_ai_service.py

# Run with coverage
pytest --cov=services tests/

# Run integration tests
python scripts/test_full_pipeline.py
```

## 📖 Documentation Standards

### Code Documentation

- **Docstrings** for all public functions, classes, and modules
- **Type hints** for function signatures
- **Comments** for complex logic
- **README** updates for new features

### User Documentation

- Update relevant documentation files
- Add examples for new features
- Update CLI help text
- Create or update troubleshooting guides

### Example Documentation

```python
class EmailGenerator:
    """Generate personalized outreach emails using AI.
    
    This class orchestrates the email generation process by combining
    prospect data, company intelligence, and sender profiles to create
    highly personalized emails that achieve better response rates.
    
    Attributes:
        ai_service: AI service for content generation
        notion_manager: Data storage and retrieval
        config: Application configuration
        
    Example:
        >>> generator = EmailGenerator(ai_service, notion_manager, config)
        >>> email = generator.generate_email(prospect_id, template_type)
        >>> print(email.subject)
    """
```

## 🔧 Architecture Guidelines

### Design Principles

1. **Single Responsibility** - Each class/function has one job
2. **Dependency Injection** - Pass dependencies explicitly
3. **Configuration-Driven** - Use config for all settings
4. **Error Recovery** - Graceful handling of failures
5. **Testability** - Easy to unit test and mock

### Adding New Features

1. **Services** - Create service classes for business logic
2. **Models** - Define data models with type hints
3. **Configuration** - Add config options with validation
4. **CLI Integration** - Add CLI commands if needed
5. **Tests** - Comprehensive test coverage

### Example Service Structure

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from models.data_models import Prospect, CompanyData
from utils.config import Config

class ProspectExtractor(ABC):
    """Abstract base class for prospect extraction services."""
    
    def __init__(self, config: Config):
        self.config = config
    
    @abstractmethod
    def extract_prospects(self, company: CompanyData) -> List[Prospect]:
        """Extract prospects from company data."""
        pass

class LinkedInProspectExtractor(ProspectExtractor):
    """Extract prospects from LinkedIn company pages."""
    
    def extract_prospects(self, company: CompanyData) -> List[Prospect]:
        # Implementation here
        pass
```

## 🚨 Security Guidelines

### API Keys and Secrets

- **Never commit** API keys or secrets
- Use **environment variables** for configuration
- Add sensitive files to **.gitignore**
- **Validate** API keys before use

### External APIs

- **Rate limiting** for all external APIs
- **Retry logic** with exponential backoff
- **Error handling** for API failures
- **Monitoring** of API usage and costs

### Data Privacy

- **No PII** in logs or error messages
- **Secure storage** of temporary data
- **GDPR compliance** for European users
- **Clear data retention** policies

## 📊 Performance Guidelines

### Optimization Principles

1. **Parallel Processing** - Use async/await or threading
2. **Caching** - Cache expensive operations
3. **Rate Limiting** - Respect API limits
4. **Memory Management** - Clean up resources
5. **Profiling** - Measure before optimizing

### Performance Testing

```python
import time
from utils.performance import track_performance

@track_performance
def expensive_operation():
    start_time = time.time()
    # Your operation here
    duration = time.time() - start_time
    print(f"Operation took {duration:.2f} seconds")
```

## 🐛 Bug Reports

### When Reporting Bugs

1. **Search existing issues** first
2. **Provide clear reproduction steps**
3. **Include error messages and logs**
4. **Specify environment details**
5. **Add relevant configuration** (anonymized)

### Bug Report Template

```markdown
**Bug Description**
Clear description of the bug

**Reproduction Steps**
1. Step one
2. Step two
3. Step three

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Environment**
- OS: [e.g., Windows 11, macOS 12.6, Ubuntu 22.04]
- Python: [e.g., 3.13.1]
- ProspectAI Version: [e.g., 1.0.0]

**Error Messages**
```
Include any error messages or logs
```

**Configuration**
```yaml
# Relevant configuration (remove API keys)
```
```

## 💡 Feature Requests

### Proposing New Features

1. **Check existing feature requests**
2. **Describe the problem** you're solving
3. **Propose a solution** with examples
4. **Consider alternatives** and trade-offs
5. **Estimate complexity** and effort

### Feature Request Template

```markdown
**Problem Statement**
What problem does this feature solve?

**Proposed Solution**
How should this feature work?

**Examples**
Show examples of how it would be used

**Alternatives**
What other solutions did you consider?

**Additional Context**
Any other relevant information
```

## 📞 Getting Help

### Community Support

- **GitHub Discussions** - Questions and general discussion
- **GitHub Issues** - Bug reports and feature requests
- **Documentation** - Check README and docs/ directory
- **Examples** - Review examples/ directory

### Maintainer Contact

- **GitHub Issues** - Primary communication method
- **Email** - For security issues only
- **LinkedIn** - [Minhal Abdul Sami](https://www.linkedin.com/in/minhal-abdul-sami/)

## 🏆 Recognition

### Contributors

All contributors are recognized in:
- **GitHub Contributors** section
- **CHANGELOG.md** for significant contributions
- **README.md** acknowledgments
- **Release notes** for major features

### Contribution Types

We value all types of contributions:
- **Code** - New features, bug fixes, optimizations
- **Documentation** - Guides, examples, API docs
- **Testing** - Test cases, bug reports, QA
- **Design** - UI/UX improvements, graphics
- **Community** - Answering questions, moderation

## 📝 License

By contributing to ProspectAI, you agree that your contributions will be licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🎉 Thank You!

Your contributions make ProspectAI better for everyone. Whether you're fixing a typo, adding a feature, or helping other users, every contribution is valuable and appreciated!

---

**Questions?** Feel free to open a discussion or issue. We're here to help! 🚀