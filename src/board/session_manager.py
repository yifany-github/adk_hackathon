#!/usr/bin/env python3
"""
Session Manager - Handles context refresh and narrative compaction
Prevents AI memory corruption through periodic session resets
"""

from typing import Dict, Any, Tuple
from google.adk.runners import InMemoryRunner
from google.genai.types import Part, UserContent
from .live_game_board import LiveGameBoard


class SessionManager:
    """
    Manages AI session lifecycle and context refresh to prevent memory corruption.
    """
    
    def __init__(self, refresh_interval: int = 10):
        self.refresh_interval = refresh_interval
        self.timestamp_count = 0
        self.data_session_history = []
        self.commentary_session_history = []
        
    async def maybe_refresh_sessions(self, 
                                   data_runner: InMemoryRunner, 
                                   data_session,
                                   commentary_runner: InMemoryRunner,
                                   commentary_session,
                                   game_board: LiveGameBoard) -> Tuple[Any, Any]:
        """
        Check if sessions need refresh and create new ones if necessary.
        Returns updated sessions (either existing or new ones).
        """
        self.timestamp_count += 1
        
        if self.timestamp_count % self.refresh_interval == 0:
            print(f"🔄 Refreshing sessions at timestamp {self.timestamp_count}")
            
            # Generate compact narrative summary
            narrative_summary = game_board.get_narrative_context()
            
            # Create new sessions with fresh context
            new_data_session = await self.create_fresh_data_session(
                data_runner, game_board, narrative_summary
            )
            new_commentary_session = await self.create_fresh_commentary_session(
                commentary_runner, game_board, narrative_summary
            )
            
            print(f"✅ Session refresh completed")
            return new_data_session, new_commentary_session
        
        return data_session, commentary_session
    
    async def create_fresh_data_session(self, 
                                      data_runner: InMemoryRunner,
                                      game_board: LiveGameBoard,
                                      narrative_summary: str):
        """
        Create fresh data agent session with current game state and narrative context.
        """
        # Create new session
        new_session = await data_runner.session_service.create_session(
            app_name=data_runner.app_name,
            user_id=f"data_agent_{game_board.game_id}_refresh_{self.timestamp_count}"
        )
        
        # Initialize with current game state and narrative context
        initialization_context = UserContent(parts=[Part(text=f"""
You are analyzing NHL game {game_board.game_id} with FRESH CONTEXT after session refresh.

PREVIOUS GAME NARRATIVE:
{narrative_summary}

{game_board.get_prompt_injection()}

TEMPORAL CONSISTENCY RULES (CRITICAL):
- Scores can only INCREASE, never decrease
- Shot counts can only INCREASE, never decrease  
- Goals scored in previous analysis remain scored - never "un-score" them
- Penalties called previously remain active until they logically expire
- Timeline moves forward: time_remaining decreases as game progresses

CUMULATIVE STATE AWARENESS:
- Build on the previous narrative context provided above
- Maintain continuity with established game flow
- Reference previous events when relevant for context
- Track power play situations until they naturally end

You'll receive timestamp data sequentially. Always maintain consistency with the authoritative game state and previous narrative.

Ready to continue NHL game analysis with fresh session context?
""")])
        
        # Send initialization context
        async for event in data_runner.run_async(
            user_id=new_session.user_id,
            session_id=new_session.id,
            new_message=initialization_context,
        ):
            pass  # Just establish context
        
        return new_session
    
    async def create_fresh_commentary_session(self,
                                            commentary_runner: InMemoryRunner,
                                            game_board: LiveGameBoard,
                                            narrative_summary: str):
        """
        Create fresh commentary agent session with current game state and narrative context.
        """
        # Create new session
        new_session = await commentary_runner.session_service.create_session(
            app_name=commentary_runner.app_name,
            user_id=f"commentary_agent_{game_board.game_id}_refresh_{self.timestamp_count}"
        )
        
        # Initialize with current game state and narrative context
        initialization_context = UserContent(parts=[Part(text=f"""
You are continuing the live commentary for NHL game {game_board.game_id} with FRESH SESSION CONTEXT.

PREVIOUS BROADCAST NARRATIVE:
{narrative_summary}

{game_board.get_prompt_injection()}

BROADCAST CONTINUITY REQUIREMENTS:
- You are Alex Chen (Play-by-Play) and Mike Rodriguez (Color Commentary)
- Maintain natural conversational flow building on the previous broadcast narrative
- Don't repeat recent talking points or player mentions from the narrative above
- Build naturally on the established game storyline
- Acknowledge major events that have already occurred (referenced in narrative)
- Keep professional broadcast energy consistent with game momentum

SESSION REFRESH CONTEXT:
- This is a fresh session, but the game continues from the narrative above
- Maintain broadcast authenticity - don't reference "session refresh" on air
- Flow naturally from previous commentary themes
- Reference established player performances and game situations

Ready to continue professional NHL broadcast commentary with fresh session context?
""")])
        
        # Send initialization context
        async for event in commentary_runner.run_async(
            user_id=new_session.user_id,
            session_id=new_session.id,
            new_message=initialization_context,
        ):
            pass  # Just establish context
        
        return new_session
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Return session management statistics for monitoring.
        """
        return {
            "total_timestamps": self.timestamp_count,
            "refresh_interval": self.refresh_interval,
            "refreshes_performed": self.timestamp_count // self.refresh_interval,
            "next_refresh_at": ((self.timestamp_count // self.refresh_interval) + 1) * self.refresh_interval
        }