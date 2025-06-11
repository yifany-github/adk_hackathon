#!/usr/bin/env python3
"""
Test script for the simplified ADK Commentary Agent
"""

import asyncio
import json
import sys
import os
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agents.commentary_agent.commentary_agent import create_commentary_agent_for_game


async def test_commentary_agent_simple():
    """Test the simplified commentary agent with sample data"""
    
    print("🏒 Testing Simplified NHL Commentary Agent")
    print("=" * 50)
    
    # Sample data agent output
    sample_data = {
        "for_commentary_agent": {
            "recommendation": "MIXED_COVERAGE",
            "priority_level": 2,
            "momentum_score": 45,
            "key_talking_points": [
                "McDavid has been quiet early, looking for his first point of the night",
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
    
    # Test game ID
    test_game_id = "2024030412"
    
    try:
        # Create simplified commentary agent
        print(f"Creating commentary agent for game: {test_game_id}")
        agent = create_commentary_agent_for_game(test_game_id)
        
        print(f"✅ Agent created: {agent.name}")
        print(f"Model: {agent.model}")
        print(f"Tools: {len(agent.tools)}")
        
        # Test the agent by running it with sample data using ADK pattern
        print("\n🎯 Testing agent with sample data...")
        
        # Use InMemoryRunner like data agent
        from google.adk.runners import InMemoryRunner
        from google.genai.types import Part, UserContent
        
        runner = InMemoryRunner(agent=agent)
        session = await runner.session_service.create_session(
            app_name=runner.app_name, user_id="test_user"
        )
        
        # Format input for commentary agent
        input_text = f"Generate commentary for NHL game {test_game_id}: {json.dumps(sample_data, indent=2)}"
        content = UserContent(parts=[Part(text=input_text)])
        
        response_text = ""
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.content.parts and event.content.parts[0].text:
                response_text = event.content.parts[0].text
        
        print("✅ Agent execution completed!")
        
        # Parse the result
        if response_text:
            try:
                parsed_result = json.loads(response_text)
                print(f"✅ Generated commentary: {parsed_result.get('status', 'unknown')}")
                
                # Show commentary data if available
                commentary_data = parsed_result.get('commentary_data', {})
                if commentary_data:
                    commentary_sequence = commentary_data.get('commentary_sequence', [])
                    print(f"📝 Commentary lines: {len(commentary_sequence)}")
                    
                    # Show first line of commentary
                    if commentary_sequence:
                        first_line = commentary_sequence[0]
                        print(f"🎙️ First line ({first_line.get('speaker', 'unknown')}): {first_line.get('text', 'N/A')}")
                
            except json.JSONDecodeError:
                print(f"⚠️ Could not parse result as JSON: {response_text[:200]}...")
        else:
            print("⚠️ No response text from agent")
            
    except Exception as e:
        print(f"❌ Error testing commentary agent: {e}")
        import traceback
        traceback.print_exc()


def test_agent_creation_only():
    """Test just creating the agent without running it"""
    
    print("\n🔧 Testing Agent Creation Only")
    print("-" * 30)
    
    test_game_id = "2024030412"
    
    try:
        # Create agent
        agent = create_commentary_agent_for_game(test_game_id)
        
        print(f"✅ Agent Name: {agent.name}")
        print(f"✅ Model: {agent.model}")
        print(f"✅ Instruction Length: {len(agent.instruction)} chars")
        print(f"✅ Tools Count: {len(agent.tools)}")
        
        # List tool names
        tool_names = [tool.__name__ for tool in agent.tools]
        print(f"✅ Tool Names: {', '.join(tool_names)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating agent: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🏒 Simplified Commentary Agent Test Suite")
    print("=" * 60)
    
    # Test 1: Agent creation
    creation_success = test_agent_creation_only()
    
    if creation_success:
        # Test 2: Full agent run (only if creation worked)
        asyncio.run(test_commentary_agent_simple())
    else:
        print("❌ Skipping full test due to creation failure")
    
    print("\n✅ Test completed!")