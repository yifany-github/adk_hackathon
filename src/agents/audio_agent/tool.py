from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.adk.agents import LlmAgent
import asyncio
import websockets
import json
import base64
import io
from typing import Dict, Any, Optional, List, Set
import os
import sys
from datetime import datetime
import uuid
import math
import random

# Global server reference for proper shutdown
websocket_server = None
server_task = None

# Load .env file FIRST
import dotenv
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
env_path = os.path.join(project_root, '.env')
dotenv.load_dotenv(env_path)

# 添加项目根目录到路径
sys.path.append(project_root)

# 导入配置
try:
    from config import get_gemini_api_key, get_audio_config, set_gemini_api_key
except ImportError:
    # 如果找不到config模块，提供默认实现 (.env already loaded above)
    def get_gemini_api_key():
        return os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_AI_API_KEY')
    
    def get_audio_config():
        return {
            "model": "gemini-2.5-flash-preview-tts",
            "default_language": "en-US",
            "websocket_port": 8765
        }


class AudioProcessor:
    """音频处理类，负责Gemini TTS和音频流管理"""
    
    def __init__(self):
        # 不再使用任何Google Cloud TTS相关代码
        self.connected_clients: Set = set()
        self.audio_queue = asyncio.Queue()
        
        # 从配置文件获取设置
        self.config = get_audio_config()
        
        # Gemini配置
        self.gemini_model = self.config["model"]
        
        print(f"🎯 Audio Processor初始化完成，使用模型: {self.gemini_model}")


# 全局音频处理器实例
audio_processor = AudioProcessor()


async def text_to_speech(
    tool_context: Optional[ToolContext] = None,
    text: str = "", 
    voice_style: str = "enthusiastic",
    language: str = "en-US"
) -> Dict[str, Any]:
    """
    使用真正的 Gemini TTS 将文本转换为语音
    
    Args:
        tool_context: ADK工具上下文
        text: 需要转换的解说文本
        voice_style: 语音风格 (enthusiastic, calm, dramatic)
        language: 语言代码 (en-US, en-CA等)
        
    Returns:
        包含音频信息和状态的字典
    """
    try:
        print(f"🎙️ Gemini TTS: 开始转换 - {text[:50]}...")
        
        # 检查API Key
        api_key = get_gemini_api_key()
        if not api_key:
            error_msg = "未找到Gemini API Key，请设置GEMINI_API_KEY环境变量"
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
        
        # 尝试使用真正的 Gemini TTS
        try:
            from google import genai
            from google.genai import types
            
            # 创建客户端
            client = genai.Client(api_key=api_key)
            
            # 根据语音风格选择声音
            voice_mapping = {
                "enthusiastic": "Puck",      # 兴奋的声音
                "dramatic": "Kore",          # 戏剧性的声音
                "calm": "Aoede"             # 平静的声音
            }
            
            voice_name = voice_mapping.get(voice_style, "Puck")
            
            # 构建提示词
            if voice_style == "enthusiastic":
                prompt = f"Say with high energy and excitement like a sports announcer: {text}"
            elif voice_style == "dramatic":
                prompt = f"Say with dramatic intensity and emphasis: {text}"
            elif voice_style == "calm":
                prompt = f"Say in a calm, professional announcer voice: {text}"
            else:
                prompt = f"Say clearly: {text}"
            
            print(f"🔊 使用声音: {voice_name}, 风格: {voice_style}")
            
            # 调用 Gemini TTS API
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
            
            # 获取音频数据
            audio_data = response.candidates[0].content.parts[0].inline_data.data
            
            # 生成音频ID
            audio_id = str(uuid.uuid4())[:8]
            timestamp = datetime.now().strftime("%H%M%S")
            
            print(f"✅ 真实Gemini TTS成功! 大小: {len(audio_data):,} 字节")
            
            # 编码音频数据
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # 准备WebSocket广播数据
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
            
            # 广播音频
            asyncio.create_task(_broadcast_audio(broadcast_data))
            
            # 更新工具上下文
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
                "audio_data": audio_base64,  # 直接返回音频数据
                "message": f"真实Gemini TTS音频生成成功，ID: {audio_id}"
            }
            
        except ImportError:
            error_msg = "google-genai库未安装，请安装: pip install google-genai"
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
            error_msg = f"Gemini TTS API调用失败: {str(e)}"
            print(f"❌ {error_msg}")
            
            if tool_context:
                tool_context.state["last_audio_generation"] = {
                    "status": "error",
                    "error": error_msg,
                    "model": "gemini-api-error"
                }
            
            return {
                "status": "error",
                "error": error_msg,
                "text": text[:50] + "..." if len(text) > 50 else text,
                "model": "gemini-api-error"
            }
        
    except Exception as e:
        error_msg = f"音频生成失败: {str(e)}"
        print(f"❌ {error_msg}")
        
        if tool_context:
            tool_context.state["last_audio_generation"] = {
                "status": "error",
                "error": error_msg,
                "model": "unknown-error"
            }
        
        return {
            "status": "error",
            "error": error_msg,
            "text": text[:50] + "..." if len(text) > 50 else text,
            "model": "unknown-error"
        }


async def _generate_fallback_audio(text: str, voice_style: str, tool_context: Optional[ToolContext] = None) -> Dict[str, Any]:
    """生成模拟音频作为备用方案"""
    
    # 生成音频ID
    audio_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%H%M%S")
    
    print(f"🔄 生成模拟音频 (备用方案)")
    
    try:
        # 使用改进的语音模拟方法
        audio_data = _generate_simple_wav_audio(text, voice_style)
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # 准备WebSocket广播数据
        broadcast_data = {
            "type": "audio_stream",
            "audio_id": audio_id,
            "text": text,
            "voice_style": voice_style,
            "timestamp": timestamp,
            "audio_data": audio_base64,
            "format": "wav",
            "model": "fallback_simulation",
            "is_real_tts": False,
            "api_key_status": "fallback"
        }
        
        # 广播音频
        asyncio.create_task(_broadcast_audio(broadcast_data))
        
        # 更新工具上下文
        if tool_context:
            if "audio_history" not in tool_context.state:
                tool_context.state["audio_history"] = []
            
            tool_context.state["audio_history"].append({
                "audio_id": audio_id,
                "text": text[:100],
                "timestamp": timestamp,
                "voice_style": voice_style,
                "model": "fallback_simulation",
                "is_real_tts": False
            })
            
            tool_context.state["last_audio_generation"] = {
                "status": "success",
                "audio_id": audio_id,
                "duration_estimate": len(text) * 0.05,
                "model": "fallback_simulation",
                "is_real_tts": False
            }
        
        return {
            "status": "success",
            "audio_id": audio_id,
            "text_length": len(text),
            "voice_style": voice_style,
            "timestamp": timestamp,
            "model": "fallback_simulation",
            "is_real_tts": False,
            "audio_size": len(audio_data),
            "message": f"模拟音频生成成功 (备用方案)，ID: {audio_id}"
        }
        
    except Exception as e:
        error_msg = f"模拟音频生成失败: {str(e)}"
        print(f"❌ {error_msg}")
        
        return {
            "status": "error",
            "error": error_msg,
            "text": text[:50] + "..." if len(text) > 50 else text,
            "model": "fallback"
        }


def stream_audio_websocket(
    tool_context: Optional[ToolContext] = None,
    port: int = 8765,
    host: str = "localhost"
) -> Dict[str, Any]:
    """
    启动WebSocket服务器进行音频流传输
    """
    try:
        print(f"🌐 启动WebSocket音频流服务器 {host}:{port}")
        
        # 启动WebSocket服务器
        global server_task
        server_task = asyncio.create_task(_start_websocket_server(host, port))
        
        if tool_context:
            tool_context.state["websocket_server"] = {
                "status": "running",
                "host": host,
                "port": port,
                "started_at": datetime.now().isoformat()
            }
        
        return {
            "status": "success",
            "message": f"WebSocket音频流服务器已启动",
            "server_url": f"ws://{host}:{port}",
            "port": port,
            "host": host
        }
        
    except Exception as e:
        error_msg = f"WebSocket服务器启动失败: {str(e)}"
        print(f"❌ {error_msg}")
        
        if tool_context:
            tool_context.state["websocket_server"] = {
                "status": "error",
                "error": error_msg
            }
        
        return {
            "status": "error",
            "error": error_msg
        }


def get_audio_status(tool_context: Optional[ToolContext] = None) -> Dict[str, Any]:
    """获取音频代理状态"""
    try:
        status_info = {
            "connected_clients": len(audio_processor.connected_clients),
            "queue_size": audio_processor.audio_queue.qsize(),
            "model": audio_processor.gemini_model,
            "api_key_configured": bool(get_gemini_api_key()),
            "timestamp": datetime.now().isoformat()
        }
        
        if tool_context:
            audio_history = tool_context.state.get("audio_history", [])
            last_generation = tool_context.state.get("last_audio_generation", {})
            websocket_status = tool_context.state.get("websocket_server", {})
            
            status_info.update({
                "audio_history_count": len(audio_history),
                "last_generation": last_generation,
                "websocket_server": websocket_status,
                "recent_audio": audio_history[-3:] if len(audio_history) > 3 else audio_history
            })
        
        return {
            "status": "success",
            "audio_agent_status": status_info
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"获取状态失败: {str(e)}"
        }


# 辅助函数
def _apply_voice_style_text(text: str, style: str) -> str:
    """根据风格调整文本内容"""
    if style == "enthusiastic":
        return f"{text}!" if not text.endswith(('!', '?', '.')) else text
    elif style == "dramatic":
        return f"*{text}*" if not text.startswith('*') else text
    elif style == "calm":
        return text.rstrip('!') + '.' if text.endswith('!') else text
    else:
        return text


def _get_speaking_rate(style: str) -> float:
    """根据风格设置语速"""
    config = get_audio_config()
    return config.get("speaking_rates", {}).get(style, 1.1)


def _get_pitch(style: str) -> float:
    """根据风格设置音调"""
    config = get_audio_config()
    return config.get("pitch_adjustments", {}).get(style, 0.0)


async def _broadcast_audio(data: Dict[str, Any]):
    """向所有连接的客户端广播音频数据"""
    if not audio_processor.connected_clients:
        print("📡 没有连接的客户端，跳过广播")
        return
    
    message = json.dumps(data)
    disconnected_clients = set()
    
    for client in audio_processor.connected_clients:
        try:
            await client.send(message)
            print(f"📤 音频已发送到客户端")
        except websockets.exceptions.ConnectionClosed:
            disconnected_clients.add(client)
        except Exception as e:
            print(f"❌ 广播失败: {e}")
            disconnected_clients.add(client)
    
    # 清理断开的连接
    for client in disconnected_clients:
        audio_processor.connected_clients.remove(client)


async def _start_websocket_server(host: str, port: int):
    """启动WebSocket服务器"""
    global websocket_server
    
    async def handle_client(websocket):
        print(f"🔗 新客户端连接: {websocket.remote_address}")
        audio_processor.connected_clients.add(websocket)
        
        try:
            # 发送欢迎消息
            welcome_msg = {
                "type": "connection",
                "status": "connected",
                "message": "欢迎连接到NHL Gemini音频流",
                "model": audio_processor.gemini_model,
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(welcome_msg))
            
            # 保持连接
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await _handle_client_message(websocket, data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "无效的JSON格式"
                    }))
                    
        except websockets.exceptions.ConnectionClosed:
            print(f"🔌 客户端断开连接: {websocket.remote_address}")
        except Exception as e:
            print(f"❌ WebSocket处理错误: {e}")
        finally:
            audio_processor.connected_clients.discard(websocket)
    
    try:
        websocket_server = await websockets.serve(handle_client, host, port)
        print(f"🚀 WebSocket音频服务器运行在 ws://{host}:{port}")
        await websocket_server.wait_closed()
    except Exception as e:
        print(f"❌ WebSocket服务器错误: {e}")


async def stop_websocket_server():
    """停止WebSocket服务器"""
    global websocket_server, server_task
    
    try:
        if websocket_server:
            print("🛑 正在停止WebSocket服务器...")
            websocket_server.close()
            await websocket_server.wait_closed()
            websocket_server = None
            print("✅ WebSocket服务器已停止")
        
        if server_task:
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
            server_task = None
            
    except Exception as e:
        print(f"❌ 停止WebSocket服务器时出错: {e}")


async def _handle_client_message(websocket, data: Dict[str, Any]):
    """处理客户端消息"""
    message_type = data.get("type")
    
    if message_type == "ping":
        await websocket.send(json.dumps({
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        }))
    elif message_type == "request_status":
        status = get_audio_status()
        await websocket.send(json.dumps({
            "type": "status_response",
            "data": status
        }))


def _generate_realistic_mock_audio(text: str, voice_style: str) -> bytes:
    """生成可播放的模拟音频数据"""
    
    # 创建一个最小的MP3文件结构
    # 这是一个非常简单的MP3文件，包含短暂的静音
    
    # MP3文件头（ID3v2.3标签）
    id3_header = bytearray([
        0x49, 0x44, 0x33,  # "ID3"
        0x03, 0x00,        # Version 2.3
        0x00,              # Flags
        0x00, 0x00, 0x00, 0x17  # Size (23 bytes)
    ])
    
    # 标题标签
    title_frame = bytearray([
        0x54, 0x49, 0x54, 0x32,  # "TIT2" (Title frame)
        0x00, 0x00, 0x00, 0x0D,  # Frame size (13 bytes)
        0x00, 0x00,              # Flags
        0x00                     # Text encoding (ISO-8859-1)
    ])
    
    # 根据语音风格生成不同的标题
    style_titles = {
        "enthusiastic": b"NHL_ENERGETIC",
        "dramatic": b"NHL_INTENSE", 
        "calm": b"NHL_SMOOTH"
    }
    title_text = style_titles.get(voice_style, b"NHL_NORMAL")
    
    # MP3帧头（128 kbps, 44.1 kHz, Stereo）
    mp3_frame_header = bytearray([
        0xFF, 0xFB,  # Frame sync + MPEG Audio Layer III
        0x90, 0x00   # Bitrate + Frequency + Padding + Mode
    ])
    
    # 创建短暂的静音MP3数据（约0.1秒）
    # 这个是经过简化的MP3帧数据
    silence_data = bytearray([
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
    ] * 4)  # 重复几次以创建短暂的静音
    
    # 组合完整的MP3文件
    mp3_data = id3_header + title_frame + title_text + mp3_frame_header + silence_data
    
    return bytes(mp3_data)


def _generate_simple_wav_audio(text: str, voice_style: str) -> bytes:
    """生成更接近语音的WAV音频文件"""
    
    # WAV文件头
    sample_rate = 44100
    duration = min(3.0, max(1.0, len(text) * 0.12))  # 根据文本长度调整
    num_samples = int(sample_rate * duration)
    
    # RIFF头
    riff_header = b'RIFF'
    file_size = (36 + num_samples * 2).to_bytes(4, 'little')
    wave_header = b'WAVE'
    
    # fmt子块
    fmt_header = b'fmt '
    fmt_size = (16).to_bytes(4, 'little')
    audio_format = (1).to_bytes(2, 'little')  # PCM
    num_channels = (1).to_bytes(2, 'little')  # Mono
    sample_rate_bytes = sample_rate.to_bytes(4, 'little')
    byte_rate = (sample_rate * 1 * 2).to_bytes(4, 'little')
    block_align = (1 * 2).to_bytes(2, 'little')
    bits_per_sample = (16).to_bytes(2, 'little')
    
    # data子块
    data_header = b'data'
    data_size = (num_samples * 2).to_bytes(4, 'little')
    
    # 语音风格配置 - NHL解说员风格
    voice_configs = {
        "enthusiastic": {
            "base_freq": 170,     # 兴奋的解说员
            "formants": [850, 1250, 2650],  # 共振峰
            "pitch_variation": 0.5,
            "amplitude": 7000,
            "speech_rate": 1.4
        },
        "dramatic": {
            "base_freq": 150,     # 戏剧性的低沉声音
            "formants": [750, 1150, 2450],
            "pitch_variation": 0.7,
            "amplitude": 8000,
            "speech_rate": 0.9
        },
        "calm": {
            "base_freq": 130,     # 平静的解说
            "formants": [650, 1050, 2250],
            "pitch_variation": 0.3,
            "amplitude": 6000,
            "speech_rate": 0.8
        }
    }
    
    config = voice_configs.get(voice_style, voice_configs["enthusiastic"])
    
    # 分析文本内容调整语音特征
    text_upper = text.upper()
    words = text.split()
    
    # 创建语调模式
    pitch_pattern = []
    for word in words:
        word_upper = word.upper()
        if any(x in word_upper for x in ["GOAL", "SCORE", "YES"]):
            pitch_pattern.extend([1.3, 1.6, 1.8, 1.4])  # 兴奋上升
        elif any(x in word_upper for x in ["SAVE", "BLOCK", "STOP"]):
            pitch_pattern.extend([1.2, 0.7, 1.4, 1.0])  # 紧张变化
        elif any(x in word_upper for x in ["OVERTIME", "FINAL"]):
            pitch_pattern.extend([1.0, 1.1, 1.0, 0.9])  # 紧张感
        else:
            pitch_pattern.extend([1.0 + random.uniform(-0.15, 0.25)])
    
    audio_samples = []
    
    for i in range(num_samples):
        t = i / sample_rate
        progress = t / duration
        
        # 语调变化
        if pitch_pattern:
            pattern_index = int(progress * len(pitch_pattern))
            pattern_index = min(pattern_index, len(pitch_pattern) - 1)
            pitch_mult = pitch_pattern[pattern_index]
        else:
            pitch_mult = 1.0
        
        # 基频计算
        base_freq = config["base_freq"] * pitch_mult
        
        # 语调轮廓
        pitch_contour = config["pitch_variation"] * math.sin(2 * math.pi * progress * 3)
        freq = base_freq * (1 + pitch_contour)
        
        # 语音信号生成
        # 基频（声带振动）
        fundamental = math.sin(2 * math.pi * freq * t)
        
        # 共振峰合成（模拟口腔共鸣）
        formant_signal = 0
        for j, formant_freq in enumerate(config["formants"]):
            formant_strength = 0.8 / (j + 1)  # 递减强度
            formant_mod = formant_freq * (1 + 0.03 * math.sin(2 * math.pi * t * 4 + j))
            formant_component = formant_strength * math.sin(2 * math.pi * formant_mod * t)
            formant_signal += formant_component
        
        # 语音合成：基频调制共振峰
        voice_signal = fundamental * (1 + 0.4 * formant_signal)
        
        # 添加语音噪声成分
        noise_component = 0.08 * random.uniform(-1, 1)
        
        # 节奏控制：模拟音节间隔
        syllable_rate = config["speech_rate"] * 4
        syllable_phase = (t * syllable_rate) % 1.0
        syllable_envelope = 0.6 + 0.4 * math.sin(syllable_phase * math.pi)
        
        # 添加轻微的停顿
        if syllable_phase < 0.05:
            syllable_envelope *= 0.2
        
        # 最终信号
        sample_value = (voice_signal + noise_component) * config["amplitude"]
        sample_value *= syllable_envelope
        
        # 整体包络（淡入淡出）
        envelope = 1.0
        fade_time = 0.1
        if t < fade_time:
            envelope = t / fade_time
        elif t > duration - fade_time:
            envelope = (duration - t) / fade_time
        
        sample_value *= envelope
        
        # 转换为16位整数
        sample_int = int(sample_value)
        sample_int = max(-32768, min(32767, sample_int))
        
        # 转换为字节
        sample_bytes = sample_int.to_bytes(2, 'little', signed=True)
        audio_samples.append(sample_bytes)
    
    audio_data = b''.join(audio_samples)
    
    # 组合WAV文件
    wav_data = (riff_header + file_size + wave_header + 
                fmt_header + fmt_size + audio_format + num_channels + 
                sample_rate_bytes + byte_rate + block_align + bits_per_sample +
                data_header + data_size + audio_data)
    
    return wav_data


async def save_audio_file(
    tool_context: Optional[ToolContext],
    audio_base64: str,
    audio_id: str,
    voice_style: str = "enthusiastic",
    game_id: str = "unknown"
) -> Dict[str, Any]:
    """
    Save audio data to organized file structure
    
    Args:
        tool_context: ADK tool context (can be None)
        audio_base64: Base64 encoded audio data
        audio_id: Unique audio identifier
        voice_style: Voice style used (enthusiastic, dramatic, calm)
        game_id: NHL game ID for organized storage
        
    Returns:
        Dict with save status and file path
    """
    
    try:
        import base64
        import wave
        import os
        from datetime import datetime
        
        # Create organized output directory
        output_dir = f"audio_output/{game_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Decode audio data
        audio_bytes = base64.b64decode(audio_base64)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"nhl_{voice_style}_{audio_id}_{timestamp}.wav"
        filepath = os.path.join(output_dir, filename)
        
        # Create WAV file
        with wave.open(filepath, 'wb') as wav_file:
            wav_file.setnchannels(1)      # Mono
            wav_file.setsampwidth(2)      # 16-bit
            wav_file.setframerate(24000)  # 24kHz
            wav_file.writeframes(audio_bytes)
        
        file_size = os.path.getsize(filepath)
        
        print(f"💾 Audio saved: {filepath} ({file_size:,} bytes)")
        
        # Update tool context if available
        if tool_context:
            tool_context.state["last_audio_save"] = {
                "status": "success",
                "filepath": filepath,
                "filename": filename,
                "size": file_size,
                "audio_id": audio_id
            }
        
        return {
            "status": "success",
            "filepath": filepath,
            "filename": filename,
            "size": file_size,
            "audio_id": audio_id,
            "game_id": game_id,
            "voice_style": voice_style,
            "message": f"Audio saved successfully to {filepath}"
        }
        
    except Exception as e:
        error_msg = f"Failed to save audio file: {str(e)}"
        print(f"❌ {error_msg}")
        
        if tool_context:
            tool_context.state["last_audio_save"] = {
                "status": "error",
                "error": error_msg
            }
        
        return {
            "status": "error",
            "error": error_msg,
            "audio_id": audio_id
        }


# 创建ADK FunctionTool实例
text_to_speech_tool = FunctionTool(func=text_to_speech)
stream_audio_tool = FunctionTool(func=stream_audio_websocket)
audio_status_tool = FunctionTool(func=get_audio_status)
save_audio_tool = FunctionTool(func=save_audio_file)

# 导出工具列表
AUDIO_TOOLS = [
    text_to_speech_tool,
    stream_audio_tool,
    audio_status_tool,
    save_audio_tool
]
