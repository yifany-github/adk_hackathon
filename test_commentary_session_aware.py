#!/usr/bin/env python3
"""
Session-aware commentary pipeline that maintains context across timestamps
using Google ADK session management to eliminate repetitive commentary
"""

import asyncio
import json
import sys
import os
import glob
from datetime import datetime
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agents.commentary_agent.commentary_agent import create_commentary_agent_for_game


async def run_session_aware_commentary_pipeline(game_id: str = "2024030412", max_files: int = 5):
    """
    Run commentary pipeline with session awareness to maintain context
    Uses single session across all timestamps to prevent repetitive commentary
    """
    
    print("🏒 Session-Aware Commentary Pipeline")
    print("=" * 60)
    print(f"Game ID: {game_id}")
    print(f"Max files: {max_files}")
    print()
    
    # Create commentary agent for this game
    agent = create_commentary_agent_for_game(game_id)
    print(f"✅ Created commentary agent: {agent.name}")
    print()
    
    # Find data agent output files
    data_files = glob.glob(f"data/data_agent_outputs/{game_id}_*_adk.json")
    data_files.sort()
    
    if not data_files:
        print(f"❌ No data agent files found for game {game_id}")
        return
    
    # Limit number of files
    if len(data_files) > max_files:
        data_files = data_files[:max_files]
    
    print(f"📊 Found {len(data_files)} data agent files to process")
    print()
    
    # *** SESSION RESET STRATEGY: New session every 15 timestamps (1:15 game time) ***
    from google.adk.runners import InMemoryRunner
    from google.genai.types import Part, UserContent
    
    runner = InMemoryRunner(agent=agent)
    session = None
    session_count = 0
    SESSION_RESET_INTERVAL = 15  # Reset every 15 timestamps (1 min 15 sec)
    
    async def create_new_session():
        """Create a new session with fresh context"""
        nonlocal session, session_count
        session_count += 1
        
        session = await runner.session_service.create_session(
            app_name=runner.app_name, 
            user_id=f"game_commentator_session_{session_count}"
        )
        
        print(f"🎙️ Created commentary session #{session_count}: {session.id}")
        
        # Initialize game context in session state
        initial_context = UserContent(parts=[Part(text=f"""
You are now the live commentary team for NHL game {game_id}. This is session #{session_count} of your broadcast.
Throughout this session:
- Maintain natural conversational flow between Alex Chen and Mike Rodriguez
- Build on each other's observations organically, as real broadcasters do
- Vary your dialogue and avoid repetitive phrases
- Use names occasionally for transitions or direct questions (not every exchange)
- Let the conversation flow naturally without forced acknowledgments

You'll receive live game data at different timestamps. Generate appropriate commentary for each moment.
Ready to begin commentary for this session?
""")])
        
        # Send initial context (this establishes the session baseline)
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=initial_context,
        ):
            pass  # Just establish context, don't need the response
        
        print(f"✅ Session #{session_count} context initialized")
        return session
    
    # Create initial session
    await create_new_session()
    print()
    
    # Process each timestamp with session continuity and resets
    successful_outputs = []
    
    for i, data_file in enumerate(data_files, 1):
        # Check if we need to reset the session
        if (i - 1) % SESSION_RESET_INTERVAL == 0 and i > 1:
            print(f"🔄 Session reset triggered at file {i} (every {SESSION_RESET_INTERVAL} timestamps)")
            await create_new_session()
            print()
        
        print(f"[{i}/{len(data_files)}] 📁 Processing: {os.path.basename(data_file)} (Session #{session_count})")
        
        try:
            # Load data agent output
            with open(data_file, 'r') as f:
                data_agent_output = json.load(f)
            
            # Extract timestamp for context
            filename_base = os.path.basename(data_file).replace('_adk.json', '')
            timestamp_parts = filename_base.split('_')
            if len(timestamp_parts) >= 4:
                period = timestamp_parts[1]
                minutes = timestamp_parts[2]
                seconds = timestamp_parts[3]
                game_time = f"Period {period}, {minutes}:{seconds}"
            else:
                game_time = "Unknown time"
            
            # Create context-aware input that references the ongoing session
            input_text = f"""
Game Time: {game_time}

New game data update:
{json.dumps(data_agent_output, indent=2)}

Generate appropriate commentary for this moment. Remember our ongoing conversation and avoid repeating previous commentary themes.
"""
            
            content = UserContent(parts=[Part(text=input_text)])
            
            # *** KEY: Use the SAME session for continuity ***
            response_text = ""
            async for event in runner.run_async(
                user_id=session.user_id,
                session_id=session.id,  # Same session across all timestamps!
                new_message=content,
            ):
                if hasattr(event, 'content') and event.content and event.content.parts:
                    if event.content.parts[0].text:
                        response_text = event.content.parts[0].text
            
            if response_text:
                # Extract JSON from markdown code blocks if present
                clean_response = response_text.strip()
                
                # Handle markdown code block wrapping
                if "```json" in clean_response:
                    json_start = clean_response.find("```json") + 7
                    json_end = clean_response.find("```", json_start)
                    if json_end == -1:
                        json_end = len(clean_response)
                    clean_response = clean_response[json_start:json_end].strip()
                elif "```" in clean_response:
                    json_start = clean_response.find("```") + 3
                    json_end = clean_response.rfind("```")
                    if json_end > json_start:
                        clean_response = clean_response[json_start:json_end].strip()
                
                # Parse and save the commentary
                try:
                    parsed_result = json.loads(clean_response)
                    
                    # Add metadata to the parsed result
                    commentary_data = {
                        "generated_at": datetime.now().isoformat(),
                        "commentary_agent_version": "session_aware_v1.0",
                        "agent_type": "nhl_commentary_agent",
                        "game_id": game_id,
                        "timestamp": game_time,
                        "session_id": session.id,
                        "session_number": session_count,
                        **parsed_result  # Spread the clean parsed JSON
                    }
                    
                except json.JSONDecodeError as e:
                    # Handle non-JSON responses as fallback
                    commentary_data = {
                        "generated_at": datetime.now().isoformat(),
                        "commentary_agent_version": "session_aware_v1.0",
                        "agent_type": "nhl_commentary_agent",
                        "game_id": game_id,
                        "timestamp": game_time,
                        "session_id": session.id,
                        "session_number": session_count,
                        "status": "error",
                        "error": f"Failed to parse JSON: {str(e)}",
                        "raw_response": response_text
                    }
                
                # Save output
                os.makedirs("data/commentary_agent_outputs", exist_ok=True)
                output_file = f"data/commentary_agent_outputs/{filename_base}_commentary_session_aware.json"
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(commentary_data, f, indent=2, ensure_ascii=False)
                
                print(f"  ✅ Saved: {output_file}")
                successful_outputs.append(output_file)
                
                # Show brief sample
                if "commentary_data" in commentary_data:
                    seq = commentary_data["commentary_data"].get("commentary_sequence", [])
                    if seq and len(seq) > 0:
                        first_line = seq[0]
                        speaker = first_line.get("speaker", "Unknown")
                        text = first_line.get("text", "")[:60] + "..."
                        print(f"  🎙️ Sample: {speaker}: {text}")
                
            else:
                print(f"  ❌ No response from agent")
            
        except Exception as e:
            print(f"  ❌ Error processing {data_file}: {e}")
    
    # Summary
    print()
    print("=" * 60)
    print("✅ Session-Aware Pipeline completed!")
    print(f"✅ Processed: {len(data_files)} files")
    print(f"✅ Successful: {len(successful_outputs)} commentary files")
    print(f"🎙️ Final Session: #{session_count} (ID: {session.id})")
    print(f"📊 Session resets occurred: {session_count - 1} times")
    print()
    
    if successful_outputs:
        print("📁 Generated commentary files:")
        for output in successful_outputs:
            print(f"  - {output}")


async def test_session_context():
    """Test that session maintains context by sending sequential messages"""
    print("🧪 Testing Session Context Maintenance")
    print("=" * 50)
    
    game_id = "2024030412"
    agent = create_commentary_agent_for_game(game_id)
    
    from google.adk.runners import InMemoryRunner
    from google.genai.types import Part, UserContent
    
    runner = InMemoryRunner(agent=agent)
    session = await runner.session_service.create_session(
        app_name=runner.app_name, 
        user_id="test_user"
    )
    
    # Test sequence: intro -> follow-up -> follow-up
    test_messages = [
        "Start commentary for Florida Panthers vs Edmonton Oilers at Rogers Place",
        "Continue commentary, the game just started with a faceoff",
        "Keep the commentary going, there was just a shot on goal"
    ]
    
    for i, msg in enumerate(test_messages, 1):
        print(f"\n--- Message {i} ---")
        print(f"Input: {msg}")
        
        content = UserContent(parts=[Part(text=msg)])
        
        response_text = ""
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=content,
        ):
            if hasattr(event, 'content') and event.content and event.content.parts:
                if event.content.parts[0].text:
                    response_text = event.content.parts[0].text
        
        print(f"Response: {response_text[:200]}...")
    
    print(f"\n✅ Session test completed with session ID: {session.id}")


async def main():
    """Main function with options"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Session-aware commentary pipeline')
    parser.add_argument('--test-session', action='store_true', help='Test session context maintenance')
    parser.add_argument('--game-id', default='2024030412', help='Game ID to process')
    parser.add_argument('--max-files', type=int, default=3, help='Maximum files to process')
    
    args = parser.parse_args()
    
    if args.test_session:
        await test_session_context()
    else:
        await run_session_aware_commentary_pipeline(args.game_id, args.max_files)


if __name__ == "__main__":
    asyncio.run(main())