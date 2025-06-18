#!/usr/bin/env python3
"""
测试解说文件的音频生成

使用方法:
    python test_commentary_audio.py
"""

import asyncio
import json
import os
import base64
from typing import Dict, Any
from pydub import AudioSegment
import io
import numpy as np

from src.agents.audio_agent.tool import text_to_speech
from src.agents.audio_agent.audio_agent import create_audio_agent_for_game

AUDIO_OUTPUT_DIR = "audio_output"

def convert_raw_audio_to_wav(raw_audio_bytes: bytes, sample_rate: int = 24000) -> bytes:
    """将原始音频数据转换为WAV格式"""
    # 将字节数据转换为numpy数组
    audio_array = np.frombuffer(raw_audio_bytes, dtype=np.int16)
    
    # 创建AudioSegment对象
    audio_segment = AudioSegment(
        audio_array.tobytes(),
        frame_rate=sample_rate,
        sample_width=2,  # 16-bit audio
        channels=1       # mono
    )
    
    # 导出为WAV格式
    buffer = io.BytesIO()
    audio_segment.export(buffer, format="wav")
    return buffer.getvalue()

async def test_commentary_file(file_path: str):
    """测试解说文件的音频生成"""
    print(f"📖 读取解说文件: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            commentary_data = json.load(f)
        
        # 获取解说序列
        commentary_sequence = commentary_data['commentary_data']['commentary_data']['commentary_sequence']
        
        print(f"\n🎯 找到 {len(commentary_sequence)} 条解说")
        
        # 创建audio agent实例
        agent = create_audio_agent_for_game("2024030412")
        
        # 确保输出目录存在
        os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)
        
        # 处理每条解说
        for i, commentary in enumerate(commentary_sequence, 1):
            print(f"\n📝 处理第 {i} 条解说:")
            print(f"   说话者: {commentary['speaker']}")
            print(f"   文本: {commentary['text']}")
            print(f"   情感: {commentary['emotion']}")
            
            # 根据情感选择语音风格
            style = commentary['emotion']
            if style == 'apologetic':
                style = 'calm'
            elif style == 'informative':
                style = 'enthusiastic'
            
            # 生成音频
            result = await text_to_speech(
                text=commentary['text'],
                voice_style=style,
                language="en-US"
            )
            
            if result["status"] == "success" and "audio_data" in result:
                try:
                    # 解码base64音频数据
                    audio_bytes = base64.b64decode(result["audio_data"])
                    
                    # 打印音频数据的头部字节，用于调试
                    print(f"\n🔍 音频数据头部字节: {audio_bytes[:20].hex()}")
                    
                    # 转换为WAV格式
                    wav_bytes = convert_raw_audio_to_wav(audio_bytes)
                    
                    # 保存音频到audio_output目录
                    audio_filename = f"commentary_{i}_{style}.wav"
                    audio_path = os.path.join(AUDIO_OUTPUT_DIR, audio_filename)
                    
                    # 保存WAV文件
                    with open(audio_path, "wb") as audio_file:
                        audio_file.write(wav_bytes)
                    
                    print(f"✅ 音频生成并保存: {audio_path}")
                    print(f"   语音风格: {style}")
                    print(f"   文件大小: {len(wav_bytes):,} 字节")
                except Exception as e:
                    print(f"❌ 音频处理失败: {e}")
            else:
                print(f"❌ 音频生成失败: {result.get('error')}")
        
        print("\n🎉 测试完成!")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

async def main():
    """主函数"""
    print("🏒 NHL 解说音频测试")
    print("=" * 50)
    
    # 测试文件路径
    test_file = "data/commentary_agent_outputs/2024030412_1_02_20_commentary_session_aware.json"
    
    if not os.path.exists(test_file):
        print(f"❌ 测试文件不存在: {test_file}")
        return
    
    await test_commentary_file(test_file)

if __name__ == "__main__":
    # 环境检查
    print("🔍 检查环境和依赖...")
    
    # 检查Gemini API key
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  警告: GEMINI_API_KEY 未设置")
        print("请设置环境变量: export GEMINI_API_KEY=your_gemini_api_key")
        exit(1)
    
    print("\n开始测试...")
    asyncio.run(main()) 