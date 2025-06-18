#!/usr/bin/env python3
"""
Live Data Collector - Flow-descriptive NHL commentary generation
Core flow: fetch → filter → enhance → LLM → save

This script acts as a PRODUCER. It generates a data snapshot (JSON file) 
for a specific point in game time. It is stateless and intended to be run
at each interval of a game, creating a data stream for a separate consumer agent.

Can run in two modes:
1. Simulation Mode: Replays a past game as if it were live.
2. Live Mode: Fetches data for an ongoing game in real-time.

CLI Usage:
----------
Simulate Mode:
python3 src/data/live/live_data_collector.py simulate <GAME_ID> \
    --game_duration_minutes <MINUTES> \
    --fetch_interval_seconds <SECONDS> \
    --activity_window_seconds <SECONDS> \
    --real_time_delay_seconds <SECONDS>

Live Mode:
python3 src/data/live/live_data_collector.py live <GAME_ID> \
    --polling_interval_seconds <SECONDS> \
    --activity_window_seconds <SECONDS>
"""
import os
import json
import sys
import time
import requests
import google.generativeai as genai
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import copy
import argparse

# Assuming prompts.py and spatial_converter.py are in the same directory or accessible via PYTHONPATH
try:
    from prompts import DESCRIPTION_PROMPT
    from spatial_converter import coords_to_hockey_language, get_game_situation, format_time_remaining
except ImportError:
    print("❌ Error: Ensure 'prompts.py' and 'spatial_converter.py' are in the correct path.")
    DESCRIPTION_PROMPT = "Describe the following hockey activities that happened at {game_time}: {activity_data}"
    def coords_to_hockey_language(x, y, zone, home_side): return f"Location: {zone} ({x},{y})"
    def get_game_situation(code): return f"Situation: {code}"
    def format_time_remaining(time_str): return time_str


class LiveDataCollector:
    """Generates flow-descriptive commentary from live NHL data"""
    
    def __init__(self, game_id: str, output_dir: str = None, 
                 activity_window_seconds: int = 30,
                 fetch_interval_seconds: int = 5):
        self.game_id = game_id
        
        if output_dir is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root_candidate = os.path.join(script_dir, "..") 
            if not os.path.exists(os.path.join(project_root_candidate, "data")):
                 project_root_candidate = os.path.join(script_dir, "..", "..", "..") 
            
            project_root = os.path.abspath(project_root_candidate)
            self.output_dir = os.path.join(project_root, "data", "live", self.game_id)
        else:
            self.output_dir = output_dir
        
        self.base_url = "https://api-web.nhle.com/v1"
        self.static_context = None
        self.player_lookup = {}
        os.makedirs(self.output_dir, exist_ok=True)

        self.activity_window_seconds = activity_window_seconds
        self.fetch_interval_seconds = fetch_interval_seconds
        
        self._setup_llm()
        self._load_static_context()
        
        print(f"🏒 Live Data Collector Initialized for Game {game_id}")
        print(f"   Output directory: {self.output_dir}")
        print(f"   Activity window (game time): {self.activity_window_seconds}s")

    def _setup_llm(self):
        """Setup Google Gemini for flow commentary"""
        try:
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                print("⚠️ GOOGLE_API_KEY environment variable not set. LLM features will be disabled.")
                self.model = None
                return
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        except Exception as e:
            print(f"❌ LLM setup failed: {e}")
            self.model = None

    def _load_static_context(self):
        """Load player data for name enhancement"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root_candidate = os.path.join(script_dir, "..") 
            if not os.path.exists(os.path.join(project_root_candidate, "data")):
                 project_root_candidate = os.path.join(script_dir, "..", "..", "..")
            project_root = os.path.abspath(project_root_candidate)
            static_file = os.path.join(project_root, "data", "static", f"game_{self.game_id}_static_context.json")
            
            if os.path.exists(static_file):
                with open(static_file, 'r') as f:
                    self.static_context = json.load(f)
                self._build_player_lookup()
                print(f"✅ Static context loaded from: {static_file}")
            else:
                print(f"⚠️ No static context found at {static_file} - running without detailed player names from static file.")
        except Exception as e:
            print(f"⚠️ Could not load static context: {e}")

    def _build_player_lookup(self):
        """Build fast lookup for player names"""
        if not self.static_context or 'rosters' not in self.static_context:
            print("ℹ️ Static context does not contain roster information. Player name enhancement will rely on boxscore if available.")
            return
        rosters = self.static_context['rosters']
        for team_key, players_list_key in [('home', 'home_players'), ('away', 'away_players')]:
            for player in rosters.get(players_list_key, []):
                player_id = str(player.get('player_id', ''))
                if player_id:
                    self.player_lookup[player_id] = {
                        'name': player.get('name', 'Unknown Player'),
                        'position': player.get('position', 'N/A'),
                        'team': team_key
                    }
        if self.player_lookup:
            print(f"ℹ️ Built player lookup table with {len(self.player_lookup)} players from static context.")

    def _time_str_to_seconds(self, time_str: str) -> int:
        """Converts MM:SS string to total seconds."""
        try:
            if isinstance(time_str, str) and ':' in time_str:
                m, s = map(int, time_str.split(':'))
                return (m * 60) + s
            return 0
        except ValueError:
            return 0

    def _get_current_game_context_from_pbp(self, pbp_data: Dict) -> Dict[str, Any]:
        """
        Extracts current game state, time, and period from PBP data.
        'current_game_time_str' is in "P:MM:SS" elapsed format.
        """
        context = {
            'game_state': pbp_data.get('gameState'),
            'current_game_time_str': "1:00:00",
            'reliable_time': False
        }
        all_plays = pbp_data.get('plays', [])
        if all_plays:
            last_play = all_plays[-1]
            play_period_desc = last_play.get('periodDescriptor', {})
            play_period = play_period_desc.get('number')
            time_in_period = last_play.get('timeInPeriod')
            if play_period is not None and time_in_period:
                context['current_game_time_str'] = f"{play_period}:{time_in_period}"
                context['reliable_time'] = True
                if context['game_state'] in ["PRE", "FUT"]:
                    context['game_state'] = "LIVE"
        return context

    def _get_play_by_play(self) -> Optional[Dict[str, Any]]:
        """Fetch all play-by-play data from NHL API"""
        try:
            url = f"{self.base_url}/gamecenter/{self.game_id}/play-by-play"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error getting play-by-play from {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ Error decoding JSON from play-by-play response: {e}")
            return None

    def _filter_activities(self, pbp_data: Dict[str, Any], current_game_time_str: str) -> List[Dict]:
        """Filter activities by time window."""
        try:
            period_str, time_in_period_str = current_game_time_str.split(':', 1)
            current_period_num = int(period_str)
            current_minutes, current_seconds_val = map(int, time_in_period_str.split(':'))
            current_total_seconds_in_period_elapsed = (current_minutes * 60) + current_seconds_val
        except ValueError:
            return []
        
        activities = []
        for play in pbp_data.get('plays', []):
            play_period = play.get('periodDescriptor', {}).get('number', 0)
            if play_period != current_period_num:
                continue
            
            play_time_in_period_str = play.get('timeInPeriod', '')
            if not play_time_in_period_str: continue
            
            try:
                play_min, play_sec = map(int, play_time_in_period_str.split(':'))
                play_total_seconds_elapsed = (play_min * 60) + play_sec
                
                if play_total_seconds_elapsed > current_total_seconds_in_period_elapsed:
                    continue
                
                time_difference_seconds = current_total_seconds_in_period_elapsed - play_total_seconds_elapsed
                if 0 <= time_difference_seconds <= self.activity_window_seconds:
                    activities.append(play)
            except (ValueError, AttributeError):
                continue
        return activities

    def _get_boxscore(self) -> Optional[Dict[str, Any]]:
        """Fetch boxscore data for enhancement."""
        try:
            url = f"{self.base_url}/gamecenter/{self.game_id}/boxscore"
            response = requests.get(url, timeout=10) 
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, json.JSONDecodeError):
            return None

    def _enhance_activities(self, activities: List[Dict]) -> List[Dict]:
        """Add player names, spatial context, and basic stats to activities."""
        enhanced_activities = []
        boxscore_data = self._get_boxscore() 
        
        for activity in activities:
            enhanced_activity = copy.deepcopy(activity) 
            details = enhanced_activity.get('details', {})
            if not details: enhanced_activity['details'] = details = {}

            player_fields = ['attackingPlayerId', 'blockingPlayerId', 'committedByPlayerId', 'drawnByPlayerId', 'goalieInNetId', 'hittingPlayerId', 'hitteePlayerId', 'losingPlayerId', 'playerId', 'assist1PlayerId', 'assist2PlayerId', 'shootingPlayerId', 'winningPlayerId']
            for field in player_fields:
                if field in details and details[field] is not None:
                    player_id_val = str(details[field])
                    if player_id_val in self.player_lookup:
                        player_info = self.player_lookup[player_id_val]
                        details[field.replace('Id', 'Name')] = f"{player_info['name']} ({player_info['team']})"

            x, y, zone = details.get('xCoord'), details.get('yCoord'), details.get('zoneCode')
            home_side = enhanced_activity.get('homeTeamDefendingSide', 'left')
            if x is not None and y is not None and zone:
                details['spatialDescription'] = coords_to_hockey_language(x, y, zone, home_side)
            
            if 'situationCode' in enhanced_activity:
                enhanced_activity['gameSituation'] = get_game_situation(enhanced_activity['situationCode'])
            if 'timeRemaining' in enhanced_activity:
                enhanced_activity['timeRemainingFormatted'] = format_time_remaining(enhanced_activity['timeRemaining'])

            # Removed: boxscore injection that caused data leakage
            
            enhanced_activities.append(enhanced_activity)
        
        enhanced_activities.sort(key=self._get_time_seconds_from_play_time_in_period)
        
        # Calculate progressive game stats from filtered activities (fixes data leakage)
        progressive_stats = self._calculate_progressive_stats(enhanced_activities)
        
        # Apply progressive stats to all activities
        for activity in enhanced_activities:
            activity['gameStats'] = progressive_stats
        
        return enhanced_activities
    
    def _calculate_progressive_stats(self, activities: List[Dict]) -> Dict:
        """Calculate progressive game stats from time-filtered activities only (prevents data leakage)."""
        # Initialize counters
        away_score = home_score = away_shots = home_shots = 0
        away_team_name = "AWAY"  # Default fallback
        home_team_name = "HOME"  # Default fallback
        
        # Get team names from static context (dynamic based on game_id)
        if self.static_context and 'game_info' in self.static_context:
            game_info = self.static_context['game_info']
            away_team_name = game_info.get('away_team', 'AWAY')
            home_team_name = game_info.get('home_team', 'HOME')
        
        # Dynamically determine team IDs from actual event data
        away_team_id = None
        home_team_id = None
        
        # First pass: determine team IDs from any event (no assumptions)
        for activity in activities:
            details = activity.get('details', {})
            team_id = details.get('eventOwnerTeamId')
            if team_id:
                # Use player info to determine home/away
                player_name = details.get('scoringPlayerName', details.get('winningPlayerName', ''))
                if '(away)' in player_name:
                    away_team_id = team_id
                elif '(home)' in player_name:
                    home_team_id = team_id
        
        # If still no team IDs found, skip team-specific stats (no hardcoded assumptions)
        if away_team_id is None or home_team_id is None:
            # Return basic stats without team-specific breakdown
            return {
                "home_score": 0,
                "away_score": 0, 
                "home_shots": 0,
                "away_shots": 0,
                "home_team": home_team_name,
                "away_team": away_team_name,
                "total_events": len(activities),
                "warning": "Could not determine team IDs from event data"
            }
        
        # Second pass: count events
        for activity in activities:
            event_type = activity.get('typeDescKey', '')
            details = activity.get('details', {})
            team_id = details.get('eventOwnerTeamId')
            
            if not team_id:
                continue
                
            # Count goals
            if event_type == 'goal':
                if team_id == away_team_id:
                    away_score += 1
                elif team_id == home_team_id:
                    home_score += 1
            
            # Count shots (goals + saves + shots on goal)
            if event_type in ['goal', 'shot-on-goal', 'save']:
                if team_id == away_team_id:
                    away_shots += 1
                elif team_id == home_team_id:
                    home_shots += 1
        
        return {
            'teamStats': {
                'away': {
                    'teamName': away_team_name,
                    'score': away_score,
                    'sog': away_shots
                },
                'home': {
                    'teamName': home_team_name,
                    'score': home_score,
                    'sog': home_shots
                }
            },
            'playerStats': {}
        }

    def _extract_game_stats(self, boxscore_data: Dict) -> Dict:
        """DEPRECATED: Extracts team stats including live score and SOG from the boxscore.
        This method caused data leakage by injecting final stats into early timestamps.
        Replaced by _calculate_progressive_stats."""
        stats = {'teamStats': {}, 'playerStats': {}}
        away_team = boxscore_data.get('awayTeam', {})
        home_team = boxscore_data.get('homeTeam', {})
        
        # The only change is here: adding score and sog (shots on goal)
        stats['teamStats'] = {
            'away': {
                'teamName': away_team.get('abbrev', 'AWAY'),
                'score': away_team.get('score', 0),
                'sog': away_team.get('sog', 0)
            },
            'home': {
                'teamName': home_team.get('abbrev', 'HOME'),
                'score': home_team.get('score', 0),
                'sog': home_team.get('sog', 0)
            }
        }
        # The playerStats object remains empty as per the original design, keeping it simple.
        return stats

    def _generate_flow_commentary(self, activities: List[Dict], current_game_time_str: str) -> str:
        """Generate a basic, stateless description of the activities in the window."""
        if not self.model:
            return self._get_fallback_description(len(activities))
        try:
            prompt_activities = []
            for act in activities:
                act_summary = {
                    "type": act.get("typeDescKey", "unknown_event"),
                    "timeInPeriod": act.get("timeInPeriod"),
                }
                prompt_activities.append(act_summary)

            activities_json = json.dumps(prompt_activities, ensure_ascii=False, indent=None)
            prompt_str = DESCRIPTION_PROMPT.replace('{activity_data}', activities_json).replace('{game_time}', current_game_time_str)
            response = self.model.generate_content(prompt_str)
            
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                return self._get_fallback_description(len(activities))
            
            return response.text.strip() if hasattr(response, 'text') else self._get_fallback_description(len(activities))
        except Exception as e:
            return self._get_fallback_description(len(activities))

    def _get_fallback_description(self, activity_count: int) -> str:
        if activity_count == 0: return "No significant events in the window."
        else: return f"A sequence of {activity_count} plays occurred."

    def _save_data(self, activities: List[Dict], description: str, current_game_time_str: str, activity_count: int) -> str:
        """Save flow data to JSON file"""
        data = {
            'game_id': self.game_id,
            'game_time': current_game_time_str,
            'collected_at_utc': datetime.utcnow().isoformat() + "Z",
            'activity_window_seconds': self.activity_window_seconds,
            'fetch_interval_seconds': self.fetch_interval_seconds,
            'activities': activities,
            'llm_description': description,
            'activity_count': activity_count
        }
        filename = f"{self.game_id}_{current_game_time_str.replace(':', '_')}.json"
        filepath = os.path.join(self.output_dir, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return filepath
        except IOError as e:
            return ""

    @staticmethod
    def _get_time_seconds_from_play_time_in_period(activity: Dict) -> int:
        time_str = activity.get('timeInPeriod', '00:00')
        try:
            m, s = map(int, time_str.split(':'))
            return (m * 60) + s
        except (ValueError, AttributeError):
            return 0

    def _process_current_snapshot(self, pbp_data: Dict, current_game_context: Dict):
        """
        Stateless processing for a single PBP snapshot.
        This function ALWAYS generates and saves a file.
        """
        current_game_time_str = current_game_context['current_game_time_str']
        print(f"\nProcessing for game time approx. {current_game_time_str} (State: {current_game_context['game_state']})")

        activities = self._filter_activities(pbp_data, current_game_time_str)
        enhanced_activities = self._enhance_activities(activities)
        description = self._generate_flow_commentary(enhanced_activities, current_game_time_str)
        
        filepath = self._save_data(enhanced_activities, description, current_game_time_str, len(enhanced_activities))
        print(f"✅ Data saved for {current_game_time_str} to {os.path.basename(filepath)}")

    def start_simulation_collection(self, game_duration_minutes: float = 3.0, real_time_delay_seconds: float = 0.5):
        """Start game-time simulation."""
        print(f"\n🚀 Starting SIMULATION for {game_duration_minutes} game minutes...")
        full_pbp_data = self._get_play_by_play()
        if not full_pbp_data: return

        total_simulated_game_seconds = 0
        end_seconds = game_duration_minutes * 60
        while total_simulated_game_seconds < end_seconds:
            period = (total_simulated_game_seconds // 1200) + 1
            seconds_in_period = total_simulated_game_seconds % 1200
            m, s = divmod(seconds_in_period, 60)
            current_sim_time = f"{period}:{m:02d}:{s:02d}"
            
            self._process_current_snapshot(full_pbp_data, {'current_game_time_str': current_sim_time, 'game_state': 'LIVE'})
            
            total_simulated_game_seconds += self.fetch_interval_seconds
            time.sleep(real_time_delay_seconds)
        print("\n🏁 Simulation finished.")

    def start_true_live_collection(self, polling_interval_seconds: int = 15):
        """Start true live collection."""
        print(f"\n🚀 Starting TRUE LIVE collection for Game ID: {self.game_id}")
        try:
            while True:
                pbp_data = self._get_play_by_play()
                if not pbp_data:
                    time.sleep(polling_interval_seconds)
                    continue
                
                current_game_context = self._get_current_game_context_from_pbp(pbp_data)
                if current_game_context.get('game_state') in ["FINAL", "OFF"]: break
                
                self._process_current_snapshot(pbp_data, current_game_context)
                
                time.sleep(polling_interval_seconds)
        except KeyboardInterrupt:
            print("\n🛑 Collection stopped.")
        finally:
            print("\n🏁 Collection process finished.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NHL Live Data Collector for flow-descriptive commentary.")
    parser.add_argument("mode", choices=['simulate', 'live'])
    parser.add_argument("game_id")
    parser.add_argument("--activity_window_seconds", type=int, default=30)
    parser.add_argument("--game_duration_minutes", type=float, default=3.0)
    parser.add_argument("--fetch_interval_seconds", type=int, default=5)
    parser.add_argument("--real_time_delay_seconds", type=float, default=0.5)
    parser.add_argument("--polling_interval_seconds", type=int, default=15)
    args = parser.parse_args()

    collector = LiveDataCollector(
        game_id=args.game_id,
        activity_window_seconds=args.activity_window_seconds,
        fetch_interval_seconds=args.fetch_interval_seconds
    )
    if args.mode == 'simulate':
        collector.start_simulation_collection(args.game_duration_minutes, args.real_time_delay_seconds)
    elif args.mode == 'live':
        collector.start_true_live_collection(args.polling_interval_seconds)