import urllib.request
import json
import ssl
from src.infrastructure.telemetry.logger import logger

class GenericLLMClient:
    def __init__(self, context):
        self.settings = context.resolve('settings_manager')
        
    def send_chat_turn(self, conversation_history: list) -> dict:
        """Sends a multi-turn conversation list to the configured endpoint and returns structured data."""
        api_key = self.settings.get('ai_api_key', '')
        endpoint_tpl = self.settings.get('ai_endpoint', '')
        model_name = self.settings.get('ai_model', '')
        
        # Build URL dynamically, appending API query tokens if utilizing Gemini fallbacks
        url = endpoint_tpl.format(model=model_name)
        if "generativelanguage.googleapis.com" in url:
            url += f"?key={api_key}"
            
        # Construct provider payload body (Gemini structure shown as base reference)
        # Enforce structured JSON constraint via system instructions or responseMimeType
        payload = {
            "contents": conversation_history,
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        
        logger.info(f"Sending AI request to {url}")
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        try:
            # Use a more secure context if possible, but allow unverified for internal flexibility if needed
            # In production, we should use a proper verified context
            ctx = ssl._create_unverified_context() 
            with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                
                # Extract text block matching standard Gemini v1beta response paths
                if 'candidates' in res_data and len(res_data['candidates']) > 0:
                    text_content = res_data['candidates'][0]['content']['parts'][0]['text']
                    return json.loads(text_content) # Yields compiled schema dictionary
                else:
                    raise ValueError("Malformed response: No candidates found")
        except Exception as e:
            logger.error(f"AI Client Error: {str(e)}")
            return {
                "estimated_hours": 0.0,
                "reasoning": f"Network execution timeout or schema validation failure: {str(e)}"
            }
