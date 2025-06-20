#!/usr/bin/env python3
"""
NHL Live Commentary Pipeline v2 - Simplified Architecture
Clean implementation with proper Sequential Agent usage and timestamp ordering.

Key Improvements:
- Single Sequential Agent per game (no per-timestamp creation)
- Timestamp ordering queue for sequential output
- GameBoard and static context injected at agent creation
- Simplified architecture (~300 lines vs 540+)
- Parallel data collection with sequential processing

Usage: python live_commentary_pipeline_v2.py GAME_ID [DURATION_MINUTES]
"""

import sys
import os
import json
import time
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import dotenv
from datetime import datetime
from collections import OrderedDict
import re

# Load environment variables
dotenv.load_dotenv()

# Add src to path for imports
sys.path.append('src')
sys.path.append('src/agents/sequential_agent')
sys.path.append('src/board')
# Import configuration and components
from src.config.pipeline_config import config
from board import create_live_game_board
from agents.sequential_agent_v2.agent import create_nhl_sequential_agent


class TimestampOrderingQueue:
    """Ensures chronological processing of timestamps even with parallel file detection"""
    
    def __init__(self):
        self.pending_files = OrderedDict()  # {(period, minute, second): file_path}
        self.processed_timestamps = set()
        self.next_expected = (1, 0, 0)  # Start with period 1, 0:00
        self.processing_lock = asyncio.Lock()
        self.new_file_event = asyncio.Event()
        
    def extract_timestamp(self, file_path: str) -> Optional[Tuple[int, int, int]]:
        """Extract period, minute, second from filename"""
        filename = os.path.basename(file_path)
        # Pattern: GAME_ID_PERIOD_MM_SS.json
        match = re.search(r'_(\d+)_(\d{2})_(\d{2})\.json$', filename)
        if match:
            period = int(match.group(1))
            minute = int(match.group(2))
            second = int(match.group(3))
            return (period, minute, second)
        return None
    
    async def add_file(self, file_path: str):
        """Add file to queue, signal if next in sequence is available"""
        timestamp = self.extract_timestamp(file_path)
        if timestamp and timestamp not in self.processed_timestamps:
            async with self.processing_lock:
                self.pending_files[timestamp] = file_path
                self.pending_files = OrderedDict(sorted(self.pending_files.items()))
                self.new_file_event.set()
    
    async def get_next_sequential_file(self) -> Optional[str]:
        """Get the next file in chronological order"""
        while True:
            async with self.processing_lock:
                # Check if next expected timestamp is available
                if self.next_expected in self.pending_files:
                    file_path = self.pending_files.pop(self.next_expected)
                    self.processed_timestamps.add(self.next_expected)
                    
                    # Calculate next expected timestamp (15-second intervals)
                    period, minute, second = self.next_expected
                    second += 15
                    if second >= 60:
                        second = 0
                        minute += 1
                        if minute >= 20:  # Assume 20-minute periods
                            minute = 0
                            period += 1
                    
                    self.next_expected = (period, minute, second)
                    return file_path
            
            # Wait for new files to arrive
            await self.new_file_event.wait()
            self.new_file_event.clear()


class SimplifiedPipeline:
    """Simplified pipeline with clean architecture"""
    
    def __init__(self, game_id: str, duration_minutes: int):
        self.game_id = game_id
        self.duration_minutes = duration_minutes
        self.game_board = None
        self.sequential_agent = None
        self.static_context = None
        self.batch_summary = ""  # Simple summary for batch continuity
        self.timestamp_queue = TimestampOrderingQueue()
        self.processing_stats = {
            "total_processed": 0,
            "processing_times": [],
            "start_time": None,
            "context_stats": []
        }
        
    async def initialize(self):
        """Initialize pipeline components"""
        print(f"🏒 NHL Live Commentary Pipeline v2 - Game {self.game_id}")
        print(f"⏱️  Duration: {self.duration_minutes} minutes")
        
        # Generate static context (using light generator)
        print("\n📋 Generating static context...")
        await self.generate_static_context()
        
        # Create GameBoard (simplified)
        print("🎯 Initializing GameBoard...")
        self.game_board = create_live_game_board(self.game_id)
        
        # Create Sequential Agent with full context
        print("🤖 Creating Sequential Agent with context...")
        await self.create_sequential_agent_with_context()
        
        print("✅ Pipeline initialized successfully\n")
        
    async def generate_static_context(self):
        """Generate static context using light generator for efficiency"""
        minimal_path = f"{config.DATA_BASE_PATH}/static/game_{self.game_id}_minimal_context.json"
        
        # Check if minimal context already exists
        if os.path.exists(minimal_path):
            print(f"📋 Using existing minimal context: {os.path.basename(minimal_path)}")
        else:
            # Generate full context first if needed
            full_path = f"{config.DATA_BASE_PATH}/static/game_{self.game_id}_static_context.json"
            if not os.path.exists(full_path):
                print("🔧 Generating full static context first...")
                cmd = ["python", "src/data/static/static_info_generator.py", self.game_id]
                result = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode != 0:
                    print(f"❌ Static context generation failed: {stderr.decode()}")
                    raise RuntimeError("Failed to generate static context")
            
            # Generate minimal context using light generator
            print("🔧 Creating minimal context using light generator...")
            cmd = ["python", "src/data/static/light_static_info_generator.py", self.game_id]
            result = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                print(f"❌ Light static context generation failed: {stderr.decode()}")
                raise RuntimeError("Failed to generate light static context")
        
        # Load the minimal static context
        with open(minimal_path, 'r') as f:
            self.static_context = json.load(f)
            
        print(f"✅ Light static context loaded: {len(json.dumps(self.static_context)):,} characters")
        print(f"   Focus: 2 teams only, essential data")
        
    async def create_sequential_agent_with_context(self):
        """Create Sequential Agent with GameBoard and static context injected"""
        # Get initial game board context
        board_context = self.game_board.get_state()
        
        # Create agent (simple interface, no complex context injection)
        self.sequential_agent = create_nhl_sequential_agent(self.game_id)
        
        # Initialize the agent with its persistent session
        await self.sequential_agent.initialize()
        
        print("✅ Sequential Agent created with persistent session")
        print("   ↳ Broadcasters handled by commentary agent")
        
    async def start_and_monitor_data_collection(self):
        """Start data collection and let it run continuously"""
        print("📊 Starting continuous data collection...")
        
        cmd = [
            "python", "src/data/live/live_data_collector.py",
            "simulate", self.game_id,
            "--game_duration_minutes", str(self.duration_minutes),
            "--fetch_interval_seconds", "15"  # Optimized: 15s intervals for realistic hockey timing
        ]
        
        # Start subprocess
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        print(f"✅ Data collection started (PID: {process.pid})")
        
        # Wait for process to complete (or be cancelled)
        try:
            await process.wait()
            print("📊 Data collection completed")
        except asyncio.CancelledError:
            print("📊 Data collection cancelled")
            process.terminate()
            await process.wait()
        
    async def monitor_and_queue_files(self):
        """Monitor for new timestamp files and add to ordering queue immediately"""
        live_data_dir = f"{config.DATA_BASE_PATH}/live/{self.game_id}"
        os.makedirs(live_data_dir, exist_ok=True)
        
        processed_files = set()
        
        print(f"📂 Monitoring directory: {live_data_dir}")
        print("⚡ Ready for immediate processing as files appear...")
        
        while True:
            try:
                # Check for new files frequently for immediate detection
                current_files = set(Path(live_data_dir).glob(f"{self.game_id}_*.json"))
                
                # Find new files
                new_files = current_files - processed_files
                
                # Add new files to ordering queue immediately
                for file_path in new_files:
                    await self.timestamp_queue.add_file(str(file_path))
                    print(f"📁 Detected & queued: {file_path.name}")
                    
                processed_files.update(new_files)
                
                # Quick check interval for immediate detection
                await asyncio.sleep(0.2)  # Check every 200ms for faster response
                
            except Exception as e:
                print(f"❌ File monitoring error: {e}")
                await asyncio.sleep(1)
                
    async def process_timestamps_immediately(self):
        """Process timestamps in batches of 3 for efficiency"""
        self.processing_stats["start_time"] = time.time()
        batch_files = []
        
        while True:
            try:
                # Collect files for batch (up to 3)
                file_path = await asyncio.wait_for(
                    self.timestamp_queue.get_next_sequential_file(),
                    timeout=20.0  # Shorter timeout for batching
                )
                
                if file_path:
                    batch_files.append(file_path)
                    print(f"📁 Added to batch: {os.path.basename(file_path)} (batch size: {len(batch_files)})")
                    
                    # Process batch when we have 3 files or timeout
                    if len(batch_files) >= 3:
                        print(f"🎯 Processing batch of {len(batch_files)} files")
                        await self.process_timestamp_batch(batch_files)
                        batch_files = []  # Reset for next batch
                    
            except asyncio.TimeoutError:
                # Process remaining files in incomplete batch
                if batch_files:
                    await self.process_timestamp_batch(batch_files)
                    batch_files = []
                
                # Stop if no new files for 20 seconds (timeout reached)
                print("⏱️  No new files for 20 seconds, assuming data generation is complete...")
                await asyncio.sleep(15)  # Wait another 15 seconds to be sure
                
                # Try one more time to get files
                try:
                    file_path = await asyncio.wait_for(
                        self.timestamp_queue.get_next_sequential_file(),
                        timeout=5.0  # Short timeout
                    )
                    if file_path:
                        batch_files.append(file_path)
                        print(f"📁 Found late file: {os.path.basename(file_path)}")
                        continue
                except asyncio.TimeoutError:
                    pass
                
                print("✅ Data generation appears complete, stopping processing")
                print("🏁 Processing pipeline finished")
                break
    
    async def process_timestamp_batch(self, timestamp_files: list):
        """Process batch of up to 3 timestamps in single session for efficiency"""
        from google.adk.runners import InMemoryRunner
        
        batch_size = len(timestamp_files)
        if batch_size > 3:
            raise ValueError("Batch size limited to 3 timestamps")
        
        print(f"⚡ Processing batch of {batch_size} timestamps...")
        start_time = time.time()
        
        try:
            # Create single session for entire batch
            runner = InMemoryRunner(agent=self.sequential_agent.agent)
            session = await runner.session_service.create_session(
                app_name=runner.app_name,
                user_id=f"batch_{self.game_id}_{batch_size}_files"
            )
            
            batch_results = []
            
            for i, timestamp_file in enumerate(timestamp_files):
                file_start = time.time()
                filename = os.path.basename(timestamp_file)
                
                # Load timestamp data to update board
                with open(timestamp_file, 'r') as f:
                    timestamp_data = json.load(f)
                
                # Update GameBoard
                board_update = self.game_board.update_from_timestamp(timestamp_data)
                board_context = self.game_board.get_state()
                
                # No continuity context - just board state
                continuity_context = None
                
                # Process through Sequential Agent with shared session
                result = await self.sequential_agent.process_with_session(
                    timestamp_file,
                    session,
                    runner,
                    board_context,
                    continuity_context
                )
                
                batch_results.append(result)
                file_time = time.time() - file_start
                
                print(f"  ✅ Batch {i+1}/{batch_size}: {filename} ({file_time:.2f}s)")
            
            # Create simple summary for next batch
            self.batch_summary = self._create_simple_batch_summary(batch_results)
            
            # Batch stats
            batch_time = time.time() - start_time
            avg_per_file = batch_time / batch_size
            
            print(f"🎯 Batch completed: {batch_time:.2f}s total, {avg_per_file:.2f}s avg per file")
            
            if avg_per_file > 5.0:
                print(f"⚠️  Batch average exceeded 5s target: {avg_per_file:.2f}s")
            
            return batch_results
            
        except Exception as e:
            print(f"❌ Batch processing error: {e}")
            # Return errors for all files in batch
            return [{"status": "error", "error": str(e)} for _ in timestamp_files]
    
    def _create_simple_batch_summary(self, batch_results: list) -> str:
        """Create simple summary of batch for next batch continuity"""
        try:
            summary_parts = []
            
            for result in batch_results:
                if result.get("status") == "success" and "clean_result" in result:
                    clean_result = result["clean_result"]
                    if "commentary_agent" in clean_result and "commentary_sequence" in clean_result["commentary_agent"]:
                        # Extract key points from commentary
                        sequence = clean_result["commentary_agent"]["commentary_sequence"]
                        if sequence:
                            # Just take a brief summary of what was discussed
                            first_comment = sequence[0].get("text", "")[:100] + "..."
                            summary_parts.append(f"Recent: {first_comment}")
            
            if summary_parts:
                return "Previous batch discussed: " + " | ".join(summary_parts[-2:])  # Keep last 2 only
            return ""
            
        except Exception:
            return ""  # Fail gracefully
            
    def print_final_stats(self):
        """Print final processing statistics including context management"""
        stats = self.processing_stats
        if not stats["processing_times"]:
            print("\n📊 No timestamps processed")
            return
            
        avg_time = sum(stats["processing_times"]) / len(stats["processing_times"])
        under_5s = sum(1 for t in stats["processing_times"] if t < 5.0)
        
        # Context stats
        # Simple stats without complex context tracking
        
        print("\n📊 Final Processing Statistics:")
        print(f"   Total processed: {stats['total_processed']} timestamps")
        print(f"   Average time: {avg_time:.2f}s")
        print(f"   Min time: {min(stats['processing_times']):.2f}s")
        print(f"   Max time: {max(stats['processing_times']):.2f}s")
        print(f"   Under 5s: {under_5s}/{len(stats['processing_times'])} ({under_5s/len(stats['processing_times'])*100:.1f}%)")
        
        print(f"\n🧠 Context Management:")
        print(f"   Window size: {context_final['window_size']} (fixed)")
        print(f"   Players tracked: {context_final['players_tracked']}")
        print(f"   Themes tracked: {context_final['themes_tracked']}")
        print(f"   Last speaker: {context_final['last_speaker']}")
        print(f"   Memory usage: {context_final['context_memory_usage']}")
        
        if stats["context_stats"]:
            avg_context_size = sum(s["context_size"] for s in stats["context_stats"]) / len(stats["context_stats"])
            print(f"   Avg context size: {avg_context_size:.0f} chars (bounded)")
            print("   ✅ No context accumulation - fixed sliding window")
        
    async def run(self):
        """Run the complete pipeline with true parallel processing"""
        try:
            # Initialize pipeline
            await self.initialize()
            
            print("🚀 Starting parallel data generation and immediate processing...")
            
            # Create parallel tasks - both start immediately
            data_task = asyncio.create_task(self.start_and_monitor_data_collection())
            monitor_task = asyncio.create_task(self.monitor_and_queue_files())
            process_task = asyncio.create_task(self.process_timestamps_immediately())
            
            # Wait for processing to complete (data generation may continue)
            await process_task
            
            # Clean up tasks
            data_task.cancel()
            monitor_task.cancel()
            
            # Print final statistics
            self.print_final_stats()
            
            print("\n🎉 Pipeline completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Pipeline error: {e}")
            raise


async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python live_commentary_pipeline_v2.py GAME_ID [DURATION_MINUTES]")
        print("Example: python live_commentary_pipeline_v2.py 2024030412 2")
        sys.exit(1)
    
    game_id = sys.argv[1]
    duration_minutes = float(sys.argv[2]) if len(sys.argv) > 2 else 2
    
    # Create and run pipeline
    pipeline = SimplifiedPipeline(game_id, duration_minutes)
    await pipeline.run()


if __name__ == "__main__":
    asyncio.run(main())