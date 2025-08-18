# Sender Profile Guide

## Introduction

The Sender Profile system allows you to create and manage your professional profile information for personalized outreach emails. By providing details about your background, skills, and experience, the system can generate highly personalized emails that highlight your relevant qualifications to each prospect.

This guide covers how to set up, manage, and use sender profiles in the Job Prospect Automation system.

## Profile Formats

The system supports three different formats for sender profiles:

1. **Markdown** (Recommended): Human-readable text format that's easy to edit
2. **JSON**: Structured data format suitable for programmatic use
3. **YAML**: Human-readable structured format that's a good middle ground

## Markdown Profile Format

The recommended way to create and manage your sender profile is using the Markdown format. Here's an example template:

```markdown
# Sender Profile

## Basic Information
- **Name**: John Doe
- **Current Role**: Senior Software Engineer
- **Years of Experience**: 5
- **Location**: San Francisco, CA
- **Remote Preference**: Hybrid
- **Availability**: Available with 2 weeks notice
- **Salary Expectations**: $120k-$150k

## Professional Summary
Experienced full-stack developer with 5 years in web development, specializing in scalable applications and cloud infrastructure.

## Key Skills
- Python
- JavaScript
- React
- AWS

## Experience Highlights
- Led team of 5 developers to deliver major product feature
- Reduced API response time by 40% through optimization
- Implemented CI/CD pipeline reducing deployment time by 60%

## Education & Certifications
- BS Computer Science - MIT
- AWS Certified Developer
- Certified Kubernetes Administrator

## Value Proposition
I build scalable web applications that drive business growth through clean code and modern architecture.

## Target Roles
- Senior Developer
- Tech Lead
- Principal Engineer

## Industries of Interest
- FinTech
- Healthcare
- E-commerce

## Portfolio/Links
- https://johndoe.dev
- https://github.com/johndoe

## Additional Context
Any other relevant information for personalization.
```

### Markdown Format Best Practices

1. **Section Headers**: Keep the section headers exactly as shown (## Basic Information, ## Professional Summary, etc.)
2. **Basic Information**: Format as bullet points with bold field names
3. **List Items**: Use bullet points (- ) for all list items
4. **URLs**: Include full URLs with http:// or https:// prefix
5. **Text Sections**: Write paragraphs without bullet points for Professional Summary and Value Proposition

## JSON Configuration Format

For programmatic use or integration with other systems, you can use the JSON format:

```json
{
  "name": "John Doe",
  "current_role": "Senior Software Engineer",
  "years_experience": 5,
  "key_skills": ["Python", "JavaScript", "React", "AWS"],
  "experience_summary": "Experienced full-stack developer with 5 years in web development, specializing in scalable applications and cloud infrastructure.",
  "education": ["BS Computer Science - MIT"],
  "certifications": ["AWS Certified Developer", "Certified Kubernetes Administrator"],
  "value_proposition": "I build scalable web applications that drive business growth through clean code and modern architecture.",
  "target_roles": ["Senior Developer", "Tech Lead", "Principal Engineer"],
  "industries_of_interest": ["FinTech", "Healthcare", "E-commerce"],
  "notable_achievements": [
    "Led team of 5 developers to deliver major product feature",
    "Reduced API response time by 40% through optimization",
    "Implemented CI/CD pipeline reducing deployment time by 60%"
  ],
  "portfolio_links": ["https://johndoe.dev", "https://github.com/johndoe"],
  "preferred_contact_method": "email",
  "availability": "Available with 2 weeks notice",
  "location": "San Francisco, CA",
  "remote_preference": "hybrid",
  "salary_expectations": "$120k-$150k",
  "additional_context": {}
}
```

### JSON Format Best Practices

1. **Field Names**: Use the exact field names shown above
2. **Data Types**: Ensure proper data types (strings, numbers, arrays)
3. **Arrays**: Use arrays for all list fields (skills, achievements, etc.)
4. **Validation**: All JSON profiles must be valid JSON format

## YAML Configuration Format

YAML offers a more human-readable alternative to JSON:

```yaml
name: John Doe
current_role: Senior Software Engineer
years_experience: 5
key_skills:
  - Python
  - JavaScript
  - React
  - AWS
experience_summary: Experienced full-stack developer with 5 years in web development, specializing in scalable applications and cloud infrastructure.
education:
  - BS Computer Science - MIT
certifications:
  - AWS Certified Developer
  - Certified Kubernetes Administrator
value_proposition: I build scalable web applications that drive business growth through clean code and modern architecture.
target_roles:
  - Senior Developer
  - Tech Lead
  - Principal Engineer
industries_of_interest:
  - FinTech
  - Healthcare
  - E-commerce
notable_achievements:
  - Led team of 5 developers to deliver major product feature
  - Reduced API response time by 40% through optimization
  - Implemented CI/CD pipeline reducing deployment time by 60%
portfolio_links:
  - https://johndoe.dev
  - https://github.com/johndoe
preferred_contact_method: email
availability: Available with 2 weeks notice
location: San Francisco, CA
remote_preference: hybrid
salary_expectations: $120k-$150k
additional_context: {}
```

### YAML Format Best Practices

1. **Indentation**: Use consistent indentation (2 spaces recommended)
2. **Lists**: Format lists with hyphens and proper indentation
3. **Strings**: No need for quotes unless strings contain special characters
4. **Validation**: All YAML profiles must be valid YAML format

## Interactive Profile Setup

The system provides an interactive CLI-based wizard to create your sender profile:

```
python cli.py profile create --interactive --output profiles/my_profile.md
```

The interactive setup will guide you through each section with prompts and examples:

1. **Basic Information**: Name, role, experience, location, etc.
2. **Professional Summary**: Brief overview of your background
3. **Key Skills**: Your technical and professional skills
4. **Experience Highlights**: Notable achievements and accomplishments
5. **Education & Certifications**: Academic background and certifications
6. **Value Proposition**: What unique value you bring to employers
7. **Target Roles**: Positions you're interested in
8. **Industries of Interest**: Industries you want to work in
9. **Portfolio Links**: URLs to your online presence

### Interactive Setup Tips

1. **Required Fields**: Some fields are required and cannot be skipped
2. **Multi-line Input**: For longer text fields, you can enter multiple lines
3. **List Input**: For lists, enter items one by one, press Enter on empty line to finish
4. **URL Validation**: Portfolio links are validated to ensure they're proper URLs
5. **Preview**: After completion, you'll see a preview of your profile

## Profile Validation and Completeness

The system validates profiles to ensure they meet minimum requirements:

### Required Fields
- Name
- Current Role
- Years of Experience

### Completeness Score

Profiles are assigned a completeness score based on how many fields are filled:

- **90-100%**: Excellent - Will generate highly personalized emails
- **70-89%**: Good - Sufficient for effective personalization
- **50-69%**: Fair - Basic personalization possible
- **Below 50%**: Poor - Limited personalization capabilities

### Validation Rules

1. **Name**: Cannot be empty
2. **Current Role**: Cannot be empty
3. **Years Experience**: Must be a non-negative integer
4. **Portfolio Links**: Must be valid URLs with http:// or https:// prefix
5. **Remote Preference**: If specified, must be one of: remote, hybrid, on-site, flexible
6. **Preferred Contact Method**: Must be one of: email, linkedin, phone, other

## CLI Commands for Profile Management

The system provides several CLI commands for managing sender profiles:

### Create a Profile

```
python cli.py profile create --format markdown --output profiles/my_profile.md --interactive
```

Options:
- `--format`: Output format (markdown, json, yaml)
- `--output`: Output file path
- `--interactive/--template`: Create interactively or generate template

### Validate a Profile

```
python cli.py profile validate profiles/my_profile.md
```

Options:
- `--format`: Profile format (auto-detected from file extension if not specified)

### Preview a Profile

```
python cli.py profile preview profiles/my_profile.md
```

Options:
- `--format`: Profile format (auto-detected from file extension if not specified)

### Convert Between Formats

```
python cli.py profile convert profiles/my_profile.md profiles/my_profile.json
```

Options:
- `--input-format`: Input format (auto-detected from file extension if not specified)
- `--output-format`: Output format (auto-detected from file extension if not specified)

### Edit a Profile

```
python cli.py profile edit profiles/my_profile.md
```

Options:
- `--format`: Profile format (auto-detected from file extension if not specified)

### Check Completeness

```
python cli.py profile check-completeness profiles/my_profile.md --threshold 0.7
```

Options:
- `--format`: Profile format (auto-detected from file extension if not specified)
- `--threshold`: Completeness threshold (0.0-1.0, default: 0.7)

### Generate Template

```
python cli.py profile generate-template --format markdown --output profiles/template.md
```

Options:
- `--format`: Output format (markdown, json, yaml)
- `--output`: Output file path

### List Profiles

```
python cli.py profile list --directory profiles --format all
```

Options:
- `--directory`: Directory to search for profiles
- `--format`: Filter profiles by format (markdown, json, yaml, all)

### Analyze Profile

```
python cli.py profile analyze profiles/my_profile.md --target-role "Python Developer"
```

Options:
- `--format`: Profile format (auto-detected from file extension if not specified)
- `--target-role`: Target role to analyze relevance for
- `--target-company`: Target company to analyze relevance for

## Best Practices for Effective Profiles

1. **Be Specific**: Include specific skills, technologies, and achievements
2. **Quantify Achievements**: Use numbers and metrics when describing accomplishments
3. **Target Roles**: Be specific about the roles you're targeting
4. **Value Proposition**: Clearly articulate what unique value you bring
5. **Keep Updated**: Regularly update your profile with new skills and achievements
6. **Completeness**: Aim for at least 70% completeness score
7. **Relevance**: Include information relevant to your target industries and roles
8. **Portfolio Links**: Include links to your online presence (LinkedIn, GitHub, personal website)