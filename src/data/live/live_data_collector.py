#!/usr/bin/env python3
"""
Live Data Collector - Flow-descriptive NHL commentary generation
Core flow: fetch → filter → enhance → LLM → save

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

Example (Simulate):
python3 src/data/live/live_data_collector.py simulate 2024020001 \
    --game_duration_minutes 3.0 \
    --fetch_interval_seconds 5 \
    --activity_window_seconds 30 \
    --real_time_delay_seconds 0.5

Example (Live):
python3 src/data/live/live_data_collector.py live 2024030123 \
    --polling_interval_seconds 10 \
    --activity_window_seconds 30
"""
import os
import json
import sys
import time
import requests
import google.generativeai as genai
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import copy # Added for deepcopy
import argparse # For better CLI argument parsing

# Assuming prompts.py and spatial_converter.py are in the same directory or accessible via PYTHONPATH
try:
    from prompts import DESCRIPTION_PROMPT
    from spatial_converter import coords_to_hockey_language, get_game_situation, format_time_remaining
except ImportError:
    print("❌ Error: Ensure 'prompts.py' and 'spatial_converter.py' are in the correct path.")
    # Define a placeholder if not found, so the script can partially run for structure review
    DESCRIPTION_PROMPT = "Describe the following hockey activities that happened at {game_time}: {activity_data}"
    def coords_to_hockey_language(x, y, zone, home_side): return f"Location: {zone} ({x},{y})"
    def get_game_situation(code): return f"Situation: {code}"
    def format_time_remaining(time_str): return time_str


class LiveDataCollector:
    """Generates flow-descriptive commentary from live NHL data"""
    
    def __init__(self, game_id: str, output_dir: str = None, 
                 activity_window_seconds: int = 30,
                 fetch_interval_seconds: int = 5): # fetch_interval for simulation
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
        self.fetch_interval_seconds = fetch_interval_seconds # Used by simulation mode
        
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
        else:
            print("⚠️ Player lookup table is empty after processing static context.")

    def _time_str_to_seconds(self, time_str: str) -> int:
        """Converts MM:SS string to total seconds."""
        try:
            if isinstance(time_str, str) and ':' in time_str:
                m, s = map(int, time_str.split(':'))
                return (m * 60) + s
            return 0 # Default if format is wrong or not a string
        except ValueError:
            return 0 # Default on parsing error

    def _get_current_game_context_from_pbp(self, pbp_data: Dict) -> Dict[str, Any]:
        """
        Extracts current game state, time, and period from PBP data.
        Returns a dictionary: {'game_state', 'current_game_time_str', 'current_period', 'reliable_time'}
        'current_game_time_str' is in "P:MM:SS" elapsed format.
        """
        context = {
            'game_state': pbp_data.get('gameState'),
            'current_game_time_str': "1:00:00", # Default, e.g. start of game
            'current_period': 1,
            'reliable_time': False
        }

        all_plays = pbp_data.get('plays', [])
        api_period = pbp_data.get('period')
        clock_data = pbp_data.get('clock', {})

        if all_plays:
            # Prioritize last play's time as it's explicitly elapsed
            last_play = all_plays[-1]
            play_period_desc = last_play.get('periodDescriptor', {})
            play_period = play_period_desc.get('number')
            time_in_period = last_play.get('timeInPeriod') # This is MM:SS elapsed

            if play_period is not None and time_in_period:
                context['current_period'] = play_period
                context['current_game_time_str'] = f"{play_period}:{time_in_period}"
                context['reliable_time'] = True
                # Ensure game_state reflects reality if plays exist
                if context['game_state'] in ["PRE", "FUT"] and context['reliable_time']:
                    context['game_state'] = "LIVE" # If there are plays, it must be at least live
                return context

        # Fallback to API clock if no plays or last play time is insufficient
        if api_period is not None and clock_data.get('running') is not None: # Check for 'running' to ensure clock is somewhat active/meaningful
            time_remaining_str = clock_data.get('timeRemaining', "20:00")
            
            # Determine period length (simplified: 20 mins for REG/PLAYOFF OT, 5 for REG OT)
            # A more robust solution would check periodDescriptor.periodType from game feed if available
            period_type = pbp_data.get('periodDescriptor', {}).get('periodType', 'REG')
            if period_type == 'OT' and api_period > 3: # Assuming regular season OT is 5 mins
                 # This is a simplification; playoff OT is 20 mins.
                 # For now, we will assume API `timeRemaining` is relative to the actual period length.
                 # So, calculating "elapsed" might be: (KnownPeriodLength - TimeRemaining).
                 # If API reports timeRemaining for a 5-min OT, that's what we use.
                 # The API PBP `timeInPeriod` on plays is generally more reliable for elapsed time.
                pass # Keep default period length of 20 mins for now for simplicity of calculating elapsed.

            # For game time representation, "P:MM:SS elapsed" is useful for filtering.
            # If period is 2 and timeRemaining is 15:00, elapsed is 5:00 -> "2:05:00"
            # If period is 2 and timeRemaining is 20:00 (start of period), elapsed is 0:00 -> "2:00:00"
            # This is the most consistent for `_filter_activities`
            
            # Let's define period total seconds. NHL API v1 does not directly give periodType in play-by-play root.
            # It's usually 20 minutes (1200s). Regular season OT is 5 mins (300s).
            # We'll default to 20 minutes for calculating elapsed time from remaining for simplicity here.
            # The `timeInPeriod` from plays is generally more robust.
            current_period_length_seconds = 20 * 60 
            if context['game_state'] == "LIVE" and period_type == "OT" and api_period == 4: # Basic check for reg season OT
                # Check boxscore or other source for actual period type if needed for precision
                # For now, assume it's a 5 min OT if API indicates such
                # The PBP `clock` object `timeRemaining` should reflect the actual remaining time in that specific period type.
                 if self._time_str_to_seconds(time_remaining_str) <= 300: # If time remaining is <= 5 mins in OT
                    current_period_length_seconds = 5 * 60


            seconds_remaining = self._time_str_to_seconds(time_remaining_str)
            seconds_elapsed_in_period = current_period_length_seconds - seconds_remaining
            if seconds_elapsed_in_period < 0: seconds_elapsed_in_period = 0 # Ensure not negative

            m, s = divmod(seconds_elapsed_in_period, 60)
            
            context['current_period'] = api_period
            context['current_game_time_str'] = f"{api_period}:{m:02d}:{s:02d}"
            context['reliable_time'] = True
            return context
        
        # If still no reliable time (e.g. game truly hasn't started, no clock, no plays)
        # context['game_state'] from pbp_data.get('gameState') is the best guess
        # current_period and current_game_time_str remain default or best guess.
        return context

    def _get_play_by_play(self) -> Optional[Dict[str, Any]]:
        """Fetch all play-by-play data from NHL API"""
        try:
            url = f"{self.base_url}/gamecenter/{self.game_id}/play-by-play"
            response = requests.get(url, timeout=10) # Increased timeout
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error getting play-by-play from {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ Error decoding JSON from play-by-play response: {e}")
            return None

    def _filter_activities(self, pbp_data: Dict[str, Any], current_game_time_str: str) -> List[Dict]:
        """Filter activities by time window (data leakage protection).
           current_game_time_str is "P:MM:SS" (elapsed).
        """
        try:
            period_str, time_in_period_str = current_game_time_str.split(':', 1)
            current_period_num = int(period_str)
            current_minutes, current_seconds_val = map(int, time_in_period_str.split(':'))
            current_total_seconds_in_period_elapsed = (current_minutes * 60) + current_seconds_val
        except ValueError:
            print(f"⚠️ Error parsing current_game_time_str for filtering: {current_game_time_str}. Using defaults.")
            current_period_num = 1
            current_total_seconds_in_period_elapsed = 0
        
        activities = []
        for play in pbp_data.get('plays', []):
            play_period_desc = play.get('periodDescriptor', {})
            play_period = play_period_desc.get('number', 0)
            
            if play_period != current_period_num:
                continue
            
            play_time_in_period_str = play.get('timeInPeriod', '') # This is MM:SS elapsed
            if not play_time_in_period_str:
                continue
            
            try:
                play_min, play_sec = map(int, play_time_in_period_str.split(':'))
                play_total_seconds_elapsed = (play_min * 60) + play_sec
                
                # Data leakage protection: Play must not be "in the future" relative to current_game_time_str.
                # For live mode, this is less of an issue as API sends past plays, but good for consistency.
                if play_total_seconds_elapsed > current_total_seconds_in_period_elapsed:
                    continue
                
                # Check if play falls within the activity window
                time_difference_seconds = current_total_seconds_in_period_elapsed - play_total_seconds_elapsed
                if 0 <= time_difference_seconds <= self.activity_window_seconds:
                    activities.append(play)
            except (ValueError, AttributeError):
                continue
        return activities

    def _get_boxscore(self) -> Optional[Dict[str, Any]]:
        """Fetch boxscore data with detailed player and team stats"""
        try:
            url = f"{self.base_url}/gamecenter/{self.game_id}/boxscore"
            response = requests.get(url, timeout=10) 
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Could not get boxscore data from {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"⚠️ Error decoding JSON from boxscore response: {e}")
            return None

    def _enhance_activities(self, activities: List[Dict], current_game_time_str: str) -> List[Dict]:
        """Add player names, spatial context, and detailed stats to activities"""
        enhanced_activities = []
        boxscore_data = self._get_boxscore() 
        
        for activity in activities:
            enhanced_activity = copy.deepcopy(activity) 
            details = enhanced_activity.get('details', {})
            if not details: 
                details = {}
                enhanced_activity['details'] = details

            player_fields = [
                'attackingPlayerId', 'blockingPlayerId', 'committedByPlayerId', 
                'drawnByPlayerId', 'goalieInNetId', 'hittingPlayerId', 
                'hitteePlayerId', 'losingPlayerId', 'playerId', 
                'assist1PlayerId', 'assist2PlayerId', 'shootingPlayerId',
                'servingPlayerId', 'winningPlayerId', 'retrievingPlayerId',
                'kickerPlayerId' 
            ]
            
            for field in player_fields:
                if field in details and details[field] is not None:
                    player_id_val = str(details[field])
                    if player_id_val in self.player_lookup:
                        player_info = self.player_lookup[player_id_val]
                        name_field = field.replace('Id', 'Name')
                        details[name_field] = f"{player_info['name']} ({player_info['position']}, {player_info['team']})"

            x_coord = details.get('xCoord')
            y_coord = details.get('yCoord') 
            zone_code = details.get('zoneCode')
            
            home_defending_side_from_play = enhanced_activity.get('homeTeamDefendingSide') 
            if not home_defending_side_from_play and self.static_context: 
                 home_defending_side_from_play = self.static_context.get('game_details', {}).get('home_team_defending_side')
            home_defending_side = home_defending_side_from_play or 'right'

            if x_coord is not None and y_coord is not None and zone_code:
                try:
                    spatial_desc = coords_to_hockey_language(x_coord, y_coord, zone_code, home_defending_side)
                    details['spatialDescription'] = spatial_desc
                except Exception as e:
                    details['spatialDescription'] = f"Error generating spatial description: {e}"

            situation_code = enhanced_activity.get('situationCode') 
            if not situation_code: 
                situation_code = details.get('situationCode')

            if situation_code:
                try:
                    game_situation = get_game_situation(situation_code)
                    if game_situation:
                        enhanced_activity['gameSituation'] = game_situation
                except Exception as e:
                    enhanced_activity['gameSituation'] = f"Error getting game situation: {e}"

            time_remaining = enhanced_activity.get('timeRemaining') 
            if time_remaining:
                try:
                    formatted_time = format_time_remaining(time_remaining)
                    if formatted_time:
                        enhanced_activity['timeRemainingFormatted'] = formatted_time
                except Exception as e:
                     enhanced_activity['timeRemainingFormatted'] = f"Error formatting time: {e}"

            if boxscore_data:
                enhanced_activity['gameStats'] = self._extract_game_stats(boxscore_data, enhanced_activity, current_game_time_str)
            
            enhanced_activities.append(enhanced_activity)
        
        enhanced_activities.sort(key=self._get_time_seconds_from_play_time_in_period)
        return enhanced_activities

    def _should_include_cumulative_stats(self, current_game_time_str: str) -> bool:
        """Determine if cumulative stats should be included based on game time"""
        try:
            period_str, time_in_period_str = current_game_time_str.split(':', 1)
            current_period_num = int(period_str)
            current_minutes, current_seconds_val = map(int, time_in_period_str.split(':'))
            current_total_seconds_in_period = (current_minutes * 60) + current_seconds_val
            
            if current_total_seconds_in_period <= 60: return False
            if current_period_num == 1 and current_total_seconds_in_period <= 300: return False
            return True
        except ValueError:
            print(f"⚠️ Error parsing game time for stat inclusion: {current_game_time_str}. Defaulting to include stats.")
            return True

    def _extract_game_stats(self, boxscore_data: Dict, activity: Dict, current_game_time_str: str) -> Dict:
        """Extract relevant game stats for the current activity (with temporal filtering for cumulative stats)"""
        stats = {'teamStats': {}, 'playerStats': {}}
        try:
            include_cumulative = self._should_include_cumulative_stats(current_game_time_str)
            away_team_box = boxscore_data.get('awayTeam', {})
            home_team_box = boxscore_data.get('homeTeam', {})

            stats['teamStats'] = {
                'away': {'teamName': away_team_box.get('abbrev', 'AWAY'),
                         'score': away_team_box.get('score', 0) if include_cumulative else None,
                         'shotsOnGoal': away_team_box.get('sog', 0) if include_cumulative else None},
                'home': {'teamName': home_team_box.get('abbrev', 'HOME'),
                         'score': home_team_box.get('score', 0) if include_cumulative else None,
                         'shotsOnGoal': home_team_box.get('sog', 0) if include_cumulative else None}
            }
            stats['teamStats']['away'] = {k: v for k, v in stats['teamStats']['away'].items() if v is not None}
            stats['teamStats']['home'] = {k: v for k, v in stats['teamStats']['home'].items() if v is not None}

            involved_player_ids = set()
            details = activity.get('details', {})
            player_id_fields = [
                'attackingPlayerId', 'blockingPlayerId', 'committedByPlayerId', 'drawnByPlayerId', 
                'goalieInNetId', 'hittingPlayerId', 'hitteePlayerId', 'losingPlayerId', 'playerId', 
                'assist1PlayerId', 'assist2PlayerId', 'shootingPlayerId', 'servingPlayerId', 
                'winningPlayerId', 'retrievingPlayerId'
            ]
            for field in player_id_fields:
                if field in details and details[field] is not None:
                    involved_player_ids.add(details[field])

            player_stats_from_boxscore = boxscore_data.get('playerByGameStats', {})
            for player_id_int in involved_player_ids:
                player_stat = self._find_player_stats(player_stats_from_boxscore, player_id_int, include_cumulative)
                if player_stat:
                    stats['playerStats'][str(player_id_int)] = player_stat
        except Exception as e:
            print(f"⚠️ Error extracting game stats: {e}")
        return stats

    def _validate_player_data(self, player_id_str: str, expected_boxscore_team_key: str) -> bool:
        if not self.player_lookup or player_id_str not in self.player_lookup: return True
        static_player_info = self.player_lookup[player_id_str]
        static_team_assignment = static_player_info.get('team')
        if static_team_assignment and expected_boxscore_team_key and static_team_assignment != expected_boxscore_team_key:
            pass # Allow, boxscore is likely more up-to-date
        return True

    def _find_player_stats(self, player_by_game_stats: Dict, player_id_int: int, include_cumulative: bool) -> Optional[Dict]:
        try:
            player_id_str = str(player_id_int)
            for team_key_in_boxscore, team_name_code in [('awayTeam', 'away'), ('homeTeam', 'home')]:
                team_stats_section = player_by_game_stats.get(team_key_in_boxscore, {})
                for position_group_key in ['forwards', 'defensemen', 'goalies']:
                    for player_data in team_stats_section.get(position_group_key, []):
                        if player_data.get('playerId') == player_id_int:
                            if not self._validate_player_data(player_id_str, team_name_code): continue
                            base_stats = {
                                'name': player_data.get('name', {}).get('default', 'Unknown Player'),
                                'position': player_data.get('positionCode', 'N/A'),
                                'team': team_name_code,
                            }
                            if include_cumulative:
                                if position_group_key == 'goalies':
                                    cumulative_stats = {
                                        'saves': player_data.get('saveShotsAgainst', '0/0').split('/')[0],
                                        'shotsAgainst': player_data.get('saveShotsAgainst', '0/0').split('/')[-1],
                                        'goalsAgainst': player_data.get('goalsAgainst', 0),
                                        'savePct': player_data.get('savePctg'),
                                        'timeOnIce': player_data.get('toi', '0:00'),
                                        'decision': player_data.get('decision', ''),
                                        'starter': player_data.get('starter', False),
                                    }
                                else: # Forwards and Defensemen
                                    cumulative_stats = {
                                        'goals': player_data.get('goals', 0), 'assists': player_data.get('assists', 0),
                                        'points': player_data.get('points', 0), 'plusMinus': player_data.get('plusMinus', 0),
                                        'pim': player_data.get('pim', 0), 'hits': player_data.get('hits', 0),
                                        'shotsOnGoal': player_data.get('sog', 0), 'blockedShots': player_data.get('blockedShots', 0),
                                        'giveaways': player_data.get('giveaways', 0), 'takeaways': player_data.get('takeaways', 0),
                                        'faceoffWins': player_data.get('faceoffWinningPctg', 0.0), 
                                        'timeOnIce': player_data.get('toi', '0:00'),
                                        'powerPlayGoals': player_data.get('powerPlayGoals', 0),
                                        'shifts': player_data.get('shifts', 0)
                                    }
                                return {**base_stats, **cumulative_stats}
                            else:
                                if position_group_key == 'goalies': base_stats['starter'] = player_data.get('starter', False)
                                return base_stats
            if player_id_str in self.player_lookup and not include_cumulative:
                return {
                    'name': self.player_lookup[player_id_str].get('name', 'Unknown Player'),
                    'position': self.player_lookup[player_id_str].get('position', 'N/A'),
                    'team': self.player_lookup[player_id_str].get('team', 'N/A')
                }
        except Exception as e:
            print(f"⚠️ Error finding player stats for ID {player_id_int}: {e}")
        return None

    def _generate_flow_commentary(self, activities: List[Dict], current_game_time_str: str) -> str:
        """Generate flow-descriptive commentary (always generates, with fallbacks)"""
        if not self.model:
            return self._get_fallback_description(len(activities))
        try:
            prompt_activities = []
            for act in activities:
                act_summary = {
                    "type": act.get("typeDescKey", act.get("type", "unknown_event")),
                    "timeInPeriod": act.get("timeInPeriod"),
                    "details": {
                        "description": act.get("description"),
                        "spatialDescription": act.get("details", {}).get("spatialDescription"),
                        "eventOwnerTeamId": act.get("details", {}).get("eventOwnerTeamId")
                    },
                    "gameSituation": act.get("gameSituation")
                }
                details = act.get("details", {})
                involved_players = {}
                for k, v in details.items():
                    if "Name" in k and isinstance(v, str): involved_players[k] = v
                if involved_players: act_summary["details"]["involvedPlayers"] = involved_players
                prompt_activities.append(act_summary)

            activities_json = json.dumps(prompt_activities, ensure_ascii=False, indent=None)
            prompt_str = DESCRIPTION_PROMPT.replace('{activity_data}', activities_json).replace('{game_time}', current_game_time_str)
            response = self.model.generate_content(prompt_str)
            
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                print(f"⚠️ LLM generation blocked. Reason: {response.prompt_feedback.block_reason}")
                return self._get_fallback_description(len(activities))
            
            generated_text = ""
            if hasattr(response, 'text') and response.text:
                generated_text = response.text
            elif response.candidates:
                first_candidate = response.candidates[0]
                if first_candidate.finish_reason != 'STOP':
                     print(f"⚠️ LLM generation did not finish normally. Reason: {first_candidate.finish_reason}")
                if not first_candidate.content or not first_candidate.content.parts:
                    print(f"⚠️ LLM response has no content parts.")
                    return self._get_fallback_description(len(activities))
                generated_text = "".join(part.text for part in first_candidate.content.parts if hasattr(part, 'text'))
            else:
                 print(f"⚠️ LLM response structure unexpected or empty.")
                 return self._get_fallback_description(len(activities))

            return generated_text.strip()
        except Exception as e:
            print(f"⚠️ Description generation error with LLM: {e}")
            return self._get_fallback_description(len(activities))

    def _get_fallback_description(self, activity_count: int) -> str:
        if activity_count == 0: return "Quiet moment in the game; teams are likely regrouping or play is stopped."
        elif activity_count <= 2: return "A brief sequence of events unfolds, possibly a quick transition or a minor stoppage."
        else: return "A series of plays developing, indicating a more active phase of the game."

    def _save_data(self, activities: List[Dict], description: str, current_game_time_str: str, activity_count: int) -> str:
        """Save flow data to JSON file"""
        data = {
            'game_id': self.game_id,
            'game_time': current_game_time_str, # This is P:MM:SS elapsed
            'collected_at_utc': datetime.utcnow().isoformat() + "Z",
            'activity_window_seconds': self.activity_window_seconds,
            'fetch_interval_seconds': self.fetch_interval_seconds, # Relevant for simulation
            'activities': activities,
            'llm_description': description,
            'activity_count': activity_count
        }
        filename_time = current_game_time_str.replace(':', '_')
        filename = f"{self.game_id}_{filename_time}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return filepath
        except IOError as e:
            print(f"❌ Error saving data to {filepath}: {e}")
            timestamp_fallback = datetime.now().strftime("%Y%m%d%H%M%S%f")
            fallback_filename = f"game_{self.game_id}_flow_error_{timestamp_fallback}.json"
            filepath = os.path.join(self.output_dir, fallback_filename)
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"ℹ️ Data saved to fallback file: {filepath}")
                return filepath
            except Exception as e_fb:
                 print(f"❌ CRITICAL: Could not save data even to fallback file: {e_fb}")
                 return ""

    @staticmethod
    def _get_time_seconds_from_play_time_in_period(activity: Dict) -> int:
        """Helper to get total seconds from activity timeInPeriod (elapsed) for sorting"""
        time_str = activity.get('timeInPeriod', '00:00') # This is MM:SS elapsed
        try:
            minutes, seconds = map(int, time_str.split(':'))
            return (minutes * 60) + seconds
        except (ValueError, AttributeError):
            return 0

    def _process_current_snapshot(self, pbp_data: Dict, current_game_context: Dict) -> Optional[str]:
        """
        Core processing logic for a fetched PBP snapshot (used by true live mode).
        Returns filepath if data was saved, else None.
        """
        current_game_time_str = current_game_context['current_game_time_str']
        print(f"\nProcessing for game time approx. {current_game_time_str} (State: {current_game_context['game_state']})")

        activities = self._filter_activities(pbp_data, current_game_time_str)

        if not activities:
            print("No recent activities in window. Sleeping.")
            return None
        
        # Check for new activity to avoid redundant LLM calls (implementation specific to how you track)
        # For this version, we'll process if activities are found.
        # A more advanced version would use a hash of play IDs in the window.

        enhanced_activities = self._enhance_activities(activities, current_game_time_str)
        description = self._generate_flow_commentary(enhanced_activities, current_game_time_str)
        
        # For live mode, fetch_interval_seconds isn't directly used in the same way, 
        # but we keep it in saved data for consistency if needed.
        filepath = self._save_data(enhanced_activities, description, current_game_time_str, len(enhanced_activities))
        print(f"✅ Data and commentary saved for approx. {current_game_time_str} to {os.path.basename(filepath)}")
        return filepath

    # --- Simulation Mode ---
    def start_simulation_collection(self, game_duration_minutes: float = 3.0, real_time_delay_seconds: float = 0.5):
        """
        Start game-time simulation.
        :param game_duration_minutes: The total duration of in-game time to simulate.
        :param real_time_delay_seconds: The real-time delay between fetching data for each game time step.
        """
        print(f"\n🚀 Starting SIMULATION for {game_duration_minutes} game minutes...")
        print(f"   Game time advances by {self.fetch_interval_seconds}s per step.")
        print(f"   Real-time delay per step: {real_time_delay_seconds}s.")

        # Fetch entire PBP data once for simulation
        full_pbp_data = self._get_play_by_play()
        if not full_pbp_data:
            print(f"❌ Could not get play-by-play data for game {self.game_id}. Simulation cannot start.")
            return

        current_period = 1
        current_period_elapsed_seconds = 0 
        total_simulated_game_seconds = 0
        simulation_end_game_seconds = game_duration_minutes * 60
        max_periods = 3 
        seconds_per_period = 20 * 60

        while total_simulated_game_seconds < simulation_end_game_seconds:
            minutes_in_period = current_period_elapsed_seconds // 60
            seconds_in_period = current_period_elapsed_seconds % 60
            # This is the "current point in time" for the simulation slice
            current_simulated_game_time_str = f"{current_period}:{minutes_in_period:02d}:{seconds_in_period:02d}"
            
            progress_percentage = (total_simulated_game_seconds / simulation_end_game_seconds) * 100 if simulation_end_game_seconds > 0 else 0
            print(f"\nProcessing simulated game time: {current_simulated_game_time_str} "
                  f"(Total: {total_simulated_game_seconds / 60:.2f} / {game_duration_minutes:.2f} mins) "
                  f"[{progress_percentage:.1f}%]")

            try:
                # Filter activities from the full PBP data based on the current simulated time
                activities_in_window = self._filter_activities(full_pbp_data, current_simulated_game_time_str)
                
                if not activities_in_window:
                    print(f"No activities in window for {current_simulated_game_time_str}.")
                else:
                    enhanced_activities = self._enhance_activities(activities_in_window, current_simulated_game_time_str)
                    description = self._generate_flow_commentary(enhanced_activities, current_simulated_game_time_str)
                    filepath = self._save_data(enhanced_activities, description, current_simulated_game_time_str, len(enhanced_activities))
                    print(f"✅ Data saved for {current_simulated_game_time_str} to {os.path.basename(filepath)}")

            except ValueError as ve: 
                print(f"⚠️ Warning at {current_simulated_game_time_str}: {ve}. Continuing simulation.")
            except Exception as e:
                print(f"❌ Error processing {current_simulated_game_time_str}: {e}")
            
            total_simulated_game_seconds += self.fetch_interval_seconds
            current_period_elapsed_seconds += self.fetch_interval_seconds

            if current_period_elapsed_seconds >= seconds_per_period:
                current_period += 1
                current_period_elapsed_seconds = 0 
                if current_period > max_periods and total_simulated_game_seconds < simulation_end_game_seconds : # Only break if not OT simulation
                    print(f"🏁 Simulation reached end of {max_periods}rd period.")
                    # Could add logic here to simulate OT if desired, by extending max_periods or changing logic.
                    # For now, simulation stops after regulation if game_duration_minutes extends beyond it.
                    if game_duration_minutes * 60 > max_periods * seconds_per_period:
                        print("   (Simulating beyond standard regulation based on game_duration_minutes)")
                    else:
                        break
            
            if total_simulated_game_seconds >= simulation_end_game_seconds:
                print(f"🏁 Simulated game duration of {game_duration_minutes} minutes reached.")
                break
            
            time.sleep(real_time_delay_seconds)
        
        print("\n🏁 Simulation finished.")

    # --- True Live Mode ---
    def start_true_live_collection(self, polling_interval_seconds: int = 15):
        print(f"\n🚀 Starting TRUE LIVE collection for Game ID: {self.game_id}")
        print(f"   Polling API every {polling_interval_seconds} seconds.")
        
        last_processed_play_ids_hash = None # To track changes in the activity window

        try:
            while True:
                pbp_data = self._get_play_by_play()
                if not pbp_data:
                    print(f"⚠️ No PBP data fetched. Retrying in {polling_interval_seconds}s...")
                    time.sleep(polling_interval_seconds)
                    continue

                current_game_context = self._get_current_game_context_from_pbp(pbp_data)
                game_state = current_game_context['game_state']
                current_game_time_str = current_game_context['current_game_time_str'] # P:MM:SS elapsed

                if not current_game_context['reliable_time'] and game_state not in ["LIVE", "CRIT"]:
                     print(f"⏳ Game state: {game_state}. Waiting for reliable time/active game... (Next check in {polling_interval_seconds}s)")
                     if game_state in ["FINAL", "OFF"]: break # End if game is over
                     time.sleep(polling_interval_seconds)
                     continue
                
                print(f"\nChecking for updates at game time ~{current_game_time_str} (State: {game_state})")

                activities_in_window = self._filter_activities(pbp_data, current_game_time_str)

                if not activities_in_window:
                    print("No recent activities in window currently.")
                else:
                    # Check if the content of the activity window has actually changed
                    # Use eventId (usually 'id' in play object for this API)
                    current_play_event_ids = sorted([
                        play.get('id', play.get('eventId', idx)) for idx, play in enumerate(activities_in_window)
                    ])
                    current_window_hash = hash(tuple(current_play_event_ids))

                    if current_window_hash == last_processed_play_ids_hash:
                        print("Activity window content unchanged since last processing. Skipping LLM/Save.")
                    else:
                        print(f"New activity detected in window. Processing {len(activities_in_window)} plays.")
                        enhanced_activities = self._enhance_activities(activities_in_window, current_game_time_str)
                        description = self._generate_flow_commentary(enhanced_activities, current_game_time_str)
                        filepath = self._save_data(enhanced_activities, description, current_game_time_str, len(enhanced_activities))
                        if filepath:
                            print(f"✅ Data and commentary saved for approx. {current_game_time_str} to {os.path.basename(filepath)}")
                        last_processed_play_ids_hash = current_window_hash
                
                if game_state in ["FINAL", "OFF"]:
                    print(f"🏁 Game {self.game_id} reported as {game_state}. Shutting down live collector.")
                    break
                
                time.sleep(polling_interval_seconds)

        except KeyboardInterrupt:
            print("\n🛑 True live collection stopped by user.")
        except Exception as e:
            print(f"❌ An unexpected error occurred in the true live collection loop: {e}")
        finally:
            print("\n🏁 True live collection process finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NHL Live Data Collector for flow-descriptive commentary.")
    parser.add_argument("mode", choices=['simulate', 'live'], help="Mode of operation: 'simulate' a past game or 'live' track an ongoing game.")
    parser.add_argument("game_id", help="The NHL Game ID (e.g., 2023020001).")
    
    # Shared arguments
    parser.add_argument("--activity_window_seconds", type=int, default=30, help="Sliding window (game seconds) for past activities (Default: 30).")
    
    # Simulate mode arguments
    parser.add_argument("--game_duration_minutes", type=float, default=3.0, help="SIMULATE: Total in-game minutes to simulate (Default: 3.0).")
    parser.add_argument("--fetch_interval_seconds", type=int, default=5, help="SIMULATE: Game time (seconds) to advance per fetch (Default: 5).")
    parser.add_argument("--real_time_delay_seconds", type=float, default=0.5, help="SIMULATE: Actual script delay (seconds) between fetches (Default: 0.5).")

    # Live mode arguments
    parser.add_argument("--polling_interval_seconds", type=int, default=15, help="LIVE: Real-time seconds between API polls (Default: 15).")
    
    args = parser.parse_args()

    # Basic validation for arguments
    if args.activity_window_seconds <= 0:
        print("⚠️ ACTIVITY_WINDOW_SECONDS must be positive. Using default 30 seconds.")
        args.activity_window_seconds = 30
    
    collector = LiveDataCollector(
        game_id=args.game_id,
        activity_window_seconds=args.activity_window_seconds,
        fetch_interval_seconds=args.fetch_interval_seconds if args.mode == 'simulate' else 5 # Pass simulation-specific fetch interval
    )

    if args.mode == 'simulate':
        if args.game_duration_minutes <= 0:
            print("⚠️ GAME_DURATION_MINUTES must be positive. Using default 3.0 minutes.")
            args.game_duration_minutes = 3.0
        if args.fetch_interval_seconds <= 0: # This is now also in constructor for collector
            print("⚠️ FETCH_INTERVAL_SECONDS must be positive. Using default 5 seconds.")
            args.fetch_interval_seconds = 5
        if args.real_time_delay_seconds < 0:
            print("⚠️ REAL_TIME_DELAY_SECONDS cannot be negative. Using default 0.5 seconds.")
            args.real_time_delay_seconds = 0.5
        
        collector.start_simulation_collection(
            game_duration_minutes=args.game_duration_minutes,
            real_time_delay_seconds=args.real_time_delay_seconds
        )
    elif args.mode == 'live':
        if args.polling_interval_seconds <= 0:
            print("⚠️ POLLING_INTERVAL_SECONDS must be positive. Using default 15 seconds.")
            args.polling_interval_seconds = 15
            
        collector.start_true_live_collection(
            polling_interval_seconds=args.polling_interval_seconds
        )