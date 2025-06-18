"""
Sequential Agent Prompts - NHL Commentary Workflow
"""

def get_workflow_prompt(game_id: str, timestamp_data: str) -> str:
    """Simple workflow prompt for Sequential Agent"""
    return f"""Process NHL timestamp for game {game_id}:

{timestamp_data}

WORKFLOW:
1. Data Agent: Analyze the timestamp data
2. Commentary Agent: Create broadcast commentary from analysis
3. Audio Agent: Convert commentary to TTS audio

Process through complete NHL workflow."""