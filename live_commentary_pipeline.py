#!/usr/bin/env python3
"""
NHL Live Commentary Pipeline - Complete but Simple
Single entry point that runs the entire pipeline with persistent session management.

Usage: python live_commentary_pipeline.py GAME_ID [DURATION_MINUTES]
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

async def create_shared_sessions(game_id: str):
    """Create shared sessions for data and commentary agents"""
    print("🎙️ Creating shared ADK sessions...")
    
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
        user_id=f"data_agent_{game_id}"
    )
    
    # Initialize data session with game state awareness
    data_initial_context = UserContent(parts=[Part(text=f"""
You are analyzing NHL game {game_id} across multiple timestamps in REAL-TIME sequence.

CRITICAL GAME STATE MANAGEMENT:
- SCORE TRACKING: Scores can only INCREASE, never decrease. If you previously reported EDM 0 - FLA 1, it stays 1-0 until another goal is scored.
- PENALTY TRACKING: Track active penalties and their expiration times. A 2-minute penalty at 19:08 expires at 17:08.
- TIMELINE INTEGRITY: Each timestamp builds on the previous. Time only moves forward (20:00 → 19:58 → 19:56...).
- PLAYER VALIDATION: Use roster data to validate all player names and team assignments.

CUMULATIVE STATE AWARENESS:
- Remember what events you've already analyzed in this session
- Build shot totals cumulatively (if EDM had 2 shots last timestamp, they can't have 1 shot this timestamp)
- Track period progression and time remaining logically
- Maintain power play situations until they naturally end

TEMPORAL CONSISTENCY RULES:
- If last timestamp was "19:10 remaining", next timestamp should be around "19:05 remaining" or earlier
- Goals scored in your previous analysis remain scored - never "un-score" them
- Penalties called in previous timestamps remain active until they logically expire
- Game situations evolve naturally: even strength → penalty → power play → goal → even strength

REALISTIC ANALYSIS REQUIREMENTS:
- Reference your previous analysis: "Building on my previous analysis where I noted the score was 1-0..."
- Acknowledge cumulative context: "This adds to the 3 shots I previously tracked for Edmonton..."
- Maintain narrative consistency: "Following the penalty I identified earlier, this power play opportunity..."

GAME CONTEXT AVAILABLE:
- Static roster data with player names and team assignments
- Live activity data with enhanced player names (use "PlayerName (team)" format)
- Progressive game statistics that should build cumulatively
- Penalty details with timing and expiration information

You'll receive timestamp data sequentially. Always reference your previous responses in this session to maintain realistic game progression.

Ready to begin real-time NHL game analysis with full temporal awareness?
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
        user_id=f"commentary_agent_{game_id}"
    )
    
    # Initialize commentary session context (like test script does)
    initial_context = UserContent(parts=[Part(text=f"""
You are now the live commentary team for NHL game {game_id}.
Throughout this session:
- Maintain natural conversational flow between Alex Chen and Mike Rodriguez
- Build on each other's observations organically, as real broadcasters do
- Vary your dialogue and avoid repetitive phrases
- Use names occasionally for transitions or direct questions (not every exchange)
- Let the conversation flow naturally without forced acknowledgments

You'll receive live game data at different timestamps. Generate appropriate commentary for each moment.
Ready to begin commentary for this session?
""")])
    
    # Send initial context to establish broadcaster names
    async for event in commentary_runner.run_async(
        user_id=commentary_session.user_id,
        session_id=commentary_session.id,
        new_message=initial_context,
    ):
        pass  # Just establish context, don't need the response
    
    print(f"✅ Data session created: {data_session.id}")
    print(f"✅ Data session initialized with temporal game state awareness")
    print(f"✅ Commentary session created: {commentary_session.id}")
    print(f"✅ Commentary session initialized with broadcaster context")
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

async def process_data_agent(timestamp_file: str, runner, session) -> Dict[str, Any]:
    """Process timestamp file with data agent using shared session"""
    try:
        # Load timestamp data
        with open(timestamp_file, 'r') as f:
            timestamp_data = json.load(f)
        
        # Process using shared session with temporal context
        from google.genai.types import Part, UserContent
        
        # Extract timing information for context
        game_time = timestamp_data.get('game_time', 'Unknown')
        activity_count = timestamp_data.get('activity_count', 0)
        
        input_text = f"""
TIMESTAMP ANALYSIS - {game_time}
Building on your previous analysis in this session, analyze this new timestamp data:

TEMPORAL CONTEXT:
- Current game time: {game_time}
- Events in this window: {activity_count}
- Reference your previous session analysis for cumulative state

ANALYSIS REQUIREMENTS:
- Maintain score continuity from your previous analysis
- Track cumulative shot totals and penalty situations
- Build on power play states you've previously identified
- Validate all player names against roster data
- Ensure timeline flows logically from your last analysis

RAW TIMESTAMP DATA:
{json.dumps(timestamp_data, indent=2)}

Provide your analysis maintaining full game state consistency with your previous responses in this session.
"""
        content = UserContent(parts=[Part(text=input_text)])
        
        response_text = ""
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,  # SAME SESSION - preserves penalties!
            new_message=content,
        ):
            if event.content.parts and event.content.parts[0].text:
                response_text = event.content.parts[0].text
        
        # Parse and save result
        result = json.loads(response_text)
        
        # Save data agent output in game-specific subfolder
        game_id = session.user_id.split('_')[-1]
        game_time = os.path.basename(timestamp_file).replace(f"{game_id}_", "").replace(".json", "")
        output_dir = f"data/data_agent_outputs/{game_id}"
        os.makedirs(output_dir, exist_ok=True)
        output_file = f"{output_dir}/{game_time}_adk.json"
        
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        return {"status": "success", "data": result, "output_file": output_file}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def process_commentary_agent(data_output_file: str, game_id: str, commentary_runner=None, commentary_session=None):
    """Process with commentary agent using session awareness"""
    try:
        # Load data agent output
        with open(data_output_file, 'r') as f:
            data_agent_output = json.load(f)
        
        # Extract timestamp for context
        filename_base = os.path.basename(data_output_file).replace('_adk.json', '')
        timestamp_parts = filename_base.split('_')
        if len(timestamp_parts) >= 4:
            period = timestamp_parts[1]
            minutes = timestamp_parts[2]
            seconds = timestamp_parts[3]
            game_time = f"Period {period}, {minutes}:{seconds}"
        else:
            game_time = "Unknown time"
        
        # Create input for commentary agent with narrative context
        from google.genai.types import Part, UserContent
        
        # Extract key context for narrative continuity
        game_context = data_agent_output.get("for_commentary_agent", {}).get("game_context", {})
        current_score = f"{game_context.get('away_score', 0)}-{game_context.get('home_score', 0)}"
        momentum_score = data_agent_output.get("for_commentary_agent", {}).get("momentum_score", 0)
        
        input_text = f"""
LIVE COMMENTARY - {game_time}
Building on our ongoing broadcast conversation, provide commentary for this moment:

NARRATIVE CONTEXT:
- Current Score: {current_score}
- Game Time: {game_time}
- Momentum Level: {momentum_score}
- Build on previous commentary in this session
- Maintain Alex Chen & Mike Rodriguez dialogue flow

SESSION CONTINUITY REQUIREMENTS:
- Reference previous commentary themes you've established this session
- Don't repeat recent talking points or player mentions
- Maintain natural conversation progression from your last exchange
- Acknowledge game state changes from your previous commentary
- Keep broadcast energy consistent with established momentum

DATA AGENT ANALYSIS:
{json.dumps(data_agent_output, indent=2)}

Generate natural commentary that flows seamlessly from your previous dialogue in this broadcast session, maintaining professional hockey broadcast standards.
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
        output_file = f"{output_dir}/{filename_base.replace(game_id + '_', '')}_commentary_session_aware.json"
        
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

def process_audio_agent(commentary_output: Dict[str, Any]):
    """Process with audio agent (placeholder for now)"""
    # For now, just indicate audio would be processed
    return {"status": "success", "message": "Audio processing would happen here"}

async def process_timestamp_with_all_agents(timestamp_file: str, data_runner, data_session, commentary_runner, commentary_session) -> Dict[str, Any]:
    """Process a single timestamp through all agents with shared sessions"""
    file_basename = os.path.basename(timestamp_file)
    print(f"  ⏰ Processing: {file_basename}")
    
    # Step 1: Data Agent with shared session
    data_result = await process_data_agent(timestamp_file, data_runner, data_session)
    if data_result["status"] != "success":
        print(f"    ❌ Data agent failed: {data_result['error']}")
        return data_result
    
    print(f"    ✅ Data agent completed")
    
    # Step 2: Commentary Agent with shared session
    game_id = data_session.user_id.split('_')[-1]
    commentary_result = await process_commentary_agent(
        data_result["output_file"], 
        game_id,
        commentary_runner,
        commentary_session
    )
    if commentary_result["status"] != "success":
        print(f"    ❌ Commentary agent failed: {commentary_result['error']}")
        return commentary_result
    
    print(f"    ✅ Commentary agent completed")
    
    # Step 3: Audio Agent
    audio_result = process_audio_agent(commentary_result)
    print(f"    ✅ Audio agent completed")
    
    return {
        "status": "success",
        "timestamp": file_basename,
        "data_result": data_result,
        "commentary_result": commentary_result,
        "audio_result": audio_result
    }

async def run_live_commentary_pipeline(game_id: str, duration_minutes: int = 5):
    """Main pipeline function - orchestrates everything"""
    print(f"🚀 NHL Live Commentary Pipeline")
    print(f"🎯 Game ID: {game_id}")
    print(f"⏱️  Duration: {duration_minutes} minutes")
    print("=" * 50)
    
    try:
        # Phase 1: Generate static context
        await generate_static_context(game_id)
        
        # Phase 2: Start live data collection (background)
        live_process = start_live_data_collection(game_id, duration_minutes)
        
        # Phase 3: Create shared sessions for data and commentary agents
        (data_runner, data_session), (commentary_runner, commentary_session) = await create_shared_sessions(game_id)
        
        # Phase 4: Process timestamps as they appear
        print(f"🔄 Starting real-time processing...")
        processed_files = set()
        processed_count = 0
        
        while live_process.poll() is None:  # While live data collection is running
            # Check for new timestamp files
            new_files = get_new_timestamp_files(game_id, processed_files)
            
            for timestamp_file in new_files:
                result = await process_timestamp_with_all_agents(timestamp_file, data_runner, data_session, commentary_runner, commentary_session)
                processed_files.add(timestamp_file)
                processed_count += 1
                
                if result["status"] == "success":
                    print(f"✅ Processed timestamp {processed_count}: {result['timestamp']}")
                else:
                    print(f"❌ Failed to process {timestamp_file}: {result.get('error', 'Unknown error')}")
            
            # Check every 2 seconds for new files
            time.sleep(2)
        
        # Process any remaining files after live collection ends
        print("🏁 Live data collection finished, processing remaining files...")
        time.sleep(3)  # Allow final files to be written
        
        final_new_files = get_new_timestamp_files(game_id, processed_files)
        for timestamp_file in final_new_files:
            result = await process_timestamp_with_all_agents(timestamp_file, data_runner, data_session, commentary_runner, commentary_session)
            processed_count += 1
            if result["status"] == "success":
                print(f"✅ Final processing {processed_count}: {result['timestamp']}")
        
        print("=" * 50)
        print(f"🎉 Pipeline completed successfully!")
        print(f"📊 Total timestamps processed: {processed_count}")
        print(f"📁 Check data/ directories for generated files")
        
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        return False
    
    return True

async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python live_commentary_pipeline.py GAME_ID [DURATION_MINUTES]")
        print("Example: python live_commentary_pipeline.py 2024030412 3")
        print("\nThis runs the complete pipeline:")
        print("  1. Generate static context")
        print("  2. Start live data collection")  
        print("  3. Process each timestamp with persistent session")
        print("  4. Generate commentary and audio in real-time")
        sys.exit(1)
    
    game_id = sys.argv[1]
    duration = float(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    success = await run_live_commentary_pipeline(game_id, duration)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())