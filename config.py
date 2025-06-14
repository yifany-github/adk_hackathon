#!/usr/bin/env python3
"""
配置文件 - 管理API keys和应用设置
"""

import os
from typing import Optional


def get_gemini_api_key() -> Optional[str]:
    """获取Gemini API Key"""
    # 方法1: 从环境变量获取 (项目标准格式)
    api_key = os.getenv('GOOGLE_API_KEY')
    if api_key:
        return api_key
    
    # 方法2: 从环境变量获取 (备用格式)
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        return api_key
    
    # 方法3: 从环境变量获取 (Google AI Studio格式)
    api_key = os.getenv('GOOGLE_AI_API_KEY')
    if api_key:
        return api_key
    
    return None


def set_gemini_api_key(api_key: str) -> None:
    """设置Gemini API Key到环境变量"""
    os.environ['GOOGLE_API_KEY'] = api_key
    os.environ['GEMINI_API_KEY'] = api_key  # 兼容性
    os.environ['GOOGLE_AI_API_KEY'] = api_key  # 兼容性
    print(f"✅ Gemini API Key已设置")


def get_audio_config() -> dict:
    """获取音频配置"""
    return {
        "model": "gemini-2.5-flash-preview-tts",
        "default_language": "en-US",
        "default_voice_style": "enthusiastic",
        "websocket_port": 8765,
        "websocket_host": "localhost",
        "audio_format": "mp3",
        "speaking_rates": {
            "enthusiastic": 1.2,
            "dramatic": 1.0,
            "calm": 0.9
        },
        "pitch_adjustments": {
            "enthusiastic": 2.0,
            "dramatic": 1.0,
            "calm": -1.0
        }
    }


def check_api_configuration() -> bool:
    """检查API配置是否完整"""
    api_key = get_gemini_api_key()
    if not api_key:
        print("❌ 未找到Gemini API Key")
        print("请设置环境变量:")
        print("  export GOOGLE_API_KEY='your_api_key_here'")
        print("或者:")
        print("  export GEMINI_API_KEY='your_api_key_here'")
        return False
    
    print(f"✅ Gemini API Key已配置 (长度: {len(api_key)})")
    return True


if __name__ == "__main__":
    print("🔧 配置检查")
    print("=" * 30)
    
    if check_api_configuration():
        config = get_audio_config()
        print(f"📱 音频模型: {config['model']}")
        print(f"🌐 WebSocket: {config['websocket_host']}:{config['websocket_port']}")
        print(f"🎯 默认语言: {config['default_language']}")
        print("✅ 配置检查完成")
    else:
        print("❌ 配置不完整，请设置API key") 