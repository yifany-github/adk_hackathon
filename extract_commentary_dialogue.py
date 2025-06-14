#!/usr/bin/env python3
"""
Extract and display dialogue from commentary agent JSON outputs
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any


def extract_dialogue_from_file(filepath: str) -> Dict[str, Any]:
    """Extract dialogue information from a single commentary JSON file"""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Extract basic info
        status = data.get('status', 'unknown')
        timestamp = os.path.basename(filepath).replace('_commentary_session_aware.json', '').replace('_commentary.json', '').replace('2024030412_', '')
        
        # Extract commentary data (handle both formats)
        # Check if data is nested under 'commentary_data' (older format) or direct (newer format)
        if 'commentary_data' in data:
            commentary_data = data['commentary_data']
            # Check if there's nested commentary_data (session-aware format)
            if 'commentary_data' in commentary_data:
                inner_data = commentary_data['commentary_data']
                commentary_type = inner_data.get('commentary_type', 'unknown')
                commentary_sequence = inner_data.get('commentary_sequence', [])
                total_duration = inner_data.get('total_duration_estimate', 0)
                game_context = inner_data.get('game_context', {})
            else:
                # Regular nested format
                commentary_type = commentary_data.get('commentary_type', 'unknown')
                commentary_sequence = commentary_data.get('commentary_sequence', [])
                total_duration = commentary_data.get('total_duration_estimate', 0)
                game_context = commentary_data.get('game_context', {})
        else:
            # Direct format (newer session-aware files)
            commentary_type = data.get('commentary_type', 'unknown')
            commentary_sequence = data.get('commentary_sequence', [])
            total_duration = data.get('total_duration_estimate', 0)
            game_context = data.get('game_context', {})
        
        return {
            'filepath': filepath,
            'timestamp': timestamp,
            'status': status,
            'commentary_type': commentary_type,
            'total_duration': total_duration,
            'dialogue_count': len(commentary_sequence),
            'dialogue': commentary_sequence,
            'game_context': game_context
        }
        
    except Exception as e:
        return {
            'filepath': filepath,
            'timestamp': timestamp if 'timestamp' in locals() else 'unknown',
            'status': 'error',
            'error': str(e),
            'dialogue': []
        }


def format_dialogue_display(dialogue_data: Dict[str, Any]) -> str:
    """Format dialogue data for readable display"""
    output = []
    
    # Header
    output.append("=" * 80)
    output.append(f"TIMESTAMP: {dialogue_data['timestamp']} | STATUS: {dialogue_data['status']}")
    output.append(f"TYPE: {dialogue_data.get('commentary_type', 'unknown')} | DURATION: {dialogue_data.get('total_duration', 0):.1f}s")
    
    # Game context
    game_context = dialogue_data.get('game_context', {})
    if game_context:
        if isinstance(game_context, dict):
            context_info = []
            if 'home_team' in game_context and 'away_team' in game_context:
                context_info.append(f"{game_context['away_team']} @ {game_context['home_team']}")
            if 'home_score' in game_context and 'away_score' in game_context:
                context_info.append(f"Score: {game_context['away_score']}-{game_context['home_score']}")
            if 'period' in game_context:
                context_info.append(f"Period {game_context['period']}")
            if 'time_remaining' in game_context:
                context_info.append(f"Time: {game_context['time_remaining']}")
            output.append(f"CONTEXT: {' | '.join(context_info)}")
        else:
            output.append(f"CONTEXT: {game_context}")
    
    output.append("-" * 80)
    
    # Dialogue
    if dialogue_data['status'] == 'error':
        output.append(f"❌ ERROR: {dialogue_data.get('error', 'Unknown error')}")
    elif not dialogue_data.get('dialogue'):
        output.append("❌ No dialogue found")
    else:
        for i, line in enumerate(dialogue_data['dialogue'], 1):
            speaker = line.get('speaker', 'unknown')
            text = line.get('text', '')
            emotion = line.get('emotion', '')
            timing = line.get('timing', 0)
            duration = line.get('duration_estimate', 0)
            
            # Format speaker name
            speaker_display = speaker.replace('_', ' ').title()
            if speaker in ['pbp', 'play-by-play']:
                speaker_display = "Play-by-Play"
            elif speaker in ['color', 'analyst']:
                speaker_display = "Analyst"
            elif speaker.startswith('announcer'):
                speaker_display = f"Announcer {speaker[-1]}"
            
            # Format timing and emotion
            metadata = []
            if timing:
                metadata.append(f"@{timing}s")
            if duration:
                metadata.append(f"{duration}s")
            if emotion and emotion != 'neutral':
                metadata.append(f"[{emotion}]")
            
            metadata_str = f" ({', '.join(metadata)})" if metadata else ""
            
            output.append(f"{i:2d}. {speaker_display}: {text}{metadata_str}")
    
    output.append("")
    return "\n".join(output)


def create_continuous_commentary(all_dialogue_data: List[Dict[str, Any]]) -> str:
    """Create a continuous commentary flow from all timestamps"""
    output = []
    
    # Header
    output.append("🎙️ NHL LIVE COMMENTARY - CONTINUOUS FLOW")
    output.append("=" * 80)
    
    game_info = None
    total_lines = 0
    total_duration = 0
    
    for data in all_dialogue_data:
        if data['status'] != 'success':
            continue
            
        # Extract game info from first successful file
        if not game_info and data.get('game_context'):
            game_info = data['game_context']
    
    # Show game header
    if game_info:
        if isinstance(game_info, dict):
            context_parts = []
            # Handle both old and new game context formats
            if 'teams' in game_info:
                away_team = game_info['teams']['away']
                home_team = game_info['teams']['home']
                context_parts.append(f"{away_team} @ {home_team}")
            elif 'away_team' in game_info and 'home_team' in game_info:
                context_parts.append(f"{game_info['away_team']} @ {game_info['home_team']}")
            
            if 'venue' in game_info:
                context_parts.append(game_info['venue'])
            
            if 'away_score' in game_info and 'home_score' in game_info:
                if 'teams' in game_info:
                    away_team = game_info['teams']['away']
                    home_team = game_info['teams']['home']
                    context_parts.append(f"Score: {away_team} {game_info['away_score']} - {home_team} {game_info['home_score']}")
                else:
                    context_parts.append(f"Score: {game_info['away_team']} {game_info['away_score']} - {game_info['home_team']} {game_info['home_score']}")
            output.append(" | ".join(context_parts))
        else:
            output.append(str(game_info))
    
    output.append("=" * 80)
    output.append("")
    
    # Process all dialogue in chronological order
    for data in all_dialogue_data:
        if data['status'] != 'success' or not data.get('dialogue'):
            continue
            
        timestamp = data['timestamp']
        output.append(f"⏰ {timestamp}")
        output.append("-" * 40)
        
        for line in data['dialogue']:
            speaker = line.get('speaker', 'unknown')
            text = line.get('text', '')
            
            # Format speaker name consistently
            if speaker in ['pbp', 'play-by-play']:
                speaker_name = "Play-by-Play"
            elif speaker in ['color', 'analyst']:
                speaker_name = "Analyst"
            elif speaker == 'announcer_1':
                speaker_name = "Jim Harrison"
            elif speaker == 'announcer_2':
                speaker_name = "Eddie Martinez"
            else:
                speaker_name = speaker.replace('_', ' ').title()
            
            output.append(f"{speaker_name}: {text}")
            total_lines += 1
        
        total_duration += data.get('total_duration', 0)
        output.append("")
    
    # Summary footer
    output.append("=" * 80)
    output.append(f"📊 COMMENTARY SUMMARY")
    output.append(f"📝 Total lines: {total_lines}")
    output.append(f"⏱️  Total duration: {total_duration:.1f} seconds")
    output.append("=" * 80)
    
    return "\n".join(output)


def main():
    """Main function to extract and display all commentary dialogues"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract NHL commentary dialogue')
    parser.add_argument('--output', '-o', help='Output file for continuous commentary (default: display only)')
    parser.add_argument('--continuous', '-c', action='store_true', help='Show continuous commentary flow')
    args = parser.parse_args()
    
    print("🎙️ NHL Commentary Dialogue Extractor")
    print("=" * 80)
    
    # Find commentary output directory
    output_dir = Path("data/commentary_agent_outputs")
    if not output_dir.exists():
        print(f"❌ Directory not found: {output_dir}")
        sys.exit(1)
    
    # Find all commentary JSON files (including session-aware ones)
    json_files = list(output_dir.glob("*_commentary*.json"))
    if not json_files:
        print(f"❌ No commentary JSON files found in {output_dir}")
        sys.exit(1)
    
    # Separate session-aware and regular files
    session_aware_files = [f for f in json_files if "_session_aware" in f.name]
    regular_files = [f for f in json_files if "_session_aware" not in f.name]
    
    if session_aware_files and regular_files:
        print("📋 Found both regular and session-aware commentary files")
        print("   Use --session-aware flag to view session-aware files only")
        print("   Use --regular flag to view regular files only")
    
    # Default to session-aware files if they exist, otherwise regular files
    if session_aware_files:
        json_files = session_aware_files
        print(f"📁 Using session-aware files: {len(json_files)} files")
    else:
        json_files = regular_files
        print(f"📁 Using regular files: {len(json_files)} files")
    
    # Sort files by timestamp
    json_files.sort()
    
    print(f"📁 Found {len(json_files)} commentary files")
    print()
    
    # Process each file
    all_dialogue_data = []
    for filepath in json_files:
        dialogue_data = extract_dialogue_from_file(str(filepath))
        all_dialogue_data.append(dialogue_data)
    
    # Show continuous commentary if requested
    if args.continuous or args.output:
        continuous_commentary = create_continuous_commentary(all_dialogue_data)
        
        if args.output:
            # Write to file
            with open(args.output, 'w') as f:
                f.write(continuous_commentary)
            print(f"✅ Continuous commentary saved to: {args.output}")
        else:
            # Display on screen
            print(continuous_commentary)
    else:
        # Show detailed breakdown (original behavior)
        for dialogue_data in all_dialogue_data:
            print(format_dialogue_display(dialogue_data))
        
        # Summary
        print("=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)
        
        successful_files = [d for d in all_dialogue_data if d['status'] == 'success']
        error_files = [d for d in all_dialogue_data if d['status'] == 'error']
        
        print(f"✅ Successful files: {len(successful_files)}")
        print(f"❌ Error files: {len(error_files)}")
        
        if successful_files:
            total_dialogue_lines = sum(d['dialogue_count'] for d in successful_files)
            total_duration = sum(d.get('total_duration', 0) for d in successful_files)
            print(f"📝 Total dialogue lines: {total_dialogue_lines}")
            print(f"⏱️  Total duration: {total_duration:.1f} seconds")
            
            # Commentary types
            types = [d['commentary_type'] for d in successful_files]
            unique_types = set(types)
            print(f"🎯 Commentary types: {', '.join(unique_types)}")
        
        if error_files:
            print("\n❌ Error files:")
            for error_file in error_files:
                print(f"   - {error_file['timestamp']}: {error_file.get('error', 'Unknown error')}")
        
        print(f"\n💡 Tip: Use --continuous or -c to see continuous commentary flow")
        print(f"💡 Tip: Use --output filename.txt to save continuous commentary to file")


if __name__ == "__main__":
    main()