#!/usr/bin/env python3
"""
Test script for audio agent using commentary file
"""
import asyncio
import json
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.agents.audio_agent.audio_agent import AudioAgent

async def test_audio_agent_with_commentary():
    """Test audio agent with commentary file data"""
    
    # Read the commentary file
    commentary_file = "/Users/yifan/Downloads/google_hackathon/adk_hackathon/data/commentary_agent_outputs/2024030412_1_00_00_commentary_session_aware.json"
    
    try:
        with open(commentary_file, 'r') as f:
            commentary_data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to read commentary file: {e}")
        return
    
    print("📄 Commentary file loaded successfully")
    print(f"🎯 Commentary type: {commentary_data.get('commentary_data', {}).get('commentary_type', 'unknown')}")
    
    # Extract commentary sequence
    commentary_sequence = commentary_data.get('for_audio_agent', {}).get('commentary_sequence', [])
    
    if not commentary_sequence:
        print("❌ No commentary sequence found in file")
        return
    
    print(f"🎭 Found {len(commentary_sequence)} commentary items")
    
    # Create audio agent
    audio_agent = AudioAgent()
    
    # Test each commentary item
    for i, commentary_item in enumerate(commentary_sequence):
        speaker = commentary_item.get('speaker', 'Unknown')
        text = commentary_item.get('text', '')
        emotion = commentary_item.get('emotion', 'neutral')
        
        print(f"\n🎙️ Testing item {i+1}/{len(commentary_sequence)}")
        print(f"   Speaker: {speaker}")
        print(f"   Text: {text[:60]}...")
        print(f"   Emotion: {emotion}")
        
        # Map emotion to voice style
        voice_style_map = {
            'excited': 'enthusiastic',
            'analytical': 'calm',
            'dramatic': 'dramatic'
        }
        voice_style = voice_style_map.get(emotion, 'enthusiastic')
        print(f"   Voice style: {voice_style}")
        
        try:
            # Process commentary text
            result = await audio_agent.process_commentary(
                commentary_text=text,
                voice_style=voice_style,
                auto_start_server=True
            )
            
            if result.get('status') == 'success':
                print(f"   ✅ Success: {result.get('message', 'Audio processed')}")
                audio_info = result.get('audio_processing', {})
                if audio_info.get('audio_id'):
                    print(f"   🎵 Audio ID: {audio_info['audio_id']}")
            else:
                print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
        
        # Small delay between items
        await asyncio.sleep(1)
    
    print(f"\n🏆 Audio Agent Test Complete")
    print(f"📊 Processed {len(commentary_sequence)} commentary items")
    
    # Get final status
    try:
        from src.agents.audio_agent.tool import get_audio_status
        status = get_audio_status()
        print(f"📈 Final status: {json.dumps(status, indent=2)}")
    except Exception as e:
        print(f"⚠️ Could not get final status: {e}")

if __name__ == "__main__":
    print("🚀 Starting Audio Agent Test with Commentary File")
    print("=" * 60)
    
    try:
        asyncio.run(test_audio_agent_with_commentary())
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()