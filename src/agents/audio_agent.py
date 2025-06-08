#!/usr/bin/env python3
"""
Audio Agent - Real-time TTS and audio streaming using Google ADK
Converts commentary text to speech and streams via WebSocket
"""
import os
import json
import asyncio
import websockets
import io
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime
from google.adk.agents import BaseAgent
from google.cloud import texttospeech
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AudioAgent(BaseAgent):
    """
    Audio Agent for NHL Live Commentary System
    
    Responsibilities:
    - Convert commentary text to speech using Google Cloud TTS
    - Stream audio in real-time via WebSocket
    - Handle multiple audio formats and voice options
    - Manage audio quality and streaming optimization
    """
    
    def __init__(
        self,
        name: str = "audio_agent",
        description: str = "Real-time TTS and audio streaming agent for NHL commentary",
        voice_name: str = "en-US-Studio-M",
        audio_encoding: str = "MP3",
        speaking_rate: float = 1.0,
        websocket_port: int = 8765,
        **kwargs
    ):
        super().__init__(name=name, description=description, **kwargs)
        
        # TTS Configuration
        self.voice_name = voice_name
        self.audio_encoding = audio_encoding
        self.speaking_rate = speaking_rate
        
        # WebSocket Configuration
        self.websocket_port = websocket_port
        self.connected_clients = set()
        
        # Initialize Google Cloud TTS
        self._setup_tts_client()
        
        # Audio processing state
        self.audio_queue = asyncio.Queue()
        self.is_streaming = False
        
        logger.info(f"🎙️ Audio Agent '{name}' initialized")
        logger.info(f"🔊 Voice: {voice_name}, Encoding: {audio_encoding}")
        logger.info(f"🌐 WebSocket Port: {websocket_port}")
    
    def _setup_tts_client(self):
        """Initialize Google Cloud Text-to-Speech client"""
        try:
            self.tts_client = texttospeech.TextToSpeechClient()
            
            # Configure voice settings
            self.voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name=self.voice_name,
                ssml_gender=texttospeech.SsmlVoiceGender.MALE
            )
            
            # Configure audio settings
            encoding_map = {
                "MP3": texttospeech.AudioEncoding.MP3,
                "LINEAR16": texttospeech.AudioEncoding.LINEAR16,
                "OGG_OPUS": texttospeech.AudioEncoding.OGG_OPUS
            }
            
            self.audio_config = texttospeech.AudioConfig(
                audio_encoding=encoding_map.get(self.audio_encoding, texttospeech.AudioEncoding.MP3),
                speaking_rate=self.speaking_rate,
                pitch=0.0,
                volume_gain_db=0.0
            )
            
            logger.info("✅ Google Cloud TTS client configured")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup TTS client: {e}")
            self.tts_client = None
    
    async def process_commentary(self, commentary_text: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main agent method: Convert commentary text to audio and stream
        
        Args:
            commentary_text: The commentary text to convert to speech
            metadata: Additional context (game_time, event_type, etc.)
            
        Returns:
            Dict containing audio processing results
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"🎙️ Processing commentary: {commentary_text[:50]}...")
            
            # Generate audio
            audio_data = await self._text_to_speech(commentary_text)
            if not audio_data:
                return {"error": "Failed to generate audio", "success": False}
            
            # Add to streaming queue
            audio_item = {
                "audio_data": audio_data,
                "text": commentary_text,
                "metadata": metadata or {},
                "timestamp": start_time.isoformat(),
                "encoding": self.audio_encoding
            }
            
            await self.audio_queue.put(audio_item)
            
            # Broadcast to connected clients if streaming
            if self.is_streaming and self.connected_clients:
                await self._broadcast_audio(audio_item)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "audio_length_bytes": len(audio_data),
                "processing_time_seconds": processing_time,
                "text_length": len(commentary_text),
                "connected_clients": len(self.connected_clients),
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing commentary: {e}")
            return {"error": str(e), "success": False}
    
    async def _text_to_speech(self, text: str) -> Optional[bytes]:
        """Convert text to speech using Google Cloud TTS"""
        if not self.tts_client:
            logger.error("❌ TTS client not available")
            return None
        
        try:
            # Prepare the synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Perform the text-to-speech request
            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=self.voice,
                audio_config=self.audio_config
            )
            
            logger.info(f"✅ Generated {len(response.audio_content)} bytes of audio")
            return response.audio_content
            
        except Exception as e:
            logger.error(f"❌ TTS synthesis failed: {e}")
            return None
    
    async def start_websocket_server(self):
        """Start WebSocket server for real-time audio streaming"""
        try:
            logger.info(f"🌐 Starting WebSocket server on port {self.websocket_port}")
            
            server = await websockets.serve(
                self._handle_websocket_client,
                "localhost",
                self.websocket_port
            )
            
            self.is_streaming = True
            logger.info(f"✅ WebSocket server running on ws://localhost:{self.websocket_port}")
            
            # Keep server running
            await server.wait_closed()
            
        except Exception as e:
            logger.error(f"❌ WebSocket server error: {e}")
            self.is_streaming = False
    
    async def _handle_websocket_client(self, websocket, path):
        """Handle individual WebSocket client connections"""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.connected_clients.add(websocket)
        logger.info(f"🔗 Client connected: {client_id} (Total: {len(self.connected_clients)})")
        
        try:
            # Send welcome message
            welcome_msg = {
                "type": "connection",
                "message": "Connected to NHL Audio Stream",
                "audio_format": self.audio_encoding,
                "voice": self.voice_name
            }
            await websocket.send(json.dumps(welcome_msg))
            
            # Keep connection alive and handle messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_client_message(websocket, data)
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ Invalid JSON from {client_id}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔌 Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"❌ Client error {client_id}: {e}")
        finally:
            self.connected_clients.discard(websocket)
            logger.info(f"📊 Remaining clients: {len(self.connected_clients)}")
    
    async def _handle_client_message(self, websocket, data: Dict[str, Any]):
        """Handle messages from WebSocket clients"""
        message_type = data.get("type", "")
        
        if message_type == "ping":
            await websocket.send(json.dumps({"type": "pong"}))
        
        elif message_type == "request_audio":
            # Client requesting specific audio generation
            text = data.get("text", "")
            if text:
                result = await self.process_commentary(text, data.get("metadata", {}))
                await websocket.send(json.dumps({
                    "type": "audio_result",
                    "result": result
                }))
        
        elif message_type == "get_status":
            status = {
                "type": "status",
                "connected_clients": len(self.connected_clients),
                "is_streaming": self.is_streaming,
                "queue_size": self.audio_queue.qsize(),
                "voice": self.voice_name,
                "encoding": self.audio_encoding
            }
            await websocket.send(json.dumps(status))
    
    async def _broadcast_audio(self, audio_item: Dict[str, Any]):
        """Broadcast audio to all connected WebSocket clients"""
        if not self.connected_clients:
            return
        
        # Encode audio data as base64 for JSON transmission
        audio_b64 = base64.b64encode(audio_item["audio_data"]).decode('utf-8')
        
        broadcast_message = {
            "type": "audio_stream",
            "text": audio_item["text"],
            "audio_data": audio_b64,
            "encoding": audio_item["encoding"],
            "timestamp": audio_item["timestamp"],
            "metadata": audio_item["metadata"]
        }
        
        # Send to all connected clients
        disconnected_clients = set()
        for client in self.connected_clients:
            try:
                await client.send(json.dumps(broadcast_message))
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logger.warning(f"⚠️ Broadcast error to client: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        self.connected_clients -= disconnected_clients
        
        logger.info(f"📡 Broadcasted audio to {len(self.connected_clients)} clients")
    
    async def save_audio_file(self, audio_data: bytes, filename: str, output_dir: str = None) -> str:
        """Save audio data to file"""
        if output_dir is None:
            output_dir = "data/audio"
        
        os.makedirs(output_dir, exist_ok=True)
        
        if not filename.endswith(f".{self.audio_encoding.lower()}"):
            filename += f".{self.audio_encoding.lower()}"
        
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, "wb") as f:
            f.write(audio_data)
        
        logger.info(f"💾 Audio saved: {filepath}")
        return filepath
    
    def get_audio_stats(self) -> Dict[str, Any]:
        """Get current audio agent statistics"""
        return {
            "agent_name": self.name,
            "voice_name": self.voice_name,
            "audio_encoding": self.audio_encoding,
            "speaking_rate": self.speaking_rate,
            "websocket_port": self.websocket_port,
            "connected_clients": len(self.connected_clients),
            "is_streaming": self.is_streaming,
            "queue_size": self.audio_queue.qsize(),
            "tts_available": self.tts_client is not None
        }
    
    async def stop_streaming(self):
        """Stop audio streaming and close connections"""
        logger.info("🛑 Stopping audio streaming...")
        self.is_streaming = False
        
        # Close all client connections
        for client in self.connected_clients.copy():
            try:
                await client.close()
            except:
                pass
        
        self.connected_clients.clear()
        logger.info("✅ Audio streaming stopped")


# Example usage and testing
async def test_audio_agent():
    """Test the Audio Agent functionality"""
    print("🧪 Testing Audio Agent...")
    
    # Create audio agent
    agent = AudioAgent(
        name="test_audio_agent",
        voice_name="en-US-Studio-M",
        speaking_rate=1.1
    )
    
    # Test commentary processing
    test_commentary = "Connor McDavid speeds down the left wing and fires a wrist shot that goes wide of the net."
    
    result = await agent.process_commentary(
        test_commentary,
        metadata={"game_time": "1:15:30", "event_type": "shot-on-goal"}
    )
    
    print(f"📊 Processing result: {result}")
    
    # Save test audio
    if result.get("success"):
        # Get audio from queue
        audio_item = await agent.audio_queue.get()
        filepath = await agent.save_audio_file(
            audio_item["audio_data"],
            "test_commentary",
            "data/audio/test"
        )
        print(f"💾 Test audio saved to: {filepath}")
    
    print("✅ Audio Agent test completed")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_audio_agent()) 