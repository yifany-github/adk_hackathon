from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.adk.agents import LlmAgent
import asyncio
import websockets
import json
import base64
import io
import wave
from typing import Dict, Any, Optional, List, Set
import os
import sys
from datetime import datetime
import uuid
import math
import random
import logging

# Add project root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Import configuration
try:
    from config import get_gemini_api_key, get_audio_config, set_gemini_api_key
except ImportError:
    # If config module not found, provide default implementation
    def get_gemini_api_key():
        return os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_AI_API_KEY')
    
    def get_audio_config():
        return {
            "model": "gemini-2.5-flash-preview-tts",
            "default_language": "en-US",
            "websocket_port": 8765
        }


class AudioProcessor:
    """Audio processing class responsible for Gemini TTS and audio stream management"""
    
    def __init__(self):
        # No longer uses any Google Cloud TTS related code
        self.connected_clients: Set = set()
        self.audio_queue = asyncio.Queue()
        
        # Get settings from configuration file
        self.config = get_audio_config()
        
        # Gemini configuration
        self.gemini_model = self.config["model"]
        
        print(f"🎯 Audio Processor initialization completed, using model: {self.gemini_model}")


# Global audio processor instance
audio_processor = AudioProcessor()


async def text_to_speech(
    tool_context: Optional[ToolContext] = None,
    text: str = "", 
    voice_style: str = "enthusiastic",
    language: str = "en-US",
    speaker: str = "",
    emotion: str = "",
    game_id: str = "",
    game_timestamp: str = "",
    segment_index: int = -1
) -> Dict[str, Any]:
    """
    Convert text to speech using real Gemini TTS
    
    Args:
        tool_context: ADK tool context
        text: Commentary text to convert
        voice_style: Voice style (enthusiastic, calm, dramatic)
        language: Language code (en-US, en-CA, etc.)
        speaker: Speaker name (Alex Chen, Mike Rodriguez, etc.)
        emotion: Emotion type (neutral, analytical, excited, etc.)
        
    Returns:
        Dictionary containing audio information and status
    """
    try:
        print(f"🎙️ Gemini TTS: Starting conversion - {text[:50]}...")
        
        # Check API Key
        api_key = get_gemini_api_key()
        if not api_key:
            error_msg = "Gemini API Key not found, please set GEMINI_API_KEY environment variable"
            print(f"❌ {error_msg}")
            
            if tool_context:
                tool_context.state["last_audio_generation"] = {
                    "status": "error",
                    "error": error_msg,
                    "model": "none"
                }
            
            return {
                "status": "error",
                "error": error_msg,
                "text": text[:50] + "..." if len(text) > 50 else text,
                "model": "none"
            }
        
        # Try using real Gemini TTS
        try:
            from google import genai
            from google.genai import types
            
            # Create client
            client = genai.Client(api_key=api_key)
            
            # Select voice based on speaker and emotion/voice_style
            voice_name = _select_voice_for_speaker(speaker, emotion or voice_style)
            
            # Build prompt based on emotion or voice_style
            effective_style = emotion or voice_style
            prompt = _build_prompt_for_emotion(text, effective_style, speaker)
            
            print(f"🔊 Using voice: {voice_name}, style: {voice_style}")
            
            # Call Gemini TTS API
            response = client.models.generate_content(
                model="gemini-2.5-flash-preview-tts",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_name
                            )
                        )
                    )
                )
            )
            
            # Get audio data
            audio_data = response.candidates[0].content.parts[0].inline_data.data
            
            # Generate audio ID
            audio_id = str(uuid.uuid4())[:8]
            timestamp = datetime.now().strftime("%H%M%S")
            
            print(f"✅ Real Gemini TTS successful! Size: {len(audio_data):,} bytes")
            
            # Save audio to file as proper WAV format
            saved_file_path = _save_audio_to_file(audio_data, audio_id, timestamp, voice_style, speaker, game_id, game_timestamp, segment_index)
            
            # Encode audio data
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Prepare WebSocket broadcast data
            broadcast_data = {
                "type": "audio_stream",
                "audio_id": audio_id,
                "text": text,
                "voice_style": voice_style,
                "voice_name": voice_name,
                "timestamp": timestamp,
                "audio_data": audio_base64,
                "format": "wav",
                "model": "gemini-2.5-flash-preview-tts",
                "is_real_tts": True,
                "api_key_status": "configured"
            }
            
            # Broadcast audio
            asyncio.create_task(_broadcast_audio(broadcast_data))
            
            # Update tool context
            if tool_context:
                if "audio_history" not in tool_context.state:
                    tool_context.state["audio_history"] = []
                
                tool_context.state["audio_history"].append({
                    "audio_id": audio_id,
                    "text": text[:100],
                    "timestamp": timestamp,
                    "voice_style": voice_style,
                    "voice_name": voice_name,
                    "model": "gemini-2.5-flash-preview-tts",
                    "is_real_tts": True
                })
                
                tool_context.state["last_audio_generation"] = {
                    "status": "success",
                    "audio_id": audio_id,
                    "duration_estimate": len(text) * 0.05,
                    "model": "gemini-2.5-flash-preview-tts",
                    "is_real_tts": True
                }
            
            return {
                "status": "success",
                "audio_id": audio_id,
                "text_length": len(text),
                "voice_style": voice_style,
                "voice_name": voice_name,
                "language": language,
                "timestamp": timestamp,
                "model": "gemini-2.5-flash-preview-tts",
                "is_real_tts": True,
                "audio_size": len(audio_data),
                "audio_data": audio_base64,  # Return audio data directly
                "saved_file": saved_file_path,  # File path where audio was saved
                "message": f"Real Gemini TTS audio generation successful, ID: {audio_id}"
            }
            
        except ImportError:
            error_msg = "google-genai library not installed, please install: pip install google-genai"
            print(f"❌ {error_msg}")
            
            if tool_context:
                tool_context.state["last_audio_generation"] = {
                    "status": "error",
                    "error": error_msg,
                    "model": "none"
                }
            
            return {
                "status": "error",
                "error": error_msg,
                "text": text[:50] + "..." if len(text) > 50 else text,
                "model": "none"
            }
            
        except Exception as e:
            error_msg = f"Gemini TTS call failed: {str(e)}"
            print(f"❌ {error_msg}")
            
            # Try fallback audio generation
            fallback_result = await _generate_fallback_audio(text, voice_style, tool_context)
            return fallback_result
            
    except Exception as e:
        error_msg = f"Text-to-speech processing failed: {str(e)}"
        print(f"❌ {error_msg}")
        
        if tool_context:
            tool_context.state["last_audio_generation"] = {
                "status": "error",
                "error": error_msg,
                "model": "error"
            }
        
        return {
            "status": "error",
            "error": error_msg,
            "text": text[:50] + "..." if len(text) > 50 else text,
            "model": "error"
        }


async def _generate_fallback_audio(text: str, voice_style: str, tool_context: Optional[ToolContext]) -> Dict[str, Any]:
    """
    Generate fallback audio when Gemini TTS is unavailable
    
    Args:
        text: Text to convert
        voice_style: Voice style
        tool_context: Tool context for state management
        
    Returns:
        Audio generation result
    """
    try:
        print(f"🔄 Generating fallback audio for: {text[:50]}...")
        
        # Generate mock realistic audio
        audio_bytes = _generate_realistic_mock_audio(text, voice_style)
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        # Generate audio ID
        audio_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%H%M%S")
        
        print(f"✅ Fallback audio generated! Size: {len(audio_bytes):,} bytes")
        
        # Save fallback audio to file (it's already in WAV format)
        saved_file_path = _save_fallback_audio_to_file(audio_bytes, audio_id, timestamp, voice_style)
        
        # Prepare WebSocket broadcast data
        broadcast_data = {
            "type": "audio_stream",
            "audio_id": audio_id,
            "text": text,
            "voice_style": voice_style,
            "voice_name": "mock_voice",
            "timestamp": timestamp,
            "audio_data": audio_base64,
            "format": "wav",
            "model": "fallback-mock",
            "is_real_tts": False,
            "api_key_status": "fallback"
        }
        
        # Broadcast audio
        asyncio.create_task(_broadcast_audio(broadcast_data))
        
        # Update tool context
        if tool_context:
            if "audio_history" not in tool_context.state:
                tool_context.state["audio_history"] = []
            
            tool_context.state["audio_history"].append({
                "audio_id": audio_id,
                "text": text[:100],
                "timestamp": timestamp,
                "voice_style": voice_style,
                "voice_name": "mock_voice",
                "model": "fallback-mock",
                "is_real_tts": False
            })
            
            tool_context.state["last_audio_generation"] = {
                "status": "success",
                "audio_id": audio_id,
                "duration_estimate": len(text) * 0.05,
                "model": "fallback-mock",
                "is_real_tts": False
            }
        
        return {
            "status": "success",
            "audio_id": audio_id,
            "text_length": len(text),
            "voice_style": voice_style,
            "voice_name": "mock_voice",
            "language": "en-US",
            "timestamp": timestamp,
            "model": "fallback-mock",
            "is_real_tts": False,
            "audio_size": len(audio_bytes),
            "audio_data": audio_base64,
            "saved_file": saved_file_path,  # File path where audio was saved
            "message": f"Fallback audio generation successful, ID: {audio_id}"
        }
        
    except Exception as e:
        error_msg = f"Fallback audio generation failed: {str(e)}"
        print(f"❌ {error_msg}")
        
        if tool_context:
            tool_context.state["last_audio_generation"] = {
                "status": "error",
                "error": error_msg,
                "model": "fallback-error"
            }
        
        return {
            "status": "error",
            "error": error_msg,
            "text": text[:50] + "..." if len(text) > 50 else text,
            "model": "fallback-error"
        }


async def stream_audio_websocket(
    tool_context: Optional[ToolContext] = None,
    port: int = 8765,
    host: str = "localhost"
) -> Dict[str, Any]:
    """
    Start WebSocket audio streaming server
    
    Args:
        tool_context: ADK tool context
        port: Server port number
        host: Server host address
        
    Returns:
        Server startup result
    """
    try:
        print(f"🌐 Starting WebSocket audio streaming server on {host}:{port}")
        
        # Start WebSocket server
        asyncio.create_task(_start_websocket_server(host, port))
        
        # Wait a moment to ensure server starts
        await asyncio.sleep(0.5)
        
        server_url = f"ws://{host}:{port}"
        print(f"✅ WebSocket server started successfully: {server_url}")
        
        if tool_context:
            tool_context.state["websocket_server"] = {
                "url": server_url,
                "host": host,
                "port": port,
                "status": "running"
            }
        
        return {
            "status": "success",
            "message": f"WebSocket audio streaming server started on {host}:{port}",
            "server_url": server_url,
            "host": host,
            "port": port
        }
        
    except Exception as e:
        error_msg = f"Failed to start WebSocket server: {str(e)}"
        print(f"❌ {error_msg}")
        
        return {
            "status": "error",
            "error": error_msg,
            "host": host,
            "port": port
        }


def get_audio_status(tool_context: Optional[ToolContext]) -> Dict[str, Any]:
    """
    Get current audio system status
    
    Args:
        tool_context: ADK tool context
        
    Returns:
        Audio system status information
    """
    try:
        connected_count = len(audio_processor.connected_clients)
        queue_size = audio_processor.audio_queue.qsize() if hasattr(audio_processor.audio_queue, 'qsize') else 0
        
        # Get audio history from tool context
        audio_history = []
        if tool_context and "audio_history" in tool_context.state:
            audio_history = tool_context.state["audio_history"]
        
        status_info = {
            "connected_clients": connected_count,
            "audio_queue_size": queue_size,
            "audio_history_count": len(audio_history),
            "processor_model": audio_processor.gemini_model,
            "last_generated": audio_history[-1] if audio_history else None,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"📊 Audio Status: {connected_count} clients, {len(audio_history)} audio files generated")
        
        return {
            "status": "success",
            "audio_agent_status": status_info,
            "message": f"Audio system running normally, {connected_count} clients connected"
        }
        
    except Exception as e:
        error_msg = f"Failed to get audio status: {str(e)}"
        print(f"❌ {error_msg}")
        
        return {
            "status": "error",
            "error": error_msg,
            "audio_agent_status": {}
        }


def _apply_voice_style_text(text: str, style: str) -> str:
    """Apply voice style to text (add SSML-like markup)"""
    if style == "enthusiastic":
        return f"<prosody rate='fast' pitch='high'>{text}</prosody>"
    elif style == "dramatic":
        return f"<prosody rate='slow' pitch='low' volume='loud'>{text}</prosody>"
    elif style == "calm":
        return f"<prosody rate='medium' pitch='medium'>{text}</prosody>"
    else:
        return text


def _get_speaking_rate(style: str) -> float:
    """Get speaking rate based on style"""
    return {"enthusiastic": 1.2, "dramatic": 0.9, "calm": 1.0}.get(style, 1.0)


def _get_pitch(style: str) -> float:
    """Get pitch adjustment based on style"""
    return {"enthusiastic": 1.1, "dramatic": 0.8, "calm": 1.0}.get(style, 1.0)


async def _broadcast_audio(data: Dict[str, Any]):
    """
    Broadcast audio data to all connected WebSocket clients
    
    Args:
        data: Audio data to broadcast
    """
    if not audio_processor.connected_clients:
        print("📢 No WebSocket clients connected, skipping broadcast")
        return
    
    message = json.dumps(data)
    disconnected_clients = []
    
    print(f"📢 Broadcasting audio to {len(audio_processor.connected_clients)} clients")
    
    for client in audio_processor.connected_clients:
        try:
            await client.send(message)
        except websockets.exceptions.ConnectionClosed:
            disconnected_clients.append(client)
        except Exception as e:
            print(f"❌ Error broadcasting to client: {e}")
            disconnected_clients.append(client)
    
    # Clean up disconnected clients
    for client in disconnected_clients:
        audio_processor.connected_clients.discard(client)
    
    if disconnected_clients:
        print(f"🧹 Cleaned up {len(disconnected_clients)} disconnected clients")


async def _start_websocket_server(host: str, port: int):
    """Start WebSocket server"""
    async def handle_client(websocket):
        """Handle individual client connections"""
        client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        print(f"🔗 New WebSocket client connected: {client_addr}")
        
        audio_processor.connected_clients.add(websocket)
        
        try:
            # Send welcome message
            welcome_msg = {
                "type": "connection",
                "status": "connected",
                "message": "Connected to NHL Audio Streaming Server",
                "timestamp": datetime.now().isoformat(),
                "client_id": client_addr
            }
            await websocket.send(json.dumps(welcome_msg))
            
            # Listen for client messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await _handle_client_message(websocket, data)
                except json.JSONDecodeError:
                    print(f"❌ Invalid JSON from client {client_addr}: {message}")
                except Exception as e:
                    print(f"❌ Error handling message from {client_addr}: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            print(f"🔌 Client disconnected: {client_addr}")
        except Exception as e:
            print(f"❌ Client connection error {client_addr}: {e}")
        finally:
            audio_processor.connected_clients.discard(websocket)
            print(f"🧹 Cleaned up client: {client_addr}")
    
    try:
        server = await websockets.serve(handle_client, host, port)
        print(f"🎵 WebSocket server listening on {host}:{port}")
        await server.wait_closed()
    except Exception as e:
        print(f"❌ WebSocket server error: {e}")


async def _handle_client_message(websocket, data: Dict[str, Any]):
    """
    Handle messages from WebSocket clients
    
    Args:
        websocket: Client WebSocket connection
        data: Message data from client
    """
    try:
        message_type = data.get("type", "unknown")
        
        if message_type == "ping":
            # Respond to ping
            await websocket.send(json.dumps({
                "type": "pong",
                "timestamp": datetime.now().isoformat()
            }))
        
        elif message_type == "audio_ack":
            # Audio acknowledgment
            audio_id = data.get("audio_id")
            print(f"✅ Client acknowledged audio: {audio_id}")
        
        elif message_type == "status_request":
            # Status request
            status = {
                "type": "status_response",
                "connected_clients": len(audio_processor.connected_clients),
                "server_status": "running",
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(status))
        
        else:
            print(f"❓ Unknown message type from client: {message_type}")
            
    except Exception as e:
        print(f"❌ Error handling client message: {e}")


def _generate_realistic_mock_audio(text: str, voice_style: str) -> bytes:
    """
    Generate realistic mock audio data (for testing when real TTS unavailable)
    
    Args:
        text: Text content
        voice_style: Voice style
        
    Returns:
        Mock audio data as bytes
    """
    try:
        # Calculate approximate duration (words per minute)
        word_count = len(text.split())
        wpm = {"enthusiastic": 180, "dramatic": 120, "calm": 150}.get(voice_style, 160)
        duration_seconds = max(1.0, (word_count / wpm) * 60)
        
        # Generate realistic audio file with proper WAV header
        sample_rate = 24000  # 24kHz to match Gemini TTS
        samples = int(duration_seconds * sample_rate)
        
        # Create WAV file structure
        wav_data = _generate_simple_wav_audio(text, voice_style)
        
        print(f"🎵 Generated mock audio: {len(wav_data):,} bytes, {duration_seconds:.1f}s duration")
        return wav_data
        
    except Exception as e:
        print(f"❌ Mock audio generation error: {e}")
        # Return minimal valid WAV file
        return _generate_simple_wav_audio("error", "calm")


def _save_fallback_audio_to_file(audio_data: bytes, audio_id: str, timestamp: str, voice_style: str) -> str:
    """
    Save fallback audio data to file (already in WAV format)
    
    Args:
        audio_data: WAV audio bytes
        audio_id: Unique audio identifier
        timestamp: Timestamp string
        voice_style: Voice style used
        
    Returns:
        Path to the saved WAV file
    """
    try:
        # Create output directory
        output_dir = "audio_output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"nhl_fallback_{date_str}_{audio_id}_{voice_style}.wav"
        filepath = os.path.join(output_dir, filename)
        
        # Save directly (already WAV format)
        with open(filepath, 'wb') as f:
            f.write(audio_data)
        
        print(f"💾 Fallback audio saved to: {filepath}")
        
        return filepath
        
    except Exception as e:
        print(f"❌ Failed to save fallback audio file: {e}")
        return None


def _save_audio_to_file(audio_data: bytes, audio_id: str, timestamp: str, voice_style: str) -> str:
    """
    Save raw audio data as a proper WAV file
    
    Args:
        audio_data: Raw audio bytes from Gemini TTS
        audio_id: Unique audio identifier
        timestamp: Timestamp string
        voice_style: Voice style used
        
    Returns:
        Path to the saved WAV file
    """
    try:
        # Create output directory
        output_dir = "audio_output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"nhl_commentary_{date_str}_{audio_id}_{voice_style}.wav"
        filepath = os.path.join(output_dir, filename)
        
        # Create proper WAV file from raw audio data
        # Gemini TTS typically outputs 24kHz, 16-bit, mono audio
        output = io.BytesIO()
        
        with wave.open(output, 'wb') as wav_file:
            wav_file.setnchannels(1)        # Mono
            wav_file.setsampwidth(2)        # 16-bit (2 bytes)
            wav_file.setframerate(24000)    # 24kHz sample rate
            wav_file.writeframes(audio_data)
        
        # Save to file
        with open(filepath, 'wb') as f:
            f.write(output.getvalue())
        
        print(f"💾 Audio saved to: {filepath}")
        
        return filepath
        
    except Exception as e:
        print(f"❌ Failed to save audio file: {e}")
        return None


def _generate_simple_wav_audio(text: str, voice_style: str) -> bytes:
    """
    Generate simple WAV audio data
    
    Args:
        text: Text content (affects duration)
        voice_style: Voice style (affects frequency)
        
    Returns:
        WAV audio data as bytes
    """
    # WAV file parameters
    sample_rate = 24000
    word_count = len(text.split())
    duration = max(1.0, word_count * 0.3)  # Roughly 0.3 seconds per word
    samples = int(duration * sample_rate)
    
    # Generate audio samples based on style
    if voice_style == "enthusiastic":
        # Higher frequency, more variation
        base_freq = 220  # A3
        amplitude = 0.3
    elif voice_style == "dramatic":
        # Lower frequency, steady
        base_freq = 110  # A2
        amplitude = 0.4
    else:  # calm
        # Medium frequency
        base_freq = 165  # E3
        amplitude = 0.25
    
    # Generate sine wave with some variation
    audio_data = []
    for i in range(samples):
        t = i / sample_rate
        
        # Add slight frequency modulation for more natural sound
        freq_mod = 1 + 0.1 * math.sin(2 * math.pi * 2 * t)  # 2Hz modulation
        frequency = base_freq * freq_mod
        
        # Generate sample
        sample = amplitude * math.sin(2 * math.pi * frequency * t)
        
        # Add envelope (fade in/out)
        envelope = 1.0
        fade_samples = sample_rate // 10  # 0.1 second fade
        if i < fade_samples:
            envelope = i / fade_samples
        elif i > samples - fade_samples:
            envelope = (samples - i) / fade_samples
        
        sample *= envelope
        
        # Convert to 16-bit PCM
        pcm_sample = int(sample * 32767)
        pcm_sample = max(-32768, min(32767, pcm_sample))
        
        # Little-endian 16-bit
        audio_data.append(pcm_sample & 0xFF)
        audio_data.append((pcm_sample >> 8) & 0xFF)
    
    # Create WAV header
    data_size = len(audio_data)
    file_size = 36 + data_size
    
    wav_header = bytearray([
        # RIFF header
        ord('R'), ord('I'), ord('F'), ord('F'),
        file_size & 0xFF, (file_size >> 8) & 0xFF, (file_size >> 16) & 0xFF, (file_size >> 24) & 0xFF,
        ord('W'), ord('A'), ord('V'), ord('E'),
        
        # fmt chunk
        ord('f'), ord('m'), ord('t'), ord(' '),
        16, 0, 0, 0,  # fmt chunk size
        1, 0,  # PCM format
        1, 0,  # mono
        sample_rate & 0xFF, (sample_rate >> 8) & 0xFF, (sample_rate >> 16) & 0xFF, (sample_rate >> 24) & 0xFF,
        (sample_rate * 2) & 0xFF, ((sample_rate * 2) >> 8) & 0xFF, ((sample_rate * 2) >> 16) & 0xFF, ((sample_rate * 2) >> 24) & 0xFF,
        2, 0,  # block align
        16, 0,  # bits per sample
        
        # data chunk
        ord('d'), ord('a'), ord('t'), ord('a'),
        data_size & 0xFF, (data_size >> 8) & 0xFF, (data_size >> 16) & 0xFF, (data_size >> 24) & 0xFF,
    ])
    
    return bytes(wav_header) + bytes(audio_data)


def _select_voice_for_speaker(speaker: str, emotion_or_style: str) -> str:
    """
    Select appropriate voice based on speaker and emotion/style
    
    Args:
        speaker: Speaker name (Alex Chen, Mike Rodriguez, etc.)
        emotion_or_style: Emotion or voice style
        
    Returns:
        Gemini voice name
    """
    # Speaker-specific voice mapping
    speaker_voices = {
        "Alex Chen": {
            "neutral": "aoede",      # Calm
            "analytical": "aoede",   # Calm
            "excited": "puck",       # Enthusiastic 
            "dramatic": "kore",      # Dramatic
            "enthusiastic": "puck",  # For backward compatibility
            "calm": "aoede"          # For backward compatibility
        },
        "Mike Rodriguez": {
            "neutral": "orus",       # Different calm voice
            "analytical": "orus",    # Different calm voice
            "excited": "charon",     # Different enthusiastic voice
            "dramatic": "fenrir",    # Different dramatic voice
            "enthusiastic": "charon", # For backward compatibility
            "calm": "orus"           # For backward compatibility
        }
    }
    
    # Default voice mapping if speaker not recognized
    default_voices = {
        "neutral": "aoede",
        "analytical": "aoede", 
        "excited": "puck",
        "dramatic": "kore",
        "enthusiastic": "puck",
        "calm": "aoede"
    }
    
    # Get voice for specific speaker, fallback to default
    if speaker in speaker_voices:
        voice = speaker_voices[speaker].get(emotion_or_style.lower())
        if voice:
            return voice.capitalize()  # Gemini expects capitalized names
    
    # Fallback to default voice mapping
    voice = default_voices.get(emotion_or_style.lower(), "aoede")
    return voice.capitalize()


def _build_prompt_for_emotion(text: str, emotion_or_style: str, speaker: str) -> str:
    """
    Build appropriate prompt based on emotion/style and speaker
    
    Args:
        text: Text to convert
        emotion_or_style: Emotion or voice style
        speaker: Speaker name (optional)
        
    Returns:
        Formatted prompt for TTS
    """
    # Speaker context
    speaker_context = ""
    if speaker:
        if "Alex" in speaker:
            speaker_context = "As Alex, a professional play-by-play announcer, "
        elif "Mike" in speaker or "Rodriguez" in speaker:
            speaker_context = "As Mike, an analytical color commentator, "
    
    # Emotion-based prompt variations
    emotion_prompts = {
        "neutral": f"{speaker_context}say in a clear, professional announcer voice: {text}",
        "analytical": f"{speaker_context}say with thoughtful analysis and insight: {text}",
        "excited": f"{speaker_context}say with high energy and excitement like during a big play: {text}",
        "dramatic": f"{speaker_context}say with dramatic intensity and emphasis: {text}",
        "enthusiastic": f"{speaker_context}say with high energy and excitement like a sports announcer: {text}",
        "calm": f"{speaker_context}say in a calm, professional announcer voice: {text}"
    }
    
    return emotion_prompts.get(emotion_or_style.lower(), f"{speaker_context}say clearly: {text}")


def _save_audio_to_file(audio_data: bytes, audio_id: str, timestamp: str, voice_style: str, speaker: str, game_id: str, game_timestamp: str, segment_index: int) -> str:
    """
    Save raw audio data as a proper WAV file with speaker info
    使用新的文件管理器确保文件名唯一性
    
    Args:
        audio_data: Raw audio bytes from Gemini TTS
        audio_id: Unique audio identifier
        timestamp: Timestamp string
        voice_style: Voice style used
        speaker: Speaker name (optional)
        game_id: NHL game ID (optional)
        game_timestamp: Game timestamp like "1_00_05" (optional)
        segment_index: Segment index (optional)
        
    Returns:
        Path to the saved WAV file
    """
    try:
        # Create output directory with game_id subfolder if provided
        if game_id:
            output_dir = os.path.join("audio_output", game_id)
        else:
            output_dir = "audio_output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Use the new audio file manager for unique naming
        if game_id and game_timestamp and speaker:
            from .audio_file_manager import generate_unique_audio_filename
            
            filename, sequence_num = generate_unique_audio_filename(
                game_id=game_id,
                game_timestamp=game_timestamp,
                speaker=speaker,
                voice_style=voice_style,
                audio_id=audio_id
            )
            
            print(f"🔢 Generated unique filename: {filename} (sequence: {sequence_num})")
            
        else:
            # Fallback to original naming for non-game scenarios
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            if speaker:
                speaker_clean = speaker.lower().replace(" ", "").replace(".", "")
                filename = f"nhl_{speaker_clean}_{date_str}_{audio_id}_{voice_style}.wav"
            else:
                filename = f"nhl_commentary_{date_str}_{audio_id}_{voice_style}.wav"
            
        filepath = os.path.join(output_dir, filename)
        
        # Create proper WAV file from raw audio data
        # Gemini TTS typically outputs 24kHz, 16-bit, mono audio
        output = io.BytesIO()
        
        with wave.open(output, 'wb') as wav_file:
            wav_file.setnchannels(1)        # Mono
            wav_file.setsampwidth(2)        # 16-bit (2 bytes)
            wav_file.setframerate(24000)    # 24kHz sample rate
            wav_file.writeframes(audio_data)
        
        # Save to file
        with open(filepath, 'wb') as f:
            f.write(output.getvalue())
        
        print(f"💾 Audio saved to: {filepath}")
        
        return filepath
        
    except Exception as e:
        print(f"❌ Failed to save audio file: {e}")
        return None


# Define AUDIO_TOOLS for ADK integration
AUDIO_TOOLS = [
    FunctionTool(func=text_to_speech),
    FunctionTool(func=stream_audio_websocket),
    FunctionTool(func=get_audio_status)
]
