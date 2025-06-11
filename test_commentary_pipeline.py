#!/usr/bin/env python3
"""
Test script for the Commentary Pipeline - generates timestamped dialogue
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agents.commentary_agent.commentary_pipeline import run_commentary_pipeline

async def test_pipeline():
    """Test the commentary pipeline with timestamped data"""
    
    print("🏒 NHL Commentary Pipeline Test")
    print("=" * 50)
    
    try:
        # Test with first 3 timestamps of the game
        print("Testing with first 3 timestamps...")
        result = await run_commentary_pipeline("2024030412", max_files=3)
        
        if result['status'] == 'success':
            print(f"\n✅ Pipeline test completed successfully!")
            print(f"📊 Results:")
            print(f"   Game ID: {result['game_id']}")
            print(f"   Files processed: {result['processed_files']}")
            print(f"   Successful: {result['successful']}")
            print(f"   Failed: {result['failed']}")
            print(f"   Output directory: {result['output_directory']}")
            
            # Show individual results
            for i, res in enumerate(result['results'], 1):
                if res['status'] == 'success':
                    timestamp = res.get('timestamp', 'unknown')
                    lines = res.get('dialogue_lines', 0)
                    print(f"   {i}. Timestamp {timestamp}: {lines} dialogue lines ✅")
                else:
                    error = res.get('error', 'Unknown error')
                    print(f"   {i}. Failed: {error} ❌")
            
            return True
        else:
            print(f"\n❌ Pipeline failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    success = await test_pipeline()
    if success:
        print("\n✅ Commentary pipeline test passed!")
        sys.exit(0)
    else:
        print("\n❌ Commentary pipeline test failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())