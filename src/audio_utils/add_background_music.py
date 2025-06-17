#!/usr/bin/env python3
"""
WAV 音频背景音乐添加工具

使用方法:
    python add_background_music.py input.wav background.wav output.wav --volume -20
"""

import sys
import os
from pydub import AudioSegment
import argparse

def add_background_music(
    input_file: str,
    background_file: str,
    output_file: str,
    background_volume: int = -20,
    fade_duration: int = 1000
) -> bool:
    """
    为音频添加背景音乐
    
    Args:
        input_file: 主音频文件路径
        background_file: 背景音乐文件路径
        output_file: 输出文件路径
        background_volume: 背景音乐音量（dB，负值表示降低音量）
        fade_duration: 淡入淡出时间（毫秒）
        
    Returns:
        bool: 处理是否成功
    """
    try:
        # 检查输入文件是否存在
        if not os.path.exists(input_file):
            print(f"❌ 错误: 找不到主音频文件 {input_file}")
            return False
        if not os.path.exists(background_file):
            print(f"❌ 错误: 找不到背景音乐文件 {background_file}")
            return False
            
        # 加载音频文件
        print(f"📂 正在加载音频文件...")
        main_audio = AudioSegment.from_wav(input_file)
        background = AudioSegment.from_wav(background_file)
        
        # 调整背景音乐长度以匹配主音频
        if len(background) < len(main_audio):
            # 如果背景音乐较短，则循环播放
            repeats = (len(main_audio) // len(background)) + 1
            background = background * repeats
        background = background[:len(main_audio)]
        
        # 调整背景音乐音量
        print(f"🔊 调整背景音乐音量...")
        background = background + background_volume
        
        # 添加淡入淡出效果
        print(f"🎵 添加淡入淡出效果...")
        background = background.fade_in(fade_duration).fade_out(fade_duration)
        
        # 合并音频
        print(f"🔄 正在合并音频...")
        combined = main_audio.overlay(background)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
        
        # 导出处理后的文件
        print(f"💾 正在保存文件...")
        combined.export(output_file, format="wav")
        
        # 打印音频信息
        print(f"\n📊 音频信息:")
        print(f"   主音频时长: {len(main_audio)/1000:.1f}秒")
        print(f"   背景音乐时长: {len(background)/1000:.1f}秒")
        print(f"   背景音乐音量: {background_volume}dB")
        print(f"   淡入淡出时间: {fade_duration/1000:.1f}秒")
        print(f"   采样率: {combined.frame_rate}Hz")
        print(f"   声道数: {combined.channels}")
        
        print(f"\n✅ 音频处理成功: {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ 错误: 音频处理失败 - {str(e)}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="为音频添加背景音乐")
    parser.add_argument("input", help="主音频 WAV 文件")
    parser.add_argument("background", help="背景音乐 WAV 文件")
    parser.add_argument("output", help="输出 WAV 文件")
    parser.add_argument("--volume", type=int, default=-20,
                      help="背景音乐音量（dB，负值表示降低音量），默认 -20")
    parser.add_argument("--fade", type=int, default=1000,
                      help="淡入淡出时间（毫秒），默认 1000")
    
    args = parser.parse_args()
    
    print("🎵 音频背景音乐添加工具")
    print("=" * 50)
    
    success = add_background_music(
        args.input,
        args.background,
        args.output,
        args.volume,
        args.fade
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 