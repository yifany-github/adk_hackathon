"""True Hockey Data Agent using Google ADK - Intelligent, not just rule-based."""

import json
from typing import Dict, Any, List, Optional
from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse

from . import prompts
from .config import DEFAULT_MODEL
from .tools import (
    analyze_hockey_momentum_adk,
    extract_game_context_adk,
    create_game_specific_get_player_information,
    create_game_specific_generate_filler_content,
    load_static_context
)




def create_hockey_agent_for_game(game_id: str, model: str) -> Agent:
    """
    Create a hockey data agent with pre-loaded game-specific context.
    
    Args:
        game_id: NHL game ID (e.g., "2024030412")
        model: LLM model to use (default: 'gemini-2.0-flash')
        
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
    game_specific_get_player_information = create_game_specific_get_player_information(static_context)
    game_specific_generate_filler_content = create_game_specific_generate_filler_content(static_context)
    
    # Create agent with game-specific context
    return Agent(
        model=model,
        name=f'hockey_data_agent_{game_id}',
        instruction=enhanced_instruction,
        tools=[
            analyze_hockey_momentum_adk,
            game_specific_get_player_information,
            game_specific_generate_filler_content, 
            extract_game_context_adk
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
        
        # Transform new schema to maintain compatibility with commentary agent
        analysis = parsed_response.get("analysis", {})
        recommendation = parsed_response.get("recommendation", {})
        
        # Map new schema to legacy format for commentary agent compatibility
        formatted_response = {
            "generated_at": "2025-06-10T15:00:00.000000Z",  # Would use real timestamp
            "data_agent_version": "adk_v2.0",
            "agent_type": "intelligent_adk_agent",
            "for_commentary_agent": {
                "recommendation": recommendation.get("coverage_type", "FILLER_CONTENT"),
                "priority_level": recommendation.get("priority", 3),
                "momentum_score": analysis.get("momentum_score", 0),
                "key_talking_points": recommendation.get("talking_points", []),
                "context": recommendation.get("reasoning", "Analysis completed"),
                "game_context": analysis.get("game_context", {}),
                "high_intensity_events": analysis.get("high_intensity_events", []),
                "task_details": {
                    "task_type": "intelligent_analysis",
                    "priority": recommendation.get("priority", 3),
                    "specific_guidance": recommendation.get("guidance", "Continue monitoring")
                }
            }
        }
        
        # Update the response with formatted JSON
        llm_response.content.parts[0].text = json.dumps(formatted_response, indent=2)
        
    except (json.JSONDecodeError, IndexError) as e:
        # If JSON parsing fails, wrap in error response
        error_response = {
            "generated_at": "2025-06-10T15:00:00.000000Z",
            "data_agent_version": "adk_v2.0", 
            "agent_type": "intelligent_adk_agent",
            "error": f"Failed to parse agent response: {str(e)}",
            "raw_response": llm_response.content.parts[0].text if llm_response.content.parts else "",
            "for_commentary_agent": {
                "recommendation": "FILLER_CONTENT",
                "priority_level": 3,
                "momentum_score": 0,
                "key_talking_points": ["Agent error - using fallback content"],
                "context": "Technical error occurred",
                "game_context": {},
                "high_intensity_events": [],
                "task_details": {
                    "task_type": "error_fallback",
                    "priority": 3,
                    "specific_guidance": "Handle technical error gracefully"
                }
            }
        }
        llm_response.content.parts[0].text = json.dumps(error_response, indent=2)
    
    return llm_response


# Usage: 
# agent = create_hockey_agent_for_game("your_game_id")
# For each specific game, call create_hockey_agent_for_game() with the appropriate game_id