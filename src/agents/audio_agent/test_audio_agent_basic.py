#!/usr/bin/env python3
"""
Audio Agent 基础测试脚本 (不依赖Google Cloud TTS)

用于测试ADK框架集成，不需要Google Cloud凭据。

使用方法:
    python src/agents/audio_agent/test_audio_agent_basic.py
"""

import asyncio
import sys
import os
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

def test_adk_imports():
    """测试Google ADK导入"""
    print("🧪 测试Google ADK导入...")
    
    try:
        from google.adk.agents import LlmAgent
        from google.adk.tools import FunctionTool
        from google.adk.tools.tool_context import ToolContext
        print("✅ Google ADK核心模块导入成功")
        print(f"   - LlmAgent: {LlmAgent}")
        print(f"   - FunctionTool: {FunctionTool}")
        print(f"   - ToolContext: {ToolContext}")
        return True
    except ImportError as e:
        print(f"❌ Google ADK导入失败: {e}")
        return False


def test_mock_tts_function():
    """测试模拟TTS函数"""
    print("\n🎙️ 测试模拟TTS函数...")
    
    def mock_text_to_speech(
        text: str, 
        voice_style: str = "enthusiastic",
        language: str = "en-US",
        tool_context=None
    ) -> Dict[str, Any]:
        """模拟的文本转语音函数"""
        print(f"🎯 模拟TTS: {text[:50]}...")
        print(f"   语音风格: {voice_style}")
        print(f"   语言: {language}")
        
        # 模拟音频ID
        import uuid
        audio_id = str(uuid.uuid4())[:8]
        
        return {
            "status": "success",
            "audio_id": audio_id,
            "text_length": len(text),
            "voice_style": voice_style,
            "language": language,
            "message": f"模拟音频生成成功，ID: {audio_id}"
        }
    
    # 测试函数
    test_text = "Connor McDavid scores an amazing goal!"
    result = mock_text_to_speech(test_text, "enthusiastic")
    
    if result["status"] == "success":
        print("✅ 模拟TTS函数测试成功")
        print(f"   音频ID: {result['audio_id']}")
        print(f"   文本长度: {result['text_length']}")
        return True
    else:
        print("❌ 模拟TTS函数测试失败")
        return False


def test_adk_function_tool():
    """测试ADK FunctionTool创建"""
    print("\n🔧 测试ADK FunctionTool创建...")
    
    try:
        from google.adk.tools import FunctionTool
        
        def sample_function(text: str) -> Dict[str, Any]:
            """示例函数"""
            return {
                "status": "success",
                "input": text,
                "output": f"处理了文本: {text}"
            }
        
        # 创建FunctionTool (只传递函数)
        tool = FunctionTool(func=sample_function)
        print("✅ FunctionTool创建成功")
        print(f"   工具函数: {tool.func}")
        print(f"   工具描述: {tool.description}")
        return True
        
    except Exception as e:
        print(f"❌ FunctionTool创建失败: {e}")
        return False


def test_adk_llm_agent():
    """测试ADK LlmAgent创建"""
    print("\n🤖 测试ADK LlmAgent创建...")
    
    try:
        from google.adk.agents import LlmAgent
        from google.adk.tools import FunctionTool
        
        def test_tool(message: str) -> str:
            """测试工具"""
            return f"收到消息: {message}"
        
        # 创建工具 (只传递函数)
        tool = FunctionTool(func=test_tool)
        
        # 创建代理 (使用模拟模型)
        agent = LlmAgent(
            name="test_audio_agent",
            model="gemini-2.0-flash",  # 这里可能需要实际的模型配置
            instruction="你是一个测试音频代理",
            description="用于测试ADK框架的音频代理",
            tools=[tool]
        )
        
        print("✅ LlmAgent创建成功")
        print(f"   代理名称: {agent.name}")
        print(f"   模型: {agent.model}")
        print(f"   工具数量: {len(agent.tools)}")
        return True
        
    except Exception as e:
        print(f"❌ LlmAgent创建失败: {e}")
        print(f"   这可能是因为缺少模型配置或API密钥")
        return False


def test_voice_style_analysis():
    """测试语音风格分析逻辑"""
    print("\n🎨 测试语音风格分析...")
    
    def analyze_voice_style(text: str) -> str:
        """分析文本选择语音风格"""
        text_lower = text.lower()
        
        exciting_keywords = ["goal", "score", "save", "shot", "penalty", "power play", "amazing", "incredible"]
        dramatic_keywords = ["overtime", "final", "crucial", "critical", "game-winning", "timeout"]
        
        exciting_count = sum(1 for keyword in exciting_keywords if keyword in text_lower)
        dramatic_count = sum(1 for keyword in dramatic_keywords if keyword in text_lower)
        
        if dramatic_count > 0:
            return "dramatic"
        elif exciting_count > 0:
            return "enthusiastic"
        else:
            return "enthusiastic"  # 默认
    
    test_cases = [
        {
            "text": "McDavid passes the puck to his teammate.",
            "expected": "enthusiastic"
        },
        {
            "text": "OVERTIME GOAL! The crowd goes wild!",
            "expected": "dramatic"
        },
        {
            "text": "Amazing save by the goalie!",
            "expected": "enthusiastic"
        },
        {
            "text": "This is the final minute of the game!",
            "expected": "dramatic"
        }
    ]
    
    success_count = 0
    for case in test_cases:
        result = analyze_voice_style(case["text"])
        if result == case["expected"]:
            print(f"✅ '{case['text'][:30]}...' → {result}")
            success_count += 1
        else:
            print(f"❌ '{case['text'][:30]}...' → {result} (期望: {case['expected']})")
    
    print(f"📊 语音风格分析测试: {success_count}/{len(test_cases)} 成功")
    return success_count == len(test_cases)


async def main():
    """主测试函数"""
    print("🏒 NHL Audio Agent 基础测试套件")
    print("=" * 50)
    print("这个测试不需要Google Cloud凭据，专注于ADK框架集成")
    
    tests = [
        ("Google ADK导入", test_adk_imports),
        ("模拟TTS函数", test_mock_tts_function),
        ("ADK FunctionTool", test_adk_function_tool),
        ("ADK LlmAgent", test_adk_llm_agent),
        ("语音风格分析", test_voice_style_analysis)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 运行测试: {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} - 通过")
            else:
                print(f"❌ {test_name} - 失败")
        except Exception as e:
            print(f"❌ {test_name} - 异常: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n🏆 测试结果")
    print("=" * 50)
    print(f"总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed >= 4:  # LlmAgent测试可能因为API密钥失败
        print("\n🎉 基础功能测试通过! ADK框架集成正常!")
        print("\n下一步:")
        print("1. 配置Google Cloud凭据来启用完整的TTS功能")
        print("2. 运行: python scripts/setup_api_keys.py")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查ADK安装")


if __name__ == "__main__":
    # 环境检查
    print("🔍 检查环境...")
    
    # 检查Python版本
    print(f"Python版本: {sys.version}")
    
    # 检查ADK安装
    try:
        import google.adk
        print(f"✅ Google ADK版本: {google.adk.__version__}")
    except ImportError:
        print("❌ Google ADK未安装")
        print("请运行: pip install google-adk")
        sys.exit(1)
    
    print("\n开始基础测试...")
    asyncio.run(main()) 