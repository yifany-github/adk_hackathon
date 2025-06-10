# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""True Hockey Data Agent using Google ADK - Intelligent, not just rule-based."""

import json
from typing import Dict, Any, List, Optional
from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse

from . import prompts
from .tools import (
    analyze_game_momentum, 
    get_player_name_from_static,
    create_specific_filler_content,
    load_static_context
)


def analyze_hockey_momentum(game_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    ADK Tool: Analyze hockey game data and calculate momentum.
    
    Args:
        game_data: Raw hockey game data including events and context
        
    Returns:
        Dict with momentum analysis including score, recommendation, events
    """
    try:
        # Extract events and context
        activities = game_data.get("activities", [])
        game_context = {
            "period": 1,
            "time_remaining": "20:00", 
            "home_score": 0,
            "away_score": 0,
            "game_situation": "even_strength",
            "periodType": "REG"
        }
        
        # Extract actual game context if available
        if activities:
            latest_event = activities[-1]
            period_desc = latest_event.get("periodDescriptor", {})
            game_stats = latest_event.get("gameStats", {}).get("teamStats", {})
            
            game_context.update({
                "period": period_desc.get("number", 1),
                "time_remaining": latest_event.get("timeRemaining", "20:00"),
                "home_score": game_stats.get("home", {}).get("score", 0),
                "away_score": game_stats.get("away", {}).get("score", 0),
                "game_situation": latest_event.get("gameSituation", "even_strength"),
                "periodType": period_desc.get("periodType", "REG")
            })
        
        # Use existing momentum analysis
        momentum_data = {
            "unique_events": activities,
            "deduplication_summary": f"Processed {len(activities)} events",
            "total_original": len(activities),
            "total_unique": len(activities)
        }
        
        return analyze_game_momentum(momentum_data, game_context)
        
    except Exception as e:
        return {
            "total_momentum_score": 0,
            "broadcast_recommendation": "FILLER_CONTENT",
            "broadcast_focus": "Error in analysis - use filler content",
            "high_intensity_events": [],
            "context_analysis": {},
            "error": str(e)
        }


def get_player_information(player_id: int, static_context: Dict[str, Any]) -> str:
    """
    ADK Tool: Get player name and information from static context.
    
    Args:
        player_id: NHL player ID
        static_context: Game's static context data
        
    Returns:
        Player name or fallback with ID
    """
    return get_player_name_from_static(player_id, static_context)


def generate_filler_content(static_context: Dict[str, Any], used_topics: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    ADK Tool: Generate varied filler content avoiding repetition.
    
    Args:
        static_context: Game's static context data
        used_topics: Recently used filler topics to avoid
        
    Returns:
        Dict with filler content type, content, and talking points
    """
    # Simple topic rotation to avoid repetition
    available_topics = ["TEAM_RECORD", "PLAYER_PERFORMANCE", "MATCHUP_CONTEXT", 
                       "GOALIE_STATS", "POWER_PLAY_STATS"]
    
    if used_topics:
        available_topics = [t for t in available_topics if t not in used_topics[-2:]]
    
    if not available_topics:
        available_topics = ["TEAM_RECORD"]
    
    # Use the first available topic
    topic_type = available_topics[0]
    
    return create_specific_filler_content(static_context, "normal")


def extract_game_context(game_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    ADK Tool: Extract current game context (period, time, score, situation).
    
    Args:
        game_data: Raw hockey game data
        
    Returns:
        Dict with current game state information
    """
    activities = game_data.get("activities", [])
    
    if not activities:
        return {
            "period": 1,
            "time_remaining": "20:00",
            "home_score": 0,
            "away_score": 0,
            "game_situation": "even_strength",
            "periodType": "REG"
        }
    
    # Use the most recent event for current context
    latest_event = activities[-1]
    period_desc = latest_event.get("periodDescriptor", {})
    game_stats = latest_event.get("gameStats", {}).get("teamStats", {})
    
    return {
        "period": period_desc.get("number", 1),
        "time_remaining": latest_event.get("timeRemaining", "20:00"),
        "home_score": game_stats.get("home", {}).get("score", 0),
        "away_score": game_stats.get("away", {}).get("score", 0),
        "game_situation": latest_event.get("gameSituation", "even_strength"),
        "periodType": period_desc.get("periodType", "REG")
    }


def create_hockey_agent_for_game(game_id: str) -> Agent:
    """
    Create a hockey data agent with pre-loaded game-specific context.
    
    Args:
        game_id: NHL game ID (e.g., "2024030412")
        
    Returns:
        ADK Agent configured with game-specific context
    """
    # Load static game context
    static_context = load_static_context(game_id)
    
    # Extract game information
    game_info = static_context.get('game_info', {})
    rosters = static_context.get('rosters', {})
    
    home_team = game_info.get('home_team', 'HOME')
    away_team = game_info.get('away_team', 'AWAY') 
    venue = game_info.get('venue', 'Unknown Arena')
    
    # Format roster information for context
    home_players = rosters.get('home_players', [])
    away_players = rosters.get('away_players', [])
    
    roster_summary = f"""
GAME CONTEXT:
- Game ID: {game_id}
- Teams: {away_team} (Away) vs {home_team} (Home)
- Venue: {venue}
- Home roster: {len(home_players)} players
- Away roster: {len(away_players)} players

Use this context for player name resolution and game-specific analysis.
"""
    
    # Enhanced instruction with game context
    enhanced_instruction = prompts.DATA_AGENT_PROMPT + roster_summary
    
    # Create game-specific tools with static context
    def game_specific_get_player_information(player_id: int) -> str:
        """Get player name from this game's static context"""
        return get_player_name_from_static(player_id, static_context)
    
    def game_specific_generate_filler_content(used_topics: List[str]) -> Dict[str, Any]:
        """Generate filler content using this game's static context"""
        return create_specific_filler_content(static_context, "normal")
    
    # Create agent with game-specific context
    return Agent(
        model='gemini-2.0-flash',
        name=f'hockey_data_agent_{game_id}',
        instruction=enhanced_instruction,
        tools=[
            analyze_hockey_momentum,
            game_specific_get_player_information,
            game_specific_generate_filler_content, 
            extract_game_context
        ],
        after_model_callback=_format_agent_response,
    )


def _format_agent_response(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> LlmResponse:
    """
    Post-process the agent's response to ensure proper JSON formatting 
    and add metadata for the commentary agent.
    """
    del callback_context  # unused
    
    if not llm_response.content or not llm_response.content.parts:
        return llm_response
    
    # Try to parse and validate the JSON response
    try:
        response_text = llm_response.content.parts[0].text
        
        # Extract JSON from the response if it's wrapped in markdown
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.rfind("```")
            response_text = response_text[json_start:json_end].strip()
        
        # Parse and validate JSON
        parsed_response = json.loads(response_text)
        
        # Add metadata
        formatted_response = {
            "generated_at": "2025-06-10T15:00:00.000000Z",  # Would use real timestamp
            "data_agent_version": "adk_v1.0",
            "agent_type": "intelligent_adk_agent",
            "for_commentary_agent": parsed_response
        }
        
        # Update the response with formatted JSON
        llm_response.content.parts[0].text = json.dumps(formatted_response, indent=2)
        
    except (json.JSONDecodeError, IndexError) as e:
        # If JSON parsing fails, wrap in error response
        error_response = {
            "generated_at": "2025-06-10T15:00:00.000000Z",
            "data_agent_version": "adk_v1.0", 
            "agent_type": "intelligent_adk_agent",
            "error": f"Failed to parse agent response: {str(e)}",
            "raw_response": llm_response.content.parts[0].text if llm_response.content.parts else "",
            "for_commentary_agent": {
                "recommendation": "FILLER_CONTENT",
                "priority_level": 3,
                "momentum_score": 0,
                "key_talking_points": ["Agent error - using fallback content"],
                "context": "Technical error occurred"
            }
        }
        llm_response.content.parts[0].text = json.dumps(error_response, indent=2)
    
    return llm_response


# Create the default ADK Agent for game 2024030412
hockey_data_agent = create_hockey_agent_for_game("2024030412")

# For compatibility with existing code
DataAgent = hockey_data_agent