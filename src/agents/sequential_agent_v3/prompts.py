"""
Complete Sequential Agent V3 - Prompts
Enhanced workflow prompts for NHL commentary pipeline with audio integration
"""

def get_workflow_prompt_v3(game_id: str, timestamp_data: dict, board_context: dict, commentary_context: dict = None) -> str:
    """Create enhanced prompt for Sequential Agent V3 with audio processing support"""
    
    period = timestamp_data.get("period", 1)
    time_in_period = timestamp_data.get("timeInPeriod", "0:00")
    score = board_context.get("current_score", {"away": 0, "home": 0})
    
    # Extract key events only
    events = timestamp_data.get("activities", [])
    key_events = [e for e in events if e.get("typeDescKey") in ["goal", "shot-on-goal", "hit", "penalty"]]
    
    # Add recent commentary context for natural flow
    context_section = ""
    if commentary_context and commentary_context.get("recent_dialogue"):
        recent_exchanges = commentary_context["recent_dialogue"][-3:]  # Last 3 exchanges only
        context_section = f"\nRecent commentary:\n"
        for exchange in recent_exchanges:
            context_section += f"- {exchange['speaker']}: \"{exchange['text'][:50]}...\"\n"
        context_section += "\nContinue naturally from above, avoid repetition.\n"
    
    prompt = f"""Game {game_id} | P{period} {time_in_period} | Score: {score["away"]}-{score["home"]}

Events: {key_events[:3] if key_events else "No significant events"}{context_section}

Generate complete pipeline output: 
1. Data analysis 
2. Commentary with Alex Chen (play-by-play) and Mike Rodriguez (analyst) - 2-3 natural exchanges
3. Audio processing with appropriate voice styles

Audio Guidelines:
- Alex Chen: Use "enthusiastic" for exciting plays, "dramatic" for critical moments
- Mike Rodriguez: Use "calm" for analysis, "dramatic" for crucial insights
- Each dialogue segment should be audio-ready with clear speaker identification

Return JSON: {{
  "data_agent": {{"recommendation": "...", "key_points": [...]}}, 
  "commentary_agent": {{"commentary_sequence": [...]}},
  "audio_agent": {{"processing_instructions": [...], "voice_styles": {{...}}}}
}}"""
    
    return prompt


def get_audio_processing_prompt(commentary_sequence: list, game_context: dict) -> str:
    """Create specific prompt for audio processing stage"""
    
    speakers = [segment.get("speaker", "Unknown") for segment in commentary_sequence]
    unique_speakers = list(set(speakers))
    
    prompt = f"""Audio Processing Instructions for NHL Commentary

Commentary Segments: {len(commentary_sequence)} segments
Speakers: {', '.join(unique_speakers)}
Game Context: {game_context.get('game_situation', 'Regular play')}

For each commentary segment, determine:
1. Appropriate voice style (enthusiastic/dramatic/calm)
2. Speaker-specific audio characteristics
3. Emotional tone based on game situation
4. Audio file naming and organization

Process each segment with TTS and generate organized audio files.

Return audio processing results with file paths and metadata."""
    
    return prompt 