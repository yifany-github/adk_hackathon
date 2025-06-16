#!/usr/bin/env python3
"""
Simple NHL Commentary Dialogue Extractor
Extracts clean dialogue from commentary JSON files
"""

import json
import glob
import os
from datetime import datetime

def extract_all_dialogue():
    """Extract dialogue from all commentary files and create clean summary"""
    
    # Find all commentary files
    pattern = "/Users/yongboyu/Desktop/adk_hackathon/data/commentary_agent_outputs/*.json"
    files = sorted(glob.glob(pattern))
    
    if not files:
        print("❌ No commentary files found!")
        return
    
    print(f"🎙️ Found {len(files)} commentary files")
    
    all_dialogue = []
    
    for file_path in files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Extract basic info
            timestamp = data.get('timestamp', 'Unknown')
            commentary_type = data.get('commentary_type', 'general')
            
            # Extract dialogue sequence
            if 'commentary_sequence' in data:
                dialogue_entry = {
                    'timestamp': timestamp,
                    'type': commentary_type,
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
    output_file = "/Users/yongboyu/Desktop/adk_hackathon/full_game_commentary_final_test.txt"
    
    with open(output_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("NHL GAME COMMENTARY - COMPLETE SESSION\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Game: Florida Panthers @ Edmonton Oilers\n")
        f.write(f"Venue: Rogers Place\n")
        f.write(f"Commentary Files: {len(all_dialogue)}\n")
        f.write("\n")
        
        f.write("BROADCASTERS:\n")
        f.write("• Alex Chen (Play-by-Play) - 35-year veteran, Olympic & Stanley Cup Finals caller\n")
        f.write("• Mike Rodriguez (Analyst) - Former NHL scout & assistant coach\n")
        f.write("\n")
        
        f.write("-" * 80 + "\n")
        f.write("GAME COMMENTARY\n")
        f.write("-" * 80 + "\n\n")
        
        for entry in all_dialogue:
            # Write clean timestamp header
            f.write(f"🕐 {entry['timestamp']}\n")
            f.write("-" * 50 + "\n")
            
            # Write dialogue with cleaner format
            for line in entry['dialogue']:
                f.write(f"{line['speaker']}: {line['text']}\n")
            
            f.write("\n")
    
    print(f"✅ Extracted dialogue from {len(all_dialogue)} timestamps")
    print(f"📄 Summary saved to: {output_file}")
    
    # Show a preview
    print(f"\\n📖 Preview (first 3 entries):")
    print("-" * 60)
    
    for i, entry in enumerate(all_dialogue[:3]):
        print(f"[{entry['timestamp']}]")
        for line in entry['dialogue']:
            print(f"  {line['speaker']}: {line['text'][:80]}{'...' if len(line['text']) > 80 else ''}")
        print()

if __name__ == "__main__":
    extract_all_dialogue()