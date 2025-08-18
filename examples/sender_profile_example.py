"""
Example demonstrating the sender profile management system.
"""
import os
import sys
import tempfile

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.sender_profile_manager import SenderProfileManager
from models.data_models import SenderProfile


def main():
    """Demonstrate sender profile management functionality."""
    print("=== Sender Profile Management System Demo ===\n")
    
    manager = SenderProfileManager()
    
    # 1. Create a sample profile programmatically
    print("1. Creating a sample profile programmatically...")
    sample_profile = SenderProfile(
        name="John Doe",
        current_role="Senior Software Engineer",
        years_experience=5,
        key_skills=["Python", "JavaScript", "React", "AWS"],
        experience_summary="Experienced full-stack developer with 5 years in web development, specializing in scalable applications and cloud infrastructure.",
        education=["BS Computer Science - MIT"],
        certifications=["AWS Certified Developer", "Certified Kubernetes Administrator"],
        value_proposition="I build scalable web applications that drive business growth through clean code and modern architecture.",
        target_roles=["Senior Developer", "Tech Lead", "Principal Engineer"],
        industries_of_interest=["FinTech", "Healthcare", "E-commerce"],
        notable_achievements=[
            "Led team of 5 developers to deliver major product feature",
            "Reduced API response time by 40% through optimization",
            "Implemented CI/CD pipeline reducing deployment time by 60%"
        ],
        portfolio_links=["https://johndoe.dev", "https://github.com/johndoe"],
        preferred_contact_method="email",
        availability="Available with 2 weeks notice",
        location="San Francisco, CA",
        remote_preference="hybrid",
        salary_expectations="$120k-$150k"
    )
    
    print(f"✅ Created profile for {sample_profile.name}")
    print(f"   Completeness: {sample_profile.get_completeness_score():.1%}")
    print(f"   Is complete: {sample_profile.is_complete()}")
    
    # 2. Save profile in different formats
    print("\n2. Saving profile in different formats...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Save as markdown
        md_path = os.path.join(temp_dir, "profile.md")
        manager.save_profile_to_markdown(sample_profile, md_path)
        print(f"✅ Saved as Markdown: {md_path}")
        
        # Save as JSON
        json_path = os.path.join(temp_dir, "profile.json")
        manager.save_profile_to_json(sample_profile, json_path)
        print(f"✅ Saved as JSON: {json_path}")
        
        # Save as YAML
        yaml_path = os.path.join(temp_dir, "profile.yaml")
        manager.save_profile_to_yaml(sample_profile, yaml_path)
        print(f"✅ Saved as YAML: {yaml_path}")
        
        # 3. Load profile from different formats
        print("\n3. Loading profiles from different formats...")
        
        loaded_from_md = manager.load_profile_from_markdown(md_path)
        print(f"✅ Loaded from Markdown: {loaded_from_md.name}")
        
        loaded_from_json = manager.load_profile_from_json(json_path)
        print(f"✅ Loaded from JSON: {loaded_from_json.name}")
        
        loaded_from_yaml = manager.load_profile_from_yaml(yaml_path)
        print(f"✅ Loaded from YAML: {loaded_from_yaml.name}")
        
        # 4. Validate profile
        print("\n4. Validating profile...")
        is_valid, issues = manager.validate_profile(sample_profile)
        print(f"✅ Profile is valid: {is_valid}")
        if issues:
            print("   Issues found:")
            for issue in issues:
                print(f"   - {issue}")
        
        # 5. Get profile suggestions
        print("\n5. Getting profile improvement suggestions...")
        suggestions = manager.get_profile_suggestions(sample_profile)
        if suggestions:
            print("   Suggestions:")
            for suggestion in suggestions:
                print(f"   - {suggestion}")
        else:
            print("   No suggestions - profile looks great!")
        
        # 6. Test relevant experience matching
        print("\n6. Testing relevant experience matching...")
        relevant_exp = sample_profile.get_relevant_experience("Python Developer", "fintech")
        print("   Relevant experience for 'Python Developer' at 'fintech' company:")
        for exp in relevant_exp:
            print(f"   - {exp}")
        
        # 7. Show markdown content preview
        print("\n7. Markdown content preview:")
        print("=" * 50)
        with open(md_path, 'r') as f:
            content = f.read()
            # Show first few lines
            lines = content.split('\n')[:15]
            for line in lines:
                print(line)
            if len(content.split('\n')) > 15:
                print("... (truncated)")
        print("=" * 50)
    
    # 8. Create templates
    print("\n8. Creating profile templates...")
    
    md_template = manager.create_profile_template("markdown")
    print("✅ Created Markdown template")
    
    json_template = manager.create_profile_template("json")
    print("✅ Created JSON template")
    
    yaml_template = manager.create_profile_template("yaml")
    print("✅ Created YAML template")
    
    # 9. Test profile completeness and missing fields
    print("\n9. Testing profile completeness...")
    
    # Create incomplete profile
    incomplete_profile = SenderProfile(
        name="Jane Smith",
        current_role="Developer",
        years_experience=2
    )
    
    print(f"Incomplete profile completeness: {incomplete_profile.get_completeness_score():.1%}")
    print(f"Missing fields: {', '.join(incomplete_profile.get_missing_fields())}")
    
    print("\n=== Demo completed successfully! ===")


if __name__ == "__main__":
    main()