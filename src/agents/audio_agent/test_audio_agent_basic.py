#!/usr/bin/env python3
"""
Audio Agent Basic Test Script (No Google Cloud TTS dependency)

For testing ADK framework integration, no Google Cloud credentials required.

Usage:
    python src/agents/audio_agent/test_audio_agent_basic.py
"""

import asyncio
import sys
import os
from typing import Dict, Any

# Add project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

def test_adk_imports():
    """Test Google ADK imports"""
    print("🧪 Testing Google ADK imports...")
    
    try:
        from google.adk.agents import LlmAgent
        from google.adk.tools import FunctionTool
        from google.adk.tools.tool_context import ToolContext
        print("✅ Google ADK core modules imported successfully")
        print(f"   - LlmAgent: {LlmAgent}")
        print(f"   - FunctionTool: {FunctionTool}")
        print(f"   - ToolContext: {ToolContext}")
        return True
    except ImportError as e:
        print(f"❌ Google ADK import failed: {e}")
        return False


def test_mock_tts_function():
    """Test mock TTS function"""
    print("\n🎙️ Testing mock TTS function...")
    
    def mock_text_to_speech(
        text: str, 
        voice_style: str = "enthusiastic",
        language: str = "en-US",
        tool_context=None
    ) -> Dict[str, Any]:
        """Mock text-to-speech function"""
        print(f"🎯 Mock TTS: {text[:50]}...")
        print(f"   Voice style: {voice_style}")
        print(f"   Language: {language}")
        
        # Generate mock audio ID
        import uuid
        audio_id = str(uuid.uuid4())[:8]
        
        return {
            "status": "success",
            "audio_id": audio_id,
            "text_length": len(text),
            "voice_style": voice_style,
            "language": language,
            "message": f"Mock audio generation successful, ID: {audio_id}"
        }
    
    # Test function
    test_text = "Connor McDavid scores an amazing goal!"
    result = mock_text_to_speech(test_text, "enthusiastic")
    
    if result["status"] == "success":
        print("✅ Mock TTS function test successful")
        print(f"   Audio ID: {result['audio_id']}")
        print(f"   Text length: {result['text_length']}")
        return True
    else:
        print("❌ Mock TTS function test failed")
        return False


def test_adk_function_tool():
    """Test ADK FunctionTool creation"""
    print("\n🔧 Testing ADK FunctionTool creation...")
    
    try:
        from google.adk.tools import FunctionTool
        
        def sample_function(text: str) -> Dict[str, Any]:
            """Sample function"""
            return {
                "status": "success",
                "input": text,
                "output": f"Processed text: {text}"
            }
        
        # Create FunctionTool (only pass function)
        tool = FunctionTool(func=sample_function)
        print("✅ FunctionTool created successfully")
        print(f"   Tool function: {tool.func}")
        print(f"   Tool description: {tool.description}")
        return True
        
    except Exception as e:
        print(f"❌ FunctionTool creation failed: {e}")
        return False


def test_adk_llm_agent():
    """Test ADK LlmAgent creation"""
    print("\n🤖 Testing ADK LlmAgent creation...")
    
    try:
        from google.adk.agents import LlmAgent
        from google.adk.tools import FunctionTool
        
        def test_tool(message: str) -> str:
            """Test tool"""
            return f"Received message: {message}"
        
        # Create tool (only pass function)
        tool = FunctionTool(func=test_tool)
        
        # Create agent (using mock model)
        agent = LlmAgent(
            name="test_audio_agent",
            model="gemini-2.0-flash",  # This may require actual model configuration
            instruction="You are a test audio agent",
            description="Audio agent for testing ADK framework",
            tools=[tool]
        )
        
        print("✅ LlmAgent created successfully")
        print(f"   Agent name: {agent.name}")
        print(f"   Model: {agent.model}")
        print(f"   Number of tools: {len(agent.tools)}")
        return True
        
    except Exception as e:
        print(f"❌ LlmAgent creation failed: {e}")
        print(f"   This may be due to missing model configuration or API key")
        return False


def test_voice_style_analysis():
    """Test voice style analysis logic"""
    print("\n🎨 Testing voice style analysis...")
    
    def analyze_voice_style(text: str) -> str:
        """Analyze text to select voice style"""
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
            return "enthusiastic"  # Default
    
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
            print(f"❌ '{case['text'][:30]}...' → {result} (expected: {case['expected']})")
    
    print(f"📊 Voice style analysis test: {success_count}/{len(test_cases)} successful")
    return success_count == len(test_cases)


async def main():
    """Main test function"""
    print("🏒 NHL Audio Agent Basic Test Suite")
    print("=" * 50)
    print("This test does not require Google Cloud credentials, focuses on ADK framework integration")
    
    tests = [
        test_adk_imports,
        test_mock_tts_function,
        test_adk_function_tool,
        test_adk_llm_agent,
        test_voice_style_analysis
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print("   Test failed!")
        except Exception as e:
            print(f"   Test error: {e}")
    
    print("\n" + "=" * 50)
    print(f"🏆 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All basic tests passed! ADK framework integration is working.")
        print("💡 Next step: Configure API keys and test with real services")
    else:
        print("❌ Some tests failed. Please check ADK installation and dependencies.")
        print("💡 Make sure google-adk package is installed: pip install google-adk")
    
    return passed == total


if __name__ == "__main__":
    asyncio.run(main()) 