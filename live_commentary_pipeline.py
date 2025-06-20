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
sys.path.append('src/agents/audio_agent')
sys.path.append('src/board')

# Import configuration
from config.pipeline_config import config

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
    time.sleep(config.TIMESTAMP_PROCESSING_DELAY)
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
    print("📤 Step 8: Sending initial context to commentary agent...")
    async for event in commentary_runner.run_async(
        user_id=commentary_session.user_id,
        session_id=commentary_session.id,
        new_message=initial_context,
    ):
        pass  # Just establish context
    print("✅ Commentary agent context initialized")
    
    print(f"🎉 All ADK sessions created successfully!")
    print(f"   📊 Data session: {data_session.id}")
    print(f"   🎙️ Commentary session: {commentary_session.id}")
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

async def process_audio_agent_with_board(commentary_output_file: str, game_id: str, audio_agent, audio_buffer: asyncio.Queue = None) -> Dict[str, Any]:
    """Process commentary output with audio agent for live streaming"""
    try:
        # Load commentary output
        with open(commentary_output_file, 'r') as f:
            commentary_data = json.load(f)
        
        # Extract timestamp for context
        filename_base = os.path.basename(commentary_output_file).replace('_commentary_board.json', '')
        
        print(f"    🎙️ Processing audio for {filename_base}")
        
        # Check if commentary has the expected structure
        if "commentary_sequence" not in commentary_data:
            return {"status": "error", "error": "Invalid commentary structure - missing commentary_sequence"}
        
        commentary_sequence = commentary_data["commentary_sequence"]
        
        # Process each speaker segment for live streaming
        audio_results = []
        total_duration = 0
        
        for i, segment in enumerate(commentary_sequence):
            speaker = segment.get("speaker", "Unknown")
            text = segment.get("text", "")
            emotion = segment.get("emotion", "neutral")
            duration_estimate = segment.get("duration_estimate", 3.0)
            pause_after = segment.get("pause_after", 0.5)
            
            if not text.strip():
                continue
                
            # Map emotion to voice style
            voice_style = "enthusiastic"  # default
            if emotion in ["excited", "enthusiastic"]:
                voice_style = "enthusiastic"
            elif emotion in ["dramatic", "intense"]:
                voice_style = "dramatic"  
            elif emotion in ["calm", "analytical", "neutral"]:
                voice_style = "calm"
            
            print(f"      🔊 {speaker}: {text[:40]}... (style: {voice_style})")
            
            # Generate audio for this segment using the text_to_speech tool
            from agents.audio_agent.tool import text_to_speech
            audio_result = await text_to_speech(
                text=text,
                voice_style=voice_style,
                speaker=speaker,
                emotion=emotion,
                game_id=game_id,
                game_timestamp=filename_base,  # This contains the timestamp like "1_00_05"
                segment_index=i  # Pass the segment index for proper sequencing
            )
            
            if audio_result["status"] == "success":
                # Extract audio ID directly from TTS result
                audio_id = audio_result.get("audio_id", f"unknown_{i}")
                
                segment_info = {
                    "segment_index": i,
                    "speaker": speaker,
                    "audio_id": audio_id,
                    "text_preview": text[:50] + "..." if len(text) > 50 else text,
                    "voice_style": voice_style,
                    "duration_estimate": duration_estimate,
                    "pause_after": pause_after
                }
                
                # Add to buffer if available, otherwise add to results
                if audio_buffer:
                    await audio_buffer.put(segment_info)
                    print(f"      ✅ Added to audio buffer: {speaker}")
                else:
                    audio_results.append(segment_info)
                
                total_duration += duration_estimate + pause_after
            else:
                print(f"      ❌ Audio generation failed for segment {i}: {audio_result.get('error', 'Unknown error')}")
                return {"status": "error", "error": f"Audio generation failed for segment {i}"}
        
        # Save audio processing results
        output_dir = f"data/audio_agent_outputs/{game_id}"
        os.makedirs(output_dir, exist_ok=True)
        output_file = f"{output_dir}/{filename_base}_audio_board.json"
        
        audio_summary = {
            "status": "success",
            "timestamp": filename_base,
            "total_segments": len(commentary_sequence),
            "processed_segments": len(audio_results),
            "total_duration_estimate": total_duration,
            "audio_segments": audio_results,
            "live_stream_info": {
                "websocket_url": f"ws://{config.WEBSOCKET_HOST}:{config.WEBSOCKET_PORT}",
                "clients_connected": 0,  # Will be updated by audio agent
                "streaming_active": True
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(audio_summary, f, indent=2)
        
        return {
            "status": "success", 
            "output_file": output_file,
            "audio_segments_processed": len(audio_results),
            "total_duration": total_duration,
            "clients_connected": audio_summary["live_stream_info"]["clients_connected"]
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def process_timestamp_with_board(timestamp_file: str, data_runner, data_session, commentary_runner, commentary_session, game_board, session_manager, audio_agent, audio_buffer: asyncio.Queue = None) -> Dict[str, Any]:
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
    
    # Step 3: Audio Agent with live streaming
    audio_result = await process_audio_agent_with_board(
        commentary_result["output_file"],
        game_id,
        audio_agent,
        audio_buffer  # Pass the buffer for continuous streaming
    )
    if audio_result["status"] != "success":
        print(f"    ❌ Audio agent failed: {audio_result['error']}")
        return audio_result
    
    print(f"    ✅ Audio agent completed ({audio_result['audio_segments_processed']} segments, {audio_result['clients_connected']} clients)")
    
    return {
        "status": "success",
        "timestamp": file_basename,
        "data_result": data_result,
        "commentary_result": commentary_result,
        "audio_result": audio_result,
        "board_state": game_board.get_authoritative_state()
    }

async def process_timestamp_without_audio(timestamp_file: str, data_runner, data_session, 
                                         commentary_runner, commentary_session, 
                                         game_board, session_manager) -> Dict[str, Any]:
    """Process timestamp through data and commentary agents only (no audio generation)"""
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
    
    # Return without audio processing
    return {
        "status": "success",
        "timestamp": file_basename,
        "data_result": data_result,
        "commentary_result": commentary_result,
        "board_state": game_board.get_authoritative_state()
    }

async def run_live_commentary_pipeline(game_id: str, duration_minutes: int = 5):
    """Main pipeline function with Live Game Board integration and Audio Streaming"""
    print(f"🚀 PIPELINE STARTING - NHL Live Commentary")
    print(f"🎯 Game ID: {game_id}")
    print(f"⏱️  Duration: {duration_minutes} minutes")
    print("=" * 50)
    print("📍 Pipeline function entered successfully")
    import sys
    sys.stdout.flush()
    
    try:
        # Phase 1: Generate static context
        print("📍 Phase 1: Starting static context generation...")
        sys.stdout.flush()
        await generate_static_context(game_id)
        print("📍 Phase 1: Static context completed")
        sys.stdout.flush()
        
        # Phase 2: Initialize Live Game Board
        print("📍 Phase 2: Starting Live Game Board...")
        print("🏒 Initializing Live Game Board...")
        sys.stdout.flush()
        from board import create_live_game_board, SessionManager
        
        static_context_file = f"{config.DATA_BASE_PATH}/static/game_{game_id}_static_context.json"
        game_board = create_live_game_board(game_id, static_context_file)
        session_manager = SessionManager(refresh_interval=config.SESSION_REFRESH_INTERVAL)
        
        print(f"✅ Game Board initialized: {game_board.away_team} @ {game_board.home_team}")
        print(f"✅ Rosters loaded: {len(game_board.team_rosters['away'])} away, {len(game_board.team_rosters['home'])} home players")
        
        # Phase 3: Start live data collection (background)
        print("📡 Starting live data collection...")
        sys.stdout.flush()
        live_process = start_live_data_collection(game_id, duration_minutes)
        print(f"✅ Live process started: PID {live_process.pid}")
        sys.stdout.flush()
        
        print("📍 About to start ADK session creation...")
        sys.stdout.flush()
        
        # Phase 4: Create shared sessions with board integration (with timeout)
        print("🕐 Creating ADK sessions (this may take 1-2 minutes)...")
        sys.stdout.flush()
        try:
            (data_runner, data_session), (commentary_runner, commentary_session) = await asyncio.wait_for(
                create_shared_sessions_with_board(game_id, game_board),
                timeout=config.ADK_TIMEOUT  # ADK timeout from config
            )
            print("✅ ADK sessions created successfully")
        except asyncio.TimeoutError:
            print("⚠️ ADK session creation timed out - continuing with simplified agents")
            # For now, raise error - we need ADK for the core functionality
            raise Exception("ADK session creation timed out after 2 minutes")
        
        # Phase 4.5: Initialize Audio Agent (ADK logic only)
        print("🎙️ Initializing Audio Agent for text-to-speech...")
        from agents.audio_agent.audio_agent import AudioAgent
        
        audio_agent = AudioAgent(game_id=game_id, model="gemini-2.0-flash")
        print("✅ Audio Agent initialized for TTS processing")
        
        # Phase 4.6: Start WebSocket Server for live audio streaming
        print("🎵 Starting WebSocket server for live audio streaming...")
        try:
            from agents.audio_agent.tool import start_websocket_server
            websocket_server = await start_websocket_server(port=config.WEBSOCKET_PORT, host=config.WEBSOCKET_HOST)
            print(f"✅ WebSocket server started: ws://{config.WEBSOCKET_HOST}:{config.WEBSOCKET_PORT}")
            print(f"✅ Clients can connect to: ws://{config.WEBSOCKET_HOST}:{config.WEBSOCKET_PORT}")
            print(f"🌐 Open web_client.html in your browser to listen to live commentary")
            await asyncio.sleep(2)
            print("✅ WebSocket server ready for connections")
        except Exception as e:
            print(f"⚠️ WebSocket server failed to start: {e}")
            print("🎵 Continuing with audio file generation only")
            websocket_server = None
        
        # Create audio buffer for streaming
        audio_buffer = asyncio.Queue(maxsize=100) if websocket_server else None
        
        # Start background audio streaming task
        streaming_task = None
        if audio_buffer and websocket_server:
            async def continuous_audio_streamer():
                """Background task to stream audio continuously from buffer"""
                print("🎵 Starting continuous audio streaming task...")
                try:
                    from agents.audio_agent.tool import broadcast_audio_to_clients
                    while True:
                        try:
                            # Get audio segment from buffer (with timeout)
                            audio_segment = await asyncio.wait_for(audio_buffer.get(), timeout=5.0)
                            
                            # Check for shutdown signal
                            if audio_segment == "SHUTDOWN":
                                print("🛑 Audio streaming shutdown signal received")
                                break
                            
                            # Broadcast to all connected clients
                            await broadcast_audio_to_clients(audio_segment)
                            print(f"📡 Broadcasted audio segment: {audio_segment.get('speaker', 'Unknown')}")
                            
                        except asyncio.TimeoutError:
                            # No audio in buffer, continue waiting
                            continue
                        except Exception as e:
                            print(f"⚠️ Streaming error: {e}")
                            await asyncio.sleep(1)
                            
                except Exception as e:
                    print(f"❌ Audio streaming task failed: {e}")
                finally:
                    print("🏁 Audio streaming task ended")
            
            streaming_task = asyncio.create_task(continuous_audio_streamer())
            print("✅ Continuous audio streaming task started")
        
        # Phase 5: Wait for live data collection to finish, then process ALL timestamps
        print(f"🔄 Waiting for live data collection to finish...")
        
        # Wait for live data collection to complete
        live_process.wait()
        print("🏁 Live data collection finished, processing ALL collected timestamps...")
        await asyncio.sleep(1)  # Allow final files to be written
        
        # Get ALL timestamp files (not just new ones)
        all_timestamp_files = get_new_timestamp_files(game_id, set())  # Empty set = process all files
        total_files = len(all_timestamp_files)
        
        print(f"📊 Found {total_files} timestamp files to process")
        
        processed_count = 0
        for timestamp_file in all_timestamp_files:
            # Process WITH audio agent to generate audio files
            result = await process_timestamp_with_board(
                timestamp_file, data_runner, data_session,
                commentary_runner, commentary_session,
                game_board, session_manager,
                audio_agent, audio_buffer
            )
            processed_count += 1
            
            if result["status"] == "success":
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
        
        print("=" * 50)
        print(f"🎉 Board-integrated pipeline completed successfully!")
        print(f"📊 Total timestamps processed: {processed_count}")
        print(f"🏒 Final score: {final_board_state['teams']['away']} {final_board_state['score']['away']} - {final_board_state['teams']['home']} {final_board_state['score']['home']}")
        print(f"🎯 Goals scored: {len(final_board_state['goals'])}")
        print(f"💾 Board state exported: {board_export_file}")
        
        # Cleanup streaming and WebSocket server
        if streaming_task and audio_buffer:
            try:
                print("🛑 Stopping audio streaming...")
                await audio_buffer.put("SHUTDOWN")
                await asyncio.wait_for(streaming_task, timeout=10.0)
                print("✅ Audio streaming task stopped")
            except Exception as e:
                print(f"⚠️ Audio streaming stop warning: {e}")
        
        if websocket_server:
            try:
                print("🛑 Stopping WebSocket server...")
                from agents.audio_agent.tool import stop_websocket_server
                await stop_websocket_server()
                print("✅ WebSocket server stopped successfully")
            except Exception as e:
                print(f"⚠️ WebSocket server stop failed: {e}")
        
        # Audio streaming summary
        try:
            # Try to get audio status from the agent
            from agents.audio_agent.tool import audio_processor
            audio_connected_clients = len(audio_processor.connected_clients)
            print(f"🎙️ Audio streaming completed: {audio_connected_clients} clients connected")
            print(f"📻 WebSocket server: Stopped")
            print(f"📁 Audio outputs: data/audio_agent_outputs/{game_id}/")
        except:
            print(f"🎙️ Audio streaming completed")
            print(f"📻 WebSocket server: Stopped")
            print(f"📁 Audio outputs: data/audio_agent_outputs/{game_id}/")
        
        print(f"📁 Check data/ directories for generated files")
        
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        return False
    
    return True

async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python live_commentary_pipeline.py GAME_ID [DURATION_MINUTES]")
        print("Example: python live_commentary_pipeline.py 2024030413 3")
        print("\\nThis runs the complete Live NHL Commentary Pipeline:")
        print("  1. Generate static context")
        print("  2. Initialize Live Game Board with authoritative state")
        print("  3. Start live data collection")  
        print("  4. Process each timestamp with board state injection")
        print("  5. Generate commentary with context collapse prevention")
        print("  6. Convert commentary to audio and stream via WebSocket")
        print(f"\\nClients can connect to: ws://{config.WEBSOCKET_HOST}:{config.WEBSOCKET_PORT} for live audio")
        sys.exit(1)
    
    game_id = sys.argv[1]
    duration = float(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    success = await run_live_commentary_pipeline(game_id, duration)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())