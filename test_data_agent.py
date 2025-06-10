#!/usr/bin/env python3
"""
Test script for LIVE data agent - processes each timestamp individually
"""
import sys
import os
import json
import glob
from datetime import datetime
sys.path.append('src/agents/data_agent')

from tools import load_static_context
from data_agent import DataAgent

async def process_single_timestamp_with_agent(agent: DataAgent, timestamp_file: str):
    """Process a single timestamp using the real DataAgent class"""
    try:
        # Load the timestamp data
        with open(timestamp_file, 'r') as f:
            timestamp_data = json.load(f)
        
        # Create a mock invocation context with the timestamp data
        class MockInvocationContext:
            def __init__(self, data):
                self.user_content = MockUserContent(data)
                self.session_state = MockSessionState()
        
        class MockUserContent:
            def __init__(self, data):
                self.data = data
            
            def to_dict(self):
                return self.data
        
        class MockSessionState:
            def __init__(self):
                self.game_id = "2024030412"
        
        # Process through the real agent
        ctx = MockInvocationContext(timestamp_data)
        
        # Run the agent and collect the output
        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)
        
        # Extract the result from the event
        if events:
            result = events[0].actions.state_delta.get("broadcast", {})
            return result
        else:
            return {"error": "No output from agent"}
        
    except Exception as e:
        return {"error": f"Failed to process {timestamp_file}: {str(e)}"}

# File saving is now handled by the production DataAgent - no duplicate saving needed

async def test_data_agent_tools():
    print("🏒 Testing LIVE Data Agent - Using Real DataAgent Class...")
    print("=" * 70)
    
    # Test with game that has multiple timestamps
    game_id = "2024030412"
    
    print(f"\n🎯 Processing Game: {game_id}")
    print("-" * 50)
    
    # Create real DataAgent instance
    print("🤖 Creating DataAgent instance...")
    agent = DataAgent()
    print("✅ DataAgent created successfully")
    
    # Get all timestamp files for this game
    data_dir = f"data/live/{game_id}"
    pattern = f"{data_dir}/{game_id}_*.json"
    timestamp_files = sorted(glob.glob(pattern))
    
    if not timestamp_files:
        print(f"❌ No timestamp files found for game {game_id}")
        return
    
    print(f"\n📁 Found {len(timestamp_files)} timestamp files")
    print("🔄 Processing each timestamp with REAL DataAgent...")
    
    processed_count = 0
    
    for timestamp_file in timestamp_files:
        file_basename = os.path.basename(timestamp_file)
        print(f"\n⏰ Processing: {file_basename}")
        
        # Process this timestamp using real agent
        result = await process_single_timestamp_with_agent(agent, timestamp_file)
        
        if result.get("error"):
            print(f"❌ {result['error']}")
            continue
        
        # DataAgent handles file saving automatically - just validate the output
        new_events = result.get('new_events_found', 0)
        total_events = result.get('total_events_in_timestamp', 0)
        game_time = result.get("game_time", "unknown")
        expected_filename = f"{game_id}_{game_time.replace(':', '_')}_data_agent.json"
        
        print(f"✅ NEW: {new_events}/{total_events} events, Score={result['momentum_score']}, Rec={result['recommendation'][:6]}...")
        print(f"💾 Agent saved: {expected_filename}")
        processed_count += 1
    
    print(f"\n🎉 LIVE PROCESSING COMPLETE!")
    print(f"📊 Successfully processed {processed_count}/{len(timestamp_files)} timestamps")
    print(f"📁 Outputs saved in: data/data_agent_outputs/")

import asyncio

if __name__ == "__main__":
    asyncio.run(test_data_agent_tools())