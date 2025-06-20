#!/usr/bin/env python3
"""
Test the simplified LiveGameBoard functionality
"""

import json
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from board.live_game_board import LiveGameBoard, create_live_game_board

def test_basic_board_creation():
    """Test basic board creation and state tracking"""
    print("🏒 Testing basic board creation...")
    
    # Create board
    board = create_live_game_board("2024030412")
    
    # Check initial state
    state = board.get_state()
    print(f"Initial state: {json.dumps(state, indent=2)}")
    
    assert state["game_id"] == "2024030412"
    assert state["score"] == {"away": 0, "home": 0}
    assert state["shots"] == {"away": 0, "home": 0}
    assert state["period"] == 1
    assert state["goals"] == []
    assert state["penalties"] == []
    
    print("✅ Basic creation test passed")

def test_session_serialization():
    """Test session state serialization/deserialization"""
    print("\n🔄 Testing session serialization...")
    
    # Create board and add some state
    board1 = create_live_game_board("2024030412")
    board1.current_score = {"away": 1, "home": 2}
    board1.current_shots = {"away": 15, "home": 12}
    board1.period = 2
    board1.goals = [{"scorer": "McDavid", "team": "home", "time": "15:23"}]
    
    # Serialize to session state
    session_data = board1.to_session_state()
    print(f"Session data: {json.dumps(session_data, indent=2)}")
    
    # Restore from session state
    board2 = LiveGameBoard.from_session_state("2024030412", session_data)
    
    # Verify state matches
    assert board2.current_score == {"away": 1, "home": 2}
    assert board2.current_shots == {"away": 15, "home": 12}
    assert board2.period == 2
    assert board2.goals == [{"scorer": "McDavid", "team": "home", "time": "15:23"}]
    
    print("✅ Session serialization test passed")

def test_timestamp_processing():
    """Test processing timestamp data"""
    print("\n⏱️ Testing timestamp processing...")
    
    board = create_live_game_board("2024030412")
    
    # Mock timestamp data with a goal
    timestamp_data = {
        "game_time": "1_15_23",
        "activities": [
            {
                "eventId": 123,
                "typeDescKey": "goal",
                "timeRemaining": "15:23",
                "periodDescriptor": {"number": 1},
                "gameSituation": "even_strength",
                "details": {
                    "eventOwnerTeamId": 1,  # Home team (odd = home in our simple logic)
                    "scoringPlayerName": "C. McDavid",
                    "assist1PlayerName": "L. Draisaitl",
                    "assist2PlayerName": "E. Bouchard"
                }
            }
        ]
    }
    
    # Process timestamp
    report = board.update_from_timestamp(timestamp_data)
    print(f"Update report: {json.dumps(report, indent=2)}")
    
    # Check state changes
    state = board.get_state()
    print(f"State after goal: {json.dumps(state, indent=2)}")
    
    assert state["score"]["home"] == 1
    assert state["score"]["away"] == 0
    assert len(state["goals"]) == 1
    assert state["goals"][0]["scorer"] == "C. McDavid"
    assert state["goals"][0]["assists"] == ["L. Draisaitl", "E. Bouchard"]
    assert state["goalie_stats"]["away"]["goals_allowed"] == 1
    
    print("✅ Timestamp processing test passed")

def test_with_existing_data():
    """Test with real data from existing pipeline"""
    print("\n📊 Testing with existing live data...")
    
    # Try to find existing live data file
    live_data_dir = "data/live"
    test_file = None
    
    if os.path.exists(live_data_dir):
        for game_dir in os.listdir(live_data_dir):
            game_path = os.path.join(live_data_dir, game_dir)
            if os.path.isdir(game_path):
                for file in os.listdir(game_path):
                    if file.endswith('.json'):
                        test_file = os.path.join(game_path, file)
                        break
                if test_file:
                    break
    
    if test_file:
        print(f"Found test file: {test_file}")
        
        with open(test_file, 'r') as f:
            live_data = json.load(f)
        
        game_id = live_data.get("game_id", "test")
        board = create_live_game_board(game_id)
        
        # Process the live data
        report = board.update_from_timestamp(live_data)
        state = board.get_state()
        
        print(f"Processed {report['events_processed']} events")
        print(f"Final score: {state['score']}")
        print(f"Goals: {len(state['goals'])}")
        print(f"Penalties: {len(state['penalties'])}")
        
        print("✅ Real data test passed")
    else:
        print("⚠️ No existing live data found, skipping real data test")

if __name__ == "__main__":
    print("🧪 Testing Simplified LiveGameBoard\n")
    
    try:
        test_basic_board_creation()
        test_session_serialization()
        test_timestamp_processing()
        test_with_existing_data()
        
        print("\n🎉 All tests passed! Simplified board is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)