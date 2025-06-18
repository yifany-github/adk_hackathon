#!/usr/bin/env python3
"""
使用Audio Agent处理NHL解说JSON文件
支持多说话人的语音生成
"""

import os
import json
import asyncio
from datetime import datetime
import sys

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入我们的Audio Agent
from src.agents.audio_agent.tool import text_to_speech, AudioProcessor


def parse_commentary_json(file_path: str):
    """解析解说JSON文件"""
    try:
        if not os.path.exists(file_path):
            print(f"❌ 文件不存在: {file_path}")
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if data.get("status") != "success":
            print(f"❌ 文件状态不是success: {data.get('status')}")
            return []
        
        commentary_sequence = data.get("commentary_sequence", [])
        
        print(f"✅ 解析完成: 找到 {len(commentary_sequence)} 条解说")
        print(f"   解说类型: {data.get('commentary_type', 'unknown')}")
        print(f"   总时长: {data.get('total_duration_estimate', 0)} 秒")
        
        return commentary_sequence
        
    except Exception as e:
        print(f"❌ 解析文件失败: {e}")
        return []


async def text_to_speech_with_speaker(text: str, voice_style: str, speaker: str, emotion: str = ""):
    """使用Audio Agent进行TTS，支持说话人特定的语音选择"""
    try:
        print(f"🔊 使用Audio Agent为 {speaker} 生成语音，风格: {voice_style}，情感: {emotion}")
        
        # 调用我们的Audio Agent，现在支持speaker和emotion参数
        result = await text_to_speech(
            tool_context=None,  # 可以传入None因为是独立使用
            text=text,
            voice_style=voice_style,
            language="en-US",
            speaker=speaker,     # 传递说话人信息
            emotion=emotion      # 传递情感信息
        )
        
        if result.get("status") == "success":
            print(f"✅ Audio Agent成功! 音频ID: {result.get('audio_id')}")
            
            # 为了保持与之前脚本的兼容性，添加speaker信息
            result["speaker"] = speaker
            result["voice_name"] = result.get("voice_name", "Unknown")
            
            return result
        else:
            print(f"❌ Audio Agent失败: {result.get('error')}")
            return result
            
    except Exception as e:
        print(f"❌ Audio Agent调用异常: {e}")
        return {
            "status": "error",
            "error": f"Audio Agent调用失败: {str(e)}",
            "speaker": speaker
        }


async def convert_commentary_to_audio(commentaries, max_items=None):
    """使用Audio Agent将解说转换为音频"""
    try:
        if max_items is None:
            max_items = len(commentaries)
        
        print(f"🎵 开始使用Audio Agent转换音频 (处理前 {min(len(commentaries), max_items)} 条)")
        
        results = []
        
        for i, commentary in enumerate(commentaries[:max_items]):
            speaker = commentary.get('speaker', 'Unknown')
            emotion = commentary.get('emotion', 'neutral')
            text = commentary.get('text', '')
            timing = commentary.get('timing', '0:00')
            duration = commentary.get('duration_estimate', 0)
            
            print(f"\n🎯 处理第 {i+1} 条解说:")
            print(f"   说话人: {speaker}")
            print(f"   时间: {timing}")
            print(f"   情绪: {emotion}")
            print(f"   预计时长: {duration}秒")
            print(f"   内容: {text[:80]}..." if len(text) > 80 else f"   内容: {text}")
            
            # 将情绪映射到语音风格
            emotion_to_style = {
                'excited': 'enthusiastic',
                'enthusiastic': 'enthusiastic',
                'analytical': 'calm',
                'neutral': 'calm',
                'informative': 'calm',
                'dramatic': 'dramatic'
            }
            
            voice_style = emotion_to_style.get(emotion, 'enthusiastic')
            
            # 使用Audio Agent转换为音频
            result = await text_to_speech_with_speaker(text, voice_style, speaker, emotion)
            
            if result.get("status") == "success":
                audio_id = result.get("audio_id")
                audio_size = result.get("audio_size", 0)
                voice_name = result.get("voice_name")
                saved_file = result.get("saved_file")
                
                print(f"   ✅ Audio Agent音频生成成功!")
                print(f"      音频ID: {audio_id}")
                if saved_file:
                    print(f"      文件: {saved_file}")
                if audio_size > 0:
                    print(f"      大小: {audio_size:,} 字节")
                print(f"      语音: {voice_name} ({speaker})")
                
                results.append({
                    'index': i,
                    'commentary': commentary,
                    'audio_result': result,
                    'success': True
                })
            else:
                error = result.get("error", "Unknown error")
                print(f"   ❌ Audio Agent音频生成失败: {error}")
                
                results.append({
                    'index': i,
                    'commentary': commentary,
                    'audio_result': result,
                    'success': False
                })
        
        return results
        
    except Exception as e:
        print(f"❌ 音频转换过程失败: {e}")
        return []


def save_results(results, input_file, output_dir="audio_results"):
    """保存处理结果"""
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成结果文件名
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = os.path.join(output_dir, f"{base_name}_audio_agent_results_{timestamp}.json")
        
        # 准备保存的数据
        save_data = {
            "processing_timestamp": timestamp,
            "input_file": input_file,
            "total_commentaries": len(results),
            "successful_conversions": sum(1 for r in results if r['success']),
            "using_audio_agent": True,  # 标记使用了Audio Agent
            "results": results
        }
        
        # 保存到文件
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 结果已保存到: {result_file}")
        return result_file
        
    except Exception as e:
        print(f"❌ 保存结果失败: {e}")
        return None


async def main():
    """主函数"""
    print("🏒 NHL解说音频生成器 (使用Audio Agent)")
    print("=" * 50)
    
    # 设置API密钥
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ 请设置GEMINI_API_KEY环境变量")
        print("   export GEMINI_API_KEY='your_api_key_here'")
        return
    
    # 默认文件路径
    default_file = "data/commentary_agent_outputs/2024030415/1_00_00_commentary_board.json"
    
    # 解析解说文件
    commentaries = parse_commentary_json(default_file)
    if not commentaries:
        print("❌ 没有找到有效的解说数据")
        return
    
    # 转换为音频
    results = await convert_commentary_to_audio(commentaries, max_items=4)  # 处理所有4条
    
    # 保存结果
    if results:
        result_file = save_results(results, default_file)
        
        # 统计结果
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        print(f"\n🎯 处理完成!")
        print(f"   ✅ 成功: {successful} 条")
        print(f"   ❌ 失败: {failed} 条")
        print(f"   📊 使用: Audio Agent (ADK集成)")
        
        if successful > 0:
            print(f"\n🔊 生成的音频文件:")
            for result in results:
                if result['success']:
                    audio_result = result['audio_result']
                    saved_file = audio_result.get('saved_file')
                    audio_id = audio_result.get('audio_id')
                    speaker = audio_result.get('speaker', 'Unknown')
                    if saved_file:
                        print(f"   • {speaker}: {saved_file} (ID: {audio_id})")


if __name__ == "__main__":
    asyncio.run(main()) 