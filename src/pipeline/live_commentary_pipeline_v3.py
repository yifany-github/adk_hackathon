#!/usr/bin/env python3
"""
NHL Live Commentary Pipeline v3 - Complete Real-Time Processing with Audio

A complete implementation for processing NHL live data through Data + Commentary + Audio pipeline.
Ensures commentary flows naturally with generated audio files for each timestamp.

Features:
- Complete three-agent processing (Data → Commentary → Audio)
- Sequential real-time processing (process → save → process)
- Guaranteed chronological output order
- Audio files generation with organized naming
- Enhanced session management with audio support
- Production-ready for live streaming with audio

Usage: python src/pipeline/live_commentary_pipeline_v3.py GAME_ID [DURATION_MINUTES]
"""

import sys
import os
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Add root directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Import components
from src.board import create_live_game_board
from src.agents.sequential_agent_v3.agent import create_nhl_sequential_agent_v3
from src.pipeline.utils_v3 import (
    process_timestamp_with_session_v3, 
    create_commentary_context_v3, 
    format_v3_processing_stats,
    save_audio_files_manifest
)


class LivePipelineV3:
    """NHL Live Commentary Pipeline V3 for complete real-time processing with audio"""
    
    def __init__(self, game_id: str, duration_minutes: int):
        self.game_id = game_id
        self.duration_minutes = duration_minutes
        self.game_board = None
        self.sequential_agent = None
        self.current_session = None
        self.current_runner = None
        self.static_context = None
        self.files_processed = 0
        self.all_audio_files = []  # Track all generated audio files
        self.recent_dialogues = []  # For context continuity
        self.processing_stats = {
            "total_processed": 0,
            "processing_times": [],
            "start_time": None,
            "audio_files_generated": 0
        }
        
    async def initialize(self):
        """Initialize pipeline components"""
        print(f"🏒 NHL Live Commentary Pipeline V3 - Game {self.game_id}")
        print(f"⏱️  Duration: {self.duration_minutes} minutes")
        print(f"🎵 Audio Processing: ENABLED (Complete Data + Commentary + Audio)")
        
        await self._generate_static_context()
        self.game_board = create_live_game_board(self.game_id)
        await self._create_sequential_agent()
        
        print("✅ Pipeline V3 initialized successfully")
        
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
        """Create Sequential Agent V3 and initialize session"""
        self.sequential_agent = create_nhl_sequential_agent_v3(self.game_id)
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
        """Process files in chronological order as they arrive (V3 with audio)"""
        self.processing_stats["start_time"] = time.time()
        processed_files = set()
        
        print("🎬 Starting sequential processing with audio generation...")
        
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
                    print(f"🎯 Processing: {next_file.name}")
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
        """Save processing result to output directory (V3 with audio tracking)"""
        # 检查结果状态
        if result.get("status") != "success":
            print(f"⚠️ Skipping save for failed result: {result.get('error', 'Unknown error')}")
            return
            
        response_data = result.get("response")
        if not response_data:
            print(f"⚠️ No response data to save")
            return
            
        basename = os.path.basename(filename).replace('.json', '')
        output_dir = f"data/sequential_agent_v3_outputs/{self.game_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Save main result
        output_file = f"{output_dir}/{basename}_sequential_v3.json"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(response_data, f, indent=2, ensure_ascii=False)
            print(f"💾 Saved result to: {output_file}")
        except Exception as e:
            print(f"❌ Failed to save result: {e}")
            return
        
        # Track audio files from the response
        audio_files = []
        
        # Extract audio files from audio_agent response
        if isinstance(response_data, dict) and "audio_agent" in response_data:
            audio_agent_data = response_data["audio_agent"]
            if audio_agent_data.get("status") == "success":
                audio_segments = audio_agent_data.get("audio_segments", [])
                for segment in audio_segments:
                    if segment.get("status") == "success" and "saved_file" in segment:
                        audio_files.append(segment["saved_file"])
                        
        # Also check the direct audio_files field
        direct_audio_files = result.get("audio_files", [])
        if direct_audio_files:
            audio_files.extend(direct_audio_files)
        
        # Remove duplicates
        audio_files = list(set(audio_files))
        
        if audio_files:
            self.all_audio_files.extend(audio_files)
            self.processing_stats["audio_files_generated"] += len(audio_files)
            print(f"🎵 Generated {len(audio_files)} audio files")
            
            # Print file paths for verification
            for audio_file in audio_files:
                print(f"   📁 {audio_file}")
        
        # Track dialogue for context
        dialogue = result.get("commentary_dialogue", [])
        if dialogue:
            self.recent_dialogues.append(dialogue)
            # Keep only last 5 timestamp dialogues
            if len(self.recent_dialogues) > 5:
                self.recent_dialogues.pop(0)
        
        # Update stats
        if result.get("processing_time"):
            self.processing_stats["processing_times"].append(result["processing_time"])
            self.processing_stats["total_processed"] += 1
    
    async def _process_single_file(self, timestamp_file: str) -> dict:
        """Process a single timestamp file with V3 agent (complete pipeline)"""
        start_time = time.time()
        
        try:
            await self._ensure_session()
            
            # Load timestamp data and update board
            with open(timestamp_file, 'r') as f:
                timestamp_data = json.load(f)
            
            self.game_board.update_from_timestamp(timestamp_data)
            board_context = self.game_board.get_state()
            
            # Create commentary context for continuity
            commentary_context = create_commentary_context_v3(self.recent_dialogues)
            
            # Process timestamp with V3 agent (Data + Commentary + Audio)
            result = await process_timestamp_with_session_v3(
                self.sequential_agent,  # Pass the wrapper, not the inner agent
                self.game_id,
                timestamp_file,
                self.current_session,
                self.current_runner,
                board_context,
                commentary_context
            )
            
            result["processing_time"] = time.time() - start_time
            self.files_processed += 1
            
            return result
            
        except Exception as e:
            self.files_processed += 1
            return {
                "status": "error",
                "error": str(e),
                "processing_time": time.time() - start_time,
                "pipeline_stage": "error"
            }
    
    async def _ensure_session(self):
        """Ensure session exists and refresh if needed (V3 with extended timeout)"""
        # Initialize session if needed
        if self.current_session is None or self.current_runner is None:
            from google.adk.runners import InMemoryRunner
            self.current_runner = InMemoryRunner(agent=self.sequential_agent.agent)
            self.current_session = await self.current_runner.session_service.create_session(
                app_name=self.current_runner.app_name,
                user_id=f"live_v3_{self.game_id}_{self.files_processed}"
            )
        
        # Refresh session every 8 files (more frequent for audio processing)
        elif self.files_processed > 0 and self.files_processed % 8 == 0:
            try:
                await self.current_runner.session_service.delete_session(self.current_session.id)
            except Exception:
                pass  # Ignore deletion errors
            
            self.current_session = await self.current_runner.session_service.create_session(
                app_name=self.current_runner.app_name,
                user_id=f"refreshed_v3_{self.game_id}_{self.files_processed}"
            )
            print(f"🔄 Session refreshed (file #{self.files_processed})")
    
    def print_final_stats(self):
        """Print final processing statistics (V3 enhanced with audio metrics)"""
        stats = format_v3_processing_stats(self.processing_stats, len(self.all_audio_files))
        
        if "error" in stats:
            print("No timestamps processed")
            return
            
        print(f"\n📊 Processing Statistics (Pipeline V3):")
        print(f"  Total processed: {stats['total_processed']} timestamps")
        print(f"  Average time: {stats['average_time']}s")
        print(f"  Min time: {stats['min_time']}s")
        print(f"  Max time: {stats['max_time']}s")
        print(f"  Under 10s: {stats['under_10s_count']}/{stats['total_processed']} ({stats['under_10s_percentage']}%)")
        print(f"  Session refreshes: {stats['session_refreshes']}")
        print(f"\n🎵 Audio Generation Statistics:")
        print(f"  Total audio files: {stats['total_audio_files']}")
        print(f"  Avg files per timestamp: {stats['avg_audio_per_timestamp']}")
        
        # Save audio manifest
        if self.all_audio_files:
            manifest_file = save_audio_files_manifest(self.game_id, self.all_audio_files)
            if manifest_file:
                print(f"  Audio manifest: {manifest_file}")
        
    async def run(self):
        """Run the complete pipeline V3 with sequential real-time processing and audio"""
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
            print("✅ Sequential live processing V3 completed successfully!")
            print(f"🎵 Generated {len(self.all_audio_files)} audio files")
            
        except Exception as e:
            print(f"❌ Pipeline V3 error: {e}")
            raise


async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python src/pipeline/live_commentary_pipeline_v3.py GAME_ID [DURATION_MINUTES]")
        print("Example: python src/pipeline/live_commentary_pipeline_v3.py 2024030412 2")
        print("\n🎵 Pipeline V3 Features:")
        print("  - Complete Data + Commentary + Audio processing")
        print("  - Organized audio file generation")
        print("  - Enhanced session management")
        print("  - Audio files manifest creation")
        sys.exit(1)
    
    game_id = sys.argv[1]
    duration_minutes = float(sys.argv[2]) if len(sys.argv) > 2 else 2
    
    print(f"🚀 Starting NHL Live Commentary Pipeline V3")
    print(f"   Game: {game_id}")
    print(f"   Duration: {duration_minutes} minutes")
    print(f"   Audio: YES (Complete pipeline)")
    
    pipeline = LivePipelineV3(game_id, duration_minutes)
    await pipeline.run()


if __name__ == "__main__":
    asyncio.run(main()) 