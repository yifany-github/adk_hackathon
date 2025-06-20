"""
Sequential Agent Prompts - NHL Commentary Workflow
"""

def get_workflow_prompt(game_id: str, timestamp_data: str) -> str:
    """Enhanced workflow prompt with formatted output requirements"""
    return f"""Process NHL timestamp for game {game_id}:

{timestamp_data}

CRITICAL: Each agent MUST output clean, properly formatted JSON without any ADK Part objects or raw text.

WORKFLOW WITH FORMATTED OUTPUTS:
1. Data Agent: Analyze the timestamp data
   - Output ONLY clean JSON with "for_commentary_agent" structure
   - No extra text, no Part objects, just pure JSON

2. Commentary Agent: Create professional two-person broadcast commentary (Alex Chen & Mike Rodriguez)
   - Output ONLY clean JSON with "commentary_sequence" structure
   - Format: {{"status": "success", "commentary_sequence": [...]}}
   - No extra text, no Part objects, just pure JSON

3. Audio Agent: Convert commentary to TTS audio
   - Output ONLY clean JSON with "audio_processing_details" structure
   - Format: {{"status": "success", "audio_processing_details": [...]}}
   - No extra text, no Part objects, just pure JSON

FORMATTING REQUIREMENT: All outputs must be clean JSON that can be parsed directly."""


def get_clean_output_instructions() -> str:
    """Instructions for clean JSON output formatting"""
    return """
CRITICAL OUTPUT FORMATTING RULES:
- Each agent must output ONLY clean, parseable JSON
- No text before or after the JSON
- No "parts=" or ADK object references
- Use proper JSON structure with double quotes
- Ensure all JSON is valid and parseable
- No debugging text or extra comments
"""