#!/usr/bin/env python3
"""
Test No Duplicate Playback
Tests the improved Web Client with controlled audio segment delivery
"""

import asyncio
import sys
import os
import json
import time
from datetime import datetime

# Add src to path
sys.path.append('src')

async def test_controlled_audio_delivery():
    """Test controlled delivery of audio segments to prevent duplicate playback"""
    try:
        print("🧪 Testing Controlled Audio Delivery")
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
            print("⏰ Test will run controlled audio delivery...")
            
            # Wait for client connections
            print("\n⏳ Waiting 15 seconds for client connections...")
            await asyncio.sleep(15)
            
            if not audio_processor.connected_clients:
                print("❌ No clients connected - test cannot proceed")
                print("🔗 Please open web_client.html and connect to ws://localhost:8765")
                await asyncio.sleep(10)
            
            if audio_processor.connected_clients:
                # Send controlled test sequence
                await send_controlled_test_sequence()
            
            # Wait for completion
            print("\n⏰ Test ending in 10 seconds...")
            await asyncio.sleep(10)
            
            # Stop server
            print("🛑 Stopping WebSocket server...")
            await stop_websocket_server()
            print("✅ WebSocket server stopped")
            
        else:
            print("❌ Failed to start WebSocket server")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

async def send_controlled_test_sequence():
    """Send a carefully controlled sequence to test for duplicate playback"""
    try:
        print(f"🎬 Starting controlled test with {len(audio_processor.connected_clients)} clients...")
        
        # Test sequence with deliberate timing
        test_segments = [
            {
                "speaker": "Alex Chen",
                "text": "Test segment ONE - This should play only once",
                "delay": 2
            },
            {
                "speaker": "Mike Rodriguez", 
                "text": "Test segment TWO - Listen for any duplicates",
                "delay": 3
            },
            {
                "speaker": "Alex Chen",
                "text": "Test segment THREE - No overlapping audio should occur",
                "delay": 2
            },
            {
                "speaker": "Mike Rodriguez",
                "text": "Test segment FOUR - Final test segment for duplicate detection",
                "delay": 3
            }
        ]
        
        # Send game info first
        await send_message({
            "type": "game_info",
            "teams": {"away": "TEST", "home": "AUDIO"},
            "timestamp": datetime.now().isoformat()
        })
        print("📋 Sent game information")
        
        # Send each test segment with controlled timing
        for i, segment in enumerate(test_segments):
            print(f"\n🎙️ Sending test segment {i+1}/{len(test_segments)}: {segment['speaker']}")
            
            # Send commentary text first
            await send_message({
                "type": "commentary_text",
                "speaker": segment["speaker"],
                "text": segment["text"],
                "emotion": "neutral",
                "timestamp": datetime.now().isoformat(),
                "segment_index": i
            })
            
            print(f"📤 Sent commentary text: {segment['speaker']}")
            
            # Wait before sending audio (simulate processing time)
            await asyncio.sleep(1)
            
            # Send audio segment with empty data (to test text display without audio conflicts)
            await send_message({
                "type": "audio_segment",
                "audio_id": f"test_audio_{i}",
                "speaker": segment["speaker"],
                "text": segment["text"],
                "voice_style": "neutral",
                "timestamp": datetime.now().isoformat(),
                "segment_index": i,
                "duration_estimate": 3.0,
                "pause_after": 1.0,
                "audio_data": "",  # Empty for test
                "has_audio": False
            })
            
            print(f"🔊 Sent audio segment: {segment['speaker']} (text only)")
            
            # Wait the specified delay before next segment
            print(f"⏱️ Waiting {segment['delay']} seconds before next segment...")
            await asyncio.sleep(segment["delay"])
        
        print("\n✅ Controlled test sequence completed!")
        print("🔍 Check Web Client for:")
        print("   - No duplicate text display")
        print("   - Proper segment ordering")
        print("   - No overlapping or repeated messages")
        
    except Exception as e:
        print(f"❌ Error in controlled test: {e}")

async def send_message(message_data):
    """Send message to all connected clients"""
    try:
        if not audio_processor.connected_clients:
            return
        
        message = json.dumps(message_data)
        disconnected_clients = []
        
        for client in audio_processor.connected_clients:
            try:
                await client.send(message)
            except Exception as e:
                print(f"❌ Error sending to client: {e}")
                disconnected_clients.append(client)
        
        # Clean up disconnected clients
        for client in disconnected_clients:
            audio_processor.connected_clients.discard(client)
            
    except Exception as e:
        print(f"❌ Message send error: {e}")

def main():
    try:
        print("🔍 NHL Commentary Duplicate Playback Test")
        print("📁 Make sure to open web_client.html in your browser!")
        print("🔗 Connect to: ws://localhost:8765")
        print("🎯 This test checks for duplicate playback issues")
        print("\n" + "="*50)
        
        # Run test
        asyncio.run(test_controlled_audio_delivery())
        
        print("\n🎉 Test completed!")
        print("📊 Review the Web Client logs for any duplicate messages")
        
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    main()