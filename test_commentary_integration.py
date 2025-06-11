#!/usr/bin/env python3
"""
Integration test for Commentary Agent with other agents
"""

import asyncio
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_commentary_integration():
    """Test commentary agent integration with other components"""
    
    print("🏒 NHL Commentary Agent Integration Test")
    print("=" * 50)
    
    try:
        # Test 1: Import all agents
        print("\n✅ Test 1: Importing all agents...")
        
        from src.agents.commentary_agent.commentary_agent import get_commentary_agent
        from src.agents.commentary_agent.tools import COMMENTARY_TOOLS
        from src.agents.commentary_agent.prompts import COMMENTARY_AGENT_PROMPT
        
        print(f"   Commentary agent: ✅")
        print(f"   Commentary tools: {len(COMMENTARY_TOOLS)} tools")
        print(f"   Commentary prompts: ✅")
        
        # Test 2: Create agents for multiple games
        print(f"\n✅ Test 2: Creating agents for multiple games...")
        
        game_ids = ["2024030412", "2024030413", "2024030414"]
        agents = {}
        
        for game_id in game_ids:
            agents[game_id] = get_commentary_agent(game_id)
            print(f"   Game {game_id}: {agents[game_id].name}")
        
        # Test 3: Test tools with different scenarios
        print(f"\n✅ Test 3: Testing different commentary scenarios...")
        
        scenarios = [
            {
                "name": "High Intensity Goal",
                "data": {
                    "for_commentary_agent": {
                        "recommendation": "HIGH_INTENSITY",
                        "priority_level": 5,
                        "momentum_score": 85,
                        "key_talking_points": [
                            "McDavid scores his first goal of the night!",
                            "What a shot from the slot!"
                        ],
                        "game_context": {
                            "period": 2,
                            "time_remaining": "10:45",
                            "home_score": 2,
                            "away_score": 1,
                            "game_situation": "even strength"
                        },
                        "high_intensity_events": [
                            {
                                "summary": "Goal by McDavid assisted by Draisaitl",
                                "impact_score": 90,
                                "event_type": "goal"
                            }
                        ]
                    }
                }
            },
            {
                "name": "Filler Content",
                "data": {
                    "for_commentary_agent": {
                        "recommendation": "FILLER_CONTENT",
                        "priority_level": 1,
                        "momentum_score": 20,
                        "key_talking_points": [
                            "Both teams looking to establish their rhythm",
                            "It's been a back-and-forth battle so far"
                        ],
                        "game_context": {
                            "period": 1,
                            "time_remaining": "18:30",
                            "home_score": 0,
                            "away_score": 0,
                            "game_situation": "even strength"
                        },
                        "high_intensity_events": []
                    }
                }
            }
        ]
        
        from src.agents.commentary_agent.tools import (
            generate_two_person_commentary,
            analyze_commentary_context
        )
        
        class MockSession:
            def __init__(self, data, static_context):
                self.state = {
                    "current_data_agent_output": data,
                    "static_context": static_context
                }
        
        class MockContext:
            def __init__(self, data, static_context):
                self.session = MockSession(data, static_context)
        
        for scenario in scenarios:
            print(f"\n   🎯 Scenario: {scenario['name']}")
            
            # Use first agent's static context
            static_context = agents[game_ids[0]].static_context
            mock_context = MockContext(scenario['data'], static_context)
            
            # Test context analysis
            analysis = analyze_commentary_context(mock_context)
            print(f"      Analysis: {analysis.get('status', 'unknown')}")
            
            if analysis.get('status') == 'success':
                strategy = analysis.get('commentary_strategy', {})
                recommended_type = strategy.get('recommended_type', 'unknown')
                pbp_ratio = strategy.get('pbp_speaking_ratio', 0)
                
                print(f"      Recommended type: {recommended_type}")
                print(f"      PBP speaking ratio: {pbp_ratio:.1%}")
                
                # Test commentary generation
                commentary = generate_two_person_commentary(
                    mock_context, 
                    recommended_type
                )
                
                if commentary.get('status') == 'success':
                    lines = commentary.get('commentary_sequence', [])
                    total_duration = commentary.get('metadata', {}).get('total_duration', 0)
                    
                    print(f"      Generated {len(lines)} lines ({total_duration:.1f}s)")
                    
                    # Show first line
                    if lines:
                        first_line = lines[0]
                        speaker = first_line.get('speaker', 'unknown')
                        text = first_line.get('text', '')[:60]
                        print(f"      Sample: [{speaker.upper()}] {text}...")
        
        # Test 4: Performance and memory
        print(f"\n✅ Test 4: Performance check...")
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"   Memory usage: {memory_usage:.1f} MB")
        print(f"   Agents created: {len(agents)}")
        print(f"   Tools available: {len(COMMENTARY_TOOLS)}")
        
        print(f"\n🎯 Integration Test Completed Successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    success = await test_commentary_integration()
    if success:
        print("\n✅ All integration tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Integration tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())