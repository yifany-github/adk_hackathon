#!/usr/bin/env python3
"""
Run Audio Agent - Standalone script to start the NHL Audio Agent
Supports multiple scenarios and voice configurations
"""
import sys
import os
import asyncio
import argparse
import logging
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.audio_agent import AudioAgent
from agents.audio_config import (
    get_voice_config, get_scenario_settings, 
    list_available_voices, list_available_scenarios
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_audio_agent_server(
    scenario: str = "live_game",
    voice_type: str = None,
    port: int = None,
    duration: int = None
):
    """
    Run the Audio Agent server with specified configuration
    
    Args:
        scenario: Commentary scenario (live_game, highlights, analysis, radio_broadcast)
        voice_type: Override voice type
        port: Override WebSocket port
        duration: How long to run the server (None = indefinite)
    """
    print("🎙️ NHL Audio Agent Server")
    print("=" * 50)
    
    # Get scenario settings
    settings = get_scenario_settings(scenario)
    if not settings:
        print(f"❌ Unknown scenario: {scenario}")
        print(f"Available scenarios: {', '.join(list_available_scenarios())}")
        return False
    
    # Override settings if provided
    voice = voice_type or settings["voice"]
    websocket_port = port or settings["websocket_port"]
    
    # Get voice configuration
    voice_config = get_voice_config(voice)
    if not voice_config:
        print(f"❌ Unknown voice type: {voice}")
        print(f"Available voices: {', '.join(list_available_voices())}")
        return False
    
    print(f"📊 Configuration:")
    print(f"   Scenario: {scenario}")
    print(f"   Voice: {voice} ({voice_config.description})")
    print(f"   Port: {websocket_port}")
    print(f"   Encoding: {settings['encoding']}")
    print(f"   Duration: {'Indefinite' if duration is None else f'{duration} seconds'}")
    print()
    
    try:
        # Create Audio Agent
        agent = AudioAgent(
            name=f"nhl_audio_agent_{scenario}",
            description=f"NHL Audio Agent for {scenario} commentary",
            voice_name=voice_config.name,
            audio_encoding=settings["encoding"].upper(),
            speaking_rate=voice_config.speaking_rate,
            websocket_port=websocket_port
        )
        
        print(f"✅ Audio Agent created successfully")
        print(f"🌐 WebSocket server starting on port {websocket_port}")
        print(f"🎵 Voice: {voice_config.name} at {voice_config.speaking_rate}x speed")
        print(f"📁 Open examples/audio_client.html to test the connection")
        print()
        
        # Start WebSocket server
        server_task = asyncio.create_task(agent.start_websocket_server())
        
        # Optional: Send test commentary periodically
        if scenario == "live_game":
            test_task = asyncio.create_task(
                send_test_commentary(agent, interval=30)
            )
        
        # Run for specified duration or indefinitely
        if duration:
            print(f"⏱️ Running for {duration} seconds...")
            await asyncio.sleep(duration)
            print("⏰ Duration completed, shutting down...")
        else:
            print("🔄 Running indefinitely... Press Ctrl+C to stop")
            await server_task
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Audio Agent...")
        await agent.stop_streaming()
        print("✅ Audio Agent stopped")
        return True
        
    except Exception as e:
        print(f"❌ Error running Audio Agent: {e}")
        logger.exception("Audio Agent error")
        return False


async def send_test_commentary(agent: AudioAgent, interval: int = 30):
    """Send test commentary periodically for demonstration"""
    test_commentaries = [
        "Welcome to tonight's NHL game! The puck is about to drop.",
        "McDavid carries the puck up ice with blazing speed!",
        "What a save by the goaltender! Absolutely spectacular!",
        "GOAL! The crowd erupts as the puck finds the back of the net!",
        "That was a beautiful passing play by the home team.",
        "The power play unit takes the ice looking for an opportunity.",
        "Big hit along the boards! The crowd loves the physical play.",
        "Face-off in the offensive zone, this could be dangerous.",
        "The goalie comes up huge with another tremendous save!",
        "End of the period, what an exciting 20 minutes of hockey!"
    ]
    
    commentary_index = 0
    
    while True:
        try:
            await asyncio.sleep(interval)
            
            if agent.connected_clients:
                commentary = test_commentaries[commentary_index % len(test_commentaries)]
                
                result = await agent.process_commentary(
                    commentary,
                    metadata={
                        "source": "test_sequence",
                        "game_time": f"Period 1 - {commentary_index * 2}:00",
                        "sequence": commentary_index + 1
                    }
                )
                
                if result.get("success"):
                    logger.info(f"📺 Sent test commentary #{commentary_index + 1}")
                else:
                    logger.warning(f"⚠️ Test commentary failed: {result.get('error')}")
                
                commentary_index += 1
            else:
                logger.info("📺 No clients connected, skipping test commentary")
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"❌ Test commentary error: {e}")


def test_audio_agent_cli():
    """Test Audio Agent with command line input"""
    print("🧪 Audio Agent CLI Test Mode")
    print("Type commentary text to convert to speech (or 'quit' to exit)")
    print()
    
    # Create simple test agent
    agent = AudioAgent(
        name="test_agent",
        voice_name="en-US-Studio-M",
        speaking_rate=1.0,
        websocket_port=8769  # Different port for testing
    )
    
    async def cli_loop():
        while True:
            try:
                text = input("🎙️ Commentary: ").strip()
                
                if text.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if not text:
                    continue
                
                print(f"⚡ Processing: {text}")
                
                result = await agent.process_commentary(
                    text,
                    metadata={"source": "cli_test", "timestamp": datetime.now().isoformat()}
                )
                
                if result.get("success"):
                    print(f"✅ Audio generated: {result['audio_length_bytes']} bytes")
                    print(f"⏱️ Processing time: {result['processing_time_seconds']:.2f}s")
                    
                    # Save to file
                    audio_item = await agent.audio_queue.get()
                    filename = f"cli_test_{datetime.now().strftime('%H%M%S')}"
                    filepath = await agent.save_audio_file(
                        audio_item["audio_data"],
                        filename,
                        "data/audio/cli_tests"
                    )
                    print(f"💾 Saved to: {filepath}")
                else:
                    print(f"❌ Error: {result.get('error')}")
                
                print()
                
            except KeyboardInterrupt:
                print("\n🛑 CLI test interrupted")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    asyncio.run(cli_loop())


def main():
    parser = argparse.ArgumentParser(
        description="NHL Audio Agent - Google ADK TTS System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start live game commentary server
  python run_audio_agent.py --scenario live_game
  
  # Use analyst voice on custom port
  python run_audio_agent.py --scenario analysis --voice analyst --port 9000
  
  # Run for 5 minutes only
  python run_audio_agent.py --scenario highlights --duration 300
  
  # CLI testing mode
  python run_audio_agent.py --test-cli
  
  # List available options
  python run_audio_agent.py --list-voices
  python run_audio_agent.py --list-scenarios
        """
    )
    
    parser.add_argument(
        "--scenario", 
        default="live_game",
        help="Commentary scenario (default: live_game)"
    )
    
    parser.add_argument(
        "--voice",
        help="Voice type override"
    )
    
    parser.add_argument(
        "--port", 
        type=int,
        help="WebSocket port override"
    )
    
    parser.add_argument(
        "--duration",
        type=int,
        help="Run duration in seconds (default: indefinite)"
    )
    
    parser.add_argument(
        "--test-cli",
        action="store_true",
        help="Run in CLI test mode"
    )
    
    parser.add_argument(
        "--list-voices",
        action="store_true", 
        help="List available voice types"
    )
    
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="List available scenarios"
    )
    
    args = parser.parse_args()
    
    # Handle list commands
    if args.list_voices:
        print("🎙️ Available Voice Types:")
        for voice_type in list_available_voices():
            config = get_voice_config(voice_type)
            print(f"  {voice_type}: {config.description}")
        return
    
    if args.list_scenarios:
        print("📺 Available Scenarios:")
        for scenario in list_available_scenarios():
            settings = get_scenario_settings(scenario)
            print(f"  {scenario}: {settings['voice']} voice, port {settings['websocket_port']}")
        return
    
    # Handle CLI test mode
    if args.test_cli:
        test_audio_agent_cli()
        return
    
    # Run the server
    success = asyncio.run(run_audio_agent_server(
        scenario=args.scenario,
        voice_type=args.voice,
        port=args.port,
        duration=args.duration
    ))
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 