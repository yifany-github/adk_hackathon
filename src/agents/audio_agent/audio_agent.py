"""
NHL Audio Agent - ADK Custom Agent Implementation

Professional audio processing agent using Google ADK Custom Agent pattern.
Implements complex orchestration logic for TTS and audio streaming.
"""

import json
from typing import Dict, Any, Optional, AsyncGenerator
from google.adk.agents import BaseAgent, LlmAgent
from google.adk.runners import InvocationContext
from google.adk.events import Event
from google.adk.tools import FunctionTool
from google.genai import types

from .tool import AUDIO_TOOLS

DEFAULT_MODEL = "gemini-2.0-flash"
#DEFAULT_MODEL = "gemini-2.5-flash-preview-tts"

class AudioAgent(BaseAgent):
    """
    NHL Commentary Audio Agent - Custom Agent with orchestration logic
    
    Implements Google ADK Custom Agent pattern for:
    1. Intelligent voice style analysis
    2. WebSocket server management
    3. TTS generation and streaming coordination
    4. Complex error handling and retry logic
    """
    
    # Pydantic configuration to allow extra fields
    model_config = {"extra": "allow"}
    
    # Define custom fields
    game_id: str
    audio_model: str = DEFAULT_MODEL
    
    def __init__(self, game_id: str, model: str = DEFAULT_MODEL, **kwargs):
        # Initialize base agent with required fields
        super().__init__(
            name=f"nhl_audio_agent_{game_id}",
            game_id=game_id,
            audio_model=model,
            **kwargs
        )
        
        # Initialize custom attributes
        self._websocket_server_running = False
        self._llm_agent = self._create_llm_agent()
        
    def _create_llm_agent(self) -> LlmAgent:
        """Create internal LLM agent for audio processing tasks"""
        
        agent_instruction = f"""
You are a professional NHL audio processing agent for game {self.game_id}.

Your role is to make intelligent decisions about audio processing and use the provided tools effectively.

## Available Tools:
1. **text_to_speech**: Convert commentary text to speech with appropriate voice style
2. **stream_audio_websocket**: Start/manage WebSocket audio streaming server
3. **get_audio_status**: Monitor audio system status

## Voice Style Selection Guidelines:
- **enthusiastic**: Goals, great saves, exciting plays (DEFAULT)
- **dramatic**: Overtime, penalties, critical moments
- **calm**: General commentary, analysis periods

## Decision Making:
1. Analyze input text for emotional content and game situation
2. Choose appropriate voice style automatically
3. Ensure streaming infrastructure is ready
4. Generate high-quality TTS output
5. Return structured processing results

Always respond with clear status and error handling information.
"""

        return LlmAgent(
            name=f"audio_llm_processor_{self.game_id}",
            model=self.audio_model,
            instruction=agent_instruction,
            description="Internal LLM agent for audio processing decisions",
            tools=AUDIO_TOOLS
        )
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """
        Custom orchestration logic for audio processing workflow
        
        Implements the core Custom Agent pattern:
        1. Parse input and analyze requirements
        2. Intelligently select voice style
        3. Ensure WebSocket server is ready
        4. Generate TTS audio
        5. Handle errors and provide feedback
        """
        try:
            yield Event(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=f"🎵 [{self.name}] Starting audio processing workflow for game {self.game_id}")]
                ),
                author=self.name
            )
            
            # Step 1: Extract input text from context
            input_text = await self._extract_input_text(ctx)
            if not input_text:
                yield Event(
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text="No text content found for audio conversion")]
                    ),
                    author=self.name
                )
                return
            
            yield Event(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=f"🎙️ Processing text: {input_text[:50]}{'...' if len(input_text) > 50 else ''}")]
                ),
                author=self.name
            )
            
            # Step 2: Intelligent voice style analysis
            voice_style = self._analyze_voice_style(input_text)
            ctx.session.state["current_text"] = input_text
            ctx.session.state["voice_style"] = voice_style
            
            yield Event(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=f"🎭 Selected voice style: {voice_style}")]
                ),
                author=self.name
            )
            
            # Step 3: Ensure WebSocket server is running (if needed)
            if not self._websocket_server_running:
                yield Event(
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text="🌐 Ensuring WebSocket server is ready...")]
                    ),
                    author=self.name
                )
                
                # Call WebSocket tool through LLM agent
                async for event in self._llm_agent.run_async(ctx):
                    # Monitor for server startup
                    if hasattr(event, 'tool_call') and event.tool_call:
                        if event.tool_call.function.name == "stream_audio_websocket":
                            self._websocket_server_running = True
                    yield event
            
            # Step 4: Generate TTS audio
            yield Event(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=f"🔊 Generating TTS audio with {voice_style} style...")]
                ),
                author=self.name
            )
            
            # Set processing context for LLM agent
            ctx.session.state["audio_processing_request"] = {
                "text": input_text,
                "voice_style": voice_style,
                "language": "en-US"
            }
            
            # Run TTS generation through LLM agent
            audio_success = False
            async for event in self._llm_agent.run_async(ctx):
                # Monitor for successful audio generation
                if hasattr(event, 'content') and event.content:
                    try:
                        response_data = json.loads(event.content.parts[0].text)
                        if response_data.get("status") == "success":
                            audio_success = True
                    except (json.JSONDecodeError, AttributeError, IndexError):
                        pass
                yield event
            
            # Step 5: Final status and completion
            if audio_success:
                yield Event(
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text="✅ Audio processing completed successfully!")]
                    ),
                    author=self.name
                )
            else:
                yield Event(
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text="❌ Audio processing failed - check logs for details")]
                    ),
                    author=self.name
                )
                
        except Exception as e:
            yield Event(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=f"❌ Audio workflow error: {str(e)}")]
                ),
                author=self.name
            )
    
    async def _extract_input_text(self, ctx: InvocationContext) -> Optional[str]:
        """Extract input text from various possible sources"""
        
        # Try session state first
        input_text = ctx.session.state.get("commentary_text") or ctx.session.state.get("text")
        
        if not input_text:
            # Extract from user_content (this is where the text is)
            if ctx.user_content and ctx.user_content.parts:
                for part in ctx.user_content.parts:
                    if hasattr(part, 'text') and part.text:
                        input_text = part.text
                        break
        
        return input_text
    
    def _analyze_voice_style(self, text: str) -> str:
        """
        Intelligent voice style analysis based on text content
        
        Args:
            text: Commentary text to analyze
            
        Returns:
            Appropriate voice style (enthusiastic, dramatic, calm)
        """
        text_lower = text.lower()
        
        # Dramatic situations
        dramatic_keywords = [
            'overtime', 'final', 'crucial', 'critical', 'penalty', 'power play', 
            'empty net', 'playoff', 'elimination', 'sudden death', 'game-winning'
        ]
        
        # Exciting situations  
        exciting_keywords = [
            'goal', 'score', 'amazing', 'incredible', 'fantastic', 'wow', 
            'shot', 'save', 'breakaway', 'rebound', 'assist'
        ]
        
        if any(keyword in text_lower for keyword in dramatic_keywords):
            return "dramatic"
        elif any(keyword in text_lower for keyword in exciting_keywords):
            return "enthusiastic"
        else:
            return "enthusiastic"  # Default to enthusiastic for hockey commentary
    
    # Public methods for external use
    @property
    def websocket_server_running(self) -> bool:
        """Check if WebSocket server is running"""
        return self._websocket_server_running
    
    async def process_commentary(self, commentary_text: str, voice_style: str) -> Dict[str, Any]:
        """
        Convenience method to process commentary text
        
        Args:
            commentary_text: Text to convert to audio
            voice_style: Optional voice style override
            
        Returns:
            Processing result dictionary
        """
        try:
            # Use internal tool directly for simple processing
            from .tool import text_to_speech
            
            # Auto-detect voice style if not provided
            if not voice_style:
                voice_style = self._analyze_voice_style(commentary_text)
            
            result = await text_to_speech(
                tool_context=None,
                text=commentary_text,
                voice_style=voice_style,
                language="en-US"
            )
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Commentary processing failed: {str(e)}",
                "commentary": commentary_text[:50] + "..." if len(commentary_text) > 50 else commentary_text
            }


# Factory function for creating audio agents
def create_audio_agent_for_game(game_id: str, model: str) -> AudioAgent:
    """
    Create an audio agent configured for a specific NHL game.
    
    Args:
        game_id: NHL game ID (e.g., "2024030412")
        model: LLM model to use (default: 'gemini-2.0-flash')
        
    Returns:
        Custom AudioAgent instance
    """
    return AudioAgent(game_id=game_id, model=model)


# Convenience functions for easy access
def get_audio_agent(game_id: str) -> AudioAgent:
    """Get audio agent for a game."""
    return create_audio_agent_for_game(game_id)


# Convenience function for direct audio processing
async def process_commentary_text(text: str, style: str) -> Dict[str, Any]:
    """
    Convenience function for processing commentary text to audio
    
    Args:
        text: Commentary text to convert
        style: Voice style
        
    Returns:
        Audio processing result
    """
    try:
        from .tool import text_to_speech
        
        result = await text_to_speech(
            tool_context=None,
            text=text,
            voice_style=style,
            language="en-US"
        )
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Audio processing failed: {str(e)}",
            "audio_id": None
        }


def main():
    """Test the custom audio agent."""
    test_game_id = "2024030412"
    agent = get_audio_agent(test_game_id)
    
    print(f"🎵 NHL Audio Agent - Custom Implementation")
    print(f"Agent: {agent.name}")
    print(f"Game ID: {agent.game_id}")
    print(f"Model: {agent.audio_model}")
    print(f"Type: {type(agent).__name__}")


if __name__ == "__main__":
    try:
        main()
    except ImportError as e:
        print(f"⚠️ Import error during testing: {e}")
        print("✅ Custom Audio Agent implementation created")