#!/usr/bin/env python3
"""
Create a single JSON summary of all commentary in chronological order
"""

import json
import os
import glob
from typing import List, Dict, Any

def extract_commentary_summary(game_id: str) -> Dict[str, Any]:
    """Extract all commentary into a single chronological summary"""
    
    # Get all commentary files in order
    commentary_dir = f"data/commentary_agent_outputs/{game_id}"
    pattern = f"{commentary_dir}/*_commentary_board.json"
    all_files = sorted(glob.glob(pattern))
    
    print(f"📁 Found {len(all_files)} commentary files for game {game_id}")
    
    summary_entries = []
    
    for file_path in all_files:
        try:
            # Extract timestamp from filename
            filename = os.path.basename(file_path)
            timestamp = filename.replace('_commentary_board.json', '')
            
            # Parse timestamp (e.g., "1_00_15" -> Period 1, 00:15)
            parts = timestamp.split('_')
            period = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            
            # Load commentary data
            with open(file_path, 'r') as f:
                commentary_data = json.load(f)
            
            # Skip if no valid commentary
            if commentary_data.get('status') != 'success':
                continue
                
            commentary_type = commentary_data.get('commentary_type', 'unknown').upper()
            commentary_sequence = commentary_data.get('commentary_sequence', [])
            game_context = commentary_data.get('game_context', {})
            
            # Format dialogue
            dialogue_lines = []
            for line in commentary_sequence:
                speaker = line.get('speaker', 'Unknown')
                text = line.get('text', '')
                emotion = line.get('emotion', 'neutral')
                duration = line.get('duration_estimate', 0)
                
                dialogue_lines.append({
                    "speaker": speaker,
                    "text": text,
                    "emotion": emotion,
                    "duration_estimate": duration
                })
            
            # Create summary entry
            summary_entry = {
                "timestamp": f"Period {period}, {minutes:02d}:{seconds:02d}",
                "game_time": f"{period}_{minutes:02d}_{seconds:02d}",
                "commentary_type": commentary_type,
                "score": game_context.get('score', f"Score not available"),
                "time_remaining": game_context.get('time', 'Unknown'),
                "situation": game_context.get('situation', 'even strength'),
                "dialogue": dialogue_lines,
                "total_duration": commentary_data.get('total_duration_estimate', 0)
            }
            
            summary_entries.append(summary_entry)
            
        except Exception as e:
            print(f"⚠️ Error processing {file_path}: {e}")
            continue
    
    # Create final summary
    summary = {
        "game_id": game_id,
        "total_timestamps": len(summary_entries),
        "game_duration_covered": f"{len(summary_entries) * 5} seconds" if summary_entries else "0 seconds",
        "commentary_types_used": list(set([entry['commentary_type'] for entry in summary_entries])),
        "game_summary": {
            "start_time": summary_entries[0]['timestamp'] if summary_entries else "Unknown",
            "end_time": summary_entries[-1]['timestamp'] if summary_entries else "Unknown",
            "final_score": summary_entries[-1]['score'] if summary_entries else "Unknown"
        },
        "chronological_commentary": summary_entries
    }
    
    return summary

def format_readable_summary(summary: Dict[str, Any]) -> str:
    """Format summary into readable text format like the user requested"""
    
    readable_lines = []
    readable_lines.append(f"🏒 NHL COMMENTARY SUMMARY - Game {summary['game_id']}")
    readable_lines.append(f"📊 Duration: {summary['game_duration_covered']} ({summary['total_timestamps']} timestamps)")
    readable_lines.append(f"🎮 Final Score: {summary['game_summary']['final_score']}")
    readable_lines.append("=" * 80)
    readable_lines.append("")
    
    for entry in summary['chronological_commentary']:
        # Header for each timestamp
        readable_lines.append(f"🕐 {entry['timestamp']} [{entry['commentary_type']}]")
        readable_lines.append(f"   📊 {entry['score']} | ⏱️ {entry['time_remaining']} remaining | 🏒 {entry['situation']}")
        
        # Dialogue
        for line in entry['dialogue']:
            speaker = line['speaker']
            text = line['text']
            emotion = line['emotion']
            duration = line['duration_estimate']
            
            readable_lines.append(f"   {speaker} ({emotion}) [{duration:.1f}s]: {text}")
        
        readable_lines.append("")  # Blank line between timestamps
    
    return "\\n".join(readable_lines)

def main():
    """Create comprehensive commentary summary"""
    game_id = "2024030415"
    
    print(f"📝 Creating commentary summary for game {game_id}...")
    
    # Extract summary
    summary = extract_commentary_summary(game_id)
    
    if not summary['chronological_commentary']:
        print("❌ No commentary data found!")
        return
    
    # Save JSON summary
    output_file = f"data/commentary_summary_{game_id}.json"
    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"✅ JSON summary saved: {output_file}")
    
    # Create readable format
    readable_summary = format_readable_summary(summary)
    readable_file = f"data/commentary_summary_{game_id}_readable.txt"
    with open(readable_file, 'w') as f:
        f.write(readable_summary)
    
    print(f"✅ Readable summary saved: {readable_file}")
    
    # Show some sample output
    print(f"\\n📖 SAMPLE OUTPUT (first 3 timestamps):")
    print("=" * 60)
    
    for i, entry in enumerate(summary['chronological_commentary'][:3]):
        print(f"🕐 {entry['timestamp']} [{entry['commentary_type']}]")
        
        for line in entry['dialogue']:
            speaker = line['speaker']
            text = line['text']
            print(f"   {speaker}: {text}")
        print()
    
    if len(summary['chronological_commentary']) > 3:
        print(f"   ... and {len(summary['chronological_commentary']) - 3} more timestamps")
    
    print(f"\\n📁 Full summary files:")
    print(f"   JSON: {output_file}")
    print(f"   Text: {readable_file}")

if __name__ == "__main__":
    main()