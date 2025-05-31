#!/usr/bin/env python3
"""
NHL API Live Data Fetcher
Fetches and prints data for a given NHL game using the current NHL API endpoints.
"""
import requests
import sys
import time
import argparse
import json
import os
from datetime import datetime

def fetch_feed_live(game_id, last_play_id=None, collect_output=False):
    url = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/play-by-play"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch play-by-play: {e}")
        return [], last_play_id, []
    data = resp.json()
    plays = data.get("plays", [])
    new_plays = []
    formatted_plays = []
    
    for play in plays:
        event_id = play.get('eventId', 0)
        if last_play_id is None or event_id > last_play_id:
            period = play.get('periodDescriptor', {}).get('number', 0)
            time_str = play.get('timeInPeriod', '')
            type_desc = play.get('typeDescKey', 'unknown')
            details = play.get('details', {})
            
            # Build a meaningful description
            desc_parts = [type_desc]
            
            if details:
                # Add team info
                team_id = details.get('eventOwnerTeamId')
                if team_id:
                    # Look up team abbreviation from the game data
                    home_team = data.get('homeTeam', {})
                    away_team = data.get('awayTeam', {})
                    if home_team.get('id') == team_id:
                        desc_parts.append(f"({home_team.get('abbrev', 'HOME')})")
                    elif away_team.get('id') == team_id:
                        desc_parts.append(f"({away_team.get('abbrev', 'AWAY')})")
                
                # Add specific details based on play type
                if type_desc == 'shot-on-goal':
                    shot_type = details.get('shotType', '')
                    if shot_type:
                        desc_parts.append(f"- {shot_type} shot")
                elif type_desc == 'goal':
                    desc_parts.append("🚨 GOAL!")
                elif type_desc == 'stoppage':
                    reason = details.get('reason', '')
                    if reason:
                        desc_parts.append(f"- {reason}")
                elif type_desc == 'faceoff':
                    zone = details.get('zoneCode', '')
                    if zone:
                        zone_name = {'O': 'Offensive', 'D': 'Defensive', 'N': 'Neutral'}.get(zone, zone)
                        desc_parts.append(f"- {zone_name} zone")
            
            full_desc = " ".join(desc_parts)
            formatted_play = f"Period {period} {time_str}: {full_desc}"
            
            if not collect_output:
                print(formatted_play)
            
            formatted_plays.append(formatted_play)
            new_plays.append(play)
    
    if plays:
        last_play_id = max([play.get('eventId', 0) for play in plays])
    
    if collect_output:
        return new_plays, last_play_id, formatted_plays, data
    return new_plays, last_play_id, formatted_plays

def fetch_boxscore(game_id):
    url = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch boxscore: {e}")
        return
    data = resp.json()
    print("Boxscore summary:")
    
    # Get team info
    home_team = data.get('homeTeam', {})
    away_team = data.get('awayTeam', {})
    
    print(f"Away: {away_team.get('name', {}).get('default', 'Unknown')} - Score: {away_team.get('score', 0)}")
    print(f"Home: {home_team.get('name', {}).get('default', 'Unknown')} - Score: {home_team.get('score', 0)}")
    
    # Game state
    game_state = data.get('gameState', 'Unknown')
    print(f"Game State: {game_state}")

def fetch_shiftcharts(game_id):
    url = f"https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId={game_id}"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch shiftcharts: {e}")
        return
    data = resp.json()
    shift_data = data.get('data', [])
    print(f"Shift chart entries: {len(shift_data)}")
    if shift_data:
        print("Sample shift entries:")
        for i, shift in enumerate(shift_data[:3]):  # Show first 3 entries
            player = shift.get('firstName', '') + ' ' + shift.get('lastName', '')
            start_time = shift.get('startTime', '')
            end_time = shift.get('endTime', '')
            print(f"  {player}: {start_time} - {end_time}")

def save_game_data(game_id, data, plays_output):
    """Save game data to JSON file with meaningful filename"""
    # Extract game info for filename
    game_date = data.get('gameDate', '')
    home_team = data.get('homeTeam', {}).get('abbrev', 'HOME')
    away_team = data.get('awayTeam', {}).get('abbrev', 'AWAY')
    
    # Format date for filename (YYYYMMDD)
    if game_date:
        try:
            date_obj = datetime.fromisoformat(game_date.replace('Z', '+00:00'))
            formatted_date = date_obj.strftime('%Y%m%d')
        except:
            formatted_date = 'unknown_date'
    else:
        formatted_date = 'unknown_date'
    
    filename = f"../../../data/sample_games/{formatted_date}_{away_team}_{home_team}_nhl_playbyplay.json"
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # Prepare structured data for saving
    structured_data = {
        'game_id': game_id,
        'game_info': {
            'date': data.get('gameDate'),
            'season': data.get('season'),
            'game_state': data.get('gameState'),
            'venue': data.get('venue', {}).get('default', 'Unknown'),
            'home_team': {
                'name': data.get('homeTeam', {}).get('name', {}).get('default', 'Unknown'),
                'abbrev': home_team,
                'score': data.get('homeTeam', {}).get('score', 0)
            },
            'away_team': {
                'name': data.get('awayTeam', {}).get('name', {}).get('default', 'Unknown'),
                'abbrev': away_team,
                'score': data.get('awayTeam', {}).get('score', 0)
            }
        },
        'play_by_play': data.get('plays', []),
        'formatted_plays': plays_output,
        'total_plays': len(data.get('plays', [])),
        'extracted_timestamp': datetime.now().isoformat()
    }
    
    # Save to file
    with open(filename, 'w') as f:
        json.dump(structured_data, f, indent=2)
    
    print(f"\n💾 Game data saved to: {filename}")
    return filename

def parse_game_time(time_str):
    """Parse time string like '10:00' or '2:05:30' into (period, minutes, seconds)"""
    if not time_str:
        return None
    
    parts = time_str.split(':')
    if len(parts) == 2:
        # Format: MM:SS (Period 1)
        return (1, int(parts[0]), int(parts[1]))
    elif len(parts) == 3:
        # Format: P:MM:SS 
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    else:
        raise ValueError("Time format should be 'MM:SS' or 'P:MM:SS'")

def time_to_seconds(period, minutes, seconds):
    """Convert game time to total seconds"""
    return (period - 1) * 1200 + (minutes * 60) + seconds

def seconds_to_game_time(total_seconds):
    """Convert total seconds back to (period, minutes, seconds)"""
    period = (total_seconds // 1200) + 1
    remaining = total_seconds % 1200
    minutes = remaining // 60
    seconds = remaining % 60
    return (period, minutes, seconds)

def filter_plays_by_time(plays, target_period, target_minutes, target_seconds):
    """Filter plays up to a specific game time"""
    target_total = time_to_seconds(target_period, target_minutes, target_seconds)
    filtered_plays = []
    
    for play in plays:
        period = play.get('periodDescriptor', {}).get('number', 1)
        time_str = play.get('timeInPeriod', '00:00')
        
        # Parse time in period (format: MM:SS)
        try:
            time_parts = time_str.split(':')
            minutes = int(time_parts[0])
            seconds = int(time_parts[1])
            
            play_total = time_to_seconds(period, minutes, seconds)
            
            if play_total <= target_total:
                filtered_plays.append(play)
            else:
                break
                
        except (ValueError, IndexError):
            continue
    
    return filtered_plays

def replay_simulation(game_id, target_time_str, interval=2, speed=1.0, save_output=True):
    """Simulate live game replay up to target time with incremental updates"""
    target_period, target_minutes, target_seconds = parse_game_time(target_time_str)
    target_total = time_to_seconds(target_period, target_minutes, target_seconds)
    
    print(f"🎬 REPLAY SIMULATION MODE")
    print(f"Target: Period {target_period} {target_minutes:02d}:{target_seconds:02d} elapsed")
    print(f"Update interval: Every {interval} seconds of game time")
    print(f"Playback speed: {speed}x")
    print("=" * 60)
    
    # Fetch all game data once
    url = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/play-by-play"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"Failed to fetch game data: {e}")
        return
    
    all_plays = data.get("plays", [])
    home_team = data.get('homeTeam', {}).get('abbrev', 'HOME')
    away_team = data.get('awayTeam', {}).get('abbrev', 'AWAY')
    home_score = data.get('homeTeam', {}).get('score', 0)
    away_score = data.get('awayTeam', {}).get('score', 0)
    
    print(f"🏒 {away_team} @ {home_team}")
    print()
    
    current_time = 0
    shown_plays = set()  # Track which plays we've already shown
    replay_output = []  # Store formatted output for saving
    replay_plays = []   # Store raw play data for saving
    
    while current_time <= target_total:
        period, minutes, seconds = seconds_to_game_time(current_time)
        
        # Find plays in current time window
        window_end = current_time + interval
        new_plays_in_window = []
        
        for play in all_plays:
            play_period = play.get('periodDescriptor', {}).get('number', 1)
            play_time_str = play.get('timeInPeriod', '00:00')
            
            try:
                time_parts = play_time_str.split(':')
                play_minutes = int(time_parts[0])
                play_seconds = int(time_parts[1])
                play_total = time_to_seconds(play_period, play_minutes, play_seconds)
                
                # Check if play is in current window and not already shown
                play_id = play.get('eventId', 0)
                if (current_time <= play_total < window_end and 
                    play_id not in shown_plays and 
                    play_total <= target_total):
                    
                    new_plays_in_window.append(play)
                    shown_plays.add(play_id)
                    replay_plays.append(play)  # Save for file output
                    
            except (ValueError, IndexError):
                continue
        
        # Calculate remaining time
        remaining_minutes = 20 - minutes
        remaining_seconds = 0 - seconds
        if remaining_seconds < 0:
            remaining_minutes -= 1
            remaining_seconds += 60
        
        # Get current game state at this time
        current_home_score = home_score
        current_away_score = away_score
        
        # Update scores based on goals seen so far
        for play in replay_plays:
            if play.get('typeDescKey') == 'goal':
                goal_details = play.get('details', {})
                if goal_details.get('homeScore') is not None:
                    current_home_score = goal_details.get('homeScore')
                    current_away_score = goal_details.get('awayScore')
        
        # ALWAYS create a time window (this is the key change)
        time_header = f"⏰ Period {period} | {minutes:02d}:{seconds:02d} elapsed | {remaining_minutes:02d}:{remaining_seconds:02d} remaining"
        
        # Create game state info
        game_state = {
            "period": period,
            "time_elapsed": f"{minutes:02d}:{seconds:02d}",
            "time_remaining": f"{remaining_minutes:02d}:{remaining_seconds:02d}",
            "score": {
                "away": {"team": away_team, "score": current_away_score},
                "home": {"team": home_team, "score": current_home_score}
            }
        }
        
        print(time_header)
        print("-" * 50)
        
        window_plays = []
        
        if new_plays_in_window:
            # Process actual events that occurred
            for play in new_plays_in_window:
                period_num = play.get('periodDescriptor', {}).get('number', 0)
                time_str = play.get('timeInPeriod', '')
                type_desc = play.get('typeDescKey', 'unknown')
                details = play.get('details', {})
                
                # Build description
                desc_parts = [type_desc.replace('-', ' ').title()]
                
                if details:
                    team_id = details.get('eventOwnerTeamId')
                    if team_id:
                        home_team_data = data.get('homeTeam', {})
                        away_team_data = data.get('awayTeam', {})
                        if home_team_data.get('id') == team_id:
                            desc_parts.append(f"[{home_team}]")
                        elif away_team_data.get('id') == team_id:
                            desc_parts.append(f"[{away_team}]")
                    
                    if type_desc == 'shot-on-goal':
                        shot_type = details.get('shotType', '')
                        if shot_type:
                            desc_parts.append(f"({shot_type})")
                    elif type_desc == 'goal':
                        desc_parts.append("🚨")
                    elif type_desc == 'stoppage':
                        reason = details.get('reason', '').replace('-', ' ')
                        if reason:
                            desc_parts.append(f"({reason})")
                    elif type_desc == 'faceoff':
                        zone = details.get('zoneCode', '')
                        if zone:
                            zone_name = {'O': 'Off', 'D': 'Def', 'N': 'Neu'}.get(zone, zone)
                            desc_parts.append(f"({zone_name})")
                
                full_desc = " ".join(desc_parts)
                formatted_line = f"    {time_str} - {full_desc}"
                print(formatted_line)
                
                window_plays.append({
                    "time": time_str,
                    "description": full_desc,
                    "type": type_desc,
                    "details": details
                })
        else:
            # No events in this window - show game continuation
            print("    Game continuing...")
        
        # Store this window for saving (ALWAYS, regardless of events)
        replay_output.append({
            "time_window": f"Period {period} {minutes:02d}:{seconds:02d}",
            "header": time_header,
            "game_state": game_state,
            "plays": window_plays,
            "has_events": len(window_plays) > 0
        })
        
        print()
        current_time += interval
        
        # Sleep based on speed (don't sleep on last iteration)
        if current_time <= target_total:
            time.sleep(interval / speed)  # Adjustable playback speed
    
    # Save to file if requested
    if save_output and replay_output:
        # Create filename
        game_date = data.get('gameDate', '').split('T')[0].replace('-', '')
        if not game_date:
            game_date = 'unknown_date'
        
        time_label = f"0-{target_minutes}min" if target_period == 1 else f"P{target_period}-{target_minutes}min"
        filename = f"../../../data/sample_games/{game_date}_{away_team}_{home_team}_replay_{time_label}.json"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Prepare data for saving
        save_data = {
            "game_id": game_id,
            "game_info": {
                "date": data.get('gameDate'),
                "home_team": home_team,
                "away_team": away_team,
                "venue": data.get('venue', {}).get('default', 'Unknown')
            },
            "replay_parameters": {
                "target_time": target_time_str,
                "period": target_period,
                "minutes": target_minutes,
                "seconds": target_seconds,
                "interval": interval,
                "speed": speed
            },
            "formatted_output": replay_output,
            "raw_plays": replay_plays,
            "total_plays_shown": len(replay_plays),
            "generated_timestamp": datetime.now().isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(save_data, f, indent=2)
        
        print(f"💾 Replay simulation saved to: {filename}")
        print(f"📊 {len(replay_plays)} plays captured in {len(replay_output)} time windows")
        return filename

def main():
    parser = argparse.ArgumentParser(description="NHL API Live Data Fetcher")
    parser.add_argument('game_id', type=str, help='NHL game ID to fetch')
    parser.add_argument('--endpoint', type=str, choices=['feed', 'boxscore', 'shiftcharts'], default='feed', help='Which endpoint to poll (default: feed)')
    parser.add_argument('--replay-to', type=str, help='Replay simulation up to game time (format: "MM:SS" or "P:MM:SS")')
    parser.add_argument('--speed', type=float, default=1.0, help='Playback speed multiplier (default: 1.0)')
    parser.add_argument('--no-save', action='store_true', help='Do not save replay output to file')
    args = parser.parse_args()

    if args.replay_to:
        replay_simulation(args.game_id, args.replay_to, speed=args.speed, save_output=not args.no_save)
        return

    if args.endpoint == 'feed':
        # First check if game is live or completed
        url = f"https://api-web.nhle.com/v1/gamecenter/{args.game_id}/play-by-play"
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            data = resp.json()
            game_state = data.get('gameState', 'UNKNOWN')
            print(f"Game State: {game_state}")
            
            if game_state in ['FINAL', 'OFF']:
                print("Game is completed. Showing all plays:")
                _, _, formatted_plays, game_data = fetch_feed_live(args.game_id, last_play_id=None, collect_output=True)
                print(f"\nTotal plays: {len(game_data.get('plays', []))}")
                
                # Save data to file
                saved_file = save_game_data(args.game_id, game_data, formatted_plays)
                print(f"📊 Data ready for analysis in: {saved_file}")
            else:
                print("Game is live. Starting continuous polling. Press Ctrl+C to stop.")
                last_play_id = None
                try:
                    while True:
                        _, last_play_id, _ = fetch_feed_live(args.game_id, last_play_id)
                        time.sleep(5)
                except KeyboardInterrupt:
                    print("\nStopped live polling.")
        except Exception as e:
            print(f"Error checking game state: {e}")
    elif args.endpoint == 'boxscore':
        fetch_boxscore(args.game_id)
    elif args.endpoint == 'shiftcharts':
        fetch_shiftcharts(args.game_id)

if __name__ == "__main__":
    main() 