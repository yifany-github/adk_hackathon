#!/usr/bin/env python3
"""
NHL Audio Agent - Gemini TTS 测试脚本
简单直接的真实语音测试
"""

import asyncio
import os
import sys
import base64
import wave
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_gemini_tts():
    """测试Gemini TTS功能"""
    print("🎙️ NHL Audio Agent - Gemini TTS 测试")
    print("=" * 50)
    
    # 检查API Key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ 未配置Gemini API Key")
        print("💡 请运行: python setup_api_key.py")
        return False
    
    print(f"✅ API Key已配置 (前4位: {api_key[:4]}...)")
    
    try:
        from src.agents.audio_agent.tool import text_to_speech
        
        # 测试不同风格的NHL解说
        test_cases = [
            ("enthusiastic", "Connor McDavid scores an amazing goal!", "🏒 兴奋解说"),
            ("dramatic", "This is overtime! The final seconds!", "⚡ 戏剧性解说"),
            ("calm", "The players are lining up for the faceoff.", "😌 平静解说")
        ]
        
        saved_files = []
        
        for style, text, description in test_cases:
            print(f"\n{description}")
            print(f"📝 文本: {text}")
            print(f"🎭 风格: {style}")
            
            # 调用TTS
            result = await text_to_speech(
                tool_context=None,
                text=text,
                voice_style=style,
                language="en-US"
            )
            
            if result["status"] == "success":
                print(f"✅ 语音生成成功!")
                print(f"   音频ID: {result['audio_id']}")
                print(f"   大小: {result['audio_size']:,} 字节")
                print(f"   真实TTS: {result['is_real_tts']}")
                
                # 保存音频文件
                if 'audio_data' in result:
                    filepath = save_wav_file(result['audio_data'], result['audio_id'], style)
                    if filepath:
                        saved_files.append(filepath)
                        print(f"   📁 已保存: {filepath}")
                        
                        # 播放音频
                        print(f"   🔊 正在播放...")
                        os.system(f"afplay {filepath}")
                        
            else:
                print(f"❌ 语音生成失败: {result.get('error')}")
                return False
        
        # 显示结果摘要
        print(f"\n🎉 测试完成!")
        print(f"📁 生成了 {len(saved_files)} 个音频文件:")
        for filepath in saved_files:
            file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            print(f"   - {os.path.basename(filepath)} ({file_size:,} 字节)")
        
        print(f"\n💡 提示:")
        print(f"- 所有文件保存在 'audio_output/' 目录")
        print(f"- 使用 'afplay [文件名]' 播放音频")
        print(f"- 这些是真实的Gemini TTS语音，不是模拟音频")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def save_wav_file(audio_base64: str, audio_id: str, style: str) -> str:
    """保存WAV文件"""
    try:
        # 创建目录
        output_dir = "audio_output"
        os.makedirs(output_dir, exist_ok=True)
        
        # 解码音频数据
        audio_bytes = base64.b64decode(audio_base64)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"nhl_{style}_{audio_id}_{timestamp}.wav"
        filepath = os.path.join(output_dir, filename)
        
        # 创建WAV文件
        with wave.open(filepath, 'wb') as wav_file:
            wav_file.setnchannels(1)      # 单声道
            wav_file.setsampwidth(2)      # 16位
            wav_file.setframerate(24000)  # 24kHz
            wav_file.writeframes(audio_bytes)
        
        return filepath
        
    except Exception as e:
        print(f"❌ 保存失败: {e}")
        return ""

async def main():
    """主函数"""
    success = await test_gemini_tts()
    
    if success:
        print(f"\n🏆 所有测试通过！NHL Audio Agent 工作正常")
    else:
        print(f"\n❌ 测试失败，请检查配置")

if __name__ == "__main__":
    asyncio.run(main()) 