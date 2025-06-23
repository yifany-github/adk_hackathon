#!/usr/bin/env python3
"""
第三版音频提取脚本
从Sequential Agent V3的JSON输出文件中提取和保存音频段
直接处理PCM音频数据，不依赖外部工具
"""

import json
import base64
import os
import struct
import wave
from datetime import datetime

def analyze_audio_data(audio_data):
    """
    分析音频数据特征
    """
    size = len(audio_data)
    
    # 分析前100个样本的特征
    sample_size = min(100, size // 2)  # 假设16位样本
    samples = []
    
    for i in range(0, sample_size * 2, 2):
        if i + 1 < size:
            # 读取16位小端序样本
            sample = struct.unpack('<h', audio_data[i:i+2])[0]
            samples.append(sample)
    
    if samples:
        avg_amplitude = sum(abs(s) for s in samples) / len(samples)
        max_amplitude = max(abs(s) for s in samples)
        
        print(f"  📈 音频分析:")
        print(f"    - 数据大小: {size:,} 字节")
        print(f"    - 样本数(估计): {size // 2:,}")
        print(f"    - 平均振幅: {avg_amplitude:.1f}")
        print(f"    - 最大振幅: {max_amplitude}")
        
        return {
            'size': size,
            'estimated_samples': size // 2,
            'avg_amplitude': avg_amplitude,
            'max_amplitude': max_amplitude,
            'is_likely_audio': max_amplitude > 100  # 简单的音频检测
        }
    
    return None

def create_wav_file(audio_data, output_path, sample_rate=22050, channels=1, bits_per_sample=16):
    """
    创建WAV文件，假设输入是PCM数据
    """
    try:
        # 分析音频数据
        analysis = analyze_audio_data(audio_data)
        
        if analysis and not analysis['is_likely_audio']:
            print(f"  ⚠️  警告: 数据看起来不像音频数据 (最大振幅: {analysis['max_amplitude']})")
        
        # 使用wave模块创建WAV文件
        with wave.open(output_path, 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(bits_per_sample // 8)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)
        
        print(f"  ✅ WAV文件创建成功: {os.path.basename(output_path)}")
        return True
        
    except Exception as e:
        print(f"  ❌ WAV文件创建失败: {str(e)}")
        return False

def try_different_formats(audio_data, base_output_path):
    """
    尝试不同的音频格式参数
    """
    formats_to_try = [
        {'rate': 22050, 'channels': 1, 'bits': 16, 'desc': '22kHz单声道16位'},
        {'rate': 16000, 'channels': 1, 'bits': 16, 'desc': '16kHz单声道16位'},
        {'rate': 44100, 'channels': 1, 'bits': 16, 'desc': '44kHz单声道16位'},
        {'rate': 22050, 'channels': 2, 'bits': 16, 'desc': '22kHz立体声16位'},
        {'rate': 22050, 'channels': 1, 'bits': 8, 'desc': '22kHz单声道8位'},
    ]
    
    for i, fmt in enumerate(formats_to_try):
        output_path = base_output_path.replace('.wav', f'_fmt{i+1}_{fmt["rate"]}.wav')
        print(f"  🔄 尝试格式 {i+1}: {fmt['desc']}")
        
        # 对于8位音频，需要调整数据
        if fmt['bits'] == 8:
            # 将16位数据转换为8位
            adjusted_data = bytearray()
            for i in range(0, len(audio_data), 2):
                if i + 1 < len(audio_data):
                    sample = struct.unpack('<h', audio_data[i:i+2])[0]
                    # 转换为无符号8位 (0-255)
                    sample_8bit = ((sample + 32768) >> 8) & 0xFF
                    adjusted_data.append(sample_8bit)
            audio_data_to_use = bytes(adjusted_data)
        else:
            audio_data_to_use = audio_data
        
        if create_wav_file(audio_data_to_use, output_path, fmt['rate'], fmt['channels'], fmt['bits']):
            return output_path
    
    return None

def extract_audio_from_json_v3(json_file_path, output_dir=None):
    """
    第三版音频提取函数
    """
    
    # 读取JSON文件
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 检查是否有音频代理数据
    if 'audio_agent' not in data:
        print("❌ JSON文件中没有找到audio_agent数据")
        return
    
    audio_agent_data = data['audio_agent']
    
    if 'audio_segments' not in audio_agent_data:
        print("❌ audio_agent中没有找到audio_segments")
        return
    
    # 创建输出目录
    if output_dir is None:
        base_filename = os.path.basename(json_file_path).replace('.json', '')
        output_dir = f"extracted_audio_v3/{base_filename}"
    
    os.makedirs(output_dir, exist_ok=True)
    
    audio_segments = audio_agent_data['audio_segments']
    total_segments = len(audio_segments)
    extracted_count = 0
    file_info_list = []
    
    print(f"📁 输出目录: {output_dir}")
    print(f"🎵 找到 {total_segments} 个音频段")
    print("-" * 50)
    
    for i, segment in enumerate(audio_segments, 1):
        print(f"🎧 处理音频段 {i}/{total_segments}")
        
        # 提取音频信息
        audio_id = segment.get('audio_id', f'audio_{i}')
        voice_style = segment.get('voice_style', 'unknown')
        voice_name = segment.get('voice_name', 'unknown')
        timestamp = segment.get('timestamp', '000000')
        audio_data_b64 = segment.get('audio_data', '')
        
        if not audio_data_b64:
            print(f"  ❌ 音频段 {i} 没有音频数据")
            continue
        
        try:
            # 解码base64数据
            audio_data = base64.b64decode(audio_data_b64)
            
            print(f"  📊 数据信息:")
            print(f"    - 原始大小: {len(audio_data):,} 字节")
            print(f"    - 前16字节: {audio_data[:16].hex()}")
            
            # 生成基础文件名
            filename = f"{audio_id}_{voice_name}_{voice_style}_{timestamp}.wav"
            base_output_path = os.path.join(output_dir, filename)
            
            # 尝试直接创建WAV文件（假设是PCM数据）
            print("  🔧 尝试创建WAV文件...")
            successful_path = None
            
            # 首先尝试默认格式
            if create_wav_file(audio_data, base_output_path):
                successful_path = base_output_path
            else:
                # 如果失败，尝试不同的格式
                print("  🔄 尝试其他音频格式...")
                successful_path = try_different_formats(audio_data, base_output_path)
            
            if successful_path:
                # 记录文件信息
                file_info = {
                    "filename": os.path.basename(successful_path),
                    "filepath": successful_path,
                    "audio_id": audio_id,
                    "voice_style": voice_style,
                    "voice_name": voice_name,
                    "timestamp": timestamp,
                    "format": "wav_pcm",
                    "size": os.path.getsize(successful_path),
                    "original_size": len(audio_data)
                }
                file_info_list.append(file_info)
                extracted_count += 1
                
                print(f"  ✅ 保存成功: {file_info['filename']}")
                print(f"  📍 路径: {successful_path}")
            else:
                print(f"  ❌ 所有格式尝试都失败了")
                
                # 保存原始数据作为备份
                raw_filename = f"{audio_id}_{voice_name}_{voice_style}_{timestamp}.raw"
                raw_path = os.path.join(output_dir, raw_filename)
                with open(raw_path, 'wb') as f:
                    f.write(audio_data)
                print(f"  💾 保存原始数据: {raw_filename}")
            
        except Exception as e:
            print(f"  ❌ 提取失败: {str(e)}")
            continue
    
    # 生成清单文件
    manifest = {
        "extracted_at": datetime.now().isoformat(),
        "source_file": json_file_path,
        "total_segments": total_segments,
        "extracted_count": extracted_count,
        "extraction_method": "direct_pcm_processing",
        "files": file_info_list
    }
    
    manifest_path = os.path.join(output_dir, "audio_manifest_v3.json")
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print("-" * 50)
    print(f"✅ 提取完成!")
    print(f"📊 成功提取: {extracted_count}/{total_segments} 个音频文件")
    print(f"📁 输出目录: {output_dir}")
    print(f"📋 清单文件: {manifest_path}")
    
    # 创建播放说明
    readme_path = os.path.join(output_dir, "README.md")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(f"""# 提取的音频文件

## 文件信息
- 提取时间: {datetime.now().isoformat()}
- 源文件: {json_file_path}
- 成功提取: {extracted_count}/{total_segments} 个音频文件

## 播放方法

### macOS
```bash
# 播放单个文件
afplay filename.wav

# 播放所有文件
for file in *.wav; do echo "播放: $file"; afplay "$file"; done
```

### Linux
```bash
# 使用aplay
aplay filename.wav

# 使用paplay
paplay filename.wav
```

### Windows
```bash
# 直接双击WAV文件或使用命令行
start filename.wav
```

## 文件列表
""")
        for file_info in file_info_list:
            f.write(f"- {file_info['filename']} ({file_info['size']:,} bytes)\n")
    
    print(f"📖 说明文件: {readme_path}")
    
    return output_dir, manifest_path

def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python extract_audio_from_json_v3.py <json_file_path> [output_dir]")
        print("示例: python extract_audio_from_json_v3.py data/sequential_agent_v3_outputs/2024030411/2024030411_1_00_00_sequential_v3.json")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(json_file):
        print(f"❌ 文件不存在: {json_file}")
        sys.exit(1)
    
    try:
        extract_audio_from_json_v3(json_file, output_dir)
    except Exception as e:
        print(f"❌ 提取失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 