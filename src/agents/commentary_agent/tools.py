"""
Commentary Agent Tools - Simplified ADK Implementation

Core tool functions for NHL Commentary Agent
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any
import google.generativeai as genai
from .prompts import (
    COMMENTARY_JSON_SCHEMA, 
    COMMENTARY_EXAMPLES, 
    INTELLIGENT_COMMENTARY_PROMPT
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
            game_id = data_agent_output.get("for_commentary_agent", {}).get("game_context", {}).get("game_id", "2024030412")
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
        
        intelligent_result = _generate_intelligent_commentary(
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
        
        # Validate result has required fields
        validation_result = _validate_commentary_result(result)
        if validation_result["status"] == "error":
            return validation_result
        
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
                "speaker": line.get("speaker", "pbp"),
                "text": line.get("text", ""),
                "voice_style": _get_voice_style(line.get("speaker", "pbp"), line.get("emotion", "neutral")),
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
        
        # Validate result
        validation_result = _validate_audio_format_result(result)
        if validation_result["status"] == "error":
            return validation_result
        
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
        
        # Validate result
        validation_result = _validate_analysis_result(result)
        if validation_result["status"] == "error":
            return validation_result
        
        return result
        
    except Exception as e:
        error_result = {
            "status": "error",
            "error": f"Context analysis failed: {str(e)}"
        }
        # Return error
        return error_result


def _generate_intelligent_commentary(situation_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate intelligent commentary using LLM with structured output
    
    Args:
        situation_type: Type of situation (high_intensity, mixed_coverage, filler_content)
        context: Full game context including teams, momentum, talking points, events
        
    Returns:
        Dictionary with generated commentary or error status
    """
    try:
        # Get API key and configure
        import sys
        import os
        from dotenv import load_dotenv
        
        # Load .env file
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        load_dotenv(os.path.join(project_root, '.env'))
        
        # Get API key from environment
        api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        if not api_key:
            return {"status": "error", "error": "No Gemini API key available"}
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Format the examples for the prompt
        examples_text = "\n\n".join([
            f"SITUATION: {ex['situation']}\nCONTEXT: {ex['context']}\nOUTPUT: {ex['output']}"
            for ex in COMMENTARY_EXAMPLES
        ])
        
        # Build the prompt
        prompt = INTELLIGENT_COMMENTARY_PROMPT.format(
            game_context=json.dumps(context, indent=2),
            situation_type=situation_type,
            momentum_score=context.get('momentum_score', 0),
            talking_points=context.get('talking_points', []),
            events=context.get('high_intensity_events', []),
            schema=COMMENTARY_JSON_SCHEMA,
            examples=examples_text
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
            "error": f"Intelligent commentary generation failed: {str(e)}"
        }


# Helper functions
def _get_voice_style(speaker, emotion):
    """Map speaker and emotion to voice style"""
    if speaker == "pbp":
        return "enthusiastic" if emotion in ["excitement", "tension"] else "professional"
    else:  # color commentator
        return "analytical" if emotion == "analytical" else "conversational"


def _assess_momentum(momentum_score):
    """Assess momentum level"""
    if momentum_score > 60:
        return "high"
    elif momentum_score > 30:
        return "moderate"
    else:
        return "low"


def _ordinal(n):
    """Convert number to ordinal (1st, 2nd, 3rd)"""
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"


# Validation Functions
def _validate_commentary_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Validate commentary generation result"""
    try:
        required_fields = ["status", "commentary_sequence", "total_duration_estimate", "commentary_type"]
        for field in required_fields:
            if field not in result:
                return {
                    "status": "error",
                    "error": f"Missing required field: {field}",
                    "commentary_sequence": []
                }
        
        # Validate commentary sequence structure
        commentary_sequence = result.get("commentary_sequence", [])
        if not isinstance(commentary_sequence, list):
            return {
                "status": "error", 
                "error": "commentary_sequence must be a list",
                "commentary_sequence": []
            }
        
        # Validate each commentary item
        for i, item in enumerate(commentary_sequence):
            required_item_fields = ["speaker", "text", "duration_estimate"]
            for field in required_item_fields:
                if field not in item:
                    return {
                        "status": "error",
                        "error": f"Commentary item {i} missing field: {field}",
                        "commentary_sequence": []
                    }
        
        return {"status": "success"}
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Validation failed: {str(e)}",
            "commentary_sequence": []
        }


def _validate_audio_format_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Validate audio format result"""
    try:
        required_fields = ["status", "audio_ready", "audio_segments"]
        for field in required_fields:
            if field not in result:
                return {
                    "status": "error",
                    "error": f"Missing required field: {field}",
                    "audio_ready": False
                }
        
        # Validate audio segments
        audio_segments = result.get("audio_segments", [])
        if not isinstance(audio_segments, list):
            return {
                "status": "error",
                "error": "audio_segments must be a list", 
                "audio_ready": False
            }
        
        return {"status": "success"}
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Audio validation failed: {str(e)}",
            "audio_ready": False
        }


def _validate_analysis_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Validate analysis result"""
    try:
        required_fields = ["status", "analysis", "commentary_strategy"]
        for field in required_fields:
            if field not in result:
                return {
                    "status": "error",
                    "error": f"Missing required field: {field}"
                }
        
        return {"status": "success"}
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Analysis validation failed: {str(e)}"
        }


# ADK Tool Definitions - Use function names directly like data agent
COMMENTARY_TOOLS = [
    analyze_commentary_context,
    generate_two_person_commentary,
    format_commentary_for_audio
]