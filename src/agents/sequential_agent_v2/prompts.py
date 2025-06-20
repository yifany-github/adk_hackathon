"""
Clean Sequential Agent - Prompts
Simple workflow prompts for NHL commentary pipeline
"""

def get_workflow_prompt(game_id: str, timestamp_data: dict, board_context: dict) -> str:
    """Create simplified prompt for Sequential Agent"""
    
    period = timestamp_data.get("period", 1)
    time_in_period = timestamp_data.get("timeInPeriod", "0:00")
    score = board_context.get("current_score", {"away": 0, "home": 0})
    
    # Extract key events only
    events = timestamp_data.get("activities", [])
    key_events = [e for e in events if e.get("typeDescKey") in ["goal", "shot-on-goal", "hit", "penalty"]]
    
    prompt = f"""Game {game_id} | P{period} {time_in_period} | Score: {score["away"]}-{score["home"]}

Events: {key_events[:3] if key_events else "No significant events"}

Generate commentary: Alex Chen (play-by-play) and Mike Rodriguez (analyst). 2-3 natural exchanges.

Return JSON: {{"data_agent": {{"recommendation": "FILLER_CONTENT"}}, "commentary_agent": {{"commentary_sequence": [...]}}}}"""
    
    return prompt