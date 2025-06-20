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
sys.path.append('src/agents/sequential_agent')
sys.path.append('src/board')

# Import configuration
from src.config.pipeline_config import config
from board import create_live_game_board, SessionManager
from agents.sequential_agent import create_nhl_sequential_agent, process_timestamp


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
        # Sequential Agent handles sessions internally - no need for complex session management
        
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
            
            # Sequential Agent doesn't need session management - it handles this internally
            # The Sequential Agent creates and manages its own sessions
            
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
        """Process timestamp through Sequential Agent (Data → Commentary → Audio)"""
        
        try:
            # Create Sequential Agent for this game
            sequential_agent = create_nhl_sequential_agent(self.game_id)
            
            # Process through Sequential Agent with board context
            result = await process_timestamp(sequential_agent, timestamp_file, self.game_id, board_context)
            
            if result["status"] == "success":
                return {
                    "status": "success",
                    "sequential_output": result,
                    "audio_files": result.get("audio_files", 0)
                }
            else:
                return {
                    "status": "error",
                    "error": result.get("error", "Sequential agent failed")
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": f"Sequential agent processing failed: {str(e)}"
            }
    
    # Removed - Sequential Agent handles data processing automatically
    
    # Removed - Sequential Agent handles commentary processing automatically
    
    # Removed - Sequential Agent handles audio processing automatically
    
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
    """Create Sequential Agent for real-time processing"""
    print("🤖 Creating Sequential Agent for real-time processing...")
    
    try:
        # Sequential Agent handles all individual agents internally
        sequential_agent = create_nhl_sequential_agent(game_id)
        
        print("✅ Sequential Agent created successfully")
        print("   ↳ Data Agent, Commentary Agent, Audio Agent all integrated")
        
        return {
            "sequential_agent": sequential_agent,
        }
        
    except Exception as e:
        print(f"❌ Sequential Agent creation failed: {e}")
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
        
        # Phase 3: Create Sequential Agent
        print("\nPhase 3: Sequential Agent Creation")
        print("-" * 40)
        agents = await create_realtime_agents(game_id, game_board)
        
        # Phase 4: Initialize real-time processor  
        print("\nPhase 4: Real-Time Processor Initialization")
        print("-" * 40)
        processor = RealTimeProcessor(game_id, game_board, agents)
        print("✅ Real-time processor initialized with Sequential Agent")
        
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
        
        print(f"🎯 Real-time pipeline completed!")
        print(f"📊 Timestamps processed: {perf_stats.get('total_processed', 0)}")
        print(f"⚡ Avg processing time: {perf_stats.get('avg_processing_time', 0):.2f}s")
        print(f"🎭 Performance ratio: {perf_stats.get('performance_ratio', 0):.2%}")
        print(f"🔄 Sequential Agent: Simplified workflow management")
        
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