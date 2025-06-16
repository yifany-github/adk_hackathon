#!/usr/bin/env python3
"""
Extract dialogue from extended test session for game 2024030413
"""

import json
import glob
import os
from datetime import datetime

def extract_game_dialogue(game_id):
    """Extract dialogue from specific game's commentary files"""
    
    # Find all commentary files for this game
    pattern = f"/Users/yongboyu/Desktop/adk_hackathon/data/commentary_agent_outputs/{game_id}/*_commentary_board.json"
    files = sorted(glob.glob(pattern))
    
    if not files:
        print(f"❌ No commentary files found for game {game_id}!")
        return
    
    print(f"🎙️ Found {len(files)} commentary files for game {game_id}")
    
    all_dialogue = []
    
    for file_path in files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Extract timestamp from filename
            filename = os.path.basename(file_path)
            timestamp_part = filename.replace('_commentary_board.json', '')
            
            # Parse timestamp (e.g., "1_01_00" -> "Period 1, 1:00")
            parts = timestamp_part.split('_')
            if len(parts) >= 3:
                period = parts[0]
                minutes = parts[1]
                seconds = parts[2]
                formatted_time = f"Period {period}, {minutes}:{seconds}"
            else:
                formatted_time = timestamp_part
            
            # Extract dialogue sequence
            if 'commentary_sequence' in data:
                dialogue_entry = {
                    'timestamp': formatted_time,
                    'type': data.get('commentary_type', 'general'),
                    'dialogue': []
                }
                
                for item in data['commentary_sequence']:
                    speaker = item.get('speaker', 'Unknown')
                    text = item.get('text', '')
                    emotion = item.get('emotion', 'neutral')
                    
                    dialogue_entry['dialogue'].append({
                        'speaker': speaker,
                        'text': text,
                        'emotion': emotion
                    })
                
                all_dialogue.append(dialogue_entry)
                
        except Exception as e:
            print(f"⚠️ Error processing {os.path.basename(file_path)}: {e}")
    
    # Create clean summary
    output_file = f"/Users/yongboyu/Desktop/adk_hackathon/game_{game_id}_extended_test_dialogue.txt"
    
    with open(output_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write(f"NHL GAME {game_id} - EXTENDED SESSION TEST\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Game: Florida Panthers @ Edmonton Oilers\n")
        f.write(f"Test Duration: 2 minutes (24 timestamps)\n")
        f.write(f"Commentary Files: {len(all_dialogue)}\n")
        f.write("\n")
        
        f.write("BROADCASTERS:\n")
        f.write("• Alex Chen (Play-by-Play)\n")
        f.write("• Mike Rodriguez (Color Commentary)\n")
        f.write("\n")
        
        f.write("SESSION-AWARE COMMENTARY TEST:\n")
        f.write("This test verifies that the commentary agents maintain context across timestamps,\n")
        f.write("avoiding repetitive content and maintaining natural conversation flow.\n")
        f.write("\n")
        
        f.write("-" * 80 + "\n")
        f.write("GAME COMMENTARY\n")
        f.write("-" * 80 + "\n\n")
        
        for entry in all_dialogue:
            # Write clean timestamp header
            f.write(f"🕐 {entry['timestamp']} [{entry['type'].upper()}]\n")
            f.write("-" * 50 + "\n")
            
            # Write dialogue with cleaner format
            for line in entry['dialogue']:
                f.write(f"{line['speaker']}: {line['text']}\n")
            
            f.write("\n")
    
    print(f"✅ Extracted dialogue from {len(all_dialogue)} timestamps")
    print(f"📄 Summary saved to: {output_file}")
    
    # Show key stats
    total_lines = sum(len(entry['dialogue']) for entry in all_dialogue)
    alex_lines = sum(1 for entry in all_dialogue for line in entry['dialogue'] if line['speaker'] == 'Alex Chen')
    mike_lines = sum(1 for entry in all_dialogue for line in entry['dialogue'] if line['speaker'] == 'Mike Rodriguez')
    
    print(f"\n📊 COMMENTARY STATISTICS:")
    print(f"  Total dialogue lines: {total_lines}")
    print(f"  Alex Chen lines: {alex_lines}")
    print(f"  Mike Rodriguez lines: {mike_lines}")
    print(f"  Commentary types: {set(entry['type'] for entry in all_dialogue)}")
    
    return output_file

if __name__ == "__main__":
    extract_game_dialogue("2024030413")