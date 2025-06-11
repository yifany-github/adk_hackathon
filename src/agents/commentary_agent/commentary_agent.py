"""
NHL Commentary Agent - Google ADK Implementation

Professional two-person broadcast commentary generation using Google ADK
"""

import json
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime
from google.adk.agents import LlmAgent
from google.adk.runners import BaseAgent, InvocationContext
from google.adk.events import Event
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

from .tools import COMMENTARY_TOOLS
from .prompts import COMMENTARY_AGENT_PROMPT

DEFAULT_MODEL = "gemini-2.0-flash"

class CommentaryAgent(BaseAgent):
    """
    NHL Commentary Agent - ADK Implementation
    
    Professional two-person broadcast commentary generation using Google ADK.
    Generates authentic hockey commentary with proper speaker turn-taking,
    context-aware dialogue, and audio-ready formatting.
    """
    
    def __init__(self, game_id: str, name: str = None, model: str = DEFAULT_MODEL, **kwargs):
        # Initialize with game-specific name if none provided
        if name is None:
            name = f"nhl_commentary_agent_{game_id}"
        
        super().__init__(name=name, **kwargs)
        
        # Store game-specific attributes
        self._game_id = game_id
        self._model = model
        self._static_context = None
        
        # Create internal LLM agent for commentary generation
        self._llm_agent = self._create_llm_agent()
        
        # Load static context for this game
        self._load_static_context()
    
    @property
    def game_id(self) -> str:
        """Get the game ID for this agent"""
        return self._game_id
    
    @property
    def model(self) -> str:
        """Get the model name"""
        return self._model
    
    @property
    def static_context(self) -> Dict[str, Any]:
        """Get the static game context"""
        return self._static_context or {}
    
    @property
    def llm_agent(self) -> LlmAgent:
        """Get the internal LLM agent"""
        return self._llm_agent
    
    def _load_static_context(self):
        """Load static context for the game"""
        try:
            from ..data_agent.tools import load_static_context
            self._static_context = load_static_context(self._game_id)
        except Exception as e:
            print(f"⚠️ Could not load static context for game {self._game_id}: {e}")
            self._static_context = {"game_info": {"game_id": self._game_id}}
    
    def _create_llm_agent(self) -> LlmAgent:
        """Create the internal LLM agent for commentary generation"""
        
        # Build game-specific instruction
        game_context_info = self._build_game_context_info()
        enhanced_instruction = COMMENTARY_AGENT_PROMPT + game_context_info
        
        return LlmAgent(
            name=f"nhl_commentary_llm_{self._game_id}",
            model=self._model,
            instruction=enhanced_instruction,
            description="NHL Commentary Agent - Professional two-person broadcast commentary generation",
            tools=COMMENTARY_TOOLS
        )
    
    def _build_game_context_info(self) -> str:
        """Build game-specific context information for the instruction"""
        if not self._static_context:
            return ""
        
        game_info = self._static_context.get('game_info', {})
        home_team = game_info.get('home_team', 'HOME')
        away_team = game_info.get('away_team', 'AWAY')
        venue = game_info.get('venue', 'Unknown Arena')
        
        return f"""
        
        CURRENT GAME CONTEXT:
        - Game ID: {self._game_id}
        - Matchup: {away_team} (Away) @ {home_team} (Home)
        - Venue: {venue}
        
        Use this context when generating commentary. Reference the actual team names and venue in your dialogue.
        Remember that {home_team} is the home team and {away_team} is visiting.
        """
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """
        Core async implementation for commentary generation.
        
        This method handles:
        1. Parsing data agent input
        2. Analyzing game context
        3. Generating two-person commentary
        4. Formatting for audio agent
        5. Returning structured results
        """
        try:
            print(f"🎙️ [{self.name}] Starting commentary generation workflow...")
            
            # Extract input data from session state or context
            data_agent_output = ctx.session.state.get("data_agent_output")
            if not data_agent_output:
                # Try to get from user message if available
                if hasattr(ctx, 'user_message') and ctx.user_message:
                    try:
                        data_agent_output = json.loads(str(ctx.user_message))
                    except json.JSONDecodeError:
                        data_agent_output = {"for_commentary_agent": {"recommendation": "FILLER_CONTENT"}}
                else:
                    yield Event(
                        id="commentary_error",
                        type="error",
                        content="No data agent output provided for commentary generation",
                        author=self.name
                    )
                    return
            
            print(f"🎯 [{self.name}] Processing data agent output...")
            
            # Set up session state for tools
            ctx.session.state["current_data_agent_output"] = data_agent_output
            ctx.session.state["static_context"] = self._static_context
            ctx.session.state["commentary_generation_status"] = "started"
            
            # Step 1: Analyze commentary context
            yield Event(
                id="context_analysis",
                type="info",
                content="Analyzing game context and determining commentary strategy...",
                author=self.name
            )
            
            # Run LLM agent to perform context analysis
            analysis_complete = False
            async for event in self._llm_agent.run_async(ctx):
                if hasattr(event, 'tool_call') and event.tool_call:
                    if event.tool_call.function.name == "analyze_commentary_context":
                        analysis_complete = True
                yield event
            
            if not analysis_complete:
                yield Event(
                    id="context_analysis_failed",
                    type="warning",
                    content="Context analysis incomplete, proceeding with default strategy",
                    author=self.name
                )
            
            # Step 2: Generate commentary
            yield Event(
                id="commentary_generation",
                type="info",
                content="Generating two-person broadcast commentary...",
                author=self.name
            )
            
            # Run LLM agent to generate commentary
            commentary_complete = False
            async for event in self._llm_agent.run_async(ctx):
                if hasattr(event, 'tool_call') and event.tool_call:
                    if event.tool_call.function.name == "generate_two_person_commentary":
                        commentary_complete = True
                yield event
            
            if not commentary_complete:
                yield Event(
                    id="commentary_generation_failed",
                    type="error",
                    content="Commentary generation failed",
                    author=self.name
                )
                return
            
            # Step 3: Format for audio agent
            yield Event(
                id="audio_formatting",
                type="info",
                content="Formatting commentary for audio processing...",
                author=self.name
            )
            
            # Run LLM agent to format for audio
            async for event in self._llm_agent.run_async(ctx):
                if hasattr(event, 'tool_call') and event.tool_call:
                    if event.tool_call.function.name == "format_commentary_for_audio":
                        break
                yield event
            
            # Step 4: Return final result
            commentary_result = ctx.session.state.get("last_commentary_generation", {})
            audio_format = ctx.session.state.get("audio_formatted_commentary", {})
            
            if commentary_result.get("status") == "success":
                success_message = f"Commentary generated successfully with {len(commentary_result.get('commentary_sequence', []))} dialogue exchanges"
                ctx.session.state["commentary_generation_status"] = "completed"
                
                yield Event(
                    id="commentary_success",
                    type="success",
                    content=success_message,
                    author=self.name,
                    final_response=True
                )
            else:
                error_message = f"Commentary generation failed: {commentary_result.get('error', 'Unknown error')}"
                ctx.session.state["commentary_generation_status"] = "failed"
                
                yield Event(
                    id="commentary_error",
                    type="error",
                    content=error_message,
                    author=self.name,
                    final_response=True
                )
                
        except Exception as e:
            error_msg = f"Commentary agent execution failed: {str(e)}"
            print(f"❌ [{self.name}] {error_msg}")
            
            ctx.session.state["commentary_generation_status"] = "error"
            ctx.session.state["commentary_error"] = error_msg
            
            yield Event(
                id="commentary_agent_error",
                type="error",
                content=error_msg,
                author=self.name,
                final_response=True
            )
    
    def get_agent(self) -> LlmAgent:
        """Get the internal LLM agent for backwards compatibility"""
        return self._llm_agent


def create_commentary_agent_for_game(
    game_id: str, 
    model: str = DEFAULT_MODEL,
    static_context: Optional[Dict[str, Any]] = None
) -> CommentaryAgent:
    """
    Create a commentary agent configured for a specific NHL game.
    
    Args:
        game_id: NHL game ID (e.g., "2024030412")
        model: LLM model to use (default: 'gemini-2.0-flash')
        static_context: Optional pre-loaded static game context (will be loaded if not provided)
        
    Returns:
        CommentaryAgent configured for commentary generation
    """
    agent = CommentaryAgent(game_id=game_id, model=model)
    
    # Override static context if provided
    if static_context is not None:
        agent._static_context = static_context
        # Recreate LLM agent with new context
        agent._llm_agent = agent._create_llm_agent()
    
    return agent


class CommentaryAgentManager:
    """
    Manager class for commentary agents to handle multiple games and provide
    convenient access to commentary generation functionality.
    """
    
    def __init__(self, model: str = DEFAULT_MODEL):
        """
        Initialize the commentary agent manager.
        
        Args:
            model: Default model to use for agents
        """
        self.model = model
        self.agents = {}  # game_id -> CommentaryAgent
    
    def get_agent_for_game(self, game_id: str) -> CommentaryAgent:
        """
        Get or create a commentary agent for a specific game.
        
        Args:
            game_id: NHL game ID
            
        Returns:
            CommentaryAgent configured for the game
        """
        if game_id not in self.agents:
            # Create agent for this game
            self.agents[game_id] = create_commentary_agent_for_game(
                game_id=game_id,
                model=self.model
            )
            
            print(f"✅ Created commentary agent for game {game_id}")
        
        return self.agents[game_id]
    
    async def generate_commentary(
        self, 
        game_id: str, 
        data_agent_output: Dict[str, Any],
        save_output: bool = True
    ) -> Dict[str, Any]:
        """
        Generate commentary for a specific game using data agent output.
        
        This is a simplified version for testing. In production, this would use
        the full ADK async workflow through proper runners.
        
        Args:
            game_id: NHL game ID
            data_agent_output: Output from the data agent
            save_output: Whether to save output to file (default: True)
            
        Returns:
            Generated commentary with metadata
        """
        try:
            agent = self.get_agent_for_game(game_id)
            
            # Use tools directly for testing (bypassing full LLM agent)
            from .tools import (
                generate_two_person_commentary,
                format_commentary_for_audio,
                analyze_commentary_context
            )
            
            # Create mock context with session state
            class MockSession:
                def __init__(self):
                    self.state = {
                        "current_data_agent_output": data_agent_output,
                        "static_context": agent.static_context
                    }
            
            class MockContext:
                def __init__(self):
                    self.session = MockSession()
            
            mock_context = MockContext()
            
            # Step 1: Analyze context
            analysis = analyze_commentary_context(mock_context)
            
            # Step 2: Generate commentary
            if analysis.get('status') == 'success':
                strategy = analysis.get('commentary_strategy', {})
                recommended_type = strategy.get('recommended_type', 'MIXED_COVERAGE')
                
                commentary_result = generate_two_person_commentary(
                    mock_context, 
                    recommended_type
                )
                
                # Step 3: Format for audio
                if commentary_result.get('status') == 'success':
                    audio_result = format_commentary_for_audio(mock_context)
                    
                    return {
                        "status": "success",
                        "commentary_data": commentary_result,
                        "audio_format": audio_result,
                        "analysis": analysis,
                        "game_id": game_id
                    }
                else:
                    return {
                        "status": "error",
                        "error": f"Commentary generation failed: {commentary_result.get('error', 'Unknown error')}",
                        "game_id": game_id
                    }
            else:
                return {
                    "status": "error",
                    "error": f"Context analysis failed: {analysis.get('error', 'Unknown error')}",
                    "game_id": game_id
                }
                
        except Exception as e:
            print(f"❌ Commentary generation failed for game {game_id}: {e}")
            return {
                "status": "error",
                "error": f"Commentary generation failed: {str(e)}",
                "game_id": game_id
            }
    
    def get_agent_info(self, game_id: str) -> Dict[str, Any]:
        """Get information about a commentary agent for a specific game."""
        agent = self.get_agent_for_game(game_id)
        static_context = agent.static_context
        game_info = static_context.get("game_info", {})
        
        return {
            "agent_name": agent.name,
            "agent_type": "nhl_commentary_agent",
            "model": self.model,
            "game_id": game_id,
            "game_context": {
                "home_team": game_info.get("home_team", "HOME"),
                "away_team": game_info.get("away_team", "AWAY"),
                "venue": game_info.get("venue", "Unknown Arena")
            },
            "capabilities": [
                "Two-person dialogue generation",
                "Context-aware commentary styles",
                "Real-time game state adaptation", 
                "Professional broadcast simulation",
                "Audio-ready output formatting"
            ],
            "tools_available": len(COMMENTARY_TOOLS)
        }

# Create default manager instance
default_commentary_manager = CommentaryAgentManager()

# Create default commentary agent instance
default_commentary_agent = None  # Will be created on first use

# Export for compatibility
commentary_agent = default_commentary_manager

# Convenience functions for easy access
def get_commentary_agent(game_id: str) -> CommentaryAgent:
    """Get commentary agent for a game."""
    return default_commentary_manager.get_agent_for_game(game_id)

async def generate_game_commentary(game_id: str, data_agent_output: Dict[str, Any], save_output: bool = True) -> Dict[str, Any]:
    """Generate commentary for a game."""
    return await default_commentary_manager.generate_commentary(game_id, data_agent_output, save_output)

# Convenience function for quick processing
async def process_data_for_commentary(game_id: str, data_agent_output: Dict[str, Any], save_output: bool = True) -> Dict[str, Any]:
    """Process data agent output and generate commentary."""
    return await generate_game_commentary(game_id, data_agent_output, save_output)

async def main():
    """Test the commentary agent with sample data."""
    
    # Sample data agent output
    sample_data = {
        "for_commentary_agent": {
            "recommendation": "MIXED_COVERAGE",
            "priority_level": 2,
            "momentum_score": 35,
            "key_talking_points": [
                "McDavid has been quiet early, looking for his first point",
                "Florida's power play is clicking at 28% this series"
            ],
            "game_context": {
                "period": 1,
                "time_remaining": "15:30",
                "home_score": 1,
                "away_score": 2,
                "game_situation": "even strength"
            },
            "high_intensity_events": [
                {
                    "summary": "Big hit by Ekblad on Draisaitl in the corner",
                    "impact_score": 40,
                    "event_type": "hit"
                }
            ]
        }
    }
    
    # Create agent for test game
    test_game_id = "2024030412"
    agent = get_commentary_agent(test_game_id)
    
    print(f"🏒 NHL Commentary Agent Test")
    print(f"Agent: {agent.name}")
    print(f"Game ID: {test_game_id}")
    
    try:
        result = await generate_game_commentary(test_game_id, sample_data)
        print(f"✅ Result: {result['status']}")
        if result['status'] == 'success':
            commentary_data = result.get('commentary_data', {})
            print(f"📝 Generated {len(commentary_data.get('commentary_sequence', []))} commentary lines")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())