#!/usr/bin/env python3
"""
Test script for ADK-based data agent - processes each timestamp individually
"""
import sys
import os
import json
import glob
from datetime import datetime
import dotenv
sys.path.append('src/agents/data_agent')

# Load environment variables
dotenv.load_dotenv()

# Set up proper Python path for imports
sys.path.insert(0, 'src')
from agents.data_agent.data_agent_adk import create_hockey_agent_for_game

async def process_single_timestamp_with_adk_agent(agent, timestamp_file: str, game_id: str):
    """Process a single timestamp using the ADK DataAgent"""
    try:
        # Load the timestamp data
        with open(timestamp_file, 'r') as f:
            timestamp_data = json.load(f)
        
        # Simple input - let the agent use its existing prompt and tools
        input_text = f"Analyze hockey timestamp for game {game_id}: {json.dumps(timestamp_data)}"
        
        # Use InMemoryRunner as shown in ADK samples
        from google.adk.runners import InMemoryRunner
        from google.genai.types import Part, UserContent
        
        runner = InMemoryRunner(agent=agent)
        session = await runner.session_service.create_session(
            app_name=runner.app_name, user_id="test_user"
        )
        content = UserContent(parts=[Part(text=input_text)])
        
        response_text = ""
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.content.parts and event.content.parts[0].text:
                response_text = event.content.parts[0].text
        
        if response_text:
            try:
                # Parse JSON response
                parsed_response = json.loads(response_text)
                return parsed_response
            except json.JSONDecodeError:
                return {"error": f"Failed to parse agent response: {response_text[:200]}..."}
        else:
            return {"error": "No response from agent"}
        
    except Exception as e:
        return {"error": f"Failed to process {timestamp_file}: {str(e)}"}

def save_adk_output(result: dict, game_id: str, game_time: str):
    """Save ADK agent output to the data_agent_outputs directory"""
    try:
        # Create output directory
        output_dir = "data/data_agent_outputs"
        os.makedirs(output_dir, exist_ok=True)
        
        # Clean up game_time for filename
        game_time_clean = str(game_time).replace(":", "_").replace(" ", "_")
        filename = f"{game_id}_{game_time_clean}_adk.json"
        filepath = os.path.join(output_dir, filename)
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"💾 ADK agent output saved: {filepath}")
        return filepath
        
    except Exception as e:
        print(f"❌ Error saving ADK agent output: {e}")
        return None

async def test_adk_data_agent(use_context_memory: bool = False):
    print("🏒 Testing ADK Data Agent - Using Google ADK Agent...")
    print("=" * 70)
    
    # Test with game that has multiple timestamps
    game_id = "2024030412"
    
    print(f"\n🎯 Processing Game: {game_id}")
    print(f"🧠 Context Memory: {'ENABLED' if use_context_memory else 'DISABLED'}")
    print("-" * 50)
    
    # Create ADK agent instance
    print("🤖 Creating ADK agent instance...")
    try:
        agent = create_hockey_agent_for_game(game_id)
        print("✅ ADK agent created successfully")
    except Exception as e:
        print(f"❌ Failed to create ADK agent: {e}")
        return
    
    # Get all timestamp files for this game
    data_dir = f"data/live/{game_id}"
    pattern = f"{data_dir}/{game_id}_*.json"
    timestamp_files = sorted(glob.glob(pattern))
    
    if not timestamp_files:
        print(f"❌ No timestamp files found for game {game_id}")
        return
    
    print(f"\n📁 Found {len(timestamp_files)} timestamp files")
    print("🔄 Processing each timestamp with ADK Agent...")
    
    processed_count = 0
    
    # Context memory variables
    runner = None
    session = None
    previous_outputs = []
    
    for timestamp_file in timestamp_files:
        file_basename = os.path.basename(timestamp_file)
        print(f"\n⏰ Processing: {file_basename}")
        
        # Extract game time from filename
        game_time = file_basename.replace(f"{game_id}_", "").replace(".json", "")
        
        # Process this timestamp using ADK agent
        if use_context_memory:
            result = await process_timestamp_with_memory(agent, timestamp_file, game_id, runner, session, previous_outputs)
            if result.get("runner"):
                runner = result["runner"]
                session = result["session"]
                previous_outputs.append(result.get("output", {}))
                result = result.get("output", {})
        else:
            result = await process_single_timestamp_with_adk_agent(agent, timestamp_file, game_id)
        
        if result.get("error"):
            print(f"❌ {result['error']}")
            continue
        
        # Save the output
        save_adk_output(result, game_id, game_time)
        
        # Extract key metrics for summary
        for_commentary = result.get("for_commentary_agent", {})
        recommendation = for_commentary.get("recommendation", "UNKNOWN")
        momentum_score = for_commentary.get("momentum_score", 0)
        priority = for_commentary.get("priority_level", 3)
        
        print(f"✅ Score={momentum_score}, Rec={recommendation[:6]}..., Priority={priority}")
        processed_count += 1
    
    print(f"\n🎉 ADK PROCESSING COMPLETE!")
    print(f"📊 Successfully processed {processed_count}/{len(timestamp_files)} timestamps")
    print(f"📁 Outputs saved in: data/data_agent_outputs/")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_adk_data_agent())