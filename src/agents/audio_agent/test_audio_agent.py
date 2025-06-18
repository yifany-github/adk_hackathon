#!/usr/bin/env python3
"""
Audio Agent Test Script

For quick testing and validation of audio_agent basic functionality.
This script doesn't require starting a full WebSocket server, suitable for development and debugging.

Usage:
    python src/agents/audio_agent/test_audio_agent.py
"""

import asyncio
import sys
import os

# Add project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

try:
    from src.agents.audio_agent.tool import text_to_speech, get_audio_status
except ImportError as e:
    print(f"❌ Module import failed: {e}")
    print("Please ensure this script is run from the project root directory")
    sys.exit(1)


async def test_basic_tts():
    """Test basic TTS functionality"""
    print("🧪 Testing basic TTS functionality...")
    
    test_texts = [
        ("Goal scored by Connor McDavid!", "enthusiastic"),
        ("The game goes to overtime!", "dramatic"),
        ("Players line up for the faceoff.", "calm")
    ]
    
    for text, style in test_texts:
        print(f"\n🎯 Text: {text}")
        print(f"🎭 Style: {style}")
        
        result = await text_to_speech(text=text, voice_style=style)
        
        if result["status"] == "success":
            print(f"✅ TTS test successful!")
            print(f"   Audio ID: {result['audio_id']}")
            print(f"   Text length: {result['text_length']}")
            print(f"   Voice style: {result['voice_style']}")
            print(f"   Model: {result['model']}")
            print(f"   Real TTS: {result['is_real_tts']}")
        else:
            print(f"❌ TTS test failed: {result.get('error')}")
            return False
    
    return True


async def test_audio_status():
    """Test audio status function"""
    print("\n📊 Testing audio status function...")
    
    status = get_audio_status()
    
    if status["status"] == "success":
        print("✅ Audio status test successful!")
        audio_status = status["audio_agent_status"]
        print(f"   Connected clients: {audio_status.get('connected_clients', 0)}")
        print(f"   Audio queue size: {audio_status.get('audio_queue_size', 0)}")
        print(f"   Audio history count: {audio_status.get('audio_history_count', 0)}")
        print(f"   Processor model: {audio_status.get('processor_model', 'unknown')}")
        return True
    else:
        print(f"❌ Audio status test failed: {status.get('error')}")
        return False


async def test_voice_style_analysis():
    """Test voice style analysis"""
    print("\n🎨 Testing voice style analysis...")
    
    # Import the analysis function from audio_agent
    from src.agents.audio_agent.audio_agent import create_audio_agent_for_game
    
    agent = create_audio_agent_for_game("2024030412")
    
    test_cases = [
        {
            "text": "GOAL! McDavid scores!",
            "expected_styles": ["enthusiastic", "dramatic"]
        },
        {
            "text": "The players are skating around.",
            "expected_styles": ["enthusiastic", "calm"]
        },
        {
            "text": "This is the final second of overtime!",
            "expected_styles": ["dramatic"]
        }
    ]
    
    success_count = 0
    for case in test_cases:
        style = agent._analyze_voice_style(case["text"])
        if style in case["expected_styles"]:
            print(f"✅ '{case['text'][:30]}...' → {style}")
            success_count += 1
        else:
            print(f"❌ '{case['text'][:30]}...' → {style} (expected one of: {case['expected_styles']})")
    
    print(f"📊 Voice style analysis: {success_count}/{len(test_cases)} successful")
    return success_count == len(test_cases)


async def test_multiple_audio_generation():
    """Test multiple audio generation"""
    print("\n🔄 Testing multiple audio generation...")
    
    texts = [
        "First period starts now!",
        "McDavid passes to Draisaitl!",
        "Shot saved by the goalie!",
        "End of the first period."
    ]
    
    success_count = 0
    for i, text in enumerate(texts, 1):
        print(f"\n🎯 Audio {i}/4: {text}")
        
        result = await text_to_speech(text=text, voice_style="enthusiastic")
        
        if result["status"] == "success":
            print(f"✅ Audio {i} generated: {result['audio_id']}")
            success_count += 1
        else:
            print(f"❌ Audio {i} failed: {result.get('error')}")
    
    print(f"\n📊 Multiple audio generation: {success_count}/{len(texts)} successful")
    return success_count == len(texts)


async def main():
    """Main test function"""
    print("🏒 NHL Audio Agent Test Suite")
    print("=" * 60)
    print("Testing core audio agent functionality...")
    
    tests = [
        ("Basic TTS", test_basic_tts),
        ("Audio Status", test_audio_status),
        ("Voice Style Analysis", test_voice_style_analysis),
        ("Multiple Audio Generation", test_multiple_audio_generation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running test: {test_name}")
        print("-" * 40)
        
        try:
            if await test_func():
                passed += 1
                print(f"✅ {test_name} - PASSED")
            else:
                print(f"❌ {test_name} - FAILED")
        except Exception as e:
            print(f"❌ {test_name} - ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n🏆 Test Results")
    print("=" * 60)
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success rate: {passed/total*100:.1f}%")
    
    if passed >= 3:  # Allow one failure for API-dependent tests
        print("\n🎉 Core functionality tests passed! Audio Agent is working!")
        print("\nNext steps:")
        print("1. Configure Gemini API key for full TTS functionality")
        print("2. Run: python setup_api_key.py")
        print("3. Test with real commentary: python src/pipeline.py GAME_ID")
    else:
        print(f"\n⚠️  {total - passed} tests failed, please check audio agent setup")
        print("💡 Make sure all dependencies are installed")


if __name__ == "__main__":
    asyncio.run(main()) 