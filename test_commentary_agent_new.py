#!/usr/bin/env python3
"""
Test script for the new ADK-based Commentary Agent implementation
"""

import asyncio
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agents.commentary_agent.commentary_agent import (
    create_commentary_agent_for_game,
    generate_game_commentary,
    get_commentary_agent
)

async def test_commentary_agent():
    """Test the commentary agent with sample data"""
    
    print("🏒 Testing NHL Commentary Agent (ADK Implementation)")
    print("=" * 60)
    
    # Sample data agent output
    sample_data = {
        "for_commentary_agent": {
            "recommendation": "MIXED_COVERAGE",
            "priority_level": 2,
            "momentum_score": 45,
            "key_talking_points": [
                "McDavid has been quiet early, looking for his first point of the night",
                "Florida's power play is clicking at 28% this series",
                "Both goalies have been spectacular so far"
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
    
    test_game_id = "2024030412"
    
    try:
        # Test 1: Create commentary agent
        print(f"\n✅ Test 1: Creating commentary agent for game {test_game_id}")
        agent = get_commentary_agent(test_game_id)
        print(f"   Agent name: {agent.name}")
        print(f"   Game ID: {agent.game_id}")
        print(f"   Model: {agent.model}")
        
        # Test 2: Validate agent structure
        print(f"\n✅ Test 2: Validating agent structure...")
        
        # Test internal LLM agent
        llm_agent = agent.get_agent()
        print(f"   Internal LLM Agent: {llm_agent.name}")
        print(f"   Available tools: {len(llm_agent.tools) if hasattr(llm_agent, 'tools') else 'N/A'}")
        
        # Test static context loading
        static_context = agent.static_context
        game_info = static_context.get('game_info', {})
        print(f"   Static context loaded: {bool(static_context)}")
        print(f"   Game info: {game_info}")
        
        # Test 3: Test full commentary generation
        print(f"\n✅ Test 3: Testing commentary generation...")
        
        try:
            result = await generate_game_commentary(test_game_id, sample_data)
            print(f"   Generation status: {result['status']}")
            
            if result['status'] == 'success':
                commentary_data = result.get('commentary_data', {})
                audio_format = result.get('audio_format', {})
                analysis = result.get('analysis', {})
                
                # Show commentary details
                lines = commentary_data.get('commentary_sequence', [])
                print(f"   Generated {len(lines)} commentary lines")
                
                if lines:
                    sample_line = lines[0]
                    speaker = sample_line.get('speaker', 'unknown')
                    text = sample_line.get('text', '')[:60]
                    print(f"   Sample: [{speaker.upper()}] {text}...")
                
                # Show audio format details
                segments = audio_format.get('audio_segments', [])
                print(f"   Generated {len(segments)} audio segments")
                
                # Show analysis details
                if analysis.get('status') == 'success':
                    strategy = analysis.get('commentary_strategy', {})
                    recommended_type = strategy.get('recommended_type', 'unknown')
                    print(f"   Recommended type: {recommended_type}")
                
                return True
            else:
                print(f"   Error: {result.get('error', 'Unknown error')}")
                return False
            
        except Exception as e:
            print(f"   Generation test error: {e}")
            return False
            
        print(f"\n🎯 Commentary Agent Test Completed")
        return True  # All structure tests passed
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    success = await test_commentary_agent()
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())