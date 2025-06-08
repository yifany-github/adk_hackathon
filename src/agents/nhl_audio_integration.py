#!/usr/bin/env python3
"""
NHL Audio Integration - Connects Audio Agent with existing commentary system
Bridges the live data collector with the audio streaming agent
"""
import sys
import os
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.audio_agent import AudioAgent
from agents.audio_config import get_voice_config, get_scenario_settings
from data.live.live_data_collector import LiveDataCollector


class NHLAudioIntegration:
    """
    Integration bridge between NHL live data collector and Audio Agent
    
    This class:
    1. Monitors the live commentary output from LiveDataCollector
    2. Sends new commentary to Audio Agent for TTS conversion
    3. Streams audio via WebSocket to connected clients
    4. Provides unified control interface
    """
    
    def __init__(
        self,
        game_id: str,
        scenario: str = "live_game",
        voice_type: str = None,
        websocket_port: int = None
    ):
        self.game_id = game_id
        self.scenario = scenario
        
        # Get configuration
        self.settings = get_scenario_settings(scenario)
        if not self.settings:
            raise ValueError(f"Unknown scenario: {scenario}")
        
        voice = voice_type or self.settings["voice"]
        self.voice_config = get_voice_config(voice)
        if not self.voice_config:
            raise ValueError(f"Unknown voice type: {voice}")
        
        port = websocket_port or self.settings["websocket_port"]
        
        # Initialize components
        self.data_collector = LiveDataCollector(game_id)
        self.audio_agent = AudioAgent(
            name=f"nhl_audio_integration_{game_id}",
            description=f"NHL Audio Integration for game {game_id}",
            voice_name=self.voice_config.name,
            audio_encoding=self.settings["encoding"].upper(),
            speaking_rate=self.voice_config.speaking_rate,
            websocket_port=port
        )
        
        # State tracking
        self.is_running = False
        self.last_processed_time = None
        self.processed_files = set()
        
        print(f"🏒 NHL Audio Integration Ready")
        print(f"🎮 Game ID: {game_id}")
        print(f"🎙️ Voice: {voice} ({self.voice_config.description})")
        print(f"📡 WebSocket: {port}")
        print(f"📊 Scenario: {scenario}")
    
    async def start_integrated_system(self, duration_minutes: float = 10):
        """
        Start the complete integrated system:
        1. Audio Agent WebSocket server
        2. Live data collection
        3. Commentary-to-audio processing
        """
        print(f"\n🚀 Starting NHL Audio Integration System")
        print(f"⏱️ Duration: {duration_minutes} minutes")
        print(f"📁 Open examples/audio_client.html and connect to ws://localhost:{self.audio_agent.websocket_port}")
        print()
        
        self.is_running = True
        
        try:
            # Start Audio Agent WebSocket server
            audio_task = asyncio.create_task(
                self.audio_agent.start_websocket_server()
            )
            
            # Start live data collection
            data_task = asyncio.create_task(
                self.data_collector.start_live_collection(duration_minutes)
            )
            
            # Start commentary monitoring and audio processing
            monitor_task = asyncio.create_task(
                self._monitor_commentary_files()
            )
            
            # Wait for all tasks
            await asyncio.gather(data_task, return_exceptions=True)
            
            # Stop monitoring
            self.is_running = False
            monitor_task.cancel()
            
            print("\n✅ NHL Audio Integration completed successfully")
            
        except KeyboardInterrupt:
            print("\n🛑 Stopping NHL Audio Integration...")
            self.is_running = False
            await self.audio_agent.stop_streaming()
            print("✅ System stopped")
        
        except Exception as e:
            print(f"❌ Integration error: {e}")
            self.is_running = False
            raise
    
    async def _monitor_commentary_files(self):
        """Monitor for new commentary files and process them for audio"""
        descriptions_dir = os.path.join(self.data_collector.output_dir, "descriptions")
        
        print(f"👁️ Monitoring commentary files in: {descriptions_dir}")
        
        while self.is_running:
            try:
                await asyncio.sleep(2)  # Check every 2 seconds
                
                if not os.path.exists(descriptions_dir):
                    continue
                
                # Find new description files for this game
                files = [
                    f for f in os.listdir(descriptions_dir)
                    if f.startswith(f"game_{self.game_id}_") and f.endswith("_description.json")
                    and f not in self.processed_files
                ]
                
                # Process new files
                for filename in sorted(files):
                    filepath = os.path.join(descriptions_dir, filename)
                    await self._process_commentary_file(filepath)
                    self.processed_files.add(filename)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️ Commentary monitoring error: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _process_commentary_file(self, filepath: str):
        """Process a single commentary file and send to Audio Agent"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Extract commentary text
            commentary_text = data.get("description", "").strip()
            if not commentary_text or commentary_text == "No significant events in the recent action":
                return  # Skip empty or placeholder commentary
            
            # Extract metadata
            metadata = {
                "game_id": self.game_id,
                "game_time": data.get("game_time", "Unknown"),
                "timestamp": data.get("timestamp", datetime.now().isoformat()),
                "activity_count": data.get("activity_count", 0),
                "source": "live_data_collector",
                "file": os.path.basename(filepath)
            }
            
            # Send to Audio Agent
            result = await self.audio_agent.process_commentary(commentary_text, metadata)
            
            if result.get("success"):
                print(f"🎵 Audio generated: {commentary_text[:60]}...")
                print(f"   ⏱️ Processing: {result['processing_time_seconds']:.2f}s")
                print(f"   📊 Connected clients: {result['connected_clients']}")
            else:
                print(f"❌ Audio generation failed: {result.get('error')}")
                
        except Exception as e:
            print(f"⚠️ Error processing {filepath}: {e}")
    
    async def send_manual_commentary(self, text: str, metadata: Dict[str, Any] = None):
        """Send manual commentary text to Audio Agent"""
        if not metadata:
            metadata = {
                "game_id": self.game_id,
                "source": "manual_input",
                "timestamp": datetime.now().isoformat()
            }
        
        result = await self.audio_agent.process_commentary(text, metadata)
        return result
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            "integration_running": self.is_running,
            "game_id": self.game_id,
            "scenario": self.scenario,
            "voice_config": {
                "name": self.voice_config.name,
                "speaking_rate": self.voice_config.speaking_rate,
                "description": self.voice_config.description
            },
            "audio_agent_stats": self.audio_agent.get_audio_stats(),
            "processed_files": len(self.processed_files),
            "last_processed": self.last_processed_time
        }


# Standalone integration script
async def run_nhl_audio_integration(
    game_id: str,
    duration_minutes: float = 10,
    scenario: str = "live_game",
    voice_type: str = None,
    port: int = None
):
    """Run the complete NHL Audio Integration system"""
    integration = NHLAudioIntegration(
        game_id=game_id,
        scenario=scenario,
        voice_type=voice_type,
        websocket_port=port
    )
    
    await integration.start_integrated_system(duration_minutes)


# CLI interface
def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="NHL Audio Integration - Live Commentary with Audio Streaming",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic integration for 5 minutes
  python nhl_audio_integration.py 2024020001 --duration 5
  
  # Use analyst voice for detailed commentary
  python nhl_audio_integration.py 2024020001 --scenario analysis --voice analyst
  
  # Custom port and extended duration
  python nhl_audio_integration.py 2024020001 --port 9000 --duration 30
        """
    )
    
    parser.add_argument("game_id", help="NHL game ID (e.g., 2024020001)")
    
    parser.add_argument(
        "--duration",
        type=float,
        default=10,
        help="Duration in minutes (default: 10)"
    )
    
    parser.add_argument(
        "--scenario",
        default="live_game",
        choices=["live_game", "highlights", "analysis", "radio_broadcast"],
        help="Commentary scenario (default: live_game)"
    )
    
    parser.add_argument(
        "--voice",
        choices=["play_by_play", "color_commentary", "arena_announcer", "radio_host", "analyst"],
        help="Voice type override"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        help="WebSocket port override"
    )
    
    args = parser.parse_args()
    
    print("🏒 NHL Audio Integration System")
    print("=" * 50)
    print(f"🎮 Game ID: {args.game_id}")
    print(f"⏱️ Duration: {args.duration} minutes")
    print(f"📊 Scenario: {args.scenario}")
    if args.voice:
        print(f"🎙️ Voice: {args.voice}")
    if args.port:
        print(f"📡 Port: {args.port}")
    print()
    
    try:
        asyncio.run(run_nhl_audio_integration(
            game_id=args.game_id,
            duration_minutes=args.duration,
            scenario=args.scenario,
            voice_type=args.voice,
            port=args.port
        ))
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 