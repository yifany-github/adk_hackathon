"""
NHL Audio Agent - Google ADK-based Audio Commentary Agent

This module contains:
1. Audio agent factory function - Creates ADK Agent for audio processing
2. Audio tool functions - TTS, WebSocket streaming, status monitoring
3. Convenience interface functions - Simplified wrapper functions

Usage examples:
    from src.agents.audio_agent import create_audio_agent_for_game, process_commentary_text
    
    # Create audio agent for specific game
    audio_agent = create_audio_agent_for_game("2024030412")
    
    # Or use convenience function for direct processing
    result = await process_commentary_text("Goal scored by Connor McDavid!")
"""

from .audio_agent import (
    create_audio_agent_for_game,
    get_audio_agent,
    process_commentary_text
)

from .tool import (
    AUDIO_TOOLS,
    audio_processor
)

__all__ = [
    # Main factory function
    "create_audio_agent_for_game",
    "get_audio_agent",
    
    # Convenience functions
    "process_commentary_text",
    
    # Tools
    "AUDIO_TOOLS",
    "audio_processor"
] 