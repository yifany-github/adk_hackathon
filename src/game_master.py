#!/usr/bin/env python3
"""
Game Master - Master controller for NHL game data generation
Provides a simple interface to initialize and manage NHL games
"""
import sys
import subprocess
import os
from datetime import datetime
from typing import Optional


class GameMaster:
    """Master controller for NHL game data generation"""
    
    def __init__(self):
        self.pipeline_path = "data/pipeline/nhl_game_pipeline.py"
        self.data_root = "../data"
    
    def initialize_game(self, game_id: str, duration_minutes: int = 10) -> bool:
        """
        Initialize complete NHL game data generation
        
        Args:
            game_id: NHL game ID (e.g., "2024020001")
            duration_minutes: How long to collect live data
            
        Returns:
            bool: True if successful, False otherwise
        """
        print(f"🎮 Game Master: Initializing NHL Game {game_id}")
        print(f"⏱️  Duration: {duration_minutes} minutes")
        print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Check if pipeline exists
        if not os.path.exists(self.pipeline_path):
            print(f"❌ Pipeline not found: {self.pipeline_path}")
            return False
        
        # Run the complete pipeline
        try:
            result = subprocess.run([
                "python3", self.pipeline_path, game_id, str(duration_minutes)
            ], cwd="src/data/pipeline", check=True, capture_output=True, text=True)
            
            print(result.stdout)
            print("\n🎉 Game Master: Initialization Complete!")
            print(f"📊 Game {game_id} data generation successful")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Game Master: Pipeline failed")
            print(f"Error: {e}")
            if e.stderr:
                print(f"Details: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ Game Master: Unexpected error: {e}")
            return False
    
    def quick_test(self, game_id: str) -> bool:
        """Quick 2-minute test of the pipeline"""
        print("⚡ Game Master: Quick Test Mode")
        return self.initialize_game(game_id, duration_minutes=2)
    
    def full_session(self, game_id: str) -> bool:
        """Full 30-minute session for comprehensive data"""
        print("🚀 Game Master: Full Session Mode")
        return self.initialize_game(game_id, duration_minutes=30)
    
    def get_data_summary(self, game_id: str) -> dict:
        """Get summary of generated data for a game"""
        summary = {
            'game_id': game_id,
            'static_files': 0,
            'raw_files': 0,
            'narrative_files': 0,
            'total_files': 0
        }
        
        # Count static files
        static_dir = f"data/static"
        if os.path.exists(static_dir):
            static_files = [f for f in os.listdir(static_dir) if f.startswith(f"game_{game_id}")]
            summary['static_files'] = len(static_files)
        
        # Count raw files
        raw_dir = f"data/live/raw"
        if os.path.exists(raw_dir):
            raw_files = [f for f in os.listdir(raw_dir) if f.startswith(f"game_{game_id}")]
            summary['raw_files'] = len(raw_files)
        
        # Count narrative files
        desc_dir = f"data/live/descriptions"
        if os.path.exists(desc_dir):
            narrative_files = [f for f in os.listdir(desc_dir) if f.startswith(f"game_{game_id}")]
            summary['narrative_files'] = len(narrative_files)
        
        summary['total_files'] = summary['static_files'] + summary['raw_files'] + summary['narrative_files']
        return summary


def main():
    if len(sys.argv) < 2:
        print("🎮 NHL Game Master")
        print("=" * 40)
        print("Usage: python3 game_master.py COMMAND [GAME_ID] [OPTIONS]")
        print("\nCommands:")
        print("  init GAME_ID [MINUTES]  - Initialize game with custom duration")
        print("  test GAME_ID           - Quick 2-minute test")
        print("  full GAME_ID           - Full 30-minute session")
        print("  summary GAME_ID        - Show data summary for game")
        print("\nExamples:")
        print("  python3 game_master.py test 2024020001")
        print("  python3 game_master.py init 2024020001 15")
        print("  python3 game_master.py full 2024020001")
        print("  python3 game_master.py summary 2024020001")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    master = GameMaster()
    
    if command == "init":
        if len(sys.argv) < 3:
            print("❌ Error: Game ID required")
            sys.exit(1)
        game_id = sys.argv[2]
        duration = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        success = master.initialize_game(game_id, duration)
        sys.exit(0 if success else 1)
    
    elif command == "test":
        if len(sys.argv) < 3:
            print("❌ Error: Game ID required")
            sys.exit(1)
        game_id = sys.argv[2]
        success = master.quick_test(game_id)
        sys.exit(0 if success else 1)
    
    elif command == "full":
        if len(sys.argv) < 3:
            print("❌ Error: Game ID required")
            sys.exit(1)
        game_id = sys.argv[2]
        success = master.full_session(game_id)
        sys.exit(0 if success else 1)
    
    elif command == "summary":
        if len(sys.argv) < 3:
            print("❌ Error: Game ID required")
            sys.exit(1)
        game_id = sys.argv[2]
        summary = master.get_data_summary(game_id)
        print(f"\n📊 Data Summary for Game {game_id}")
        print(f"Static files: {summary['static_files']}")
        print(f"Raw files: {summary['raw_files']}")
        print(f"Narrative files: {summary['narrative_files']}")
        print(f"Total files: {summary['total_files']}")
    
    else:
        print(f"❌ Error: Unknown command '{command}'")
        sys.exit(1)


if __name__ == "__main__":
    main() 