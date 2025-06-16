#!/usr/bin/env python3
"""
NHL Live Commentary Pipeline v2 - With Live Game Board Integration
Single entry point with authoritative state management to prevent context collapse.

Usage: python live_commentary_pipeline_v2.py GAME_ID [DURATION_MINUTES]
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
    time.sleep(3)
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
    data_agent = create_hockey_agent_for_game(game_id)
    data_runner = InMemoryRunner(agent=data_agent)
    
    # Create data session
    data_session = await data_runner.session_service.create_session(
        app_name=data_runner.app_name,
        user_id=f"data_agent_{game_id}_board"
    )
    
    # Initialize data session with board state awareness
    data_initial_context = UserContent(parts=[Part(text=f"""
You are analyzing NHL game {game_id} with LIVE GAME BOARD integration.

{game_board.get_prompt_injection()}

BOARD-INTEGRATED ANALYSIS:
- The authoritative game state above is your SINGLE SOURCE OF TRUTH
- NEVER contradict any information in the authoritative state
- Build your analysis on this factual foundation
- The board prevents context collapse by maintaining consistent state

TEMPORAL CONSISTENCY (BOARD-ENFORCED):
- Scores can only INCREASE (board ensures this)
- Shot counts can only INCREASE (board validates this)  
- Player mentions must come from roster lock (board validates this)
- Goals remain scored - board prevents "un-scoring"
- Timeline progression is validated by board

ANALYSIS REQUIREMENTS:
- Reference authoritative state for all factual claims
- Build narrative on board-validated events
- Trust the board state over any conflicting information
- Focus on analysis and insights, not fact verification

Ready to begin board-integrated NHL game analysis with guaranteed state consistency?
""")])
    
    # Send initial context to data agent
    async for event in data_runner.run_async(
        user_id=data_session.user_id,
        session_id=data_session.id,
        new_message=data_initial_context,
    ):
        pass  # Just establish context
    
    # Create commentary agent and runner
    commentary_agent = create_commentary_agent_for_game(game_id)
    commentary_runner = InMemoryRunner(agent=commentary_agent)
    
    # Create commentary session
    commentary_session = await commentary_runner.session_service.create_session(
        app_name=commentary_runner.app_name,
        user_id=f"commentary_agent_{game_id}_board"
    )
    
    # Initialize commentary session context with board state
    initial_context = UserContent(parts=[Part(text=f"""
You are the live commentary team for NHL game {game_id} with LIVE GAME BOARD integration.

{game_board.get_prompt_injection()}

BOARD-INTEGRATED COMMENTARY:
- The authoritative game state above is your SINGLE SOURCE OF TRUTH
- NEVER contradict any information in the authoritative state
- Build natural commentary on this factual foundation
- The board prevents phantom players, score contradictions, and goalie paradoxes

BROADCAST REQUIREMENTS:
- You are Alex Chen (Play-by-Play) and Mike Rodriguez (Color Commentary)
- Maintain natural conversational flow between broadcasters
- Reference authoritative state for all factual claims
- Build excitement and analysis on board-validated events
- Trust board state over any conflicting information

CONTEXT COLLAPSE PREVENTION:
- Board maintains consistent scores, shots, and rosters
- No more phantom players or statistical amnesia
- Goalies' performance accurately tracked by board
- Timeline integrity enforced by board state

Ready to begin professional NHL broadcast commentary with guaranteed factual accuracy?
""")])
    
    # Send initial context to establish broadcaster names
    async for event in commentary_runner.run_async(
        user_id=commentary_session.user_id,
        session_id=commentary_session.id,
        new_message=initial_context,
    ):
        pass  # Just establish context
    
    print(f"✅ Data session created with board integration: {data_session.id}")
    print(f"✅ Commentary session created with board integration: {commentary_session.id}")
    return (data_runner, data_session), (commentary_runner, commentary_session)

def get_new_timestamp_files(game_id: str, processed_files: Set[str]) -> List[str]:
    """Find new timestamp files that haven't been processed yet"""
    data_dir = f"data/live/{game_id}"
    if not os.path.exists(data_dir):
        return []
    
    pattern = f"{data_dir}/{game_id}_*.json"
    all_files = sorted(glob.glob(pattern))
    new_files = [f for f in all_files if f not in processed_files]
    return new_files

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

async def process_timestamp_with_board(timestamp_file: str, data_runner, data_session, commentary_runner, commentary_session, game_board, session_manager) -> Dict[str, Any]:
    """Process a single timestamp through all agents with board integration"""
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
    
    return {
        "status": "success",
        "timestamp": file_basename,
        "data_result": data_result,
        "commentary_result": commentary_result,
        "board_state": game_board.get_authoritative_state()
    }

async def run_live_commentary_pipeline_v2(game_id: str, duration_minutes: int = 5):
    """Main pipeline function with Live Game Board integration"""
    print(f"🚀 NHL Live Commentary Pipeline v2 (Board-Integrated)")
    print(f"🎯 Game ID: {game_id}")
    print(f"⏱️  Duration: {duration_minutes} minutes")
    print("=" * 50)
    
    try:
        # Phase 1: Generate static context
        await generate_static_context(game_id)
        
        # Phase 2: Initialize Live Game Board
        print("🏒 Initializing Live Game Board...")
        from board import create_live_game_board, SessionManager
        
        static_context_file = f"data/static/game_{game_id}_static_context.json"
        game_board = create_live_game_board(game_id, static_context_file)
        session_manager = SessionManager(refresh_interval=10)
        
        print(f"✅ Game Board initialized: {game_board.away_team} @ {game_board.home_team}")
        print(f"✅ Rosters loaded: {len(game_board.team_rosters['away'])} away, {len(game_board.team_rosters['home'])} home players")
        
        # Phase 3: Start live data collection (background)
        live_process = start_live_data_collection(game_id, duration_minutes)
        
        # Phase 4: Create shared sessions with board integration
        (data_runner, data_session), (commentary_runner, commentary_session) = await create_shared_sessions_with_board(game_id, game_board)
        
        # Phase 5: Process timestamps with board state management
        print(f"🔄 Starting board-integrated processing...")
        processed_files = set()
        processed_count = 0
        
        while live_process.poll() is None:  # While live data collection is running
            # Check for new timestamp files
            new_files = get_new_timestamp_files(game_id, processed_files)
            
            for timestamp_file in new_files:
                result = await process_timestamp_with_board(
                    timestamp_file, data_runner, data_session, 
                    commentary_runner, commentary_session, 
                    game_board, session_manager
                )
                processed_files.add(timestamp_file)
                processed_count += 1
                
                if result["status"] == "success":
                    print(f"✅ Board-processed timestamp {processed_count}: {result['timestamp']}")
                    # Print board state summary
                    board_state = result["board_state"]
                    print(f"   📊 Score: {board_state['away_team']} {board_state['score']['away']} - {board_state['home_team']} {board_state['score']['home']}")
                else:
                    print(f"❌ Failed to process {timestamp_file}: {result.get('error', 'Unknown error')}")
            
            # Check every 2 seconds for new files
            time.sleep(2)
        
        # Process any remaining files after live collection ends
        print("🏁 Live data collection finished, processing remaining files...")
        time.sleep(3)  # Allow final files to be written
        
        final_new_files = get_new_timestamp_files(game_id, processed_files)
        for timestamp_file in final_new_files:
            result = await process_timestamp_with_board(
                timestamp_file, data_runner, data_session,
                commentary_runner, commentary_session,
                game_board, session_manager
            )
            processed_count += 1
            if result["status"] == "success":
                print(f"✅ Final board processing {processed_count}: {result['timestamp']}")
        
        # Export final board state
        final_board_state = game_board.export_state()
        board_export_file = f"data/board_states/game_{game_id}_final_state.json"
        os.makedirs("data/board_states", exist_ok=True)
        with open(board_export_file, 'w') as f:
            json.dump(final_board_state, f, indent=2)
        
        print("=" * 50)
        print(f"🎉 Board-integrated pipeline completed successfully!")
        print(f"📊 Total timestamps processed: {processed_count}")
        print(f"🏒 Final score: {final_board_state['teams']['away']} {final_board_state['score']['away']} - {final_board_state['teams']['home']} {final_board_state['score']['home']}")
        print(f"🎯 Goals scored: {len(final_board_state['goals'])}")
        print(f"💾 Board state exported: {board_export_file}")
        print(f"📁 Check data/ directories for generated files")
        
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        return False
    
    return True

async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python live_commentary_pipeline_v2.py GAME_ID [DURATION_MINUTES]")
        print("Example: python live_commentary_pipeline_v2.py 2024030413 3")
        print("\\nThis runs the Live Game Board integrated pipeline:")
        print("  1. Generate static context")
        print("  2. Initialize Live Game Board with authoritative state")
        print("  3. Start live data collection")  
        print("  4. Process each timestamp with board state injection")
        print("  5. Generate commentary with context collapse prevention")
        sys.exit(1)
    
    game_id = sys.argv[1]
    duration = float(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    success = await run_live_commentary_pipeline_v2(game_id, duration)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())