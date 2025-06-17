#!/usr/bin/env python3
"""
WAV 音频文件合并工具

使用方法:
    python merge_audio.py input1.wav input2.wav output.wav
"""

import sys
import os
from pydub import AudioSegment
import argparse

def merge_wav_files(input_file1: str, input_file2: str, output_file: str, pause_duration: float = 0.5) -> bool:
    """
    合并两个 WAV 文件，并在中间添加可选的暂停
    
    Args:
        input_file1: 第一个输入文件路径
        input_file2: 第二个输入文件路径
        output_file: 输出文件路径
        pause_duration: 两个音频之间的暂停时间（秒）
        
    Returns:
        bool: 合并是否成功
    """
    try:
        # 检查输入文件是否存在
        if not os.path.exists(input_file1):
            print(f"❌ 错误: 找不到输入文件 {input_file1}")
            return False
        if not os.path.exists(input_file2):
            print(f"❌ 错误: 找不到输入文件 {input_file2}")
            return False
            
        # 加载音频文件
        print(f"📂 正在加载音频文件...")
        audio1 = AudioSegment.from_wav(input_file1)
        audio2 = AudioSegment.from_wav(input_file2)
        
        # 创建暂停
        pause = AudioSegment.silent(duration=int(pause_duration * 1000))  # 转换为毫秒
        
        # 合并音频
        print(f"🔄 正在合并音频...")
        combined = audio1 + pause + audio2
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
        
        # 导出合并后的文件
        print(f"💾 正在保存合并后的文件...")
        combined.export(output_file, format="wav")
        
        # 打印音频信息
        print(f"\n📊 音频信息:")
        print(f"   第一个文件: {len(audio1)/1000:.1f}秒")
        print(f"   暂停时间: {pause_duration}秒")
        print(f"   第二个文件: {len(audio2)/1000:.1f}秒")
        print(f"   总时长: {len(combined)/1000:.1f}秒")
        print(f"   采样率: {combined.frame_rate}Hz")
        print(f"   声道数: {combined.channels}")
        
        print(f"\n✅ 音频合并成功: {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ 错误: 音频合并失败 - {str(e)}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="合并两个 WAV 音频文件")
    parser.add_argument("input1", help="第一个输入 WAV 文件")
    parser.add_argument("input2", help="第二个输入 WAV 文件")
    parser.add_argument("output", help="输出 WAV 文件")
    parser.add_argument("--pause", type=float, default=0.5,
                      help="两个音频之间的暂停时间（秒），默认 0.5 秒")
    
    args = parser.parse_args()
    
    print("🎵 WAV 音频合并工具")
    print("=" * 50)
    
    success = merge_wav_files(
        args.input1,
        args.input2,
        args.output,
        args.pause
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 