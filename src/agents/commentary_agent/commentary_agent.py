"""
NHL Commentary Agent - Simplified ADK Implementation

Professional two-person broadcast commentary generation using Google ADK.
Follows the simple Agent pattern like the data agent.
"""

import json
from typing import Dict, Any, Optional
from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse

from .tools import COMMENTARY_TOOLS
from .prompts import COMMENTARY_AGENT_PROMPT

DEFAULT_MODEL = "gemini-2.0-flash"


def create_commentary_agent_for_game(
    game_id: str, 
    model: str = DEFAULT_MODEL
) -> Agent:
    """
    Create a commentary agent configured for a specific NHL game.
    Follows the simple ADK Agent pattern like the data agent.
    
    Args:
        game_id: NHL game ID (e.g., "2024030412")
        model: LLM model to use (default: 'gemini-2.0-flash')
        
    Returns:
        ADK Agent configured for commentary generation
    """
    # Load static game context
    static_context = _load_static_context(game_id)
    
    # Build game-specific context information
    game_context_info = _build_game_context_info(static_context, game_id)
    
    # Enhanced instruction with game context
    enhanced_instruction = COMMENTARY_AGENT_PROMPT + game_context_info
    
    # Create agent with game-specific context
    return Agent(
        model=model,
        name=f'nhl_commentary_agent_{game_id}',
        instruction=enhanced_instruction,
        tools=COMMENTARY_TOOLS,
    )


def _load_static_context(game_id: str) -> Dict[str, Any]:
    """Load static context for the game"""
    try:
        # Import here to avoid circular imports
        from ..data_agent.tools import load_static_context
        return load_static_context(game_id)
    except Exception as e:
        print(f"⚠️ Could not load static context for game {game_id}: {e}")
        return {"game_info": {"game_id": game_id}}


def _build_game_context_info(static_context: Dict[str, Any], game_id: str) -> str:
    """Build game-specific context information for the instruction"""
    if not static_context:
        return f"\n\nCURRENT GAME CONTEXT:\n- Game ID: {game_id}\n"
    
    game_info = static_context.get('game_info', {})
    home_team = game_info.get('home_team', 'HOME')
    away_team = game_info.get('away_team', 'AWAY')
    venue = game_info.get('venue', 'Unknown Arena')
    
    return f"""

CURRENT GAME CONTEXT:
- Game ID: {game_id}
- Matchup: {away_team} (Away) @ {home_team} (Home)
- Venue: {venue}

Use this context when generating commentary. Reference the actual team names and venue in your dialogue.
Remember that {home_team} is the home team and {away_team} is visiting.
"""




# Convenience functions for easy access
def get_commentary_agent(game_id: str) -> Agent:
    """Get commentary agent for a game."""
    return create_commentary_agent_for_game(game_id)


# Legacy compatibility - create default agent for testing
commentary_agent = None  # Will be created when needed


def main():
    """Test the simplified commentary agent."""
    test_game_id = "2024030412"
    agent = get_commentary_agent(test_game_id)
    
    print(f"🏒 NHL Commentary Agent - Simplified")
    print(f"Agent: {agent.name}")
    print(f"Game ID: {test_game_id}")
    print(f"Model: {agent.model}")
    print(f"Tools: {len(agent.tools)}")


if __name__ == "__main__":
    main()