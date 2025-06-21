#!/usr/bin/env python3
"""
NHL Live Commentary Pipeline v2 - Sequential Real-Time Processing

A clean implementation for processing NHL live data in chronological order.
Ensures commentary flows naturally without temporal inconsistencies.

Features:
- Sequential real-time processing (process → save → process)
- Guaranteed chronological output order
- Background data collection with foreground processing
- Session management with periodic refresh
- Production-ready for live streaming

Usage: python live_commentary_pipeline_v2.py GAME_ID [DURATION_MINUTES]
"""

import sys
import os
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Add root directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Import components
from src.board import create_live_game_board
from src.agents.sequential_agent_v2.agent import create_nhl_sequential_agent
from src.pipeline.utils import process_timestamp_with_session


class LivePipeline:
    """NHL Live Commentary Pipeline for sequential real-time processing"""
    
    def __init__(self, game_id: str, duration_minutes: int):
        self.game_id = game_id
        self.duration_minutes = duration_minutes
        self.game_board = None
        self.sequential_agent = None
        self.current_session = None
        self.current_runner = None
        self.static_context = None
        self.files_processed = 0
        self.processing_stats = {
            "total_processed": 0,
            "processing_times": [],
            "start_time": None
        }
        
    async def initialize(self):
        """Initialize pipeline components"""
        print(f"🏒 NHL Live Commentary Pipeline v2 - Game {self.game_id}")
        print(f"⏱️  Duration: {self.duration_minutes} minutes")
        
        await self._generate_static_context()
        self.game_board = create_live_game_board(self.game_id)
        await self._create_sequential_agent()
        
        print("✅ Pipeline initialized successfully")
        
    async def _generate_static_context(self):
        """Generate static context using light generator for efficiency"""
        minimal_path = f"data/static/game_{self.game_id}_minimal_context.json"
        
        if not os.path.exists(minimal_path):
            # Generate full context first if needed
            full_path = f"data/static/game_{self.game_id}_static_context.json"
            if not os.path.exists(full_path):
                await self._run_command([
                    "python", "src/data/static/static_info_generator.py", self.game_id
                ], "Static context generation failed")
            
            # Generate minimal context
            await self._run_command([
                "python", "src/data/static/light_static_info_generator.py", self.game_id
            ], "Light static context generation failed")
        
        # Load the minimal static context
        with open(minimal_path, 'r') as f:
            self.static_context = json.load(f)
    
    async def _run_command(self, cmd: list, error_msg: str):
        """Run a subprocess command with error handling"""
        result = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await result.communicate()
        
        if result.returncode != 0:
            raise RuntimeError(f"{error_msg}: {stderr.decode()}")
        
    async def _create_sequential_agent(self):
        """Create Sequential Agent and initialize session"""
        self.sequential_agent = create_nhl_sequential_agent(self.game_id)
        await self.sequential_agent.initialize()
        
    async def start_and_monitor_data_collection(self):
        """Start data collection subprocess in background"""
        cmd = [
            "python", "src/data/live/live_data_collector.py",
            "simulate", self.game_id,
            "--game_duration_minutes", str(self.duration_minutes),
            "--fetch_interval_seconds", "15"
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        
        try:
            await process.wait()
        except asyncio.CancelledError:
            process.terminate()
            await process.wait()
        
                
    async def process_files_sequentially_as_they_arrive(self):
        """Process files in chronological order as they arrive"""
        self.processing_stats["start_time"] = time.time()
        processed_files = set()
        
        while True:
            try:
                await asyncio.sleep(1.0)
                
                live_data_dir = f"data/live/{self.game_id}"
                if not os.path.exists(live_data_dir):
                    continue
                    
                # Get new files and sort chronologically
                available_files = list(Path(live_data_dir).glob(f"{self.game_id}_*.json"))
                new_files = [f for f in available_files if str(f) not in processed_files]
                new_files_sorted = self._sort_files_chronologically(new_files)
                
                # Process next file in chronological order
                if new_files_sorted:
                    next_file = new_files_sorted[0]
                    result = await self._process_single_file(str(next_file))
                    processed_files.add(str(next_file))
                    await self._save_result(str(next_file), result)
                    continue
                
                # Check for completion
                if len(new_files) == 0:
                    await asyncio.sleep(30)
                    final_check_files = list(Path(live_data_dir).glob(f"{self.game_id}_*.json"))
                    final_new = [f for f in final_check_files if str(f) not in processed_files]
                    
                    if len(final_new) == 0:
                        break
                        
            except Exception as e:
                print(f"Sequential processing error: {e}")
                await asyncio.sleep(1)
    
    def _sort_files_chronologically(self, files):
        """Sort files by their timestamp (period, minutes, seconds)"""
        def parse_timestamp(file_path):
            try:
                basename = file_path.name.replace('.json', '')
                parts = basename.split('_')
                if len(parts) >= 4:
                    period = int(parts[1])
                    minutes = int(parts[2]) 
                    seconds = int(parts[3])
                    return (period, minutes, seconds)
            except (ValueError, IndexError):
                pass
            return (999, 999, 999)
        
        return sorted(files, key=parse_timestamp)
    
    async def _save_result(self, filename: str, result: dict):
        """Save processing result to output directory"""
        if result.get("status") != "success" or not result.get("response"):
            return
            
        basename = os.path.basename(filename).replace('.json', '')
        output_dir = f"data/sequential_agent_outputs/{self.game_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = f"{output_dir}/{basename}_sequential.json"
        with open(output_file, 'w') as f:
            json.dump(result["response"], f, indent=2)
        
        # Update stats
        if result.get("processing_time"):
            self.processing_stats["processing_times"].append(result["processing_time"])
            self.processing_stats["total_processed"] += 1
    
    async def _process_single_file(self, timestamp_file: str) -> dict:
        """Process a single timestamp file"""
        start_time = time.time()
        
        try:
            await self._ensure_session()
            
            # Load timestamp data and update board
            with open(timestamp_file, 'r') as f:
                timestamp_data = json.load(f)
            
            self.game_board.update_from_timestamp(timestamp_data)
            board_context = self.game_board.get_state()
            
            # Process timestamp
            result = await process_timestamp_with_session(
                self.sequential_agent.agent,
                self.game_id,
                timestamp_file,
                self.current_session,
                self.current_runner,
                board_context,
                None
            )
            
            result["processing_time"] = time.time() - start_time
            self.files_processed += 1
            
            return result
            
        except Exception as e:
            self.files_processed += 1
            return {
                "status": "error",
                "error": str(e),
                "processing_time": time.time() - start_time
            }
    
    async def _ensure_session(self):
        """Ensure session exists and refresh if needed"""
        # Initialize session if needed
        if self.current_session is None or self.current_runner is None:
            from google.adk.runners import InMemoryRunner
            self.current_runner = InMemoryRunner(agent=self.sequential_agent.agent)
            self.current_session = await self.current_runner.session_service.create_session(
                app_name=self.current_runner.app_name,
                user_id=f"live_{self.game_id}_{self.files_processed}"
            )
        
        # Refresh session every 10 files to prevent accumulation
        elif self.files_processed > 0 and self.files_processed % 10 == 0:
            try:
                await self.current_runner.session_service.delete_session(self.current_session.id)
            except Exception:
                pass  # Ignore deletion errors
            
            self.current_session = await self.current_runner.session_service.create_session(
                app_name=self.current_runner.app_name,
                user_id=f"refreshed_{self.game_id}_{self.files_processed}"
            )
    
    def print_final_stats(self):
        """Print final processing statistics"""
        stats = self.processing_stats
        if not stats["processing_times"]:
            print("No timestamps processed")
            return
            
        avg_time = sum(stats["processing_times"]) / len(stats["processing_times"])
        under_5s = sum(1 for t in stats["processing_times"] if t < 5.0)
        
        print(f"\nProcessing Statistics:")
        print(f"  Total processed: {stats['total_processed']} timestamps")
        print(f"  Average time: {avg_time:.2f}s")
        print(f"  Min time: {min(stats['processing_times']):.2f}s")
        print(f"  Max time: {max(stats['processing_times']):.2f}s")
        print(f"  Under 5s: {under_5s}/{len(stats['processing_times'])} ({under_5s/len(stats['processing_times'])*100:.1f}%)")
        print(f"  Session refreshes: {self.files_processed // 10}")
        
    async def run(self):
        """Run the complete pipeline with sequential real-time processing"""
        try:
            await self.initialize()
            
            # Create tasks: Data generation in background + Sequential processing
            data_task = asyncio.create_task(self.start_and_monitor_data_collection())
            process_task = asyncio.create_task(self.process_files_sequentially_as_they_arrive())
            
            # Wait for sequential processing to complete
            await process_task
            
            # Clean up data generation task
            data_task.cancel()
            
            # Print final statistics
            self.print_final_stats()
            print("Sequential live processing completed successfully")
            
        except Exception as e:
            print(f"Pipeline error: {e}")
            raise


async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python live_commentary_pipeline_v2.py GAME_ID [DURATION_MINUTES]")
        print("Example: python live_commentary_pipeline_v2.py 2024030412 2")
        sys.exit(1)
    
    game_id = sys.argv[1]
    duration_minutes = float(sys.argv[2]) if len(sys.argv) > 2 else 2
    
    pipeline = LivePipeline(game_id, duration_minutes)
    await pipeline.run()


if __name__ == "__main__":
    asyncio.run(main())