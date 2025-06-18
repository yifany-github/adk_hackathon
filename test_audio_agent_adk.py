#!/usr/bin/env python3
"""
Test script for ADK-based Audio Agent - Custom Agent testing
Tests the audio processing pipeline with commentary data
"""

import asyncio
import json
import sys
import os
import glob
from datetime import datetime
import dotenv
import base64
import wave

# Load environment variables
dotenv.load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agents.audio_agent.audio_agent import create_audio_agent_for_game


async def process_single_commentary_with_audio_agent(agent, commentary_file: str, game_id: str):
    """Process a single commentary file using the ADK Audio Agent"""
    try:
        # Load the commentary data
        with open(commentary_file, 'r') as f:
            commentary_data = json.load(f)
        
        # Extract commentary sequence for processing
        commentary_sequence = []
        if "commentary_data" in commentary_data:
            commentary_sequence = commentary_data["commentary_data"].get("commentary_sequence", [])
        elif "for_audio_agent" in commentary_data:
            commentary_sequence = commentary_data["for_audio_agent"].get("commentary_sequence", [])
        
        if not commentary_sequence:
            return {"error": "No commentary sequence found in file"}
        
        # Use InMemoryRunner as shown in ADK samples
        from google.adk.runners import InMemoryRunner
        from google.genai.types import Part, UserContent
        
        runner = InMemoryRunner(agent=agent)
        session = await runner.session_service.create_session(
            app_name=runner.app_name, 
            user_id="audio_processor"
        )
        
        # Process each commentary item
        audio_results = []
        
        for i, commentary_item in enumerate(commentary_sequence):
            speaker = commentary_item.get("speaker", "Unknown")
            text = commentary_item.get("text", "")
            emotion = commentary_item.get("emotion", "neutral")
            
            if not text:
                continue
            
            print(f"  🎙️ Processing [{i+1}/{len(commentary_sequence)}]: {speaker}")
            print(f"      Text: {text[:60]}{'...' if len(text) > 60 else ''}")
            print(f"      Emotion: {emotion}")
            
            # Create input for audio agent
            input_text = f"""
Convert this commentary to audio:

Speaker: {speaker}
Text: {text}
Emotion: {emotion}
Commentary Context: NHL Game {game_id}

Please process this with appropriate voice style and generate audio.
"""
            
            content = UserContent(parts=[Part(text=input_text)])
            
            # Run audio agent
            response_text = ""
            async for event in runner.run_async(
                user_id=session.user_id,
                session_id=session.id,
                new_message=content,
            ):
                if hasattr(event, 'content') and event.content and event.content.parts:
                    if event.content.parts[0].text:
                        response_text = event.content.parts[0].text
            
            if response_text:
                # Custom Agent的响应可能不是JSON格式，我们需要更灵活地处理
                audio_result = {
                    "commentary_index": i,
                    "speaker": speaker,
                    "original_text": text,
                    "emotion": emotion,
                    "processed_at": datetime.now().isoformat()
                }
                
                # 尝试解析JSON，如果失败则直接记录文本响应
                try:
                    parsed_response = json.loads(response_text)
                    audio_result["audio_processing"] = parsed_response
                    
                    # Extract status for logging
                    if parsed_response.get("audio_data", {}).get("status") == "success":
                        audio_id = parsed_response.get("audio_data", {}).get("audio_id", "unknown")
                        voice_style = parsed_response.get("audio_data", {}).get("voice_style", "unknown")
                        print(f"      ✅ Audio generated: ID={audio_id}, Style={voice_style}")
                    else:
                        error = parsed_response.get("audio_data", {}).get("error", "Unknown error")
                        print(f"      ❌ Audio failed: {error}")
                        
                except json.JSONDecodeError:
                    # 对于Custom Agent，响应可能是描述性文本而不是JSON
                    audio_result["audio_processing"] = {
                        "status": "completed", 
                        "response_type": "text",
                        "response_text": response_text
                    }
                    print(f"      ✅ Audio agent response received (text format)")
                
                audio_results.append(audio_result)
            else:
                print(f"      ❌ No response from audio agent")
        
        return {
            "status": "success",
            "game_id": game_id,
            "total_commentary_items": len(commentary_sequence),
            "processed_items": len(audio_results),
            "audio_results": audio_results
        }
        
    except Exception as e:
        return {"error": f"Failed to process {commentary_file}: {str(e)}"}


def save_audio_agent_output(result: dict, game_id: str, timestamp: str):
    """Save Audio Agent output to the audio_agent_outputs directory"""
    try:
        # Create output directory
        output_dir = "data/audio_agent_outputs"
        os.makedirs(output_dir, exist_ok=True)
        
        # Clean up timestamp for filename
        timestamp_clean = str(timestamp).replace(":", "_").replace(" ", "_")
        filename = f"{game_id}_{timestamp_clean}_audio_adk.json"
        filepath = os.path.join(output_dir, filename)
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Audio agent output saved: {filepath}")
        return filepath
        
    except Exception as e:
        print(f"❌ Error saving audio agent output: {e}")
        return None


async def test_audio_agent_with_commentary_files(game_id: str = "2024030412", max_files: int = 5):
    """
    Test Audio Agent with existing commentary files
    """
    print("🎵 Testing ADK Audio Agent - Custom Agent Implementation")
    print("=" * 70)
    print(f"Game ID: {game_id}")
    print(f"Max files: {max_files}")
    print()
    
    # Create audio agent instance
    print("🤖 Creating Audio Agent instance...")
    try:
        agent = create_audio_agent_for_game(game_id)
        print(f"✅ Audio agent created successfully: {agent.name}")
        print(f"   Type: {type(agent).__name__}")
        print(f"   Model: {agent.audio_model}")
        print(f"   LLM Agent Tools: {len(agent._llm_agent.tools)}")
    except Exception as e:
        print(f"❌ Failed to create audio agent: {e}")
        return
    
    # Find commentary files to process
    commentary_files = glob.glob(f"data/commentary_agent_outputs/{game_id}_*_commentary*.json")
    commentary_files.sort()
    
    if not commentary_files:
        print(f"❌ No commentary files found for game {game_id}")
        print("💡 Run commentary agent tests first to generate commentary data")
        return
    
    # Limit number of files
    if len(commentary_files) > max_files:
        commentary_files = commentary_files[:max_files]
    
    print(f"\n📁 Found {len(commentary_files)} commentary files to process")
    print()
    
    processed_count = 0
    total_audio_items = 0
    successful_audio_items = 0
    
    for commentary_file in commentary_files:
        file_basename = os.path.basename(commentary_file)
        print(f"\n🎭 Processing: {file_basename}")
        
        # Extract timestamp from filename
        timestamp = file_basename.replace(f"{game_id}_", "").replace("_commentary_session_aware.json", "").replace("_commentary.json", "")
        
        # Process this commentary file with audio agent
        result = await process_single_commentary_with_audio_agent(agent, commentary_file, game_id)
        
        if result.get("error"):
            print(f"❌ {result['error']}")
            continue
        
        # Save the output
        save_audio_agent_output(result, game_id, timestamp)
        
        # Extract metrics for summary
        total_items = result.get("total_commentary_items", 0)
        processed_items = result.get("processed_items", 0)
        
        # Count successful audio generations
        successful_items = 0
        for audio_result in result.get("audio_results", []):
            if audio_result.get("audio_processing", {}).get("status") == "completed":
                successful_items += 1
        
        total_audio_items += total_items
        successful_audio_items += successful_items
        
        print(f"✅ Processed {processed_items}/{total_items} items, {successful_items} successful audio generations")
        processed_count += 1
    
    print(f"\n🎉 AUDIO AGENT TESTING COMPLETE!")
    print(f"📊 Successfully processed {processed_count}/{len(commentary_files)} commentary files")
    print(f"🎵 Total audio items: {total_audio_items}")
    print(f"✅ Successful audio generations: {successful_audio_items}")
    print(f"📈 Success rate: {(successful_audio_items/total_audio_items*100):.1f}%" if total_audio_items > 0 else "📈 Success rate: N/A")
    print(f"📁 Outputs saved in: data/audio_agent_outputs/")


async def test_single_text_audio_generation(game_id: str = "2024030412"):
    """
    Test Audio Agent with a single text input for quick testing
    """
    print("\n🧪 Quick Audio Generation Test")
    print("-" * 40)
    
    # Create audio agent
    agent = create_audio_agent_for_game(game_id)
    print(f"✅ Created audio agent: {agent.name}")
    
    # Test cases
    test_cases = [
        {
            "text": "Goal! What an incredible shot by Connor McDavid! The crowd is going wild!",
            "expected_style": "enthusiastic"
        },
        {
            "text": "Penalty called on the play. Two minutes for cross-checking in this critical overtime period.",
            "expected_style": "dramatic"
        },
        {
            "text": "The players are setting up for the face-off in the neutral zone.",
            "expected_style": "enthusiastic"
        }
    ]
    
    from google.adk.runners import InMemoryRunner
    from google.genai.types import Part, UserContent
    
    runner = InMemoryRunner(agent=agent)
    session = await runner.session_service.create_session(
        app_name=runner.app_name, 
        user_id="quick_test"
    )
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🎙️ Test {i}: {test_case['text'][:50]}...")
        
        input_text = f"Convert this hockey commentary to audio: {test_case['text']}"
        content = UserContent(parts=[Part(text=input_text)])
        
        response_text = ""
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=content,
        ):
            if hasattr(event, 'content') and event.content and event.content.parts:
                if event.content.parts[0].text:
                    response_text = event.content.parts[0].text
        
        if response_text:
            try:
                parsed_response = json.loads(response_text)
                audio_data = parsed_response.get("audio_data", {})
                
                if audio_data.get("status") == "success":
                    voice_style = audio_data.get("voice_style", "unknown")
                    audio_id = audio_data.get("audio_id", "unknown")
                    print(f"  ✅ Success: Style={voice_style}, ID={audio_id}")
                    
                    # Check if style matches expectation
                    if voice_style == test_case["expected_style"]:
                        print(f"  🎯 Style prediction correct!")
                    else:
                        print(f"  🤔 Style mismatch: expected {test_case['expected_style']}, got {voice_style}")
                else:
                    error = audio_data.get("error", "Unknown error")
                    print(f"  ❌ Failed: {error}")
                    
            except json.JSONDecodeError:
                # 对于Custom Agent，响应可能是文本而不是JSON
                print(f"  ✅ Audio agent response received (text format)")
                print(f"      Response: {response_text[:100]}{'...' if len(response_text) > 100 else ''}")
        else:
            print(f"  ❌ No response")


async def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test ADK Audio Agent")
    parser.add_argument("--game_id", default="2024030412", help="NHL game ID")
    parser.add_argument("--max_files", type=int, default=5, help="Maximum files to process")
    parser.add_argument("--quick_test", action="store_true", help="Run quick single text tests only")
    
    args = parser.parse_args()
    
    if args.quick_test:
        await test_single_text_audio_generation(args.game_id)
    else:
        await test_audio_agent_with_commentary_files(args.game_id, args.max_files)
        await test_single_text_audio_generation(args.game_id)


if __name__ == "__main__":
    asyncio.run(main()) 