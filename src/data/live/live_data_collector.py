#!/usr/bin/env python3
"""
Live Data Collector - Flow-descriptive NHL commentary generation
Core flow: fetch → filter → enhance → LLM → save

CLI Usage:
----------
python3 src/data/live/live_data_collector.py \
    <GAME_ID> \
    <GAME_DURATION_MINUTES> \
    <FETCH_INTERVAL_SECONDS> \
    <ACTIVITY_WINDOW_SECONDS> \
    <REAL_TIME_DELAY_SECONDS>

Arguments:
  GAME_ID                 : The NHL Game ID (e.g., 2024020001)
  GAME_DURATION_MINUTES   : Total in-game minutes to simulate (e.g., 3.0)
  FETCH_INTERVAL_SECONDS  : Game time (seconds) to advance per fetch (e.g., 5)
  ACTIVITY_WINDOW_SECONDS : Sliding window (seconds) for past activities (e.g., 30)
  REAL_TIME_DELAY_SECONDS : Actual script delay (seconds) between fetches (e.g., 0.5)

Example:
---------
python3 src/data/live/live_data_collector.py \
    2024020001 \    # game_id: The NHL Game ID you want to process
    3.0 \           # game_duration_minutes: Simulate 3 minutes of game time
    5 \             # fetch_interval_seconds: Advance 5 seconds of game time per fetch
    30 \            # activity_window_seconds: Look back 30 seconds for activity window
    0.5             # real_time_delay_seconds: Wait 0.5 seconds in real time between fetches

Replace the values as needed for your use case.
"""
import os
import json
import sys
import time
import requests
import google.generativeai as genai
from datetime import datetime
from typing import Dict, List, Optional, Any
import copy # Added for deepcopy

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
                 fetch_interval_seconds: int = 5, 
                 activity_window_seconds: int = 30):
        self.game_id = game_id
        
        if output_dir is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Adjust project_root if your script is in a different location relative to the project
            project_root_candidate = os.path.join(script_dir, "..") # Assuming script is in a 'scripts' or 'src' subdir
            if not os.path.exists(os.path.join(project_root_candidate, "data")):
                 project_root_candidate = os.path.join(script_dir, "..", "..", "..") # Original path
            
            project_root = os.path.abspath(project_root_candidate)
            self.output_dir = os.path.join(project_root, "data", "live", self.game_id)
        else:
            self.output_dir = output_dir
        
        self.base_url = "https://api-web.nhle.com/v1"
        self.static_context = None
        self.player_lookup = {}
        os.makedirs(self.output_dir, exist_ok=True)

        self.fetch_interval_seconds = fetch_interval_seconds
        self.activity_window_seconds = activity_window_seconds
        
        self._setup_llm()
        self._load_static_context()
        
        print(f"🏒 Live Data Collector Ready for Game {game_id}")
        print(f"   Output directory: {self.output_dir}")
        print(f"   Fetch interval (game time): {self.fetch_interval_seconds}s")
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
            # Consider making the model name configurable if you might switch models
            self.model = genai.GenerativeModel("gemini-1.5-flash") # Updated to a common flash model
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
                if player_id: # Ensure player_id is not empty
                    self.player_lookup[player_id] = {
                        'name': player.get('name', 'Unknown Player'),
                        'position': player.get('position', 'N/A'),
                        'team': team_key # 'home' or 'away'
                    }
        if self.player_lookup:
            print(f"ℹ️ Built player lookup table with {len(self.player_lookup)} players from static context.")
        else:
            print("⚠️ Player lookup table is empty after processing static context.")


    def collect_live_data(self, current_game_time_str: str) -> str:
        """Main flow: fetch → filter → enhance → LLM → save"""
        # 1. Fetch all play-by-play data
        pbp_data = self._get_play_by_play()
        if not pbp_data:
            # Raise specific error if critical, or handle gracefully
            raise ValueError(f"Could not get play-by-play data for game {self.game_id} at {current_game_time_str}")
        
        # 2. Filter by time window (data leakage protection)
        activities = self._filter_activities(pbp_data, current_game_time_str)
        
        # 3. Enhance with player names and spatial context
        enhanced_activities = self._enhance_activities(activities, current_game_time_str)
        
        # 4. Generate description (always generates, with fallbacks)
        description = self._generate_flow_commentary(enhanced_activities, current_game_time_str)
        
        # 5. Save data
        filepath = self._save_data(enhanced_activities, description, current_game_time_str, len(enhanced_activities))
        return filepath

    def start_live_collection(self, game_duration_minutes: float = 3.0, real_time_delay_seconds: float = 0.5):
        """
        Start live game-time simulation.
        :param game_duration_minutes: The total duration of in-game time to simulate.
        :param real_time_delay_seconds: The real-time delay between fetching data for each game time step.
        """
        current_period = 1
        current_period_elapsed_seconds = 0 # Seconds elapsed in the current period
        total_simulated_game_seconds = 0
        simulation_end_game_seconds = game_duration_minutes * 60

        max_periods = 3 # Standard NHL game periods
        seconds_per_period = 20 * 60 # 20 minutes

        print(f"\n🚀 Starting live collection for {game_duration_minutes} game minutes...")
        print(f"   Simulating game time, advancing by {self.fetch_interval_seconds}s per step.")
        print(f"   Real-time delay per step: {real_time_delay_seconds}s.")

        while total_simulated_game_seconds < simulation_end_game_seconds:
            minutes_in_period = current_period_elapsed_seconds // 60
            seconds_in_period = current_period_elapsed_seconds % 60
            current_game_time_str = f"{current_period}:{minutes_in_period:02d}:{seconds_in_period:02d}"
            
            progress_percentage = (total_simulated_game_seconds / simulation_end_game_seconds) * 100 if simulation_end_game_seconds > 0 else 0
            print(f"\nProcessing game time: {current_game_time_str} "
                  f"(Total simulated: {total_simulated_game_seconds / 60:.2f} / {game_duration_minutes:.2f} mins) "
                  f"[{progress_percentage:.1f}%]")

            try:
                filepath = self.collect_live_data(current_game_time_str)
                print(f"✅ Data saved for {current_game_time_str} to {os.path.basename(filepath)}")
            except ValueError as ve: 
                print(f"⚠️ Warning at {current_game_time_str}: {ve}. Continuing simulation.")
            except Exception as e:
                print(f"❌ Error processing {current_game_time_str}: {e}")
                # Decide if you want to stop or continue on other errors
                # For now, we'll continue
            
            # Advance game time
            total_simulated_game_seconds += self.fetch_interval_seconds
            current_period_elapsed_seconds += self.fetch_interval_seconds

            if current_period_elapsed_seconds >= seconds_per_period:
                current_period += 1
                current_period_elapsed_seconds = 0 # Reset for new period
                if current_period > max_periods:
                    print("🏁 Simulation reached end of 3rd period.")
                    break 
            
            if total_simulated_game_seconds >= simulation_end_game_seconds:
                print(f"🏁 Simulated game duration of {game_duration_minutes} minutes reached.")
                break
            
            time.sleep(real_time_delay_seconds)
        
        print("\n🏁 Live collection simulation finished.")

    def _get_play_by_play(self) -> Optional[Dict[str, Any]]:
        """Fetch all play-by-play data from NHL API"""
        try:
            url = f"{self.base_url}/gamecenter/{self.game_id}/play-by-play"
            response = requests.get(url, timeout=5) # Increased timeout slightly
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error getting play-by-play from {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ Error decoding JSON from play-by-play response: {e}")
            return None

    def _filter_activities(self, pbp_data: Dict[str, Any], current_game_time_str: str) -> List[Dict]:
        """Filter activities by time window (data leakage protection)"""
        period_str, time_in_period_str = current_game_time_str.split(':', 1)
        current_period_num = int(period_str)
        current_minutes, current_seconds_val = map(int, time_in_period_str.split(':'))
        current_total_seconds_in_period = (current_minutes * 60) + current_seconds_val
        
        activities = []
        for play in pbp_data.get('plays', []):
            # Ensure play is in the current period
            play_period = play.get('periodDescriptor', {}).get('number', 0)
            if play_period != current_period_num:
                continue
            
            play_time_in_period = play.get('timeInPeriod', '')
            if not play_time_in_period:
                continue
            
            try:
                play_min, play_sec = map(int, play_time_in_period.split(':'))
                play_total_seconds = (play_min * 60) + play_sec
                
                # Data leakage protection: Play must not be in the future
                if play_total_seconds > current_total_seconds_in_period:
                    continue
                
                # Check if play falls within the activity window
                time_difference_seconds = current_total_seconds_in_period - play_total_seconds
                if 0 <= time_difference_seconds <= self.activity_window_seconds:
                    activities.append(play)
            except (ValueError, AttributeError) as e:
                # Log problematic play for debugging if necessary
                # print(f"⚠️Skipping play due to parsing error: {play.get('eventDescription') if 'eventDescription' in play else 'Unknown event'} - {e}")
                continue
        return activities

    def _get_boxscore(self) -> Optional[Dict[str, Any]]:
        """Fetch boxscore data with detailed player and team stats"""
        try:
            url = f"{self.base_url}/gamecenter/{self.game_id}/boxscore"
            response = requests.get(url, timeout=5) # Increased timeout
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
        boxscore_data = self._get_boxscore() # Fetch once per call to reduce API load
        
        for activity in activities:
            enhanced_activity = copy.deepcopy(activity) # Use copy.deepcopy
            details = enhanced_activity.get('details', {})
            if not details: # If details is None or empty, create it
                details = {}
                enhanced_activity['details'] = details

            player_fields = [
                'attackingPlayerId', 'blockingPlayerId', 'committedByPlayerId', 
                'drawnByPlayerId', 'goalieInNetId', 'hittingPlayerId', 
                'hitteePlayerId', 'losingPlayerId', 'playerId', 
                'assist1PlayerId', 'assist2PlayerId', 'shootingPlayerId',
                'servingPlayerId', 'winningPlayerId', 'retrievingPlayerId',
                'kickerPlayerId' # Soccer term but sometimes appears in test data
            ]
            
            for field in player_fields:
                if field in details and details[field] is not None:
                    player_id_val = str(details[field])
                    if player_id_val in self.player_lookup:
                        player_info = self.player_lookup[player_id_val]
                        name_field = field.replace('Id', 'Name')
                        details[name_field] = f"{player_info['name']} ({player_info['position']}, {player_info['team']})"
                    # else:
                        # If not in static lookup, name might come from boxscore or remain ID

            x_coord = details.get('xCoord')
            y_coord = details.get('yCoord') 
            zone_code = details.get('zoneCode')
            # Determine homeTeamDefendingSide, default to 'right' if not available
            # This might come from game static context or pbp_data root if available
            home_defending_side_from_play = enhanced_activity.get('homeTeamDefendingSide') # Check play level
            if not home_defending_side_from_play and self.static_context: # Check static context
                 home_defending_side_from_play = self.static_context.get('game_details', {}).get('home_team_defending_side')

            home_defending_side = home_defending_side_from_play or 'right'

            if x_coord is not None and y_coord is not None and zone_code:
                try:
                    spatial_desc = coords_to_hockey_language(x_coord, y_coord, zone_code, home_defending_side)
                    details['spatialDescription'] = spatial_desc
                except Exception as e:
                    details['spatialDescription'] = f"Error generating spatial description: {e}"


            situation_code = enhanced_activity.get('situationCode') # From play root
            if not situation_code: # Fallback to details if needed
                situation_code = details.get('situationCode')

            if situation_code:
                try:
                    game_situation = get_game_situation(situation_code)
                    if game_situation:
                        enhanced_activity['gameSituation'] = game_situation
                except Exception as e:
                    enhanced_activity['gameSituation'] = f"Error getting game situation: {e}"


            time_remaining = enhanced_activity.get('timeRemaining') # From play root
            if not time_remaining and 'periodDescriptor' in enhanced_activity: # Calculate if possible
                # This requires knowing period length; NHL API often provides timeRemaining directly
                pass # Keep it simple for now, rely on API's timeRemaining

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
        
        enhanced_activities.sort(key=self._get_time_seconds)
        return enhanced_activities

    def _should_include_cumulative_stats(self, current_game_time_str: str) -> bool:
        """Determine if cumulative stats should be included based on game time"""
        try:
            period_str, time_in_period_str = current_game_time_str.split(':', 1)
            current_period_num = int(period_str)
            current_minutes, current_seconds_val = map(int, time_in_period_str.split(':'))
            
            # Total seconds from the start of the current period
            current_total_seconds_in_period = (current_minutes * 60) + current_seconds_val
            
            # Don't include stats in the first 60 seconds of any period
            if current_total_seconds_in_period <= 60:
                return False
            
            # Don't include stats in the first 5 minutes (300 seconds) of the first period
            if current_period_num == 1 and current_total_seconds_in_period <= 300:
                return False
            
            return True
        except ValueError:
            # If time format is unexpected, default to including stats to be safe or log error
            print(f"⚠️ Error parsing game time for stat inclusion: {current_game_time_str}. Defaulting to include stats.")
            return True


    def _extract_game_stats(self, boxscore_data: Dict, activity: Dict, current_game_time_str: str) -> Dict:
        """Extract relevant game stats for the current activity (with temporal filtering for cumulative stats)"""
        stats = {
            'teamStats': {},
            'playerStats': {} # Store stats by player ID string
        }
        try:
            include_cumulative = self._should_include_cumulative_stats(current_game_time_str)
            
            away_team_box = boxscore_data.get('awayTeam', {})
            home_team_box = boxscore_data.get('homeTeam', {})

            stats['teamStats'] = {
                'away': {
                    'teamName': away_team_box.get('abbrev', 'AWAY'),
                    'score': away_team_box.get('score', 0) if include_cumulative else None,
                    'shotsOnGoal': away_team_box.get('sog', 0) if include_cumulative else None
                },
                'home': {
                    'teamName': home_team_box.get('abbrev', 'HOME'),
                    'score': home_team_box.get('score', 0) if include_cumulative else None,
                    'shotsOnGoal': home_team_box.get('sog', 0) if include_cumulative else None
                }
            }
            # Filter out None values for cleaner JSON
            stats['teamStats']['away'] = {k: v for k, v in stats['teamStats']['away'].items() if v is not None}
            stats['teamStats']['home'] = {k: v for k, v in stats['teamStats']['home'].items() if v is not None}


            # Extract stats for players involved in the activity
            involved_player_ids = set()
            details = activity.get('details', {})
            player_id_fields = [
                'attackingPlayerId', 'blockingPlayerId', 'committedByPlayerId', 
                'drawnByPlayerId', 'goalieInNetId', 'hittingPlayerId', 
                'hitteePlayerId', 'losingPlayerId', 'playerId', 
                'assist1PlayerId', 'assist2PlayerId', 'shootingPlayerId',
                'servingPlayerId', 'winningPlayerId', 'retrievingPlayerId'
            ]
            for field in player_id_fields:
                if field in details and details[field] is not None:
                    involved_player_ids.add(details[field]) # API playerIDs are integers

            player_stats_from_boxscore = boxscore_data.get('playerByGameStats', {})
            for player_id_int in involved_player_ids:
                player_stat = self._find_player_stats(player_stats_from_boxscore, player_id_int, include_cumulative)
                if player_stat:
                    stats['playerStats'][str(player_id_int)] = player_stat # Use string ID as key

        except Exception as e:
            print(f"⚠️ Error extracting game stats: {e}")
        return stats

    def _validate_player_data(self, player_id_str: str, expected_boxscore_team_key: str) -> bool:
        """Validate player team assignment against static context if available.
           expected_boxscore_team_key is 'home' or 'away'.
        """
        if not self.player_lookup or player_id_str not in self.player_lookup:
            return True # No static data to validate against

        static_player_info = self.player_lookup[player_id_str]
        static_team_assignment = static_player_info.get('team') # 'home' or 'away'

        if static_team_assignment and expected_boxscore_team_key and static_team_assignment != expected_boxscore_team_key:
            # This indicates a potential discrepancy between static roster data and live boxscore data
            # For example, a player might have been traded, or data error.
            # For live processing, boxscore is usually more current for team assignment on gameday.
            # print(f"ℹ️ Player team info: ID {player_id_str} ({static_player_info.get('name', 'N/A')}) - "
            #       f"Static Roster: '{static_team_assignment}', Boxscore: '{expected_boxscore_team_key}'. Using boxscore team.")
            # Depending on strictness, you could return False here, but often boxscore is truth for game day.
            pass # Allow, as boxscore is likely more up-to-date for current game team
        return True


    def _find_player_stats(self, player_by_game_stats: Dict, player_id_int: int, include_cumulative: bool) -> Optional[Dict]:
        """Find detailed stats for a specific player (player_id_int is integer from API)."""
        try:
            player_id_str = str(player_id_int) # For lookup in self.player_lookup if needed for validation

            for team_key_in_boxscore, team_name_code in [('awayTeam', 'away'), ('homeTeam', 'home')]:
                team_stats_section = player_by_game_stats.get(team_key_in_boxscore, {})
                
                for position_group_key in ['forwards', 'defensemen', 'goalies']:
                    for player_data in team_stats_section.get(position_group_key, []):
                        if player_data.get('playerId') == player_id_int:
                            if not self._validate_player_data(player_id_str, team_name_code):
                                # Validation failed (e.g. team mismatch if strict) - skip this player entry
                                continue 

                            # Common data for both cumulative and non-cumulative
                            base_stats = {
                                'name': player_data.get('name', {}).get('default', 'Unknown Player'),
                                'position': player_data.get('positionCode', 'N/A'), # positionCode is like "R", "L", "C", "D", "G"
                                'team': team_name_code, # 'home' or 'away'
                                # Add sweater number if available and useful
                                # 'sweaterNumber': player_data.get('sweaterNumber', None)
                            }

                            if include_cumulative:
                                if position_group_key == 'goalies':
                                    cumulative_stats = {
                                        'saves': player_data.get('saveShotsAgainst', '0/0').split('/')[0], # Often "saves/shotsAgainst"
                                        'shotsAgainst': player_data.get('saveShotsAgainst', '0/0').split('/')[-1],
                                        'goalsAgainst': player_data.get('goalsAgainst', 0),
                                        'savePct': player_data.get('savePctg'), # Can be null
                                        'timeOnIce': player_data.get('toi', '0:00'),
                                        'decision': player_data.get('decision', ''), # W, L, OTL
                                        'starter': player_data.get('starter', False),
                                        'evenStrengthSaves': player_data.get('evenStrengthSaveShotsAgainst', '0/0'),
                                        'powerPlaySaves': player_data.get('powerPlaySaveShotsAgainst', '0/0'),
                                        'shortHandedSaves': player_data.get('shorthandedSaveShotsAgainst', '0/0')
                                    }
                                else: # Forwards and Defensemen
                                    cumulative_stats = {
                                        'goals': player_data.get('goals', 0),
                                        'assists': player_data.get('assists', 0),
                                        'points': player_data.get('points', 0),
                                        'plusMinus': player_data.get('plusMinus', 0),
                                        'pim': player_data.get('pim', 0), # Penalty minutes
                                        'hits': player_data.get('hits', 0),
                                        'shotsOnGoal': player_data.get('sog', 0),
                                        'blockedShots': player_data.get('blockedShots', 0),
                                        'giveaways': player_data.get('giveaways', 0),
                                        'takeaways': player_data.get('takeaways', 0),
                                        'faceoffWins': player_data.get('faceoffWinningPctg', 0.0), # Often a percentage
                                        'timeOnIce': player_data.get('toi', '0:00'),
                                        'powerPlayGoals': player_data.get('powerPlayGoals', 0),
                                        'shifts': player_data.get('shifts', 0)
                                    }
                                return {**base_stats, **cumulative_stats}
                            else: # Not including cumulative, just basic info
                                if position_group_key == 'goalies':
                                     base_stats['starter'] = player_data.get('starter', False)
                                return base_stats
            # Player not found in boxscore stats
            # This can happen if a player ID from PBP is not in the boxscore (e.g. penalty on bench, etc.)
            # print(f"ℹ️ Player ID {player_id_int} not found in structured boxscore playerByGameStats.")
            # Fallback to static context if available and only basic info needed
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
            # print("ℹ️ LLM model not available. Using fallback description.")
            return self._get_fallback_description(len(activities))

        try:
            # Prepare a concise summary of activities for the prompt
            # Avoid sending overly verbose data if activities list is huge
            # This might need refinement based on token limits and desired LLM input
            prompt_activities = []
            for act in activities:
                # Select key fields to send to LLM
                act_summary = {
                    "type": act.get("typeDescKey", act.get("type", "unknown_event")),
                    "timeInPeriod": act.get("timeInPeriod"),
                    "details": {
                        "description": act.get("description"), # NHL's own description
                        "spatialDescription": act.get("details", {}).get("spatialDescription"),
                        "eventOwnerTeam": act.get("details", {}).get("eventOwnerTeamId") # could map to home/away
                    },
                    "gameSituation": act.get("gameSituation")
                }
                 # Add player names if available from enhancement
                details = act.get("details", {})
                involved_players = {}
                for k, v in details.items():
                    if "Name" in k and isinstance(v, str): # e.g. shootingPlayerName
                         involved_players[k] = v
                if involved_players:
                    act_summary["details"]["involvedPlayers"] = involved_players
                
                prompt_activities.append(act_summary)


            activities_json = json.dumps(prompt_activities, ensure_ascii=False, indent=None) # Compact JSON
            
            # Check token count if possible/necessary (genai library might handle internally or error)
            # For now, assume it fits reasonable limits for typical activity windows

            prompt_str = DESCRIPTION_PROMPT.replace('{activity_data}', activities_json).replace('{game_time}', current_game_time_str)
            
            # print(f"DEBUG: LLM Prompt (first 200 chars): {prompt_str[:200]}...")

            response = self.model.generate_content(prompt_str)
            
            # Check for safety ratings or blocks if applicable with Gemini
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                print(f"⚠️ LLM generation blocked. Reason: {response.prompt_feedback.block_reason}")
                return self._get_fallback_description(len(activities))
            if not response.candidates or not response.text: # Check if response.text is directly available
                first_candidate = response.candidates[0]
                if first_candidate.finish_reason != 'STOP':
                     print(f"⚠️ LLM generation did not finish normally. Reason: {first_candidate.finish_reason}")
                if not first_candidate.content or not first_candidate.content.parts:
                    print(f"⚠️ LLM response has no content parts.")
                    return self._get_fallback_description(len(activities))
                generated_text = "".join(part.text for part in first_candidate.content.parts if hasattr(part, 'text'))
            else: # If response.text is directly available (older API versions or simpler models)
                generated_text = response.text


            return generated_text.strip()

        except Exception as e:
            print(f"⚠️ Description generation error with LLM: {e}")
            return self._get_fallback_description(len(activities))

    def _get_fallback_description(self, activity_count: int) -> str:
        """Provides a generic description based on activity count if LLM fails or is disabled."""
        if activity_count == 0:
            return "Quiet moment in the game; teams are likely regrouping or play is stopped."
        elif activity_count <= 2:
            return "A brief sequence of events unfolds, possibly a quick transition or a minor stoppage."
        else:
            return "A series of plays developing, indicating a more active phase of the game."

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
        # Sanitize filename from colons
        filename_time = current_game_time_str.replace(':', '_')
        filename = f"{self.game_id}_{filename_time}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return filepath
        except IOError as e:
            print(f"❌ Error saving data to {filepath}: {e}")
            # Fallback: try to save with a timestamp if filename is an issue (though unlikely here)
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
                 return "" # Indicate failure

    @staticmethod
    def _get_time_seconds(activity: Dict) -> int:
        """Helper to get total seconds from activity timeInPeriod for sorting"""
        time_str = activity.get('timeInPeriod', '00:00')
        try:
            minutes, seconds = map(int, time_str.split(':'))
            return (minutes * 60) + seconds
        except (ValueError, AttributeError):
            # Default to a large number to sort non-standard times last or 0 for first
            return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 live_data_collector.py GAME_ID [GAME_DURATION_MINUTES] [FETCH_INTERVAL_SECONDS] [ACTIVITY_WINDOW_SECONDS] [REAL_TIME_DELAY_SECONDS]")
        print("Example: python3 live_data_collector.py 2023020001 2 5 30 0.5")
        print("\nArguments:")
        print("  GAME_ID                 : The NHL Game ID (e.g., 2023020001).")
        print("  GAME_DURATION_MINUTES   : Total in-game minutes to simulate (optional, default: 3.0).")
        print("  FETCH_INTERVAL_SECONDS  : Game time (seconds) to advance per fetch (optional, default: 5).")
        print("  ACTIVITY_WINDOW_SECONDS : Sliding window (seconds) for past activities (optional, default: 30).")
        print("  REAL_TIME_DELAY_SECONDS : Actual script delay (seconds) between fetches (optional, default: 0.5). If omitted, defaults to 0.5.")
        sys.exit(1)
    
    game_id_arg = sys.argv[1]
    
    # Default values
    game_duration_min_arg = 3.0
    fetch_interval_sec_arg = 5
    activity_window_sec_arg = 30
    real_time_delay_sec_arg = 0.5

    if len(sys.argv) > 2:
        try:
            game_duration_min_arg = float(sys.argv[2])
        except ValueError:
            print(f"⚠️ Invalid value for GAME_DURATION_MINUTES: '{sys.argv[2]}'. Using default: {game_duration_min_arg}.")
    if len(sys.argv) > 3:
        try:
            fetch_interval_sec_arg = int(sys.argv[3])
        except ValueError:
            print(f"⚠️ Invalid value for FETCH_INTERVAL_SECONDS: '{sys.argv[3]}'. Using default: {fetch_interval_sec_arg}.")
    if len(sys.argv) > 4:
        try:
            activity_window_sec_arg = int(sys.argv[4])
        except ValueError:
            print(f"⚠️ Invalid value for ACTIVITY_WINDOW_SECONDS: '{sys.argv[4]}'. Using default: {activity_window_sec_arg}.")
    if len(sys.argv) > 5:
        try:
            real_time_delay_sec_arg = float(sys.argv[5])
        except ValueError:
            print(f"⚠️ Invalid value for REAL_TIME_DELAY_SECONDS: '{sys.argv[5]}'. Using default: {real_time_delay_sec_arg}.")

    # Basic validation for arguments
    if game_duration_min_arg <= 0:
        print("⚠️ GAME_DURATION_MINUTES must be positive. Using default 3.0 minutes.")
        game_duration_min_arg = 3.0
    if fetch_interval_sec_arg <= 0:
        print("⚠️ FETCH_INTERVAL_SECONDS must be positive. Using default 5 seconds.")
        fetch_interval_sec_arg = 5
    if activity_window_sec_arg <= 0:
        print("⚠️ ACTIVITY_WINDOW_SECONDS must be positive. Using default 30 seconds.")
        activity_window_sec_arg = 30
    if real_time_delay_sec_arg < 0: # Can be 0 for fastest possible real-time simulation
        print("⚠️ REAL_TIME_DELAY_SECONDS cannot be negative. Using default 0.5 seconds.")
        real_time_delay_sec_arg = 0.5
    
    collector = LiveDataCollector(
        game_id=game_id_arg,
        fetch_interval_seconds=fetch_interval_sec_arg,
        activity_window_seconds=activity_window_sec_arg
    )
    collector.start_live_collection(
        game_duration_minutes=game_duration_min_arg,
        real_time_delay_seconds=real_time_delay_sec_arg
    )