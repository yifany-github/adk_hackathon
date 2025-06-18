#!/usr/bin/env python3
"""
Generate NHL Audio - Clean audio generation using audio agent
"""

import os
import sys
import asyncio
import subprocess
from datetime import datetime

# Set your API key
os.environ["GEMINI_API_KEY"] = "AIzaSyCXbDwkaI4RTm-75ZpAD4Bq1eincDfh7cs"

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# NHL commentary examples
NHL_COMMENTARIES = [
    "McDavid breaks away, he's got speed! He dekes the goalie... HE SCORES! An absolutely spectacular goal by Connor McDavid!",
    "Pastrnak with the puck, one-on-one! He shoots... TOP SHELF! David Pastrnak finds the back of the net!",
    "Ovechkin from his office! The pass comes across... HE SCORES! Alexander Ovechkin with his trademark one-timer!",
    "Crosby steals the puck, breakaway chance! He goes five-hole... GOAL! Sidney Crosby with a beautiful finish!",
    "MacKinnon flying down the ice! Nobody can catch him... WHAT A SHOT! Nathan MacKinnon beats the goalie clean!"
]

async def generate_nhl_audio(commentary_text: str = None, voice_style: str = "enthusiastic"):
    """Generate NHL commentary audio using the audio agent"""
    try:
        # Import the audio processing function
        from src.agents.audio_agent.tool import text_to_speech
        
        # Use provided text or pick a random one
        if not commentary_text:
            import random
            commentary_text = random.choice(NHL_COMMENTARIES)
        
        print(f"🎯 生成NHL解说音频:")
        print(f"   文本: {commentary_text}")
        print(f"   风格: {voice_style}")
        print("🎵 正在处理...")
        
        # Generate audio using the audio agent tool
        result = await text_to_speech(
            tool_context=None,
            text=commentary_text,
            voice_style=voice_style,
            language="en-US"
        )
        
        if result.get("status") == "success":
            # Audio was generated and saved automatically
            saved_file = result.get("saved_file")
            audio_id = result.get("audio_id")
            audio_size = result.get("audio_size", 0)
            model = result.get("model", "unknown")
            
            print(f"✅ 音频生成成功!")
            print(f"   文件: {saved_file}")
            print(f"   ID: {audio_id}")
            print(f"   大小: {audio_size:,} 字节")
            print(f"   模型: {model}")
            
            # Play the audio if file exists
            if saved_file and os.path.exists(saved_file):
                print(f"🔊 播放音频...")
                try:
                    subprocess.run(["afplay", saved_file], check=True)
                    print("✅ 音频播放完成!")
                    return True
                except subprocess.CalledProcessError as e:
                    print(f"⚠️ 播放失败: {e}")
                    print("💡 请手动播放文件")
                    return True  # Still success, just playback failed
            else:
                print("⚠️ 音频文件未找到，但生成成功")
                return True
        else:
            error = result.get("error", "Unknown error")
            print(f"❌ 音频生成失败: {error}")
            return False
            
    except Exception as e:
        print(f"❌ 出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    print("🏒 NHL解说音频生成器 🏒")
    print("=" * 50)
    print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # You can customize these
    custom_text = None  # Set to specific text or None for random
    voice_style = "enthusiastic"  # enthusiastic, dramatic, calm
    
    success = asyncio.run(generate_nhl_audio(custom_text, voice_style))
    
    if success:
        print("\n🎉 NHL解说音频生成完成!")
        print("📁 查看 audio_output/ 目录获取所有生成的文件")
    else:
        print("\n❌ 音频生成失败")

if __name__ == "__main__":
    main() 