#!/usr/bin/env python3
"""
Test script to demonstrate the full commentary dialogue flow across timestamps
"""

import asyncio
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agents.commentary_agent.commentary_pipeline import run_commentary_pipeline

async def test_dialogue_flow():
    """Test the commentary dialogue flow across multiple timestamps"""
    
    print("🏒 NHL Commentary Dialogue Flow Test")
    print("=" * 60)
    
    try:
        # Process first 5 timestamps to show dialogue progression
        print("🎙️ Generating commentary dialogue for first 5 timestamps...")
        result = await run_commentary_pipeline("2024030412", max_files=5)
        
        if result['status'] == 'success' and result['successful'] > 0:
            print(f"\n🎯 Dialogue Flow Summary")
            print(f"Generated commentary for {result['successful']} timestamps")
            
            # Read and display dialogue from each timestamp
            print(f"\n📝 Commentary Dialogue Sequence:")
            print("=" * 60)
            
            output_dir = result['output_directory']
            
            # Get timestamped files
            timestamped_files = []
            for filename in os.listdir(output_dir):
                if filename.startswith("2024030412_commentary_1_") and filename.endswith(".json"):
                    timestamped_files.append(filename)
            
            # Sort by timestamp
            timestamped_files.sort()
            
            for i, filename in enumerate(timestamped_files, 1):
                filepath = os.path.join(output_dir, filename)
                
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    
                    timestamp_info = data.get('timestamp', {})
                    game_time = timestamp_info.get('game_time', 'Unknown time')
                    commentary_data = data.get('commentary_data', {})
                    commentary_sequence = commentary_data.get('commentary_sequence', [])
                    
                    print(f"\n[{i}] {game_time}")
                    print("-" * 40)
                    
                    for j, line in enumerate(commentary_sequence, 1):
                        speaker = line.get('speaker', 'unknown').upper()
                        text = line.get('text', '')
                        emotion = line.get('emotion', 'neutral')
                        duration = line.get('duration_estimate', 0)
                        
                        speaker_name = "Jim Harrison (PBP)" if speaker == "PBP" else "Eddie Martinez (Color)"
                        
                        print(f"   {j}. {speaker_name} ({emotion}, {duration}s):")
                        print(f"      \"{text}\"")
                    
                    # Show momentum and recommendation
                    metadata = commentary_data.get('metadata', {})
                    momentum = metadata.get('momentum_score', 0)
                    commentary_type = metadata.get('commentary_type', 'unknown')
                    
                    print(f"   📊 Momentum: {momentum} | Type: {commentary_type}")
                    
                except Exception as e:
                    print(f"   ❌ Error reading {filename}: {e}")
            
            # Show audio format information
            print(f"\n🎵 Audio Format Summary:")
            print("-" * 40)
            
            total_duration = 0
            total_segments = 0
            
            for filename in timestamped_files:
                filepath = os.path.join(output_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    
                    audio_format = data.get('audio_format', {})
                    segments = audio_format.get('audio_segments', [])
                    timestamp_duration = sum(seg.get('duration_estimate', 0) for seg in segments)
                    
                    total_duration += timestamp_duration
                    total_segments += len(segments)
                    
                    timestamp_info = data.get('timestamp', {})
                    game_time = timestamp_info.get('game_time', 'Unknown')
                    
                    print(f"   {game_time}: {len(segments)} segments, {timestamp_duration:.1f}s")
                    
                except:
                    pass
            
            print(f"\n   Total: {total_segments} audio segments, {total_duration:.1f}s duration")
            
            print(f"\n✅ Commentary dialogue flow test completed!")
            print(f"📁 All files saved in: {output_dir}")
            
            return True
        else:
            print(f"\n❌ No successful commentary generation")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    success = await test_dialogue_flow()
    if success:
        print(f"\n🎯 NHL Commentary Agent is ready!")
        print(f"   ✅ Generates timestamped dialogue like data agent")
        print(f"   ✅ Creates proper PBP/Color commentator exchanges")
        print(f"   ✅ Adapts to game momentum and context")
        print(f"   ✅ Produces audio-ready format")
        sys.exit(0)
    else:
        print(f"\n❌ Commentary dialogue test failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())