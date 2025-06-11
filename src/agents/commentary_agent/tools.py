"""
Commentary Agent Tools - Google ADK Implementation

Tool functions for the NHL Commentary Agent using Google ADK framework
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

def save_commentary_output(
    game_id: str,
    commentary_data: Dict[str, Any],
    timestamp: str = None
) -> str:
    """
    Save commentary output to data/commentary_agent_outputs/ directory
    
    Args:
        game_id: NHL game ID
        commentary_data: Generated commentary data
        timestamp: Optional timestamp, will use current time if not provided
        
    Returns:
        Path to saved file
    """
    try:
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create output directory if it doesn't exist
        output_dir = "data/commentary_agent_outputs"
        os.makedirs(output_dir, exist_ok=True)
        
        # Create filename
        filename = f"{game_id}_commentary_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        # Add metadata to the output
        output_data = {
            "metadata": {
                "game_id": game_id,
                "generated_at": datetime.now().isoformat(),
                "agent_version": "adk_commentary_v1.0",
                "agent_type": "nhl_commentary_agent",
                "output_file": filename
            },
            "commentary_data": commentary_data
        }
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Commentary output saved: {filepath}")
        return filepath
        
    except Exception as e:
        print(f"❌ Failed to save commentary output: {e}")
        return ""

class CommentaryType(Enum):
    """Types of commentary based on game intensity"""
    FILLER_CONTENT = "FILLER_CONTENT"
    MIXED_COVERAGE = "MIXED_COVERAGE" 
    HIGH_INTENSITY = "HIGH_INTENSITY"

@dataclass
class CommentaryLine:
    """Individual line of commentary dialogue"""
    speaker: str  # "pbp" or "color"
    text: str
    emotion: str  # "excitement", "analysis", "tension", etc.
    timing: str   # "immediate", "follow_up", "building"
    duration_estimate: float

@dataclass
class CommentaryOutput:
    """Complete commentary output with metadata"""
    sequence: List[CommentaryLine]
    game_context: Dict[str, Any]
    commentary_type: CommentaryType
    total_duration: float

def generate_two_person_commentary(
    context: ToolContext,
    commentary_type: str = "MIXED_COVERAGE"
) -> Dict[str, Any]:
    """
    Generate two-person broadcast commentary dialogue
    
    Args:
        commentary_type: Type of commentary (FILLER_CONTENT, MIXED_COVERAGE, HIGH_INTENSITY)
        
    Returns:
        Dictionary containing generated commentary dialogue
    """
    try:
        # Get data from session state
        game_data = context.session.state.get("current_data_agent_output", {})
        static_context = context.session.state.get("static_context", {})
        
        commentary_data = game_data.get("for_commentary_agent", {})
        game_context = commentary_data.get("game_context", {})
        momentum = commentary_data.get("momentum_score", 0)
        talking_points = commentary_data.get("key_talking_points", [])
        events = commentary_data.get("high_intensity_events", [])
        
        # Extract team info
        game_info = static_context.get("game_info", {})
        home_team = game_info.get("home_team", "HOME")
        away_team = game_info.get("away_team", "AWAY")
        
        # Determine speaker balance based on commentary type
        if commentary_type == "FILLER_CONTENT":
            # Color commentator leads (60-70%)
            pbp_weight = 0.3
            color_weight = 0.7
        elif commentary_type == "HIGH_INTENSITY":
            # Play-by-play dominates (70-80%)
            pbp_weight = 0.8
            color_weight = 0.2
        else:  # MIXED_COVERAGE
            # Balanced (50-50)
            pbp_weight = 0.5
            color_weight = 0.5
        
        # Generate commentary lines based on context
        commentary_lines = []
        
        # Line 1: Opening based on commentary type and momentum
        if commentary_type == "HIGH_INTENSITY" and momentum > 70:
            commentary_lines.append({
                "speaker": "pbp",
                "text": f"What action here as {home_team} and {away_team} battle!",
                "emotion": "excitement",
                "timing": "immediate",
                "duration_estimate": 2.5
            })
        elif talking_points:
            # Use first talking point
            commentary_lines.append({
                "speaker": "pbp" if pbp_weight >= 0.5 else "color",
                "text": talking_points[0],
                "emotion": "steady",
                "timing": "immediate", 
                "duration_estimate": 3.0
            })
        else:
            commentary_lines.append({
                "speaker": "pbp",
                "text": f"We're back with {away_team} visiting {home_team} here tonight.",
                "emotion": "steady",
                "timing": "immediate",
                "duration_estimate": 2.8
            })
        
        # Line 2: Response/Analysis
        if len(commentary_lines) > 0:
            first_speaker = commentary_lines[0]["speaker"]
            second_speaker = "color" if first_speaker == "pbp" else "pbp"
            
            if events and len(events) > 0:
                # React to recent event
                event = events[0]
                commentary_lines.append({
                    "speaker": second_speaker,
                    "text": f"That {event.get('event_type', 'play')} really shows the intensity out there.",
                    "emotion": "analysis",
                    "timing": "follow_up",
                    "duration_estimate": 2.5
                })
            elif len(talking_points) > 1:
                # Use second talking point
                commentary_lines.append({
                    "speaker": second_speaker,
                    "text": talking_points[1],
                    "emotion": "analysis",
                    "timing": "follow_up",
                    "duration_estimate": 3.2
                })
            else:
                # Generic response
                score_text = f"With the score {away_team} {game_context.get('away_score', 0)}, {home_team} {game_context.get('home_score', 0)}"
                commentary_lines.append({
                    "speaker": second_speaker,
                    "text": score_text,
                    "emotion": "analysis",
                    "timing": "follow_up",
                    "duration_estimate": 2.0
                })
        
        # Line 3: Additional context for longer commentary
        if commentary_type == "FILLER_CONTENT" and len(talking_points) > 2:
            commentary_lines.append({
                "speaker": "color",
                "text": talking_points[2],
                "emotion": "storytelling",
                "timing": "building",
                "duration_estimate": 4.0
            })
        
        # Calculate total duration
        total_duration = sum(line["duration_estimate"] for line in commentary_lines)
        
        result = {
            "status": "success",
            "commentary_sequence": commentary_lines,
            "metadata": {
                "commentary_type": commentary_type,
                "total_duration": total_duration,
                "game_context": game_context,
                "momentum_score": momentum,
                "lines_generated": len(commentary_lines)
            },
            "speakers": {
                "pbp": "Jim Harrison - Play-by-Play",
                "color": "Eddie Martinez - Color Commentary"
            }
        }
        
        # Save commentary output to file
        static_context = context.session.state.get("static_context", {})
        game_info = static_context.get("game_info", {})
        
        # Get game_id from static context (it's at the top level)
        game_id = static_context.get("game_id", "unknown_game")
        
        # Create complete output with all data
        complete_output = {
            "commentary_result": result,
            "game_context": game_context,
            "static_context": static_context,
            "data_agent_input": context.session.state.get("current_data_agent_output", {})
        }
        
        # Save to file
        saved_path = save_commentary_output(game_id, complete_output)
        result["output_file"] = saved_path
        
        context.session.state["last_commentary_generation"] = result
        return result
        
    except Exception as e:
        error_result = {
            "status": "error",
            "error": f"Commentary generation failed: {str(e)}",
            "fallback_commentary": [
                {
                    "speaker": "pbp",
                    "text": "We're back with live NHL action here tonight.",
                    "emotion": "steady",
                    "timing": "immediate",
                    "duration_estimate": 2.5
                },
                {
                    "speaker": "color",
                    "text": "Both teams looking to establish their rhythm early on.",
                    "emotion": "analysis",
                    "timing": "follow_up",
                    "duration_estimate": 3.0
                }
            ]
        }
        context.session.state["last_commentary_generation"] = error_result
        return error_result

def format_commentary_for_audio(
    context: ToolContext
) -> Dict[str, Any]:
    """
    Format commentary output for audio agent consumption
    
    Returns:
        Dictionary formatted for audio agent processing
    """
    try:
        # Get commentary data from session state
        commentary_data = context.session.state.get("last_commentary_generation", {})
        commentary_sequence = commentary_data.get("commentary_sequence", [])
        
        audio_segments = []
        
        for line in commentary_sequence:
            # Map speaker to voice characteristics
            voice_style = "enthusiastic" if line.get("speaker") == "pbp" else "analytical"
            
            emotion = line.get("emotion", "neutral")
            if emotion in ["excitement", "building_excitement"]:
                voice_style = "dramatic"
            elif emotion in ["tension", "concern"]:
                voice_style = "intense"
            
            audio_segments.append({
                "text": line.get("text", ""),
                "speaker": line.get("speaker", "pbp"),
                "voice_style": voice_style,
                "emotion": emotion,
                "duration_estimate": line.get("duration_estimate", 2.0),
                "pause_after": 0.3 if line.get("timing") == "follow_up" else 0.1
            })
        
        audio_format = {
            "status": "success",
            "audio_segments": audio_segments,
            "total_duration": commentary_data.get("metadata", {}).get("total_duration", 0),
            "commentary_type": commentary_data.get("metadata", {}).get("commentary_type", "MIXED_COVERAGE"),
            "speakers": commentary_data.get("speakers", {}),
            "ready_for_tts": True
        }
        
        context.session.state["audio_formatted_commentary"] = audio_format
        return audio_format
        
    except Exception as e:
        error_result = {
            "status": "error",
            "error": f"Audio formatting failed: {str(e)}",
            "audio_segments": []
        }
        context.session.state["audio_formatted_commentary"] = error_result
        return error_result

def analyze_commentary_context(
    context: ToolContext
) -> Dict[str, Any]:
    """
    Analyze game context to determine optimal commentary approach
    
    Returns:
        Analysis results with recommended commentary strategy
    """
    try:
        # Get data from session state
        data_agent_output = context.session.state.get("current_data_agent_output", {})
        commentary_data = data_agent_output.get("for_commentary_agent", {})
        game_context = commentary_data.get("game_context", {})
        momentum = commentary_data.get("momentum_score", 0)
        events = commentary_data.get("high_intensity_events", [])
        recommendation = commentary_data.get("recommendation", "FILLER_CONTENT")
        
        # Determine game state
        period = game_context.get("period", 1)
        time_remaining = game_context.get("time_remaining", "20:00")
        situation = game_context.get("game_situation", "even strength")
        
        # Analyze intensity level
        intensity_level = "low"
        if momentum > 70:
            intensity_level = "high"
        elif momentum > 40:
            intensity_level = "medium"
        
        # Determine speaker balance
        speaker_strategy = {
            "FILLER_CONTENT": {"pbp_ratio": 0.3, "color_ratio": 0.7, "pace": "relaxed"},
            "MIXED_COVERAGE": {"pbp_ratio": 0.5, "color_ratio": 0.5, "pace": "moderate"}, 
            "HIGH_INTENSITY": {"pbp_ratio": 0.8, "color_ratio": 0.2, "pace": "fast"}
        }
        
        strategy = speaker_strategy.get(recommendation, speaker_strategy["MIXED_COVERAGE"])
        
        analysis = {
            "status": "success",
            "game_analysis": {
                "period": period,
                "time_remaining": time_remaining,
                "game_situation": situation,
                "momentum_score": momentum,
                "intensity_level": intensity_level,
                "high_intensity_events_count": len(events)
            },
            "commentary_strategy": {
                "recommended_type": recommendation,
                "pbp_speaking_ratio": strategy["pbp_ratio"],
                "color_speaking_ratio": strategy["color_ratio"],
                "pacing": strategy["pace"],
                "focus_areas": _determine_focus_areas(game_context, events, momentum)
            },
            "dialogue_guidance": {
                "estimated_lines": 2 + (1 if recommendation == "FILLER_CONTENT" else 0),
                "average_line_duration": 2.5 + (0.5 if recommendation == "FILLER_CONTENT" else 0),
                "emotional_tone": _determine_emotional_tone(momentum, events)
            }
        }
        
        context.session.state["commentary_analysis"] = analysis
        return analysis
        
    except Exception as e:
        error_result = {
            "status": "error",
            "error": f"Context analysis failed: {str(e)}",
            "fallback_strategy": {
                "recommended_type": "MIXED_COVERAGE",
                "pbp_speaking_ratio": 0.5,
                "color_speaking_ratio": 0.5
            }
        }
        context.session.state["commentary_analysis"] = error_result
        return error_result

def _determine_focus_areas(game_context: Dict[str, Any], events: List[Dict], momentum: int) -> List[str]:
    """Determine what the commentary should focus on"""
    focus_areas = []
    
    situation = game_context.get("game_situation", "even strength")
    if "power" in situation.lower():
        focus_areas.append("special_teams")
    
    if momentum > 60:
        focus_areas.append("momentum_shift")
    
    if events:
        event_types = [e.get("event_type", "") for e in events]
        if "goal" in event_types:
            focus_areas.append("scoring_analysis")
        elif "penalty" in event_types:
            focus_areas.append("penalty_impact")
        elif "hit" in event_types:
            focus_areas.append("physical_play")
    
    if not focus_areas:
        focus_areas.append("general_play")
    
    return focus_areas

def _determine_emotional_tone(momentum: int, events: List[Dict]) -> str:
    """Determine the emotional tone for commentary"""
    if momentum > 80:
        return "high_excitement"
    elif momentum > 60:
        return "building_tension"
    elif momentum > 30:
        return "engaged_analysis"
    else:
        return "steady_professional"

# Create FunctionTool objects for ADK
generate_commentary_tool = FunctionTool(func=generate_two_person_commentary)
format_audio_tool = FunctionTool(func=format_commentary_for_audio)
analyze_context_tool = FunctionTool(func=analyze_commentary_context)

# Export all tools for the agent
COMMENTARY_TOOLS = [
    generate_commentary_tool,
    format_audio_tool,
    analyze_context_tool
]