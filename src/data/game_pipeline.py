#!/usr/bin/env python3
"""
NHL Game Pipeline - Complete 3-stage pipeline for a specific game
Implements the full NHL Live Streaming Data Architecture
"""
import sys
import subprocess
import time


def run_pipeline(game_id: str, duration_minutes: int = 2):
    """
    Run complete NHL data pipeline for a specific game
    
    Args:
        game_id: NHL game ID (e.g., "2024020001")  
        duration_minutes: How long to collect live data
    """
    print(f"🚀 Starting NHL Game Pipeline for Game {game_id}")
    print(f"⏱️  Live collection duration: {duration_minutes} minutes")
    print("=" * 50)
    
    # Phase 1: Generate static context
    print("\n📋 Phase 1: Generating static context...")
    try:
        result = subprocess.run([
            "python3", "src/data/static/static_info_generator.py", game_id
        ], check=True, capture_output=True, text=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Static context generation failed: {e}")
        print(e.stderr)
        return False
    
    # Phase 2A: Collect live data  
    print(f"\n📡 Phase 2A: Collecting live data for {duration_minutes} minutes...")
    try:
        result = subprocess.run([
            "python3", "src/data/live/live_data_collector.py", game_id, str(duration_minutes)
        ], check=True, capture_output=True, text=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Live data collection failed: {e}")
        print(e.stderr)
        return False
    
    print("\n✅ Pipeline complete!")
    print(f"📁 Check data/ directory for generated files:")
    print(f"   - data/static/game_{game_id}_static_context.json")
    print(f"   - data/live/{game_id}/game_{game_id}_live_*.json (with enhanced narratives)")
    
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 game_pipeline.py GAME_ID [DURATION_MINUTES]")
        print("Example: python3 game_pipeline.py 2024020001 5")
        print("\nThis runs the complete 2-stage pipeline:")
        print("  1. Generate static context for the game teams")
        print("  2. Collect live data with enhanced narratives in 5s intervals")  
        print("\nData will be saved to project root: data/")
        sys.exit(1)
    
    game_id = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    
    success = run_pipeline(game_id, duration)
    sys.exit(0 if success else 1) 