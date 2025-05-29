"""
Main entry point for Hockey Livestream Agent
"""
import asyncio
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__)))

from agents.data_agent import DataAgent

async def main():
    print("🏒 Starting Hockey Livestream Agent...")
    
    # Initialize data agent
    data_agent = DataAgent()
    
    if await data_agent.initialize():
        print("✅ Data agent initialized")
        
        # Test basic functionality
        state = await data_agent.get_current_game_state()
        print(f"Current game: {state}")
        
        events = await data_agent.get_new_events()
        print(f"Found {len(events)} events")
        
    await data_agent.cleanup()
    print("🏒 Hockey Livestream Agent stopped")

if __name__ == "__main__":
    asyncio.run(main())
