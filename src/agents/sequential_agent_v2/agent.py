"""
Clean Sequential Agent - NHL Commentary Pipeline
Minimal agent declaration only
"""

import os
from google.adk.agents import SequentialAgent


class NHLSequentialAgent:
    """Minimal Sequential Agent for NHL Commentary"""
    
    def __init__(self, game_id: str):
        self.game_id = game_id
        self.agent = None
        
    async def initialize(self):
        """Initialize agent with sub-agents"""
        from ..data_agent.data_agent_adk import create_hockey_agent_for_game
        from ..commentary_agent.commentary_agent import create_commentary_agent_for_game
        
        data_agent = create_hockey_agent_for_game(self.game_id, 'gemini-2.0-flash')
        commentary_agent = create_commentary_agent_for_game(self.game_id)
        
        self.agent = SequentialAgent(
            name=f"NHL_{self.game_id}",
            sub_agents=[data_agent, commentary_agent],
            description=f"NHL Data + Commentary Pipeline for {self.game_id}"
        )
        
        print(f"✅ Sequential Agent initialized for game {self.game_id} (stateless)")


def create_nhl_sequential_agent(game_id: str) -> NHLSequentialAgent:
    """Create NHL Sequential Agent"""
    import dotenv
    dotenv.load_dotenv()
    
    api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise Exception("GOOGLE_API_KEY not found in environment")
    
    try:
        import google.genai as genai
        genai.configure(api_key=api_key)
    except:
        pass
        
    return NHLSequentialAgent(game_id)