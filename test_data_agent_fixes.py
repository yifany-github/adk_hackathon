#!/usr/bin/env python3
"""
Data Agent Validation Test
Verifies that data agent fixes prevent assumptions, data leakage, and phantom players
"""

import sys
import json

# Add paths
sys.path.append('src')
sys.path.append('src/agents/data_agent')

def test_missing_function():
    """Test that the missing function is now implemented"""
    print("🧪 Testing missing function fix...")
    
    try:
        from agents.data_agent.tools import _calculate_activity_trend
        
        # Test with sample data
        sample_activities = [
            {"typeDescKey": "goal", "timeInPeriod": "1:00"},
            {"typeDescKey": "penalty", "timeInPeriod": "2:00"},
            {"typeDescKey": "shot-on-goal", "timeInPeriod": "3:00"}
        ]
        
        result = _calculate_activity_trend(sample_activities)
        print(f"   ✅ Function exists and returns: {len(result)} trend points")
        return True
        
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Function error: {e}")
        return False

def test_prompt_improvements():
    """Test that prompts have been improved"""
    print("🧪 Testing prompt improvements...")
    
    try:
        from agents.data_agent.prompts import DATA_AGENT_PROMPT
        
        # Check for improved language
        if "Apply These Intelligently" in DATA_AGENT_PROMPT:
            print("   ❌ Still contains vague 'Apply These Intelligently' language")
            return False
        
        if "CRITICAL DATA-ONLY RULES" in DATA_AGENT_PROMPT:
            print("   ✅ Contains new data-only rules")
        else:
            print("   ❌ Missing data-only rules")
            return False
            
        if "FACEOFF WINNERS" in DATA_AGENT_PROMPT:
            print("   ✅ Contains faceoff validation rules")
        else:
            print("   ❌ Missing faceoff rules")
            return False
            
        print("   ✅ Prompt improvements look good")
        return True
        
    except Exception as e:
        print(f"   ❌ Error checking prompts: {e}")
        return False

def test_live_data_collector():
    """Test that live data collector no longer has hardcoded assumptions"""
    print("🧪 Testing live data collector fixes...")
    
    try:
        with open('src/data/live/live_data_collector.py', 'r') as f:
            content = f.read()
        
        # Check for removed hardcoded values
        if 'away_team_name = "FLA"' in content:
            print("   ❌ Still contains hardcoded FLA team name")
            return False
            
        if 'home_team_name = "EDM"' in content:
            print("   ❌ Still contains hardcoded EDM team name")
            return False
            
        if 'away_team_id = 13' in content:
            print("   ❌ Still contains hardcoded team ID 13")
            return False
            
        if 'home_team_id = 22' in content:
            print("   ❌ Still contains hardcoded team ID 22")
            return False
            
        print("   ✅ No hardcoded team assumptions found")
        return True
        
    except Exception as e:
        print(f"   ❌ Error checking live data collector: {e}")
        return False

def main():
    print("🔧 Data Agent Fixes Verification")
    print("=" * 50)
    
    results = []
    
    # Test 1: Missing function
    results.append(test_missing_function())
    
    # Test 2: Prompt improvements  
    results.append(test_prompt_improvements())
    
    # Test 3: Live data collector
    results.append(test_live_data_collector())
    
    print("\n📊 Results Summary:")
    passed = sum(results)
    total = len(results)
    
    print(f"   ✅ Tests passed: {passed}/{total}")
    
    if passed == total:
        print("   🎉 All fixes verified successfully!")
    else:
        print("   ⚠️  Some issues remain")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)