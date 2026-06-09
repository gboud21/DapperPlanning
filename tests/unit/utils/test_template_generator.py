import pytest
from src.utils.template_generator import TemplateGenerator

class TestTemplateGenerator:
    def test_basic_generation(self):
        """Verifies the generator returns a valid string for basic inputs."""
        content = TemplateGenerator.generate(
            item_type="Epic", 
            tool="GitLab", 
            desc_type="Heavyweight", 
            out_of_scope=False, 
            compliance=False
        )
        assert isinstance(content, str)
        assert len(content) > 0

    def test_out_of_scope_inclusion(self):
        """Verifies the out of scope section is added when requested."""
        content = TemplateGenerator.generate(
            item_type="Feature", 
            tool="Jira", 
            desc_type="Lightweight", 
            out_of_scope=True, 
            compliance=False
        )
        assert "Out of Scope" in content or "out of scope" in content.lower()

    def test_compliance_inclusion(self):
        """Verifies compliance and security sections are injected."""
        content = TemplateGenerator.generate(
            item_type="Story", 
            tool="GitLab", 
            desc_type="Heavyweight", 
            out_of_scope=False, 
            compliance=True
        )
        assert "Compliance" in content or "Security" in content or "compliance" in content.lower()
