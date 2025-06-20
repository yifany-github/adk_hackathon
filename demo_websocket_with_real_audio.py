#!/usr/bin/env python3
"""
WebSocket Demo with Real Audio Generation
Demonstrates the Web Client functionality with actual TTS audio
"""

import asyncio
import sys
import os
import json
import base64
import time
from datetime import datetime

# Add src to path
sys.path.append('src')

async def demo_websocket_with_real_audio():
    """Demo WebSocket server with real NHL commentary audio"""
    try:
        print("🏒 NHL Commentary WebSocket Demo with Real Audio")
        print("=" * 60)
        
        # Import the audio agent tools
        from src.agents.audio_agent.tool import start_websocket_server, stop_websocket_server, audio_processor, text_to_speech
        
        # Start server
        print("🚀 Starting WebSocket server...")
        server = await start_websocket_server(host="localhost", port=8765)
        
        if server:
            print("✅ WebSocket server started successfully!")
            print("🌐 Server running on: ws://localhost:8765")
            print("📁 Open web_client.html in your browser to connect")
            print("⏰ Demo will run for 90 seconds with real commentary...")
            
            # Wait for client connections
            print("\n⏳ Waiting 10 seconds for client connections...")
            await asyncio.sleep(10)
            
            # Send game info
            await send_game_info()
            
            # Generate and send real NHL commentary
            await generate_and_send_real_commentary()
            
            # Wait a bit more
            print("\n⏰ Demo ending in 10 seconds...")
            await asyncio.sleep(10)
            
            # Stop server
            print("🛑 Stopping WebSocket server...")
            await stop_websocket_server()
            print("✅ WebSocket server stopped")
            
        else:
            print("❌ Failed to start WebSocket server")
            
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

async def send_game_info():
    """Send game information to clients"""
    try:
        game_info = {
            "type": "game_info",
            "teams": {
                "away": "FLA",
                "home": "EDM"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        await broadcast_to_clients(game_info)
        print("📋 Sent game information")
        
    except Exception as e:
        print(f"❌ Error sending game info: {e}")

async def generate_and_send_real_commentary():
    """Generate real TTS audio and send to clients"""
    try:
        from src.agents.audio_agent.tool import audio_processor
        
        if not audio_processor.connected_clients:
            print("📢 No clients connected - real commentary will not be sent")
            return
        
        print(f"📡 Generating real commentary for {len(audio_processor.connected_clients)} clients...")
        
        # Commentary segments to generate
        commentary_segments = [
            {
                "speaker": "Alex Chen",
                "text": "Welcome to Rogers Place! We have an exciting matchup tonight between the Florida Panthers and Edmonton Oilers!",
                "voice_style": "enthusiastic"
            },
            {
                "speaker": "Mike Rodriguez", 
                "text": "That's right Alex! The Oilers are looking strong on home ice. Connor McDavid has been absolutely phenomenal this season.",
                "voice_style": "calm"
            },
            {
                "speaker": "Alex Chen",
                "text": "McDavid takes the puck! He's flying down the ice with incredible speed! What a player!",
                "voice_style": "enthusiastic"
            },
            {
                "speaker": "Mike Rodriguez",
                "text": "His acceleration is just incredible to watch. That's why he's considered one of the best players in the world.",
                "voice_style": "calm"
            }
        ]
        
        # Generate and send each segment
        for i, segment in enumerate(commentary_segments):
            print(f"\n🎙️ Generating audio {i+1}/{len(commentary_segments)}: {segment['speaker']}")
            
            try:
                # Generate TTS audio
                tts_result = await text_to_speech(
                    text=segment["text"],
                    voice_style=segment["voice_style"],
                    speaker=segment["speaker"],
                    game_id="demo",
                    game_timestamp=f"demo_{i}",
                    segment_index=i
                )
                
                if tts_result["status"] == "success":
                    print(f"✅ Audio generated successfully: {tts_result.get('audio_id', 'unknown')}")
                    
                    # Send commentary text first
                    commentary_message = {
                        "type": "commentary_text",
                        "speaker": segment["speaker"],
                        "text": segment["text"],
                        "emotion": segment["voice_style"],
                        "timestamp": datetime.now().isoformat(),
                        "segment_index": i
                    }
                    
                    await broadcast_to_clients(commentary_message)
                    print(f"📤 Sent commentary text: {segment['speaker']}")
                    
                    # Wait a moment
                    await asyncio.sleep(1)
                    
                    # Send audio data
                    audio_message = {
                        "type": "audio_segment",
                        "audio_id": tts_result.get("audio_id", f"demo_audio_{i}"),
                        "speaker": segment["speaker"],
                        "text": segment["text"],
                        "voice_style": segment["voice_style"],
                        "timestamp": datetime.now().isoformat(),
                        "segment_index": i,
                        "duration_estimate": 4.0,
                        "pause_after": 1.0,
                        "audio_data": tts_result.get("audio_data", ""),  # This should contain the base64 audio
                        "has_audio": "audio_data" in tts_result and len(tts_result.get("audio_data", "")) > 0
                    }
                    
                    await broadcast_to_clients(audio_message)
                    print(f"🔊 Sent audio segment: {segment['speaker']} ({len(tts_result.get('audio_data', '')) // 1000}KB)")
                    
                else:
                    print(f"❌ Audio generation failed: {tts_result.get('error', 'Unknown error')}")
                    
                    # Send text-only message
                    text_message = {
                        "type": "commentary_text",
                        "speaker": segment["speaker"],
                        "text": segment["text"] + " [Audio generation failed]",
                        "emotion": segment["voice_style"],
                        "timestamp": datetime.now().isoformat(),
                        "segment_index": i
                    }
                    
                    await broadcast_to_clients(text_message)
                
            except Exception as e:
                print(f"❌ Error generating segment {i}: {e}")
            
            # Wait between segments
            await asyncio.sleep(5)
        
        print("✅ Real commentary sequence completed!")
        
    except Exception as e:
        print(f"❌ Error generating real commentary: {e}")
        import traceback
        traceback.print_exc()

async def broadcast_to_clients(message_data):
    """Broadcast message to all connected clients"""
    try:
        from src.agents.audio_agent.tool import audio_processor
        import websockets
        
        if not audio_processor.connected_clients:
            return
        
        message = json.dumps(message_data)
        disconnected_clients = []
        
        for client in audio_processor.connected_clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.append(client)
            except Exception as e:
                print(f"❌ Error sending to client: {e}")
                disconnected_clients.append(client)
        
        # Clean up disconnected clients
        for client in disconnected_clients:
            audio_processor.connected_clients.discard(client)
            
    except Exception as e:
        print(f"❌ Broadcast error: {e}")

def main():
    try:
        print("🌐 Starting NHL Commentary WebSocket Demo with Real Audio...")
        print("📁 Make sure to open web_client.html in your browser!")
        print("🔗 Connect to: ws://localhost:8765")
        print("🎙️ This demo will generate real TTS audio for commentary")
        print("\n" + "="*60)
        
        # Run demo
        asyncio.run(demo_websocket_with_real_audio())
        
        print("\n🎉 Demo completed!")
        print("📁 Check the web client to hear the generated commentary")
        print("🎵 Audio files saved in audio_output/ directory")
        
    except KeyboardInterrupt:
        print("\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")

if __name__ == "__main__":
    main()