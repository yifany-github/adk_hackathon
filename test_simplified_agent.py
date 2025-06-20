#!/usr/bin/env python3
"""
Test simplified Sequential Agent
"""
import asyncio
import json
import sys
import os

# Add src to path
sys.path.append('src')

from agents.sequential_agent_v2.agent import create_nhl_sequential_agent
from board import create_live_game_board

async def test_simplified_agent():
    """Test the simplified sequential agent"""
    game_id = "2024020001"
    
    # Find test file
    test_file = f"data/live/{game_id}/2024020001_1_00_00.json"
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return
    
    print(f"🧪 Testing simplified Sequential Agent with: {test_file}")
    
    # Create game board  
    game_board = create_live_game_board(game_id)
    
    # Load test data and update board
    with open(test_file, 'r') as f:
        timestamp_data = json.load(f)
    
    board_update = game_board.update_from_timestamp(timestamp_data)
    board_context = game_board.get_state()
    
    print(f"📋 Board context keys: {list(board_context.keys())}")
    score = board_context.get('current_score', board_context.get('score', 'Unknown'))
    print(f"📋 Board context: Score {score}")
    
    # Create and test agent
    agent = create_nhl_sequential_agent(game_id)
    await agent.initialize()
    
    print("⚡ Processing timestamp with simplified prompt...")
    start_time = asyncio.get_event_loop().time()
    
    result = await agent.process_timestamp_stateless(
        test_file,
        board_context,
        None  # No continuity context for test
    )
    
    end_time = asyncio.get_event_loop().time()
    processing_time = end_time - start_time
    
    print(f"✅ Processing completed in {processing_time:.2f}s")
    print(f"📊 Status: {result['status']}")
    
    if result['status'] == 'success':
        print(f"📄 Output file: {result['output_file']}")
        
        # Show sample commentary
        if 'clean_result' in result and 'commentary_agent' in result['clean_result']:
            commentary = result['clean_result']['commentary_agent']
            if 'commentary_sequence' in commentary:
                print("\n🎙️ Sample Commentary:")
                for i, exchange in enumerate(commentary['commentary_sequence'][:2]):
                    speaker = exchange.get('speaker', 'Unknown')
                    text = exchange.get('text', '')[:100] + "..."
                    print(f"   {speaker}: {text}")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(test_simplified_agent())