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
        
        # Enrich with spatial context for enhanced PBP - load raw live data
        spatial_context = _enrich_spatial_context_from_live_data(data_agent_output)
        
        # Generate commentary sequence using enhanced intelligent generation
        full_context = {
            "home_team": home_team,
            "away_team": away_team,
            "game_context": game_context,
            "momentum_score": momentum_score,
            "talking_points": talking_points,
            "high_intensity_events": high_intensity_events,
            "spatial_context": spatial_context
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
            spatial_context=json.dumps(context.get('spatial_context', {}), indent=2),
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
                        if item["speaker"] in ["Host", "Play-by-play", "PBP", "Play-by-Play"]:
                            item["speaker"] = "Alex Chen"
                        elif item["speaker"] in ["Analyst", "Analyst1", "Analyst2", "Color", "Color Commentator"]:
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


def _enrich_spatial_context_from_live_data(data_agent_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load and process live data directly to get detailed spatial information
    
    Args:
        data_agent_output: Output from data agent containing game context
        
    Returns:
        Dictionary with enhanced spatial flow information for PBP
    """
    try:
        # Extract game context to find the corresponding live data file
        game_context = data_agent_output.get("for_commentary_agent", {}).get("game_context", {})
        period = game_context.get("period", 1)
        time_remaining = game_context.get("time_remaining", "20:00")
        
        # Convert time_remaining to elapsed time format
        minutes_left = int(time_remaining.split(":")[0])
        seconds_left = int(time_remaining.split(":")[1])
        elapsed_minutes = 20 - minutes_left
        elapsed_seconds = 0 - seconds_left
        
        if elapsed_seconds < 0:
            elapsed_minutes -= 1
            elapsed_seconds = 60 + elapsed_seconds
        
        # Try to find the closest matching live data file
        import os, glob
        
        # First try exact match
        timestamp = f"{period:d}_{elapsed_minutes:02d}_{elapsed_seconds:02d}"
        live_data_file = f"data/live/2024030412/2024030412_{timestamp}.json"
        
        if not os.path.exists(live_data_file):
            # Try to find closest file - search all available files and find closest match
            pattern = f"data/live/2024030412/2024030412_{period:d}_*.json"
            available_files = glob.glob(pattern)
            
            if available_files:
                # Calculate elapsed time in seconds for comparison
                target_total_seconds = elapsed_minutes * 60 + elapsed_seconds
                
                best_match = None
                best_diff = float('inf')
                
                for file_path in available_files:
                    # Extract time from filename like "2024030412_1_00_15.json"
                    filename = os.path.basename(file_path)
                    parts = filename.replace('.json', '').split('_')
                    if len(parts) >= 4:
                        try:
                            file_minutes = int(parts[2])
                            file_seconds = int(parts[3])
                            file_total_seconds = file_minutes * 60 + file_seconds
                            
                            diff = abs(target_total_seconds - file_total_seconds)
                            if diff < best_diff:
                                best_diff = diff
                                best_match = file_path
                        except ValueError:
                            continue
                
                # Use the best match if it's within 30 seconds
                if best_match and best_diff <= 30:
                    live_data_file = best_match
                
                # However, prefer files that have more activities (likely to contain the events we want)
                # Re-evaluate matches by activity count for close time differences
                if best_diff <= 10:  # Within 10 seconds, check activity count
                    candidates = []
                    for file_path in available_files:
                        filename = os.path.basename(file_path)
                        parts = filename.replace('.json', '').split('_')
                        if len(parts) >= 4:
                            try:
                                file_minutes = int(parts[2])
                                file_seconds = int(parts[3])
                                file_total_seconds = file_minutes * 60 + file_seconds
                                diff = abs(target_total_seconds - file_total_seconds)
                                
                                if diff <= 10:  # Within 10 seconds
                                    with open(file_path, 'r') as temp_f:
                                        temp_data = json.load(temp_f)
                                    activity_count = len(temp_data.get('activities', []))
                                    candidates.append((file_path, diff, activity_count))
                            except (ValueError, json.JSONDecodeError):
                                continue
                    
                    # Sort by activity count (descending), then by time difference (ascending)
                    if candidates:
                        candidates.sort(key=lambda x: (-x[2], x[1]))
                        live_data_file = candidates[0][0]
        
        # Load the live data if found
        if os.path.exists(live_data_file):
            with open(live_data_file, 'r') as f:
                live_data = json.load(f)
            
            activities = live_data.get('activities', [])
            result = _process_live_activities_for_spatial_context(activities)
            result["matched_file"] = os.path.basename(live_data_file)
            return result
        else:
            # Fallback to basic processing
            return {"spatial_flow": [], "puck_tracking_available": False, "live_data_loaded": False, "error": f"No live data file found for {timestamp}"}
            
    except Exception as e:
        print(f"Warning: Could not load live data for spatial context: {e}")
        return {"spatial_flow": [], "puck_tracking_available": False, "error": str(e)}


def _process_live_activities_for_spatial_context(activities: List[Dict]) -> Dict[str, Any]:
    """Process live activities to extract detailed spatial information"""
    spatial_flow = []
    puck_locations = []
    pbp_sequences = []
    
    # Sort activities by time
    sorted_activities = sorted(activities, key=lambda x: x.get('timeInPeriod', '00:00'))
    
    for activity in sorted_activities:
        if 'details' in activity and activity['details']:
            details = activity['details']
            
            # Extract comprehensive spatial information
            spatial_info = {
                'time': activity.get('timeInPeriod', ''),
                'event_type': activity.get('typeDescKey', ''),
                'location': details.get('spatialDescription', ''),
                'zone': details.get('zoneCode', ''),
                'coordinates': {
                    'x': details.get('xCoord'),
                    'y': details.get('yCoord')
                },
                'players_involved': _extract_player_context_from_activity(activity)
            }
            
            # Generate PBP narrative elements
            pbp_elements = _generate_pbp_narrative_elements(activity)
            if pbp_elements:
                pbp_sequences.extend(pbp_elements)
            
            # Track puck movement patterns
            if details.get('xCoord') is not None and details.get('yCoord') is not None:
                puck_locations.append({
                    'time': activity.get('timeInPeriod', ''),
                    'x': details['xCoord'],
                    'y': details['yCoord'],
                    'zone': details.get('zoneCode', ''),
                    'action': activity.get('typeDescKey', ''),
                    'description': details.get('spatialDescription', '')
                })
            
            spatial_flow.append(spatial_info)
    
    # Generate enhanced puck movement narrative
    movement_narrative = _generate_enhanced_puck_movement_narrative(puck_locations)
    
    return {
        "spatial_flow": spatial_flow,
        "puck_tracking_available": len(puck_locations) > 0,
        "movement_narrative": movement_narrative,
        "zone_progression": _analyze_zone_progression(puck_locations),
        "pbp_sequences": pbp_sequences,
        "live_data_loaded": True,
        "total_activities": len(spatial_flow)
    }


def _extract_player_context_from_activity(activity: Dict) -> Dict[str, str]:
    """Extract player names and roles from live activity details"""
    details = activity.get('details', {})
    players = {}
    
    # Map various player role fields to standardized names
    player_mappings = [
        ('shootingPlayerName', 'shooter'),
        ('goalieInNetName', 'goalie'),
        ('hittingPlayerName', 'hitter'),
        ('hitteePlayerName', 'hittee'),
        ('committedByPlayerName', 'penalty_player'),
        ('drawnByPlayerName', 'penalty_drawn'),
        ('winningPlayerName', 'faceoff_winner'),
        ('losingPlayerName', 'faceoff_loser')
    ]
    
    for field_name, role in player_mappings:
        if field_name in details:
            players[role] = details[field_name]
    
    return players


def _generate_pbp_narrative_elements(activity: Dict) -> List[str]:
    """Generate specific PBP narrative elements for different event types"""
    event_type = activity.get('typeDescKey', '')
    details = activity.get('details', {})
    spatial_desc = details.get('spatialDescription', '')
    
    narratives = []
    
    if event_type == 'missed-shot':
        shooter = details.get('shootingPlayerName', 'Player')
        shot_type = details.get('shotType', 'shot')
        reason = details.get('reason', 'missed')
        
        if 'behind the net' in spatial_desc:
            narratives.append(f"{shooter} works it {spatial_desc}, turns and fires a {shot_type}")
        if reason == 'hit-crossbar':
            narratives.append("Off the crossbar!")
        
    elif event_type == 'hit':
        hitter = details.get('hittingPlayerName', 'Player')
        hittee = details.get('hitteePlayerName', 'Player')
        
        if 'corner' in spatial_desc:
            narratives.append(f"Puck worked {spatial_desc}")
            narratives.append(f"{hittee} goes to retrieve it, and he's hit by {hitter}!")
            
    elif event_type == 'penalty':
        penalty_player = details.get('committedByPlayerName', 'Player')
        penalty_type = details.get('descKey', 'penalty')
        
        narratives.append(f"And that aggressive play leads to a penalty")
        narratives.append(f"{penalty_player} called for {penalty_type}")
    
    return narratives


def _generate_enhanced_puck_movement_narrative(locations: List[Dict]) -> List[str]:
    """Generate enhanced descriptive puck movement phrases for PBP use"""
    if len(locations) < 2:
        return []
    
    narratives = []
    for i in range(len(locations) - 1):
        current = locations[i]
        next_loc = locations[i + 1]
        
        # Analyze movement between locations
        zone_change = current['zone'] != next_loc['zone']
        action_type = next_loc['action']
        current_desc = current.get('description', '')
        next_desc = next_loc.get('description', '')
        
        if zone_change:
            narratives.append(f"Puck worked from {current_desc} to {next_desc}")
        elif 'corner' in next_desc and action_type == 'hit':
            narratives.append(f"Play continues {next_desc}")
        elif abs(current.get('x', 0) - next_loc.get('x', 0)) > 20:
            narratives.append("Puck moved across the ice")
    
    return narratives


def _enrich_spatial_context(events: List[Dict]) -> Dict[str, Any]:
    """
    Convert coordinate data into broadcast-friendly spatial descriptions
    
    Args:
        events: List of high-intensity events from data agent
        
    Returns:
        Dictionary with spatial flow information for enhanced PBP
    """
    spatial_flow = []
    puck_locations = []
    
    for event in events:
        if 'details' in event:
            details = event['details']
            
            # Extract spatial information
            spatial_info = {
                'time': event.get('timeInPeriod', ''),
                'event_type': event.get('typeDescKey', ''),
                'location': details.get('spatialDescription', ''),
                'zone': details.get('zoneCode', ''),
                'coordinates': {
                    'x': details.get('xCoord'),
                    'y': details.get('yCoord')
                }
            }
            
            # Add player context for better PBP
            player_context = _extract_player_context(event)
            if player_context:
                spatial_info['players'] = player_context
            
            # Track puck movement patterns
            if details.get('xCoord') is not None and details.get('yCoord') is not None:
                puck_locations.append({
                    'time': event.get('timeInPeriod', ''),
                    'x': details['xCoord'],
                    'y': details['yCoord'],
                    'zone': details.get('zoneCode', ''),
                    'action': event.get('typeDescKey', '')
                })
            
            spatial_flow.append(spatial_info)
    
    # Generate puck movement narrative
    movement_narrative = _generate_puck_movement_narrative(puck_locations)
    
    return {
        "spatial_flow": spatial_flow,
        "puck_tracking_available": len(puck_locations) > 0,
        "movement_narrative": movement_narrative,
        "zone_progression": _analyze_zone_progression(puck_locations)
    }


def _extract_player_context(event: Dict) -> Dict[str, str]:
    """Extract player names and roles from event details"""
    details = event.get('details', {})
    players = {}
    
    # Map various player role fields to standardized names
    player_mappings = [
        ('shootingPlayerName', 'shooter'),
        ('goalieInNetName', 'goalie'),
        ('hittingPlayerName', 'hitter'),
        ('hitteePlayerName', 'hittee'),
        ('committedByPlayerName', 'penalty_player'),
        ('drawnByPlayerName', 'penalty_drawn'),
        ('winningPlayerName', 'faceoff_winner'),
        ('losingPlayerName', 'faceoff_loser')
    ]
    
    for field_name, role in player_mappings:
        if field_name in details:
            players[role] = details[field_name]
    
    return players


def _generate_puck_movement_narrative(locations: List[Dict]) -> List[str]:
    """Generate descriptive puck movement phrases for PBP use"""
    if len(locations) < 2:
        return []
    
    narratives = []
    for i in range(len(locations) - 1):
        current = locations[i]
        next_loc = locations[i + 1]
        
        # Analyze movement between locations
        zone_change = current['zone'] != next_loc['zone']
        action_type = next_loc['action']
        
        if zone_change:
            narratives.append(f"puck worked from {current['zone']} zone to {next_loc['zone']} zone")
        elif action_type in ['hit', 'penalty']:
            narratives.append("play continues in the same area")
        elif abs(current.get('x', 0) - next_loc.get('x', 0)) > 20:
            narratives.append("puck moved across the ice")
    
    return narratives


def _analyze_zone_progression(locations: List[Dict]) -> Dict[str, Any]:
    """Analyze zone-to-zone progression for strategic commentary"""
    if not locations:
        return {"progression_type": "static", "zones_visited": []}
    
    zones = [loc['zone'] for loc in locations if loc.get('zone')]
    unique_zones = list(dict.fromkeys(zones))  # Preserve order, remove duplicates
    
    progression_type = "static"
    if len(unique_zones) > 1:
        if 'D' in zones and 'O' in zones:
            progression_type = "end_to_end"
        elif len(unique_zones) == 2:
            progression_type = "zone_change"
        else:
            progression_type = "multi_zone"
    
    return {
        "progression_type": progression_type,
        "zones_visited": unique_zones,
        "zone_changes": len(unique_zones) - 1 if len(unique_zones) > 1 else 0
    }




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