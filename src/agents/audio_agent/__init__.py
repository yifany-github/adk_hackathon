"""
NHL Audio Agent - Google ADK-based Audio Commentary Agent

This module contains:
1. AudioAgent class - Main audio processing agent
2. Audio tool functions - TTS, WebSocket streaming, status monitoring
3. Convenience interface functions - Simplified wrapper functions

Usage examples:
    from src.agents.audio_agent import audio_agent, process_commentary_text
    
    # Process commentary text
    result = await process_commentary_text("Goal scored by Connor McDavid!")
    
    # Or use the full agent
    agent = AudioAgent()
    result = await agent.process_commentary("Amazing save by the goalie!")
"""

from .audio_agent import (
    AudioAgent,
    process_commentary_text,
    start_audio_streaming_service
)

from .tool import (
    AUDIO_TOOLS,
    audio_processor
)

__all__ = [
    # Main classes and instances
    "AudioAgent",
    
    # Convenience functions
    "process_commentary_text",
    "start_audio_streaming_service",
    
    # Tools
    "AUDIO_TOOLS",
    "audio_processor"
] 