"""
Commentary Agent Tools - Simplified ADK Implementation

Core tool functions for NHL Commentary Agent
"""

import json
import os
import random
from datetime import datetime
from typing import Dict, List, Any, Tuple
import google.generativeai as genai
from .prompts import (
    COMMENTARY_JSON_SCHEMA, 
    SIMPLE_COMMENTARY_EXAMPLES, 
    INTELLIGENT_COMMENTARY_PROMPT,
    FIXED_BROADCASTERS
)
# Simple tool functions following data agent pattern



def generate_two_person_commentary(
    data_agent_output: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate professional two-person broadcast commentary dialogue.
    
    Args:
        data_agent_output: Output from the data agent containing game analysis
        
    Returns:
        Dictionary with commentary sequence and metadata
    """
    try:
        # Load static context (simplified approach)
        try:
            from ..data_agent.tools import load_static_context
            game_id = data_agent_output.get("for_commentary_agent", {}).get("game_context", {}).get("game_id")
            if not game_id:
                raise ValueError("game_id is required in data_agent_output")
            static_context = load_static_context(game_id)
        except (ImportError, FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Failed to load static context: {e}")
            static_context = {"game_info": {"home_team": "HOME", "away_team": "AWAY"}}
        
        # Extract key information from data agent output
        for_commentary = data_agent_output.get("for_commentary_agent", {})
        talking_points = for_commentary.get("key_talking_points", [])
        momentum_score = for_commentary.get("momentum_score", 0)
        game_context = for_commentary.get("game_context", {})
        high_intensity_events = for_commentary.get("high_intensity_events", [])
        
        # Extract game information
        game_info = static_context.get("game_info", {})
        home_team = game_info.get("home_team", "HOME")
        away_team = game_info.get("away_team", "AWAY")
        
        # Determine commentary style based on momentum and events
        if momentum_score > 60 or len(high_intensity_events) > 0:
            actual_type = "HIGH_INTENSITY"
        elif momentum_score > 30 or len(talking_points) > 2:
            actual_type = "MIXED_COVERAGE"
        else:
            actual_type = "FILLER_CONTENT"
        
        # Generate commentary sequence using intelligent generation
        full_context = {
            "home_team": home_team,
            "away_team": away_team,
            "game_context": game_context,
            "momentum_score": momentum_score,
            "talking_points": talking_points,
            "high_intensity_events": high_intensity_events
        }
        
        intelligent_result = _generate_simplified_commentary(
            situation_type=actual_type.lower(),
            context=full_context
        )
        
        if intelligent_result and intelligent_result.get("status") == "success":
            commentary_sequence = intelligent_result.get("commentary_sequence", [])
            # Use intelligent generation's total duration if available, otherwise calculate
            total_duration = intelligent_result.get("total_duration_estimate") or sum(line.get("duration_estimate", 3.0) for line in commentary_sequence)
        else:
            # Return error if intelligent generation fails
            return {
                "status": "error",
                "error": f"Commentary generation failed: {intelligent_result.get('error', 'Unknown error')}",
                "commentary_sequence": [],
                "total_duration_estimate": 0
            }
        
        result = {
            "status": "success",
            "commentary_type": actual_type,
            "commentary_sequence": commentary_sequence,
            "total_duration_estimate": total_duration,
            "game_context": {
                "home_team": home_team,
                "away_team": away_team,
                "momentum_score": momentum_score,
                "talking_points_count": len(talking_points)
            }
        }
        
        return result
        
    except Exception as e:
        error_result = {
            "status": "error",
            "error": f"Commentary generation failed: {str(e)}",
            "commentary_sequence": []
        }
        # Return error result
        return error_result


def format_commentary_for_audio(commentary_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format commentary for audio processing with TTS-ready output.
    
    Args:
        commentary_result: Result from generate_two_person_commentary
        
    Returns:
        Dictionary with audio-ready formatting
    """
    try:
        
        if commentary_result.get("status") != "success":
            return {
                "status": "error",
                "error": "No valid commentary to format",
                "audio_ready": False
            }
        
        commentary_sequence = commentary_result.get("commentary_sequence", [])
        
        # Format for audio processing
        audio_segments = []
        for i, line in enumerate(commentary_sequence):
            audio_segments.append({
                "segment_id": i + 1,
                "speaker": line.get("speaker", "Play-by-play"),
                "text": line.get("text", ""),
                "voice_style": _get_voice_style(line.get("speaker", "Play-by-play"), line.get("emotion", "neutral")),
                "duration_estimate": line.get("duration_estimate", 3.0),
                "pause_after": line.get("pause_after", 0.5)
            })
        
        result = {
            "status": "success",
            "audio_ready": True,
            "audio_segments": audio_segments,
            "total_segments": len(audio_segments),
            "estimated_total_duration": sum(seg["duration_estimate"] + seg["pause_after"] for seg in audio_segments)
        }
        
        return result
        
    except Exception as e:
        error_result = {
            "status": "error",
            "error": f"Audio formatting failed: {str(e)}",
            "audio_ready": False
        }
        # Return error
        return error_result


def analyze_commentary_context(data_agent_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze the data agent output to determine commentary strategy.
    
    Args:
        data_agent_output: Output from the data agent containing game analysis
        
    Returns:
        Dictionary with analysis and recommendations
    """
    try:
        
        # Extract key information
        for_commentary = data_agent_output.get("for_commentary_agent", {})
        recommendation = for_commentary.get("recommendation", "FILLER_CONTENT")
        momentum_score = for_commentary.get("momentum_score", 0)
        talking_points = for_commentary.get("key_talking_points", [])
        high_intensity_events = for_commentary.get("high_intensity_events", [])
        
        # Analyze context
        analysis = {
            "momentum_assessment": _assess_momentum(momentum_score),
            "content_richness": len(talking_points),
            "intensity_level": len(high_intensity_events),
            "recommended_type": recommendation
        }
        
        # Determine strategy
        if momentum_score > 60 or len(high_intensity_events) > 0:
            strategy_type = "HIGH_INTENSITY"
            focus = "immediate_action"
        elif momentum_score > 30 or len(talking_points) > 2:
            strategy_type = "MIXED_COVERAGE"
            focus = "analysis_with_action"
        else:
            strategy_type = "FILLER_CONTENT"
            focus = "general_discussion"
        
        result = {
            "status": "success",
            "analysis": analysis,
            "commentary_strategy": {
                "recommended_type": strategy_type,
                "focus_area": focus,
                "talking_points_available": len(talking_points),
                "high_intensity_events": len(high_intensity_events)
            }
        }
        
        return result
        
    except Exception as e:
        error_result = {
            "status": "error",
            "error": f"Context analysis failed: {str(e)}"
        }
        # Return error
        return error_result


def get_secure_api_key() -> str:
    """
    Securely retrieve API key with proper error handling.
    
    Returns:
        API key string
        
    Raises:
        ValueError: If API key is not found or invalid
    """
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key or api_key.strip() == '':
        raise ValueError(
            "GOOGLE_API_KEY environment variable not set. "
            "Please configure your Google AI API key in the .env file."
        )
    return api_key.strip()


def _generate_simplified_commentary(situation_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate intelligent commentary using Alex Chen and Mike Rodriguez
    
    Args:
        situation_type: Type of situation (high_intensity, mixed_coverage, filler_content)
        context: Full game context including teams, momentum, talking points, events
        
    Returns:
        Dictionary with generated commentary or error status
    """
    try:
        # Load environment and configure API
        import sys
        import os
        from dotenv import load_dotenv
        
        # Load .env file
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        load_dotenv(os.path.join(project_root, '.env'))
        
        # Securely get API key
        try:
            api_key = get_secure_api_key()
        except ValueError as e:
            return {"status": "error", "error": str(e)}
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Get broadcaster personas
        alex = FIXED_BROADCASTERS["alex_chen"]
        mike = FIXED_BROADCASTERS["mike_rodriguez"]
        
        # Format the examples for the prompt
        examples_text = "\n\n".join([
            f"SITUATION: {ex['situation']}\nCONTEXT: {ex['context']}\nOUTPUT: {ex['output']}"
            for ex in SIMPLE_COMMENTARY_EXAMPLES
        ])
        
        # Import PBP guidelines and game state discipline
        from .prompts import PBP_ENHANCEMENT_GUIDELINES, GAME_STATE_DISCIPLINE
        
        # Build the enhanced persona prompt with spatial context
        prompt = INTELLIGENT_COMMENTARY_PROMPT.format(
            alex_background=alex["background"],
            alex_personality=alex["personality"],
            alex_style=alex["broadcasting_style"],
            alex_traits=alex["signature_traits"],
            alex_interaction=alex["interaction_style"],
            mike_background=mike["background"],
            mike_personality=mike["personality"],
            mike_style=mike["broadcasting_style"],
            mike_traits=mike["signature_traits"],
            mike_interaction=mike["interaction_style"],
            game_context=json.dumps(context, indent=2),
            situation_type=situation_type,
            momentum_score=context.get('momentum_score', 0),
            talking_points=context.get('talking_points', []),
            events=context.get('high_intensity_events', []),
            game_state_discipline=GAME_STATE_DISCIPLINE,
            pbp_guidelines=PBP_ENHANCEMENT_GUIDELINES,
            examples=examples_text,
            schema=COMMENTARY_JSON_SCHEMA
        )
        
        # Generate response
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Clean and parse JSON
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.rfind("```")
            response_text = response_text[json_start:json_end].strip()
        
        # Parse JSON response
        try:
            result = json.loads(response_text)
            result["status"] = "success"
            
            # Post-process to ensure correct names (failsafe)
            if "commentary_sequence" in result:
                for item in result["commentary_sequence"]:
                    if "speaker" in item:
                        # Replace any generic names with our fixed names
                        if item["speaker"] in ["Host", "Play-by-play", "PBP", "Play-by-Play", "Commentator 1", "commentator1"]:
                            item["speaker"] = "Alex Chen"
                        elif item["speaker"] in ["Analyst", "Analyst1", "Analyst2", "Color", "Color Commentator", "Commentator 2", "commentator2"]:
                            item["speaker"] = "Mike Rodriguez"
            
            # Add broadcaster information to result
            result["broadcasters"] = {
                "play_by_play": "Alex Chen",
                "analyst": "Mike Rodriguez"
            }
            return result
        except json.JSONDecodeError as e:
            return {
                "status": "error", 
                "error": f"Invalid JSON response: {str(e)}",
                "raw_response": response_text
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": f"Commentary generation failed: {str(e)}"
        }


# Helper functions
def _get_voice_style(speaker, emotion):
    """Map speaker and emotion to voice style (handles Alex Chen and Mike Rodriguez)"""
    # Alex Chen is play-by-play, Mike Rodriguez is analyst
    if speaker == "Alex Chen":
        return "enthusiastic" if emotion in ["excited", "excitement", "tension"] else "professional"
    else:  # Mike Rodriguez or any other analyst
        return "analytical" if emotion == "analytical" else "conversational"


def _assess_momentum(momentum_score):
    """Assess momentum level"""
    if momentum_score > 60:
        return "high"
    elif momentum_score > 30:
        return "moderate"
    else:
        return "low"






















# Helper functions


# ADK Tool Definitions - Use function names directly like data agent
COMMENTARY_TOOLS = [
    analyze_commentary_context,
    generate_two_person_commentary,
    format_commentary_for_audio
]