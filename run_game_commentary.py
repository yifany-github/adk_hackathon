#!/usr/bin/env python3
"""
NHL Game Commentary Runner
Process existing timestamp files with the proven hybrid approach

Usage: python run_game_commentary.py GAME_ID [MAX_FILES]
"""

import asyncio
import sys
import os
import json
import glob
import base64
import wave
from datetime import datetime
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Add src to path
sys.path.append('src')

async def run_game_commentary(game_id: str, max_files: int = 5):
    """Run NHL game commentary on existing timestamp files"""
    
    print("🏒 NHL GAME COMMENTARY RUNNER")
    print("=" * 50)
    print(f"🎯 Game: {game_id}")
    print(f"📁 Max files: {max_files}")
    print("-" * 50)
    
    try:
        # Get timestamp files
        timestamp_files = sorted(glob.glob(f"data/live/{game_id}/*.json"))[:max_files]
        
        if not timestamp_files:
            print(f"❌ No timestamp files found for game {game_id}")
            return False
        
        print(f"📄 Processing {len(timestamp_files)} timestamp files...")
        
        # Setup agents and tools
        from src.agents.data_agent.data_agent_adk import create_hockey_agent_for_game
        from src.agents.commentary_agent.commentary_agent import create_commentary_agent_for_game
        from src.agents.audio_agent.tool import text_to_speech
        from google.adk.runners import InMemoryRunner
        from google.genai.types import Part, UserContent
        
        # Create agents
        print("\n🤖 Setting up agents...")
        data_agent = create_hockey_agent_for_game(game_id)
        data_runner = InMemoryRunner(agent=data_agent)
        data_session = await data_runner.session_service.create_session(
            app_name=data_runner.app_name, user_id=f"game_data_{game_id}"
        )
        
        commentary_agent = create_commentary_agent_for_game(game_id)
        commentary_runner = InMemoryRunner(agent=commentary_agent)
        commentary_session = await commentary_runner.session_service.create_session(
            app_name=commentary_runner.app_name, user_id=f"game_commentary_{game_id}"
        )
        
        print("✅ Agents ready")
        
        # Audio setup
        audio_output_dir = f"audio_output/{game_id}"
        os.makedirs(audio_output_dir, exist_ok=True)
        
        total_audio_files = 0
        
        # Process each timestamp
        for i, timestamp_file in enumerate(timestamp_files):
            timestamp_name = os.path.basename(timestamp_file).replace('.json', '')
            print(f"\n🎬 Processing {i+1}/{len(timestamp_files)}: {timestamp_name}")
            
            # Load data
            with open(timestamp_file, 'r') as f:
                timestamp_data = json.load(f)
            
            # Data Agent
            print(f"  📊 Data analysis...")
            data_input = UserContent(parts=[Part(text=f"Analyze hockey data: {json.dumps(timestamp_data)}")])
            
            data_result = ""
            async for event in data_runner.run_async(
                user_id=data_session.user_id,
                session_id=data_session.id,
                new_message=data_input,
            ):
                if hasattr(event, 'content') and event.content and event.content.parts:
                    data_result = event.content.parts[0].text
                    break
            
            if not data_result:
                print(f"  ❌ Data Agent failed")
                continue
            
            print(f"  ✅ Data analysis complete ({len(data_result)} chars)")
            
            # Commentary Agent
            print(f"  🎙️ Commentary generation...")
            commentary_input = UserContent(parts=[Part(text=f"Generate NHL commentary: {data_result}")])
            
            commentary_result = ""
            async for event in commentary_runner.run_async(
                user_id=commentary_session.user_id,
                session_id=commentary_session.id,
                new_message=commentary_input,
            ):
                if hasattr(event, 'content') and event.content and event.content.parts:
                    commentary_result = event.content.parts[0].text
                    break
            
            if not commentary_result:
                print(f"  ❌ Commentary Agent failed")
                continue
            
            print(f"  ✅ Commentary complete ({len(commentary_result)} chars)")
            
            # Parse commentary
            try:
                if "```json" in commentary_result:
                    json_start = commentary_result.find("```json") + 7
                    json_end = commentary_result.find("```", json_start)
                    commentary_result = commentary_result[json_start:json_end].strip()
                
                commentary_data = json.loads(commentary_result)
                commentary_sequence = commentary_data.get('commentary_sequence', [])
            except:
                print(f"  ⚠️  Using fallback commentary")
                commentary_sequence = [{"speaker": "Commentator", "text": commentary_result[:200]}]
            
            # Audio Generation (Your Direct Approach)
            print(f"  🔊 Audio generation...")
            file_count = 0
            
            for j, segment in enumerate(commentary_sequence[:3]):  # Limit to 3 segments
                text = segment.get('text', '')
                if not text:
                    continue
                
                speaker = segment.get('speaker', f'Speaker_{j}')
                print(f"    🗣️  {speaker}: {text[:40]}...")
                
                # Voice style
                voice_style = "enthusiastic"
                if any(word in text.lower() for word in ['penalty', 'crucial']):
                    voice_style = "dramatic"
                
                # TTS
                tts_result = await text_to_speech(
                    tool_context=None,
                    text=text,
                    voice_style=voice_style,
                    language="en-US"
                )
                
                if tts_result["status"] == "success" and "audio_data" in tts_result:
                    # Save audio
                    audio_bytes = base64.b64decode(tts_result["audio_data"])
                    time_str = datetime.now().strftime("%H%M%S")
                    filename = f"{timestamp_name}_{j:02d}_{voice_style}_{time_str}.wav"
                    filepath = os.path.join(audio_output_dir, filename)
                    
                    with wave.open(filepath, 'wb') as wav_file:
                        wav_file.setnchannels(1)
                        wav_file.setsampwidth(2)
                        wav_file.setframerate(24000)
                        wav_file.writeframes(audio_bytes)
                    
                    file_size = os.path.getsize(filepath)
                    print(f"    💾 {filename} ({file_size:,} bytes)")
                    file_count += 1
                    total_audio_files += 1
            
            print(f"  ✅ Generated {file_count} audio files for this timestamp")
            
            # Small pause between timestamps
            await asyncio.sleep(1)
        
        print(f"\n🎉 GAME COMMENTARY COMPLETE!")
        print(f"📊 Processed: {len(timestamp_files)} timestamps")
        print(f"🎵 Generated: {total_audio_files} audio files")
        print(f"📁 Audio location: audio_output/{game_id}/")
        
        return total_audio_files > 0
        
    except Exception as e:
        print(f"❌ Game commentary failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_game_commentary.py GAME_ID [MAX_FILES]")
        print("Example: python run_game_commentary.py 2024030412 3")
        sys.exit(1)
    
    game_id = sys.argv[1]
    max_files = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    success = asyncio.run(run_game_commentary(game_id, max_files))
    
    if success:
        print(f"\n✅ NHL Game Commentary completed successfully!")
        print(f"🎵 Play your audio files from audio_output/{game_id}/")
    else:
        print(f"\n❌ NHL Game Commentary failed!")

if __name__ == "__main__":
    main()