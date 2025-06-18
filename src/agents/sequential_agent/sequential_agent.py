"""
NHL Sequential Agent - Simple ADK Workflow
"""

from google.adk.agents import SequentialAgent
from google.adk.runners import InMemoryRunner
from google.genai.types import Part, UserContent
import json
import os
import asyncio

try:
    from .prompts import get_workflow_prompt
    from .tools import extract_audio_from_result, save_result
except ImportError:
    # For direct execution
    from prompts import get_workflow_prompt
    from tools import extract_audio_from_result, save_result


def create_nhl_sequential_agent(game_id: str) -> SequentialAgent:
    """Create Sequential Agent: Data → Commentary → Audio"""
    import sys
    import os
    
    # Add project root to path
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    sys.path.append(project_root)
    
    from src.agents.data_agent.data_agent_adk import create_hockey_agent_for_game
    from src.agents.commentary_agent.commentary_agent import create_commentary_agent_for_game
    from src.agents.audio_agent.audio_agent import AudioAgent
    
    # Create agents
    data_agent = create_hockey_agent_for_game(game_id)
    commentary_agent = create_commentary_agent_for_game(game_id)
    audio_agent = AudioAgent(name=f"audio_{game_id}")
    
    # Create Sequential Agent
    return SequentialAgent(
        name=f"NHL_{game_id}",
        sub_agents=[data_agent, commentary_agent, audio_agent],
        description=f"NHL Commentary Pipeline for {game_id}"
    )


async def process_timestamp(sequential_agent: SequentialAgent, timestamp_file: str, game_id: str):
    """Process timestamp through Sequential Agent"""
    try:
        # Load timestamp data
        with open(timestamp_file, 'r') as f:
            timestamp_data = json.load(f)
        
        # Create input
        prompt = get_workflow_prompt(game_id, json.dumps(timestamp_data, indent=2))
        input_content = UserContent(parts=[Part(text=prompt)])
        
        # Run Sequential Agent
        runner = InMemoryRunner(agent=sequential_agent)
        session = await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id=f"nhl_{game_id}"
        )
        
        result_text = ""
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=input_content
        ):
            if hasattr(event, 'content'):
                result_text += str(event.content)
        
        # Extract audio and save result
        timestamp_name = os.path.basename(timestamp_file).replace('.json', '')
        audio_files = extract_audio_from_result(result_text, game_id, timestamp_name)
        output_file = save_result(game_id, timestamp_file, result_text)
        
        return {
            "status": "success",
            "timestamp": timestamp_name,
            "output_file": output_file,
            "audio_files": len(audio_files)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "timestamp": os.path.basename(timestamp_file),
            "error": str(e)
        }


async def test_sequential_agent(game_id: str = "2024030412"):
    """Simple test of Sequential Agent"""
    try:
        # Create agent and find test file
        sequential_agent = create_nhl_sequential_agent(game_id)
        timestamp_files = [f for f in os.listdir(f"data/live/{game_id}") if f.endswith('.json')]
        
        if not timestamp_files:
            print("❌ No timestamp files found")
            return False
        
        test_file = f"data/live/{game_id}/{timestamp_files[0]}"
        result = await process_timestamp(sequential_agent, test_file, game_id)
        
        if result["status"] == "success":
            print(f"✅ Test successful! Audio files: {result['audio_files']}")
            return True
        else:
            print(f"❌ Test failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_sequential_agent())
    print(f"Result: {'SUCCESS' if success else 'FAILED'}")