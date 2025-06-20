#!/usr/bin/env python3
"""
WebSocket Demo with Mock Audio
Demonstrates the Web Client functionality with mock audio data
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

async def demo_websocket_with_mock_audio():
    """Demo WebSocket server with mock NHL commentary audio"""
    try:
        print("🏒 NHL Commentary WebSocket Demo")
        print("=" * 50)
        
        # Import the audio agent tools
        from src.agents.audio_agent.tool import start_websocket_server, stop_websocket_server, audio_processor
        
        # Start server
        print("🚀 Starting WebSocket server...")
        server = await start_websocket_server(host="localhost", port=8765)
        
        if server:
            print("✅ WebSocket server started successfully!")
            print("🌐 Server running on: ws://localhost:8765")
            print("📁 Open web_client.html in your browser to connect")
            print("⏰ Demo will run for 60 seconds with mock commentary...")
            
            # Wait for client connections
            print("\n⏳ Waiting 10 seconds for client connections...")
            await asyncio.sleep(10)
            
            # Send mock NHL commentary
            await send_mock_commentary_sequence()
            
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

async def send_mock_commentary_sequence():
    """Send a sequence of mock NHL commentary"""
    try:
        from src.agents.audio_agent.tool import audio_processor
        import websockets
        
        if not audio_processor.connected_clients:
            print("📢 No clients connected - mock commentary will not be sent")
            return
        
        print(f"📡 Sending mock commentary to {len(audio_processor.connected_clients)} clients...")
        
        # Mock commentary sequence
        commentary_segments = [
            {
                "speaker": "Alex Chen",
                "text": "Welcome to Rogers Place! We're ready for an exciting game between the Edmonton Oilers and Florida Panthers!",
                "emotion": "enthusiastic",
                "timestamp": "1:00:00"
            },
            {
                "speaker": "Mike Rodriguez", 
                "text": "That's right Alex! The Oilers are looking to capitalize on their home ice advantage tonight.",
                "emotion": "analytical",
                "timestamp": "1:00:05"
            },
            {
                "speaker": "Alex Chen",
                "text": "Connor McDavid takes the puck up ice... he's flying! What speed from the Oilers captain!",
                "emotion": "excited",
                "timestamp": "1:00:10"
            },
            {
                "speaker": "Mike Rodriguez",
                "text": "And that's why he's considered one of the best players in the world. McDavid's acceleration is just incredible to watch.",
                "emotion": "neutral",
                "timestamp": "1:00:15"
            }
        ]
        
        # Send game info first
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
        
        # Send commentary segments with delays
        for i, segment in enumerate(commentary_segments):
            await asyncio.sleep(3)  # 3 second delay between segments
            
            # Send commentary text first
            commentary_message = {
                "type": "commentary_text",
                "speaker": segment["speaker"],
                "text": segment["text"],
                "emotion": segment["emotion"],
                "timestamp": segment["timestamp"],
                "segment_index": i
            }
            
            await broadcast_to_clients(commentary_message)
            print(f"🎙️ Sent commentary: {segment['speaker']} - {segment['text'][:50]}...")
            
            # Send mock audio data (empty for now, but shows the structure)
            audio_message = {
                "type": "audio_segment",
                "audio_id": f"mock_audio_{i}",
                "speaker": segment["speaker"],
                "text": segment["text"],
                "voice_style": segment["emotion"],
                "timestamp": datetime.now().isoformat(),
                "segment_index": i,
                "duration_estimate": 3.0,
                "pause_after": 0.5,
                "audio_data": ""  # Empty for demo - would contain base64 audio in real implementation
            }
            
            await broadcast_to_clients(audio_message)
            print(f"🔊 Sent audio segment: {segment['speaker']}")
        
        print("✅ Mock commentary sequence completed!")
        
    except Exception as e:
        print(f"❌ Error sending mock commentary: {e}")

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
        print("🌐 Starting NHL Commentary WebSocket Demo...")
        print("📁 Make sure to open web_client.html in your browser!")
        print("🔗 Connect to: ws://localhost:8765")
        print("\n" + "="*50)
        
        # Run demo
        asyncio.run(demo_websocket_with_mock_audio())
        
        print("\n🎉 Demo completed!")
        print("📁 Check the web client to see the received commentary")
        
    except KeyboardInterrupt:
        print("\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")

if __name__ == "__main__":
    main()