#!/usr/bin/env python3
"""
Extract Timestamp Descriptions - Extracts detailed play-by-play descriptions from live JSON files
Saves all descriptions in one chronological text file
"""
import os
import json
import sys
from pathlib import Path


def extract_timestamp_descriptions(game_id: str, output_dir: str = None):
    """Extract timestamp descriptions from live JSON files and save as one chronological text file"""
    
    # Set up paths
    script_dir = Path(__file__).parent
    project_root = script_dir
    live_dir = project_root / "data" / "live" / game_id
    
    if output_dir is None:
        txt_dir = project_root / "data" / "txt"
    else:
        txt_dir = Path(output_dir)
    
    # Create output directory
    txt_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all timestamp data files
    files = []
    for file in sorted(live_dir.glob('*.json')):
        if file.name.startswith(f'game_{game_id}_timestamp_'):
            files.append(file)
    
    if not files:
        # Check old flow files as fallback
        for file in sorted(live_dir.glob('*.json')):
            if file.name.startswith(f'game_{game_id}_flow_'):
                files.append(file)
                
    if not files:
        # NEW: Check for new naming pattern (e.g., 2024020001_1_12_15.json)
        for file in sorted(live_dir.glob(f'{game_id}_*.json')):
            files.append(file)
        
    if not files:
        print(f"⚠️ No timestamp or flow data files found for game {game_id}")
        return
        
    print(f"📊 Found {len(files)} data files for game {game_id}")
    
    # Create output file
    output_file = txt_dir / f"game_{game_id}_timestamps.txt"
    
    periods = {}
    error_count = 0
    
    # Process each file in chronological order
    with open(output_file, 'w') as out:
        out.write(f"NHL Game {game_id} - Timestamp Descriptions\n")
        out.write("=" * 60 + "\n")
        
        # First pass - collect data
        for file_path in sorted(files):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                game_time = data.get('game_time', 'unknown')
                period, mins, secs = game_time.split(':')
                time_key = f"{int(period):02d}:{int(mins):02d}:{int(secs):02d}"
                
                # Check for llm_description (current format)
                if 'llm_description' in data:
                    text = data.get('llm_description', 'No description available')
                    activity_count = data.get('activity_count', 0)
                # Check for new simple description format
                elif 'description' in data:
                    text = data.get('description', 'No description available')
                    activity_count = data.get('activity_count', 0)
                # Check for timestamp description (new format)
                elif 'timestamp_description' in data:
                    description = data.get('timestamp_description', {})
                    activity_count = description.get('activity_count', 0)
                    # Skip if there's an error field
                    if 'error' in description:
                        error_count += 1
                        continue
                    text = description.get('timestamp_description', 'No description available')
                # Fall back to flow commentary (old format)
                elif 'flow_commentary' in data:
                    description = data.get('flow_commentary', {})
                    activity_count = description.get('activity_count', 0)
                    # Skip if there's an error field
                    if 'error' in description:
                        error_count += 1
                        continue
                    text = description.get('flow_commentary', 'No description available')
                else:
                    error_count += 1
                    continue
                
                periods[time_key] = {
                    'game_time': game_time,
                    'activity_count': activity_count,
                    'description': text
                }
                
            except Exception as e:
                print(f"⚠️ Error processing {file_path.name}: {e}")
                error_count += 1
        
        # Write metadata
        out.write(f"Generated from {len(periods)} time periods\n")
        out.write(f"Errors encountered: {error_count}\n")
        out.write("=" * 60 + "\n\n")
        
        # Write sorted entries
        for time_key in sorted(periods.keys()):
            entry = periods[time_key]
            out.write(f"⏰ {entry['game_time']} | Activities: {entry['activity_count']}\n")
            out.write("-" * 50 + "\n")
            out.write(f"{entry['description']}\n\n")
    
    print(f"✅ Timestamp descriptions extracted to {output_file}")
    

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 extract_timestamp_descriptions.py GAME_ID")
        print("Example: python3 extract_timestamp_descriptions.py 2024020001")
        sys.exit(1)
        
    game_id = sys.argv[1]
    extract_timestamp_descriptions(game_id) 