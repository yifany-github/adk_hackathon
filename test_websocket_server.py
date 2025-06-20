#!/usr/bin/env python3
"""
Simple WebSocket Server Test
Test the WebSocket functionality without running the full pipeline
"""

import asyncio
import sys
import os

# Add src to path
sys.path.append('src')

async def test_websocket_server():
    """Test WebSocket server startup"""
    try:
        print("🧪 Testing WebSocket Server...")
        
        # Import the audio agent tools
        from src.agents.audio_agent.tool import start_websocket_server, stop_websocket_server
        
        # Start server
        print("🚀 Starting WebSocket server...")
        server = await start_websocket_server(host="localhost", port=8765)
        
        if server:
            print("✅ WebSocket server started successfully!")
            print("🌐 Server running on: ws://localhost:8765")
            print("📁 You can now open web_client.html in your browser")
            print("⏰ Server will run for 30 seconds...")
            
            # Run for 30 seconds
            await asyncio.sleep(30)
            
            # Stop server
            print("🛑 Stopping WebSocket server...")
            await stop_websocket_server()
            print("✅ WebSocket server stopped")
            
        else:
            print("❌ Failed to start WebSocket server")
            
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_basic_audio_generation():
    """Test basic audio generation"""
    try:
        print("\n🎵 Testing Basic Audio Generation...")
        
        from src.agents.audio_agent.tool import text_to_speech
        
        # Test TTS
        result = await text_to_speech(
            text="Welcome to the NHL live commentary test!",
            voice_style="enthusiastic",
            speaker="Test Commentator"
        )
        
        if result["status"] == "success":
            print("✅ Audio generation successful!")
            print(f"🎙️ Audio ID: {result.get('audio_id', 'Unknown')}")
            print(f"📁 Saved to: {result.get('saved_file', 'Unknown')}")
        else:
            print(f"❌ Audio generation failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Audio test failed: {e}")

def main():
    print("🏒 NHL Commentary WebSocket & Audio Test")
    print("=" * 50)
    
    try:
        # Run tests
        asyncio.run(test_basic_audio_generation())
        asyncio.run(test_websocket_server())
        
        print("\n🎉 All tests completed!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    main()