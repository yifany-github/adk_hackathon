#!/usr/bin/env python3
"""
Audio Agent 测试脚本

用于快速测试和验证audio_agent的基本功能。
这个脚本不需要启动完整的WebSocket服务器，适合开发和调试。

使用方法:
    python src/agents/audio_agent/test_audio_agent.py
"""

import asyncio
import sys
import os
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

try:
    from src.agents.audio_agent.tool import text_to_speech, get_audio_status
    from src.agents.audio_agent.audio_agent import AudioAgent
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)


async def test_tts_basic():
    """测试基础TTS功能"""
    print("🧪 测试基础TTS功能...")
    
    test_text = "Connor McDavid scores an amazing goal!"
    
    try:
        result = text_to_speech(
            text=test_text,
            voice_style="enthusiastic",
            language="en-US"
        )
        
        if result["status"] == "success":
            print(f"✅ TTS测试成功!")
            print(f"   音频ID: {result['audio_id']}")
            print(f"   文本长度: {result['text_length']}")
            print(f"   语音风格: {result['voice_style']}")
            return True
        else:
            print(f"❌ TTS测试失败: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ TTS测试异常: {e}")
        return False


async def test_voice_styles():
    """测试不同的语音风格"""
    print("\n🎭 测试不同语音风格...")
    
    test_cases = [
        {
            "text": "The game is tied 2-2 in the third period.",
            "style": "calm",
            "description": "平静解说"
        },
        {
            "text": "GOAL! What an incredible shot!",
            "style": "enthusiastic", 
            "description": "激动解说"
        },
        {
            "text": "This is the final minute of overtime!",
            "style": "dramatic",
            "description": "戏剧性解说"
        }
    ]
    
    success_count = 0
    
    for case in test_cases:
        print(f"\n🎯 {case['description']}: {case['text']}")
        
        try:
            result = text_to_speech(
                text=case['text'],
                voice_style=case['style'],
                language="en-US"
            )
            
            if result["status"] == "success":
                print(f"✅ {case['style']} 风格测试成功")
                success_count += 1
            else:
                print(f"❌ {case['style']} 风格测试失败: {result.get('error')}")
                
        except Exception as e:
            print(f"❌ {case['style']} 风格测试异常: {e}")
    
    print(f"\n📊 语音风格测试结果: {success_count}/{len(test_cases)} 成功")
    return success_count == len(test_cases)


async def test_audio_agent():
    """测试AudioAgent类"""
    print("\n🤖 测试AudioAgent类...")
    
    try:
        # 创建audio agent实例
        agent = AudioAgent(model="gemini-2.0-flash")
        print("✅ AudioAgent创建成功")
        
        # 测试智能语音风格选择
        test_texts = [
            "McDavid passes the puck to his teammate.",  # 应该选择enthusiastic
            "OVERTIME GOAL! The crowd goes wild!",       # 应该选择dramatic
            "The players are warming up on the ice."     # 应该选择enthusiastic(默认)
        ]
        
        for text in test_texts:
            print(f"\n📝 测试文本: {text}")
            style = agent._analyze_voice_style(text)
            print(f"🎨 选择的风格: {style}")
        
        print("✅ AudioAgent功能测试完成")
        return True
        
    except Exception as e:
        print(f"❌ AudioAgent测试失败: {e}")
        return False


async def test_audio_status():
    """测试音频状态获取"""
    print("\n📊 测试音频状态获取...")
    
    try:
        status = get_audio_status()
        
        if status["status"] == "success":
            print("✅ 状态获取成功")
            print(f"   连接客户端: {status['audio_agent_status']['connected_clients']}")
            print(f"   队列大小: {status['audio_agent_status']['queue_size']}")
            return True
        else:
            print(f"❌ 状态获取失败: {status.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ 状态测试异常: {e}")
        return False


async def main():
    """主测试函数"""
    print("🏒 NHL Audio Agent 测试套件")
    print("=" * 50)
    
    tests = [
        ("基础TTS功能", test_tts_basic),
        ("语音风格测试", test_voice_styles), 
        ("AudioAgent类测试", test_audio_agent),
        ("音频状态测试", test_audio_status)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 运行测试: {test_name}")
        print("-" * 30)
        
        try:
            if await test_func():
                passed += 1
                print(f"✅ {test_name} - 通过")
            else:
                print(f"❌ {test_name} - 失败")
        except Exception as e:
            print(f"❌ {test_name} - 异常: {e}")
    
    print(f"\n🏆 测试结果")
    print("=" * 50)
    print(f"总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有测试通过! Audio Agent 已准备就绪!")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查配置和依赖")


if __name__ == "__main__":
    # 环境检查
    print("🔍 检查环境和依赖...")
    
    # 检查Google Cloud凭据
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        print("⚠️  警告: GOOGLE_APPLICATION_CREDENTIALS 未设置")
        print("某些TTS测试可能会失败")
    
    # 检查依赖包
    try:
        import google.cloud.texttospeech
        print("✅ Google Cloud TTS 已安装")
    except ImportError:
        print("❌ Google Cloud TTS 未安装")
        print("请运行: pip install google-cloud-texttospeech")
    
    try:
        import websockets
        print("✅ WebSocket 库已安装")
    except ImportError:
        print("❌ WebSocket 库未安装") 
        print("请运行: pip install websockets")
    
    print("\n开始测试...")
    asyncio.run(main()) 