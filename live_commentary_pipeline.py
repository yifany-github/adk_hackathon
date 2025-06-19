#!/usr/bin/env python3
"""
NHL Live Commentary Pipeline - Real-Time Streaming Edition
Process timestamps as they arrive for true live commentary generation.

Key Features:
- Real-time file monitoring (not batch processing)
- GameBoard persistent caching (ground truth)
- Advanced context optimization 
- Sub-5 second latency target

Usage: python live_commentary_pipeline_realtime.py GAME_ID [DURATION_MINUTES]
"""

import sys
import os
import json
import time
import subprocess
import asyncio
import glob
from pathlib import Path
from typing import Set, List, Dict, Any, Optional
import dotenv
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

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
from board import create_live_game_board, SessionManager


class TimestampFileWatcher(FileSystemEventHandler):
    """Monitors for new timestamp files and queues them for processing"""
    
    def __init__(self, game_id: str, file_queue: asyncio.Queue, loop):
        self.game_id = game_id
        self.file_queue = file_queue
        self.loop = loop
        self.processed_files = set()
        
    def on_created(self, event):
        if not event.is_directory and self.game_id in event.src_path and event.src_path.endswith('.json'):
            filepath = event.src_path
            if filepath not in self.processed_files:
                self.processed_files.add(filepath)
                # Schedule file for processing
                asyncio.run_coroutine_threadsafe(
                    self.file_queue.put(filepath), 
                    self.loop
                )
                print(f"📁 New timestamp file detected: {os.path.basename(filepath)}")


class AdvancedContextManager:
    """Enhanced context management with adaptive optimization"""
    
    def __init__(self):
        self.context_sizes = []
        self.max_context_size = 30000  # Token limit consideration
        self.major_event_triggers = ['goal', 'penalty', 'period_end']
        
    def analyze_context_size(self, prompt: str) -> Dict[str, Any]:
        """Analyze context size and return optimization recommendations"""
        # Rough token estimation (words * 1.3 for tokens)
        word_count = len(prompt.split())
        estimated_tokens = int(word_count * 1.3)
        
        self.context_sizes.append(estimated_tokens)
        
        return {
            "word_count": word_count,
            "estimated_tokens": estimated_tokens,
            "is_oversized": estimated_tokens > self.max_context_size,
            "size_trend": self._get_size_trend(),
            "optimization_needed": estimated_tokens > (self.max_context_size * 0.8)
        }
    
    def _get_size_trend(self) -> str:
        """Analyze recent context size trend"""
        if len(self.context_sizes) < 3:
            return "insufficient_data"
        
        recent = self.context_sizes[-3:]
        if recent[-1] > recent[0] * 1.2:
            return "increasing"
        elif recent[-1] < recent[0] * 0.8:
            return "decreasing"
        else:
            return "stable"
    
    def should_refresh_session(self, context_analysis: Dict, timestamp_count: int, 
                              recent_events: List[Dict]) -> tuple[bool, str]:
        """Determine if session refresh is needed based on multiple factors"""
        
        # Context size trigger
        if context_analysis["is_oversized"]:
            return True, "context_oversized"
        
        # Optimization needed trigger
        if context_analysis["optimization_needed"] and context_analysis["size_trend"] == "increasing":
            return True, "context_optimization"
        
        # Major game events trigger
        if self._detect_major_events(recent_events):
            return True, "major_events"
        
        # Time-based fallback (configurable)
        if timestamp_count % config.SESSION_REFRESH_INTERVAL == 0:
            return True, "time_based"
        
        return False, "no_refresh_needed"
    
    def _detect_major_events(self, recent_events: List[Dict]) -> bool:
        """Detect major game events that warrant session refresh"""
        for event in recent_events[-2:]:  # Check last 2 events
            if any(trigger in str(event.get('type', '')).lower() for trigger in self.major_event_triggers):
                return True
        return False


class AdaptiveSessionManager(SessionManager):
    """Enhanced session manager with adaptive refresh strategy"""
    
    def __init__(self, refresh_interval: int = 10):
        super().__init__(refresh_interval)
        self.context_manager = AdvancedContextManager()
        self.refresh_history = []
        
    async def maybe_refresh_sessions_adaptive(self, data_runner, data_session, 
                                            commentary_runner, commentary_session,
                                            game_board, recent_context: str,
                                            recent_events: List[Dict]):
        """Adaptive session refresh based on context analysis"""
        self.timestamp_count += 1
        
        # Analyze current context
        context_analysis = self.context_manager.analyze_context_size(recent_context)
        
        # Determine if refresh is needed
        should_refresh, reason = self.context_manager.should_refresh_session(
            context_analysis, self.timestamp_count, recent_events
        )
        
        if should_refresh:
            print(f"🔄 Adaptive session refresh triggered: {reason}")
            print(f"   Context size: {context_analysis['estimated_tokens']} tokens")
            print(f"   Timestamp count: {self.timestamp_count}")
            
            # Record refresh for analytics
            self.refresh_history.append({
                "timestamp_count": self.timestamp_count,
                "reason": reason,
                "context_size": context_analysis["estimated_tokens"],
                "timestamp": datetime.now().isoformat()
            })
            
            # Generate optimized narrative summary
            narrative_summary = self._create_optimized_narrative(game_board, context_analysis)
            
            # Create fresh sessions
            new_data_session = await self.create_fresh_data_session(
                data_runner, game_board, narrative_summary
            )
            new_commentary_session = await self.create_fresh_commentary_session(
                commentary_runner, game_board, narrative_summary
            )
            
            print(f"✅ Adaptive session refresh completed")
            return new_data_session, new_commentary_session
        
        return data_session, commentary_session
    
    def _create_optimized_narrative(self, game_board, context_analysis: Dict) -> str:
        """Create optimized narrative summary based on context analysis"""
        base_narrative = game_board.get_narrative_context()
        
        if context_analysis["optimization_needed"]:
            # Apply aggressive compression for oversized contexts
            return self._compress_narrative(base_narrative, compression_level="high")
        else:
            # Standard narrative compression
            return self._compress_narrative(base_narrative, compression_level="standard")
    
    def _compress_narrative(self, narrative: str, compression_level: str) -> str:
        """Compress narrative based on compression level"""
        if compression_level == "high":
            # Keep only essential facts
            lines = narrative.split('. ')
            essential_lines = [line for line in lines if any(keyword in line.lower() 
                             for keyword in ['score:', 'period', 'goal', 'shots:'])]
            return '. '.join(essential_lines[:3])  # Top 3 essential facts
        else:
            # Standard compression - keep recent events
            return narrative
    
    def get_refresh_analytics(self) -> Dict[str, Any]:
        """Get analytics about refresh patterns"""
        if not self.refresh_history:
            return {"total_refreshes": 0}
        
        reasons = [r["reason"] for r in self.refresh_history]
        reason_counts = {reason: reasons.count(reason) for reason in set(reasons)}
        
        return {
            "total_refreshes": len(self.refresh_history),
            "refresh_reasons": reason_counts,
            "avg_context_size_at_refresh": sum(r["context_size"] for r in self.refresh_history) / len(self.refresh_history),
            "last_refresh": self.refresh_history[-1] if self.refresh_history else None
        }


class RealTimeProcessor:
    """Processes timestamps in real-time as they arrive"""
    
    def __init__(self, game_id: str, game_board, agents: Dict):
        self.game_id = game_id
        self.game_board = game_board
        self.agents = agents
        self.processed_count = 0
        self.processing_times = []
        self.session_manager = AdaptiveSessionManager(refresh_interval=config.SESSION_REFRESH_INTERVAL)
        
    async def process_timestamp_realtime(self, timestamp_file: str) -> Dict[str, Any]:
        """Process a single timestamp file with real-time optimizations"""
        start_time = time.time()
        
        try:
            # Load timestamp data
            with open(timestamp_file, 'r') as f:
                timestamp_data = json.load(f)
            
            file_basename = os.path.basename(timestamp_file)
            print(f"⚡ Processing: {file_basename} (realtime)")
            
            # Update GameBoard (sequential for thread safety)
            board_update = self.game_board.update_from_timestamp(timestamp_data)
            
            # Get current board context for agents
            board_context = self.game_board.get_prompt_injection()
            recent_events = board_update.get("new_goals", []) + board_update.get("new_penalties", [])
            
            # Adaptive session management
            data_session, commentary_session = await self.session_manager.maybe_refresh_sessions_adaptive(
                self.agents["data_runner"], self.agents["data_session"],
                self.agents["commentary_runner"], self.agents["commentary_session"],
                self.game_board, board_context, recent_events
            )
            
            # Update session references
            self.agents["data_session"] = data_session
            self.agents["commentary_session"] = commentary_session
            
            # Process through agents (can be parallelized)
            result = await self._process_through_agents(
                timestamp_file, timestamp_data, board_context, board_update
            )
            
            # Record performance metrics
            processing_time = time.time() - start_time
            self.processing_times.append(processing_time)
            self.processed_count += 1
            
            print(f"✅ Completed: {file_basename} ({processing_time:.2f}s)")
            
            # Performance warning if too slow
            if processing_time > 5.0:
                print(f"⚠️  Processing time exceeded 5s target: {processing_time:.2f}s")
            
            return {
                "status": "success",
                "timestamp": file_basename,
                "processing_time": processing_time,
                "board_update": board_update,
                "result": result
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            print(f"❌ Failed: {os.path.basename(timestamp_file)} ({e})")
            return {
                "status": "error",
                "timestamp": os.path.basename(timestamp_file),
                "processing_time": processing_time,
                "error": str(e)
            }
    
    async def _process_through_agents(self, timestamp_file: str, timestamp_data: Dict,
                                    board_context: str, board_update: Dict) -> Dict:
        """Process timestamp through data → commentary → audio agents"""
        
        # Data Agent Processing
        data_result = await self._process_data_agent(timestamp_data, board_context, timestamp_file)
        if data_result["status"] != "success":
            return data_result
        
        # Commentary Agent Processing  
        commentary_result = await self._process_commentary_agent(
            data_result["output"], board_context, timestamp_file
        )
        if commentary_result["status"] != "success":
            return commentary_result
        
        # Audio Agent Processing
        audio_result = await self._process_audio_agent(
            commentary_result["output"], timestamp_file
        )
        
        return {
            "status": "success",
            "data_output": data_result["output"],
            "commentary_output": commentary_result["output"],
            "audio_output": audio_result
        }
    
    async def _process_data_agent(self, timestamp_data: Dict, board_context: str, timestamp_file: str) -> Dict:
        """Process through data agent with board context"""
        try:
            from google.genai.types import Part, UserContent
            
            enhanced_prompt = f"""NHL Data Analysis with Board Integration:

{board_context}

TIMESTAMP DATA TO ANALYZE:
{json.dumps(timestamp_data, indent=2)}

Analyze this timestamp data in context of the authoritative game state above.
Provide key insights about current game situation and notable events."""

            input_content = UserContent(parts=[Part(text=enhanced_prompt)])
            
            result_text = ""
            async for event in self.agents["data_runner"].run_async(
                user_id=self.agents["data_session"].user_id,
                session_id=self.agents["data_session"].id,
                new_message=input_content
            ):
                if hasattr(event, 'content'):
                    result_text += str(event.content)
            
            # Save data agent output
            filename_base = os.path.basename(timestamp_file).replace('.json', '')
            output_dir = f"data/data_agent_outputs/{self.game_id}"
            os.makedirs(output_dir, exist_ok=True)
            
            output_file = f"{output_dir}/{filename_base.replace(f'{self.game_id}_', '')}_adk_board.json"
            output_data = {
                "timestamp": filename_base,
                "game_id": self.game_id,
                "board_context": board_context,
                "data_analysis": result_text,
                "status": "success"
            }
            
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            return {"status": "success", "output": result_text, "output_file": output_file}
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _process_commentary_agent(self, data_output: str, board_context: str, timestamp_file: str) -> Dict:
        """Process through commentary agent with board context"""
        try:
            from google.genai.types import Part, UserContent
            
            enhanced_prompt = f"""NHL Commentary Generation with Board Integration:

{board_context}

DATA AGENT ANALYSIS:
{data_output}

Generate professional two-person broadcast commentary (Alex Chen & Mike Rodriguez) based on the analysis above and current game state. Focus on natural dialogue that builds on the established game narrative."""

            input_content = UserContent(parts=[Part(text=enhanced_prompt)])
            
            result_text = ""
            async for event in self.agents["commentary_runner"].run_async(
                user_id=self.agents["commentary_session"].user_id,
                session_id=self.agents["commentary_session"].id,
                new_message=input_content
            ):
                if hasattr(event, 'content'):
                    result_text += str(event.content)
            
            # Extract clean JSON from ADK response 
            clean_commentary = result_text
            parsed_commentary = None
            
            try:
                # The JSON is nested inside parts=[Part(...text='```json\n{...}\n```')]
                # First extract the text content from the Part
                if "text='" in clean_commentary and "```json" in clean_commentary:
                    # Find the text content within the Part
                    text_start = clean_commentary.find("text='") + 6
                    text_end = clean_commentary.find("')] role=", text_start)
                    if text_end == -1:
                        text_end = len(clean_commentary)
                    
                    extracted_text = clean_commentary[text_start:text_end]
                    
                    # Now extract JSON from the markdown blocks
                    if "```json" in extracted_text:
                        json_start = extracted_text.find("```json") + 7
                        json_end = extracted_text.find("```", json_start)
                        if json_end == -1:
                            json_end = len(extracted_text)
                        
                        json_content = extracted_text[json_start:json_end].strip()
                        # Unescape the JSON
                        json_content = json_content.replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'")
                        
                        # Parse the clean JSON
                        parsed_commentary = json.loads(json_content)
                        print(f"✅ Clean commentary JSON extracted successfully")
                    else:
                        raise ValueError("No ```json block found in extracted text")
                else:
                    # Fallback: try direct JSON extraction
                    if "```json" in clean_commentary:
                        json_start = clean_commentary.find("```json") + 7
                        json_end = clean_commentary.find("```", json_start)
                        if json_end == -1:
                            json_end = len(clean_commentary)
                        clean_commentary = clean_commentary[json_start:json_end].strip()
                        parsed_commentary = json.loads(clean_commentary)
                        print(f"✅ Clean commentary JSON extracted (fallback method)")
                    else:
                        raise ValueError("No JSON content found")
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"⚠️ Failed to parse commentary JSON: {e}")
                # Save raw response as fallback
                parsed_commentary = {"raw_response": result_text, "parse_error": str(e)}
            
            # Save commentary agent output
            filename_base = os.path.basename(timestamp_file).replace('.json', '')
            output_dir = f"data/commentary_agent_outputs/{self.game_id}"
            os.makedirs(output_dir, exist_ok=True)
            
            output_file = f"{output_dir}/{filename_base.replace(f'{self.game_id}_', '')}_commentary_board.json"
            
            # Save the clean parsed commentary (not the raw response)
            with open(output_file, 'w') as f:
                json.dump(parsed_commentary, f, indent=2)
            
            return {"status": "success", "output": parsed_commentary, "output_file": output_file}
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _process_audio_agent(self, commentary_output: str, timestamp_file: str) -> Dict:
        """Process through audio agent for TTS generation"""
        try:
            # Import audio processing functions
            from agents.audio_agent.audio_agent import AudioAgent
            from agents.audio_agent.tool import text_to_speech
            import json
            import re
            
            # Handle clean commentary JSON (now comes as parsed object, not raw text)
            segments = []
            
            if isinstance(commentary_output, dict):
                # If we have clean parsed JSON
                commentary_sequence = commentary_output.get("commentary_sequence", [])
                
                for item in commentary_sequence:
                    if isinstance(item, dict) and "speaker" in item and "text" in item:
                        segments.append({
                            "speaker": item["speaker"],
                            "text": item["text"],
                            "emotion": item.get("emotion", "enthusiastic")
                        })
                
                print(f"🎯 Extracted {len(segments)} commentary segments from clean JSON")
                
            else:
                # Fallback for raw text (shouldn't happen with fixed commentary agent)
                print("⚠️ Received raw text instead of clean JSON, attempting to parse...")
                
                if isinstance(commentary_output, str):
                    # Try to extract segments from raw text
                    lines = commentary_output.split('\n')
                    for line in lines:
                        line = line.strip()
                        if ':' in line and line:
                            parts = line.split(':', 1)
                            if len(parts) == 2:
                                speaker_name = parts[0].strip()
                                dialogue_text = parts[1].strip()
                                
                                if dialogue_text and not any(skip in speaker_name.lower() for skip in 
                                                           ['status', 'type', 'json', 'commentary_type', 'error']):
                                    segments.append({
                                        "speaker": speaker_name,
                                        "text": dialogue_text,
                                        "emotion": "enthusiastic"
                                    })
            
            # If no segments found, create fallback
            if not segments:
                segments = [{
                    "speaker": "Alex Chen",
                    "text": "And the action continues here at the arena.",
                    "emotion": "neutral"
                }]
            
            # Get timestamp from filename for audio naming
            filename_base = os.path.basename(timestamp_file).replace('.json', '').replace(f'{self.game_id}_', '')
            
            # Process each segment through TTS with proper sequencing
            audio_files = []
            for i, segment in enumerate(segments):
                try:
                    # Generate audio using TTS tool with sequence-based naming
                    # Format: {game_id}_{timestamp}_{speaker}_{sequence_number}.wav
                    
                    audio_result = await text_to_speech(
                        text=segment["text"],
                        voice_style="neutral",  # Remove emotion from filename
                        speaker=segment["speaker"],
                        emotion=segment.get("emotion", "neutral"),
                        game_id=self.game_id,
                        game_timestamp=filename_base,
                        segment_index=i  # Use integer index for proper ordering
                    )
                    
                    if audio_result.get("status") == "success":
                        audio_files.extend(audio_result.get("audio_files", []))
                        
                except Exception as audio_error:
                    print(f"⚠️ TTS failed for segment {i}: {audio_error}")
                    continue
            
            # Save audio agent output  
            filename_base = os.path.basename(timestamp_file).replace('.json', '')
            output_dir = f"data/audio_agent_outputs/{self.game_id}"
            os.makedirs(output_dir, exist_ok=True)
            
            output_file = f"{output_dir}/{filename_base.replace(f'{self.game_id}_', '')}_audio_board.json"
            output_data = {
                "timestamp": filename_base,
                "game_id": self.game_id,
                "commentary_input": commentary_output[:500] + "..." if len(commentary_output) > 500 else commentary_output,
                "segments_processed": len(segments),
                "audio_files": audio_files,
                "segments": segments,
                "status": "success"
            }
            
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            return {
                "status": "success",
                "audio_files": audio_files,
                "segments_processed": len(segments),
                "note": f"Generated {len(audio_files)} audio files",
                "output_file": output_file
            }
            
        except Exception as e:
            print(f"❌ Audio agent error: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get processing performance statistics"""
        if not self.processing_times:
            return {"no_data": True}
        
        return {
            "total_processed": self.processed_count,
            "avg_processing_time": sum(self.processing_times) / len(self.processing_times),
            "max_processing_time": max(self.processing_times),
            "min_processing_time": min(self.processing_times),
            "under_5s_count": sum(1 for t in self.processing_times if t < 5.0),
            "performance_ratio": sum(1 for t in self.processing_times if t < 5.0) / len(self.processing_times)
        }


async def create_realtime_agents(game_id: str, game_board) -> Dict:
    """Create and initialize agents for real-time processing"""
    print("🤖 Creating real-time agents...")
    
    try:
        from agents.data_agent.data_agent_adk import create_hockey_agent_for_game
        from agents.commentary_agent.commentary_agent import create_commentary_agent_for_game
        from google.adk.runners import InMemoryRunner
        
        # Create agents
        data_agent = create_hockey_agent_for_game(game_id)
        commentary_agent = create_commentary_agent_for_game(game_id)
        
        # Create runners
        data_runner = InMemoryRunner(agent=data_agent)
        commentary_runner = InMemoryRunner(agent=commentary_agent)
        
        # Create sessions with timeout and retry
        max_retries = 3
        session_timeout = 30.0  # Shorter timeout per attempt
        
        for attempt in range(max_retries):
            try:
                print(f"🔄 Creating ADK sessions (attempt {attempt + 1}/{max_retries})...")
                
                data_session = await asyncio.wait_for(
                    data_runner.session_service.create_session(
                        app_name=data_runner.app_name,
                        user_id=f"realtime_data_{game_id}"
                    ),
                    timeout=session_timeout
                )
                
                commentary_session = await asyncio.wait_for(
                    commentary_runner.session_service.create_session(
                        app_name=commentary_runner.app_name,
                        user_id=f"realtime_commentary_{game_id}"
                    ),
                    timeout=session_timeout
                )
                
                print("✅ ADK sessions created successfully")
                break
                
            except asyncio.TimeoutError:
                print(f"⚠️ ADK session creation timed out (attempt {attempt + 1})")
                if attempt == max_retries - 1:
                    raise Exception("ADK session creation failed after 3 attempts")
                await asyncio.sleep(2)  # Wait before retry
            except Exception as e:
                print(f"⚠️ ADK session creation error: {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2)
        
        print("✅ Real-time agents created successfully")
        
        return {
            "data_agent": data_agent,
            "commentary_agent": commentary_agent,
            "data_runner": data_runner,
            "commentary_runner": commentary_runner,
            "data_session": data_session,
            "commentary_session": commentary_session
        }
        
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        raise


async def start_realtime_file_monitoring(game_id: str, processor: RealTimeProcessor) -> None:
    """Start monitoring for new timestamp files and process them in real-time"""
    
    live_data_dir = f"{config.DATA_BASE_PATH}/live/{game_id}"
    os.makedirs(live_data_dir, exist_ok=True)
    
    # Create async queue for file events
    file_queue = asyncio.Queue()
    
    # Get current event loop for the file watcher
    loop = asyncio.get_event_loop()
    
    # Create file watcher
    event_handler = TimestampFileWatcher(game_id, file_queue, loop)
    observer = Observer()
    observer.schedule(event_handler, live_data_dir, recursive=False)
    observer.start()
    
    print(f"👀 Real-time file monitoring started: {live_data_dir}")
    
    try:
        # Process files as they arrive
        while True:
            try:
                # Wait for new file with timeout
                timestamp_file = await asyncio.wait_for(file_queue.get(), timeout=30.0)
                
                # Process immediately
                await processor.process_timestamp_realtime(timestamp_file)
                
            except asyncio.TimeoutError:
                # No new files for 30 seconds - continue monitoring
                print("⏰ No new files for 30s - continuing to monitor...")
                continue
                
    except KeyboardInterrupt:
        print("\n🛑 File monitoring stopped by user")
    finally:
        observer.stop()
        observer.join()


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
    
    # Brief wait for initialization
    time.sleep(1.0)
    print("✅ Live data collection started")
    return process


async def run_realtime_pipeline(game_id: str, duration_minutes: int = 5):
    """Main real-time pipeline function"""
    print(f"🚀 REAL-TIME PIPELINE STARTING - NHL Live Commentary")
    print(f"Game ID: {game_id}")
    print(f"Duration: {duration_minutes} minutes")
    print("=" * 60)
    
    try:
        # Phase 1: Generate static context
        print("\nPhase 1: Static Context Generation")
        print("-" * 40)
        await generate_static_context(game_id)
        
        # Phase 2: Create GameBoard (persistent cache)
        print("\nPhase 2: GameBoard Creation (Persistent Cache)")
        print("-" * 40)
        static_context_file = f"{config.DATA_BASE_PATH}/static/game_{game_id}_static_context.json"
        game_board = create_live_game_board(game_id, static_context_file)
        print(f"✅ GameBoard cached: {game_board.away_team} @ {game_board.home_team}")
        
        # Phase 3: Create real-time agents
        print("\nPhase 3: Real-Time Agent Creation")
        print("-" * 40)
        agents = await create_realtime_agents(game_id, game_board)
        
        # Phase 4: Initialize real-time processor
        print("\nPhase 4: Real-Time Processor Initialization")
        print("-" * 40)
        processor = RealTimeProcessor(game_id, game_board, agents)
        print("✅ Real-time processor initialized")
        
        # Phase 5: Start live data collection
        print("\nPhase 5: Live Data Collection Start")
        print("-" * 40)
        data_process = start_live_data_collection(game_id, duration_minutes)
        
        # Phase 6: Start real-time monitoring and processing
        print("\nPhase 6: Real-Time Monitoring & Processing")
        print("-" * 40)
        print("🎬 Real-time commentary generation active!")
        
        # Monitor for files and process them
        monitoring_task = asyncio.create_task(
            start_realtime_file_monitoring(game_id, processor)
        )
        
        # Wait for data collection to finish + allow more processing time
        await asyncio.sleep(duration_minutes * 60 + 120)  # Wait for duration + 2min buffer for slow processing
        
        # Stop monitoring
        monitoring_task.cancel()
        
        # Wait for data collection process to finish
        data_process.wait()
        
        # Phase 7: Final statistics and cleanup
        print("\nPhase 7: Final Statistics")
        print("-" * 40)
        
        # Performance statistics
        perf_stats = processor.get_performance_stats()
        refresh_analytics = processor.session_manager.get_refresh_analytics()
        
        print(f"🎯 Real-time pipeline completed!")
        print(f"📊 Timestamps processed: {perf_stats.get('total_processed', 0)}")
        print(f"⚡ Avg processing time: {perf_stats.get('avg_processing_time', 0):.2f}s")
        print(f"🎭 Performance ratio: {perf_stats.get('performance_ratio', 0):.2%}")
        print(f"🔄 Session refreshes: {refresh_analytics.get('total_refreshes', 0)}")
        
        # Export final board state
        final_board_state = game_board.export_state()
        board_export_file = f"data/board_states/game_{game_id}_realtime_final.json"
        os.makedirs("data/board_states", exist_ok=True)
        with open(board_export_file, 'w') as f:
            json.dump(final_board_state, f, indent=2)
        
        print(f"💾 GameBoard state cached to: {board_export_file}")
        
        print("=" * 60)
        print("🎉 REAL-TIME PIPELINE COMPLETED SUCCESSFULLY!")
        
    except Exception as e:
        print(f"❌ Real-time pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def main():
    if len(sys.argv) < 2:
        print("Usage: python live_commentary_pipeline_realtime.py GAME_ID [DURATION_MINUTES]")
        print("Example: python live_commentary_pipeline_realtime.py 2024030412 2")
        print("")
        print("🚀 REAL-TIME NHL COMMENTARY PIPELINE")
        print("Features:")
        print("  1. Real-time timestamp processing (not batch)")
        print("  2. GameBoard persistent caching (ground truth)")
        print("  3. Adaptive context optimization")
        print("  4. Sub-5 second processing target")
        print("  5. Advanced session management")
        sys.exit(1)
    
    game_id = sys.argv[1]
    duration_minutes = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    await run_realtime_pipeline(game_id, duration_minutes)


if __name__ == "__main__":
    asyncio.run(main())