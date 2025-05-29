"""
Data Agent - Responsible for fetching and processing hockey game data
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import json
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.scrapers.nhl_api import NHLAPIClient


class DataAgent:
    """Agent responsible for fetching and processing live hockey data"""
    
    def __init__(self, game_id: Optional[int] = None):
        self.game_id = game_id
        self.nhl_client = None
        self.last_event_id = 0
        self.game_state = {}
        
    async def initialize(self):
        """Initialize the data agent"""
        self.nhl_client = NHLAPIClient()
        await self.nhl_client.__aenter__()
        
        # If no game_id provided, find today's first game
        if not self.game_id:
            games = await self.nhl_client.get_todays_games()
            if games:
                self.game_id = games[0]["gamePk"]
                print(f"Auto-selected game: {self.game_id}")
            else:
                print("No games found for today")
                return False
        return True
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.nhl_client:
            await self.nhl_client.__aexit__(None, None, None)
    
    async def get_new_events(self) -> List[Dict]:
        """Get new events since last check"""
        if not self.nhl_client or not self.game_id:
            return []
        
        try:
            all_events = await self.nhl_client.get_game_events(self.game_id)
            
            # Filter for new events
            new_events = []
            for event in all_events:
                event_id = event.get("event_id", 0)
                if event_id > self.last_event_id:
                    new_events.append(event)
                    self.last_event_id = max(self.last_event_id, event_id)
            
            return new_events
            
        except Exception as e:
            print(f"Error fetching events: {e}")
            return []
    
    async def get_current_game_state(self) -> Dict:
        """Get current game state including score and status"""
        if not self.nhl_client or not self.game_id:
            return {}
        
        try:
            score_data = await self.nhl_client.get_game_score(self.game_id)
            self.game_state = score_data
            return score_data
            
        except Exception as e:
            print(f"Error fetching game state: {e}")
            return self.game_state
    
    def format_event_for_commentary(self, event: Dict) -> Dict:
        """Format event data for commentary generation"""
        event_type = event.get("event_type", "")
        description = event.get("description", "")
        period = event.get("period", 0)
        time = event.get("time", "")
        players = event.get("players", [])
        team = event.get("team", "")
        
        # Create context for commentary
        context = {
            "event_type": event_type,
            "raw_description": description,
            "period": period,
            "time": time,
            "players_involved": players,
            "team": team,
            "game_state": self.game_state,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add event-specific context
        if event_type == "GOAL":
            context["excitement_level"] = "high"
            context["commentary_style"] = "excited"
        elif event_type == "PENALTY":
            context["excitement_level"] = "medium"
            context["commentary_style"] = "analytical"
        elif event_type in ["SHOT", "SAVE"]:
            context["excitement_level"] = "medium"
            context["commentary_style"] = "play_by_play"
        else:
            context["excitement_level"] = "low"
            context["commentary_style"] = "informational"
        
        return context
    
    async def process_data_continuously(self, callback_func=None):
        """Continuously process new game data"""
        print(f"Starting continuous data processing for game {self.game_id}")
        
        while True:
            try:
                # Get new events
                new_events = await self.get_new_events()
                
                # Get current game state
                current_state = await self.get_current_game_state()
                
                # Process new events
                for event in new_events:
                    formatted_event = self.format_event_for_commentary(event)
                    print(f"New event: {formatted_event['event_type']} - {formatted_event['raw_description']}")
                    
                    # Call callback function if provided (for agent communication)
                    if callback_func:
                        await callback_func(formatted_event)
                
                # Wait before next check (adjust based on game pace)
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                print(f"Error in continuous processing: {e}")
                await asyncio.sleep(10)  # Wait longer on error


# Test function
async def test_data_agent():
    """Test the data agent functionality"""
    agent = DataAgent()
    
    if await agent.initialize():
        print("Data agent initialized successfully")
        
        # Test getting current state
        state = await agent.get_current_game_state()
        print(f"Current game state: {state}")
        
        # Test getting events
        events = await agent.get_new_events()
        print(f"Found {len(events)} events")
        
        for event in events[:3]:  # Show first 3 events
            formatted = agent.format_event_for_commentary(event)
            print(f"Formatted event: {formatted}")
    
    await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(test_data_agent()) 