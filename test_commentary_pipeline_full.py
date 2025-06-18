#!/usr/bin/env python3
"""
Test Script: Full Commentary Pipeline (Data + Commentary Agents Only)
Tests the complete 3-4 minute commentary generation without audio delays.

Usage: python test_commentary_pipeline_full.py GAME_ID DURATION_MINUTES
Example: python test_commentary_pipeline_full.py 2024030415 3
"""

import sys
import os
import json
import time
import subprocess
import asyncio
import glob
from pathlib import Path
from typing import Set, List, Dict, Any
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Add src to path for imports
sys.path.append('src')
sys.path.append('src/agents/data_agent')
sys.path.append('src/agents/commentary_agent')
sys.path.append('src/board')

async def generate_static_context(game_id: str):
    """Generate static context for the game"""
    print(f"📋 Generating static context for game {game_id}...")
    result = subprocess.run([
        "python", "src/data/static/static_info_generator.py", game_id
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        raise Exception(f"Static context generation failed: {result.stderr}")
    print("✅ Static context generated")

def start_live_data_collection(game_id: str, duration_minutes: int):
    """Start live data collection in background"""
    print(f"📡 Starting live data collection for {duration_minutes} minutes...")
    process = subprocess.Popen([
        "python", "src/data/live/live_data_collector.py", 
        "simulate", game_id,
        "--game_duration_minutes", str(duration_minutes)
    ])
    
    # Wait a moment for first files to appear
    time.sleep(1)
    print("✅ Live data collection started")
    return process

async def create_shared_sessions_with_board(game_id: str, game_board):
    """Create shared sessions for data and commentary agents with board state injection"""
    print("🎙️ Creating shared ADK sessions with board integration...")
    
    from agents.data_agent.data_agent_adk import create_hockey_agent_for_game
    from agents.commentary_agent.commentary_agent import create_commentary_agent_for_game
    from google.adk.runners import InMemoryRunner
    from google.genai.types import Part, UserContent
    
    # Create data agent and runner
    print("🤖 Step 1: Creating data agent...")
    data_agent = create_hockey_agent_for_game(game_id)
    print("✅ Data agent created")
    
    print("🏃 Step 2: Creating data runner...")
    data_runner = InMemoryRunner(agent=data_agent)
    print("✅ Data runner created")
    
    # Create data session
    print("🔗 Step 3: Creating data session...")
    data_session = await data_runner.session_service.create_session(
        app_name=data_runner.app_name,
        user_id=f"data_agent_{game_id}_board"
    )
    print("✅ Data session created")
    
    # Initialize data session with board state awareness
    data_initial_context = UserContent(parts=[Part(text=f"""
You are analyzing NHL game {game_id} with LIVE GAME BOARD integration.

{game_board.get_prompt_injection()}

BOARD-INTEGRATED ANALYSIS:
- The authoritative game state above is your SINGLE SOURCE OF TRUTH
- NEVER contradict any information in the authoritative state
- Build your analysis on this factual foundation
- The board prevents context collapse by maintaining consistent state

Ready to begin board-integrated NHL game analysis with guaranteed state consistency?
""")])
    
    # Send initial context to data agent
    print("📤 Step 4: Sending initial context to data agent...")
    async for event in data_runner.run_async(
        user_id=data_session.user_id,
        session_id=data_session.id,
        new_message=data_initial_context,
    ):
        pass  # Just establish context
    print("✅ Data agent context initialized")
    
    # Create commentary agent and runner
    print("🎙️ Step 5: Creating commentary agent...")
    commentary_agent = create_commentary_agent_for_game(game_id)
    print("✅ Commentary agent created")
    
    print("🏃 Step 6: Creating commentary runner...")
    commentary_runner = InMemoryRunner(agent=commentary_agent)
    print("✅ Commentary runner created")
    
    # Create commentary session
    print("🔗 Step 7: Creating commentary session...")
    commentary_session = await commentary_runner.session_service.create_session(
        app_name=commentary_runner.app_name,
        user_id=f"commentary_agent_{game_id}_board"
    )
    print("✅ Commentary session created")
    
    # Initialize commentary session context with board state
    initial_context = UserContent(parts=[Part(text=f"""
You are the live commentary team for NHL game {game_id} with LIVE GAME BOARD integration.

{game_board.get_prompt_injection()}

BOARD-INTEGRATED COMMENTARY:
- The authoritative game state above is your SINGLE SOURCE OF TRUTH
- You are Alex Chen (Play-by-Play) and Mike Rodriguez (Color Commentary)
- Maintain natural conversational flow between broadcasters
- Reference authoritative state for all factual claims

Ready to begin professional NHL broadcast commentary with guaranteed factual accuracy?
""")])
    
    # Send initial context to establish broadcaster names
    print("📤 Step 8: Sending initial context to commentary agent...")
    async for event in commentary_runner.run_async(
        user_id=commentary_session.user_id,
        session_id=commentary_session.id,
        new_message=initial_context,
    ):
        pass  # Just establish context
    print("✅ Commentary agent context initialized")
    
    print(f"🎉 All ADK sessions created successfully!")
    return (data_runner, data_session), (commentary_runner, commentary_session)

def get_all_timestamp_files(game_id: str) -> List[str]:
    """Get all timestamp files for processing"""
    data_dir = f"data/live/{game_id}"
    if not os.path.exists(data_dir):
        return []
    
    pattern = f"{data_dir}/{game_id}_*.json"
    all_files = sorted(glob.glob(pattern))
    return all_files

async def process_data_agent_with_board(timestamp_file: str, runner, session, game_board) -> Dict[str, Any]:
    """Process timestamp file with data agent using board state injection"""
    try:
        # Load timestamp data
        with open(timestamp_file, 'r') as f:
            timestamp_data = json.load(f)
        
        # Update board state FIRST (authoritative)
        board_update = game_board.update_from_timestamp(timestamp_data)
        
        # Process using shared session with board state injection
        from google.genai.types import Part, UserContent
        
        # Extract timing information for context
        game_time = timestamp_data.get('game_time', 'Unknown')
        
        input_text = f"""
TIMESTAMP ANALYSIS WITH BOARD STATE - {game_time}

{game_board.get_prompt_injection()}

BOARD UPDATE REPORT:
- Events processed: {board_update['events_processed']}
- State changes: {board_update['state_changes']}
- New goals: {board_update['new_goals']}
- New penalties: {board_update['new_penalties']}

ANALYSIS TASK:
Build your analysis on the authoritative board state above. The board has already processed and validated all events.

RAW TIMESTAMP DATA (for reference only):
{json.dumps(timestamp_data, indent=2)}

Provide analysis that builds on the board-validated state and maintains consistency with authoritative facts.
"""
        content = UserContent(parts=[Part(text=input_text)])
        
        response_text = ""
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.content.parts and event.content.parts[0].text:
                response_text = event.content.parts[0].text
        
        # Parse and save result
        result = json.loads(response_text)
        
        # Save data agent output in game-specific subfolder
        game_id = session.user_id.split('_')[2]  # Extract from user_id
        game_time = os.path.basename(timestamp_file).replace(f"{game_id}_", "").replace(".json", "")
        output_dir = f"data/data_agent_outputs/{game_id}"
        os.makedirs(output_dir, exist_ok=True)
        output_file = f"{output_dir}/{game_time}_adk_board.json"
        
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        return {
            "status": "success", 
            "data": result, 
            "output_file": output_file,
            "board_update": board_update
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def process_commentary_agent_with_board(data_output_file: str, game_id: str, commentary_runner, commentary_session, game_board):
    """Process with commentary agent using board state injection"""
    try:
        # Load data agent output
        with open(data_output_file, 'r') as f:
            data_agent_output = json.load(f)
        
        # Extract timestamp for context
        filename_base = os.path.basename(data_output_file).replace('_adk_board.json', '')
        
        # Create input for commentary agent with board state injection
        from google.genai.types import Part, UserContent
        
        input_text = f"""
LIVE COMMENTARY WITH BOARD STATE - {filename_base}

{game_board.get_prompt_injection()}

NARRATIVE CONTEXT:
{game_board.get_narrative_context()}

COMMENTARY REQUIREMENTS:
- Build natural commentary on the authoritative board state above
- Maintain Alex Chen & Mike Rodriguez dialogue flow  
- Reference board-validated facts for all claims
- Create excitement around board-confirmed events
- Trust board state over any conflicting information

DATA AGENT ANALYSIS (board-validated):
{json.dumps(data_agent_output, indent=2)}

Generate professional commentary that flows naturally while maintaining strict consistency with board state.
"""
        content = UserContent(parts=[Part(text=input_text)])
        
        # Use shared commentary session
        response_text = ""
        async for event in commentary_runner.run_async(
            user_id=commentary_session.user_id,
            session_id=commentary_session.id,
            new_message=content,
        ):
            if event.content.parts and event.content.parts[0].text:
                response_text = event.content.parts[0].text
        
        # Save commentary output in game-specific subfolder  
        output_dir = f"data/commentary_agent_outputs/{game_id}"
        os.makedirs(output_dir, exist_ok=True)
        output_file = f"{output_dir}/{filename_base}_commentary_board.json"
        
        # Parse response and save
        try:
            # Handle markdown code block wrapping
            clean_response = response_text
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
            
            result = json.loads(clean_response)
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
        except json.JSONDecodeError:
            # Save raw response if JSON parsing fails
            with open(output_file, 'w') as f:
                json.dump({"raw_response": response_text}, f, indent=2)
        
        return {"status": "success", "output_file": output_file}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def process_timestamp_commentary_only(timestamp_file: str, data_runner, data_session, commentary_runner, commentary_session, game_board, session_manager) -> Dict[str, Any]:
    """Process a single timestamp through data + commentary agents only (NO AUDIO)"""
    file_basename = os.path.basename(timestamp_file)
    print(f"  ⏰ Processing: {file_basename}")
    
    # Check for session refresh
    data_session, commentary_session = await session_manager.maybe_refresh_sessions(
        data_runner, data_session, commentary_runner, commentary_session, game_board
    )
    
    # Step 1: Data Agent with board integration
    data_result = await process_data_agent_with_board(timestamp_file, data_runner, data_session, game_board)
    if data_result["status"] != "success":
        print(f"    ❌ Data agent failed: {data_result['error']}")
        return data_result
    
    print(f"    ✅ Data agent completed (board events: {data_result['board_update']['events_processed']})")
    
    # Step 2: Commentary Agent with board integration
    game_id = data_session.user_id.split('_')[2]
    commentary_result = await process_commentary_agent_with_board(
        data_result["output_file"], 
        game_id,
        commentary_runner,
        commentary_session,
        game_board
    )
    if commentary_result["status"] != "success":
        print(f"    ❌ Commentary agent failed: {commentary_result['error']}")
        return commentary_result
    
    print(f"    ✅ Commentary agent completed")
    
    # NOTE: Audio agent processing would go here when enabled
    # Step 3: Audio Agent (DISABLED FOR TESTING)
    # audio_result = await process_audio_agent_with_board(...)
    
    return {
        "status": "success",
        "timestamp": file_basename,
        "data_result": data_result,
        "commentary_result": commentary_result,
        # "audio_result": audio_result,  # Commented out
        "board_state": game_board.get_authoritative_state()
    }

async def run_commentary_test_pipeline(game_id: str, duration_minutes: int = 3):
    """Test pipeline function with Data + Commentary agents only (NO AUDIO)"""
    print(f"🚀 TEST PIPELINE - NHL Commentary Generation (No Audio)")
    print(f"🎯 Game ID: {game_id}")
    print(f"⏱️  Duration: {duration_minutes} minutes")
    print("=" * 60)
    
    try:
        # Phase 1: Generate static context
        print("📍 Phase 1: Starting static context generation...")
        await generate_static_context(game_id)
        print("📍 Phase 1: Static context completed")
        
        # Phase 2: Initialize Live Game Board
        print("📍 Phase 2: Starting Live Game Board...")
        print("🏒 Initializing Live Game Board...")
        from board import create_live_game_board, SessionManager
        
        static_context_file = f"data/static/game_{game_id}_static_context.json"
        game_board = create_live_game_board(game_id, static_context_file)
        session_manager = SessionManager(refresh_interval=10)
        
        print(f"✅ Game Board initialized: {game_board.away_team} @ {game_board.home_team}")
        print(f"✅ Rosters loaded: {len(game_board.team_rosters['away'])} away, {len(game_board.team_rosters['home'])} home players")
        
        # Phase 3: Start live data collection (background)
        print("📡 Starting live data collection...")
        live_process = start_live_data_collection(game_id, duration_minutes)
        print(f"✅ Live process started: PID {live_process.pid}")
        
        # Phase 4: Create shared sessions with board integration
        print("🕐 Creating ADK sessions (this may take 1-2 minutes)...")
        try:
            (data_runner, data_session), (commentary_runner, commentary_session) = await asyncio.wait_for(
                create_shared_sessions_with_board(game_id, game_board),
                timeout=120.0  # 2 minute timeout
            )
            print("✅ ADK sessions created successfully")
        except asyncio.TimeoutError:
            print("⚠️ ADK session creation timed out - continuing with simplified agents")
            raise Exception("ADK session creation timed out after 2 minutes")
        
        # Phase 5: Wait for live data collection to finish, then process ALL timestamps
        print(f"🔄 Waiting for live data collection to finish...")
        
        # Wait for live data collection to complete
        live_process.wait()
        print("🏁 Live data collection finished, processing ALL collected timestamps...")
        await asyncio.sleep(1)  # Allow final files to be written
        
        # Get ALL timestamp files
        all_timestamp_files = get_all_timestamp_files(game_id)
        total_files = len(all_timestamp_files)
        
        print(f"📊 Found {total_files} timestamp files to process")
        
        if total_files == 0:
            print("❌ No timestamp files found! Check live data collection.")
            return False
        
        processed_count = 0
        successful_count = 0
        
        for timestamp_file in all_timestamp_files:
            # Process WITHOUT audio agent (commentary only)
            result = await process_timestamp_commentary_only(
                timestamp_file, data_runner, data_session,
                commentary_runner, commentary_session,
                game_board, session_manager
            )
            processed_count += 1
            
            if result["status"] == "success":
                successful_count += 1
                print(f"✅ Processed {processed_count}/{total_files}: {result['timestamp']}")
                # Print board state summary  
                board_state = result["board_state"]
                print(f"   📊 Score: {board_state['away_team']} {board_state['score']['away']} - {board_state['home_team']} {board_state['score']['home']}")
            else:
                print(f"❌ Failed to process {timestamp_file}: {result.get('error', 'Unknown error')}")
        
        # Export final board state
        final_board_state = game_board.export_state()
        board_export_file = f"data/board_states/game_{game_id}_final_state.json"
        os.makedirs("data/board_states", exist_ok=True)
        with open(board_export_file, 'w') as f:
            json.dump(final_board_state, f, indent=2)
        
        print("=" * 60)
        print(f"🎉 Commentary test pipeline completed successfully!")
        print(f"📊 Total timestamps processed: {successful_count}/{total_files}")
        print(f"🏒 Final score: {final_board_state['teams']['away']} {final_board_state['score']['away']} - {final_board_state['teams']['home']} {final_board_state['score']['home']}")
        print(f"🎯 Goals scored: {len(final_board_state['goals'])}")
        print(f"💾 Board state exported: {board_export_file}")
        print(f"📁 Commentary outputs: data/commentary_agent_outputs/{game_id}/")
        print(f"📁 Data outputs: data/data_agent_outputs/{game_id}/")
        
        return successful_count == total_files
        
    except Exception as e:
        print(f"❌ Test pipeline failed: {e}")
        return False

async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python test_commentary_pipeline_full.py GAME_ID [DURATION_MINUTES]")
        print("Example: python test_commentary_pipeline_full.py 2024030415 3")
        print("\\nThis runs the complete commentary test (Data + Commentary agents only):")
        print("  1. Generate static context")
        print("  2. Initialize Live Game Board")
        print("  3. Start live data collection")  
        print("  4. Wait for collection to finish")
        print("  5. Process ALL timestamps through Data + Commentary agents")
        print("  6. Generate complete commentary JSONs for full duration")
        print("\\nNOTE: Audio agent is disabled for faster testing")
        sys.exit(1)
    
    game_id = sys.argv[1]
    duration = float(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    success = await run_commentary_test_pipeline(game_id, duration)
    
    if success:
        print(f"\\n✅ SUCCESS: Full {duration}-minute commentary generated for game {game_id}")
        print(f"📂 Check data/commentary_agent_outputs/{game_id}/ for JSON files")
    else:
        print(f"\\n❌ FAILED: Commentary generation incomplete")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())