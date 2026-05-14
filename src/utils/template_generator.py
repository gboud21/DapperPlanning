import json
from src.utils.paths import get_app_config_dir

class TemplateGenerator:
    _config = None

    @classmethod
    def _load_config(cls):
        if cls._config is None:
            config_path = get_app_config_dir() / 'default_templates.json'
            try:
                with open(config_path, 'r') as f:
                    cls._config = json.load(f)
            except Exception:
                cls._config = {}
        return cls._config

    @classmethod
    def generate(cls, item_type: str, tool: str, desc_type: str, out_of_scope: bool, compliance: bool) -> str:
        """
        Generates a template string based on the provided parameters.
        """
        config = cls._load_config()
        if not config:
            return ""

        syntax = config.get('syntax', {}).get(tool.lower(), 'markdown')
        layouts = config.get('base_layouts', {}).get(desc_type, {})
        block_names = layouts.get(item_type, [])
        
        all_blocks = config.get('blocks', {})
        
        result_parts = []
        for name in block_names:
            block = all_blocks.get(name, {})
            content = block.get(syntax, "")
            if content:
                result_parts.append(content)
        
        if out_of_scope:
            block = all_blocks.get('out_of_scope', {})
            content = block.get(syntax, "")
            if content:
                result_parts.append(content)
                
        if compliance:
            block = all_blocks.get('compliance', {})
            content = block.get(syntax, "")
            if content:
                result_parts.append(content)
                
        return "".join(result_parts)
