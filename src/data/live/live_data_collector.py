#!/usr/bin/env python3
"""
Live Data Collector - Flow-descriptive NHL commentary generation
Core flow: fetch → filter → enhance → LLM → save
"""
import os
import json
import sys
import time
import requests
import google.generativeai as genai
from datetime import datetime
from typing import Dict, List, Optional, Any
from prompts import DESCRIPTION_PROMPT
from spatial_converter import coords_to_hockey_language, get_game_situation, format_time_remaining


class LiveDataCollector:
    """Generates flow-descriptive commentary from live NHL data"""
    
    def __init__(self, game_id: str, output_dir: str = None):
        self.game_id = game_id
        
        if output_dir is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.join(script_dir, "..", "..", "..")
            self.output_dir = os.path.join(project_root, "data", "live")
            self.output_dir = os.path.abspath(self.output_dir)
        else:
            self.output_dir = output_dir
            
        self.base_url = "https://api-web.nhle.com/v1"
        self.static_context = None
        self.player_lookup = {}
        os.makedirs(self.output_dir, exist_ok=True)
        
        self._setup_llm()
        self._load_static_context()
        
        print(f"🏒 Live Data Collector Ready for Game {game_id}")
        print(f"🎯 Flow-descriptive commentary with {len(self.player_lookup)} players")

    def _setup_llm(self):
        """Setup Google Gemini for flow commentary"""
        try:
            genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
            self.model = genai.GenerativeModel("gemini-2.0-flash")
            print("🤖 Gemini LLM configured for flow commentary")
        except Exception as e:
            print(f"❌ LLM setup failed: {e}")
            self.model = None

    def _load_static_context(self):
        """Load player data for name enhancement"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.join(script_dir, "..", "..", "..")
            static_file = os.path.join(project_root, "data", "static", f"game_{self.game_id}_static_context.json")
            static_file = os.path.abspath(static_file)
            
            if os.path.exists(static_file):
                with open(static_file, 'r') as f:
                    self.static_context = json.load(f)
                self._build_player_lookup()
                print(f"✅ Loaded static context with {len(self.player_lookup)} players")
            else:
                print(f"⚠️ No static context found - running without player names")
        except Exception as e:
            print(f"⚠️ Could not load static context: {e}")

    def _build_player_lookup(self):
        """Build fast lookup for player names"""
        if not self.static_context or 'rosters' not in self.static_context:
            return
        
        rosters = self.static_context['rosters']
        for team, players in [('home', rosters.get('home_players', [])), 
                             ('away', rosters.get('away_players', []))]:
            for player in players:
                player_id = str(player.get('player_id', ''))
                if player_id:
                    self.player_lookup[player_id] = {
                        'name': player.get('name', 'Unknown'),
                        'position': player.get('position', ''),
                        'team': team
                    }

    def collect_live_data(self, current_time: str) -> str:
        """Main flow: fetch → filter → enhance → LLM → save"""
        print(f"🔄 Collecting flow data for game {self.game_id} at {current_time}")
        
        # 1. Fetch all play-by-play data
        pbp_data = self._get_play_by_play()
        if not pbp_data:
            raise ValueError(f"Could not get play-by-play data for {self.game_id}")
        
        # 2. Filter by time window (data leakage protection)
        activities = self._filter_activities(pbp_data, current_time)
        
        # 3. Enhance with player names and spatial context
        enhanced_activities = self._enhance_activities(activities, current_time)
        
        # 4. Generate description (always generates)
        description = self._generate_flow_commentary(enhanced_activities, current_time)
        
        # 5. Save data
        filepath = self._save_data(enhanced_activities, description, current_time, len(enhanced_activities))
        
        print(f"💾 Saved: {os.path.basename(filepath)} ({len(enhanced_activities)} activities)")
        return filepath

    def start_live_collection(self, duration_minutes: float = 5):
        """Start live game-time simulation"""
        print(f"🚀 Starting flow-descriptive collection for {duration_minutes} minutes")
        
        current_period = 1
        current_seconds = 0
        end_time = time.time() + (duration_minutes * 60)
        
        while time.time() < end_time:
            minutes = current_seconds // 60
            seconds = current_seconds % 60
            current_time = f"{current_period}:{minutes:02d}:{seconds:02d}"
            
            try:
                self.collect_live_data(current_time)
            except Exception as e:
                print(f"❌ Error at {current_time}: {e}")
            
            current_seconds += 5
            
            # Handle period transitions (20 min = 1200 sec per period)
            if current_seconds >= 1200:
                current_period += 1
                current_seconds = 0
                if current_period > 3:
                    print("🏁 Game complete (3 periods)")
                    break
            
            time.sleep(0.5)
        
        print("✅ Flow collection finished")

    def _get_play_by_play(self) -> Optional[Dict[str, Any]]:
        """Fetch all play-by-play data from NHL API"""
        try:
            url = f"{self.base_url}/gamecenter/{self.game_id}/play-by-play"
            response = requests.get(url, timeout=3)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error getting play-by-play: {e}")
            return None

    def _filter_activities(self, pbp_data: Dict[str, Any], current_time: str) -> List[Dict]:
        """Filter activities by time window (data leakage protection)"""
        period, time_str = current_time.split(':', 1)
        current_period = int(period)
        current_minutes, current_seconds = map(int, time_str.split(':'))
        current_total_seconds = (current_minutes * 60) + current_seconds
        
        activities = []
        
        for play in pbp_data.get('plays', []):
            # Only current period (prevent data leakage across periods)
            if play.get('periodDescriptor', {}).get('number', 0) != current_period:
                continue
                
            play_time = play.get('timeInPeriod', '')
            if not play_time:
                continue
                
            try:
                play_min, play_sec = map(int, play_time.split(':'))
                play_total_seconds = (play_min * 60) + play_sec
                
                # Skip future activities (critical data leakage protection)
                if play_total_seconds > current_total_seconds:
                    continue
                
                # Include activities from last 30 seconds for flow context
                time_diff = current_total_seconds - play_total_seconds
                if 0 <= time_diff <= 30:
                    activities.append(play)
                    
            except (ValueError, AttributeError):
                continue
        
        return activities

    def _get_boxscore(self) -> Optional[Dict[str, Any]]:
        """Fetch boxscore data with detailed player and team stats"""
        try:
            url = f"{self.base_url}/gamecenter/{self.game_id}/boxscore"
            response = requests.get(url, timeout=3)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️ Could not get boxscore data: {e}")
            return None

    def _enhance_activities(self, activities: List[Dict], current_time: str) -> List[Dict]:
        """Add player names, spatial context, and detailed stats to activities"""
        enhanced_activities = []
        
        # Get boxscore data for additional stats
        boxscore_data = self._get_boxscore()
        
        for activity in activities:
            enhanced_activity = json.loads(json.dumps(activity))  # Deep copy
            details = enhanced_activity.get('details', {})
            
            # Add player names for key player fields
            player_fields = [
                'committedByPlayerId', 'drawnByPlayerId', 'shootingPlayerId', 
                'hittingPlayerId', 'hitteePlayerId', 'winningPlayerId', 
                'losingPlayerId', 'goalieInNetId', 'blockingPlayerId',
                'playerId'  # Used in giveaway/takeaway events
            ]
            
            for field in player_fields:
                if field in details:
                    player_id = str(details[field])
                    if player_id in self.player_lookup:
                        player_info = self.player_lookup[player_id]
                        name_field = field.replace('Id', 'Name')
                        details[name_field] = f"{player_info['name']} ({player_info['position']}, {player_info['team']})"
            
            # Add spatial context
            x_coord = details.get('xCoord')
            y_coord = details.get('yCoord') 
            zone_code = details.get('zoneCode')
            home_defending_side = enhanced_activity.get('homeTeamDefendingSide', 'right')
            
            if x_coord is not None and y_coord is not None and zone_code:
                spatial_desc = coords_to_hockey_language(x_coord, y_coord, zone_code, home_defending_side)
                details['spatialDescription'] = spatial_desc
            
            # Add game situation
            situation_code = enhanced_activity.get('situationCode', '')
            if situation_code:
                game_situation = get_game_situation(situation_code)
                if game_situation:
                    enhanced_activity['gameSituation'] = game_situation
            
            # Add formatted time remaining
            time_remaining = enhanced_activity.get('timeRemaining', '')
            if time_remaining:
                formatted_time = format_time_remaining(time_remaining)
                if formatted_time:
                    enhanced_activity['timeRemainingFormatted'] = formatted_time
            
            # Add detailed stats from boxscore if available (with temporal filtering)
            if boxscore_data:
                enhanced_activity['gameStats'] = self._extract_game_stats(boxscore_data, enhanced_activity, current_time)
            
            enhanced_activities.append(enhanced_activity)
        
        # Sort by time for proper flow analysis
        enhanced_activities.sort(key=self._get_time_seconds)
        return enhanced_activities

    def _should_include_cumulative_stats(self, current_time: str) -> bool:
        """Determine if cumulative stats should be included based on game time"""
        period, time_str = current_time.split(':', 1)
        current_period = int(period)
        current_minutes, current_seconds = map(int, time_str.split(':'))
        current_total_seconds = (current_minutes * 60) + current_seconds
        
        # Don't show cumulative stats at period start or very early in period
        if current_total_seconds <= 60:  # First minute of any period
            return False
            
        # For first period, be extra conservative
        if current_period == 1 and current_total_seconds <= 300:  # First 5 minutes
            return False
            
        return True

    def _extract_game_stats(self, boxscore_data: Dict, activity: Dict, current_time: str) -> Dict:
        """Extract relevant game stats for the current activity (with temporal filtering)"""
        stats = {
            'teamStats': {},
            'playerStats': {}
        }
        
        try:
            # Determine if we should include cumulative stats (prevent data leakage)
            include_cumulative = self._should_include_cumulative_stats(current_time)
            
            # Extract team stats (only if appropriate for timing)
            away_team = boxscore_data.get('awayTeam', {})
            home_team = boxscore_data.get('homeTeam', {})
            
            if include_cumulative:
                # Full team stats for mid/late period
                stats['teamStats'] = {
                    'away': {
                        'score': away_team.get('score', 0),
                        'shotsOnGoal': away_team.get('sog', 0),
                        'teamName': away_team.get('abbrev', 'AWAY')
                    },
                    'home': {
                        'score': home_team.get('score', 0),
                        'shotsOnGoal': home_team.get('sog', 0),
                        'teamName': home_team.get('abbrev', 'HOME')
                    }
                }
            else:
                # Minimal team stats for period start/early period
                stats['teamStats'] = {
                    'away': {
                        'teamName': away_team.get('abbrev', 'AWAY')
                    },
                    'home': {
                        'teamName': home_team.get('abbrev', 'HOME')
                    }
                }
            
            # Extract player stats from boxscore if players are involved in the activity
            player_stats = boxscore_data.get('playerByGameStats', {})
            
            # Get player IDs from activity details
            details = activity.get('details', {})
            player_fields = [
                'committedByPlayerId', 'drawnByPlayerId', 'shootingPlayerId', 
                'hittingPlayerId', 'hitteePlayerId', 'winningPlayerId', 
                'losingPlayerId', 'goalieInNetId', 'blockingPlayerId', 'playerId'
            ]
            
            for field in player_fields:
                if field in details:
                    player_id = details[field]
                    player_stat = self._find_player_stats(player_stats, player_id, include_cumulative)
                    if player_stat:
                        stats['playerStats'][field] = player_stat
            
        except Exception as e:
            print(f"⚠️ Error extracting game stats: {e}")
        
        return stats

    def _validate_player_data(self, player_id: str, expected_team: str) -> bool:
        """Validate player team assignment to prevent errors"""
        if player_id in self.player_lookup:
            static_team = self.player_lookup[player_id].get('team', '')
            if static_team and expected_team and static_team != expected_team:
                print(f"⚠️ Player team mismatch: {player_id} - static: {static_team}, boxscore: {expected_team}")
                return False
        return True

    def _find_player_stats(self, player_stats: Dict, player_id: int, include_cumulative: bool) -> Optional[Dict]:
        """Find detailed stats for a specific player (with validation)"""
        try:
            # Search through all player categories
            for team_key in ['awayTeam', 'homeTeam']:
                team_stats = player_stats.get(team_key, {})
                team_name = 'away' if team_key == 'awayTeam' else 'home'
                
                # Check forwards
                for player in team_stats.get('forwards', []):
                    if player.get('playerId') == player_id:
                        # Validate team assignment
                        if not self._validate_player_data(str(player_id), team_name):
                            print(f"⚠️ Skipping player {player_id} due to team validation failure")
                            continue
                            
                        if include_cumulative:
                            return {
                                'name': player.get('name', {}).get('default', 'Unknown'),
                                'position': player.get('position', ''),
                                'team': team_name,  # Add explicit team info
                                'goals': player.get('goals', 0),
                                'assists': player.get('assists', 0),
                                'points': player.get('points', 0),
                                'plusMinus': player.get('plusMinus', 0),
                                'pim': player.get('pim', 0),
                                'hits': player.get('hits', 0),
                                'shotsOnGoal': player.get('sog', 0),
                                'timeOnIce': player.get('toi', '0:00'),
                                'blockedShots': player.get('blockedShots', 0),
                                'shifts': player.get('shifts', 0),
                                'giveaways': player.get('giveaways', 0),
                                'takeaways': player.get('takeaways', 0),
                                'faceoffWinPct': player.get('faceoffWinningPctg', 0),
                                'powerPlayGoals': player.get('powerPlayGoals', 0)
                            }
                        else:
                            # Minimal stats for early period
                            return {
                                'name': player.get('name', {}).get('default', 'Unknown'),
                                'position': player.get('position', ''),
                                'team': team_name
                            }
                
                # Check defensemen
                for player in team_stats.get('defensemen', []):
                    if player.get('playerId') == player_id:
                        # Validate team assignment
                        if not self._validate_player_data(str(player_id), team_name):
                            print(f"⚠️ Skipping player {player_id} due to team validation failure")
                            continue
                            
                        if include_cumulative:
                            return {
                                'name': player.get('name', {}).get('default', 'Unknown'),
                                'position': player.get('position', ''),
                                'team': team_name,  # Add explicit team info
                                'goals': player.get('goals', 0),
                                'assists': player.get('assists', 0),
                                'points': player.get('points', 0),
                                'plusMinus': player.get('plusMinus', 0),
                                'pim': player.get('pim', 0),
                                'hits': player.get('hits', 0),
                                'shotsOnGoal': player.get('sog', 0),
                                'timeOnIce': player.get('toi', '0:00'),
                                'blockedShots': player.get('blockedShots', 0),
                                'shifts': player.get('shifts', 0),
                                'giveaways': player.get('giveaways', 0),
                                'takeaways': player.get('takeaways', 0),
                                'faceoffWinPct': player.get('faceoffWinningPctg', 0)
                            }
                        else:
                            # Minimal stats for early period
                            return {
                                'name': player.get('name', {}).get('default', 'Unknown'),
                                'position': player.get('position', ''),
                                'team': team_name
                            }
                
                # Check goalies
                for player in team_stats.get('goalies', []):
                    if player.get('playerId') == player_id:
                        # Validate team assignment
                        if not self._validate_player_data(str(player_id), team_name):
                            print(f"⚠️ Skipping player {player_id} due to team validation failure")
                            continue
                            
                        if include_cumulative:
                            return {
                                'name': player.get('name', {}).get('default', 'Unknown'),
                                'position': player.get('position', 'G'),
                                'team': team_name,  # Add explicit team info
                                'saves': player.get('saves', 0),
                                'shotsAgainst': player.get('shotsAgainst', 0),
                                'goalsAgainst': player.get('goalsAgainst', 0),
                                'savePct': player.get('savePctg', 0),
                                'timeOnIce': player.get('toi', '0:00'),
                                'decision': player.get('decision', ''),
                                'starter': player.get('starter', False),
                                'evenStrengthSaves': player.get('evenStrengthShotsAgainst', '0/0'),
                                'powerPlaySaves': player.get('powerPlayShotsAgainst', '0/0'),
                                'shortHandedSaves': player.get('shorthandedShotsAgainst', '0/0')
                            }
                        else:
                            # Minimal stats for early period (no save counts yet)
                            return {
                                'name': player.get('name', {}).get('default', 'Unknown'),
                                'position': player.get('position', 'G'),
                                'team': team_name,
                                'starter': player.get('starter', False)
                            }
                        
        except Exception as e:
            print(f"⚠️ Error finding player stats for {player_id}: {e}")
        
        return None

    def _generate_flow_commentary(self, activities: List[Dict], current_time: str) -> str:
        """Generate flow-descriptive commentary (always generates)"""
        try:
            # Use compact JSON to avoid formatting issues
            activities_json = json.dumps(activities, ensure_ascii=False)
            # Use string replacement to avoid JSON brace issues
            prompt = DESCRIPTION_PROMPT.replace('{activity_data}', activities_json).replace('{game_time}', current_time)
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            print(f"⚠️ Description generation error: {e}")
            # Descriptive fallback based on activity level
            activity_count = len(activities)
            if activity_count == 0:
                return "Both teams maintaining tactical positioning with measured puck movement as they probe for opportunities."
            elif activity_count <= 2:
                return "Transitional play developing as teams work to establish offensive flow and positioning."
            else:
                return "Sustained action with both teams engaged in active puck battles and positional play."

    def _save_data(self, activities: List[Dict], description: str, current_time: str, activity_count: int) -> str:
        """Save flow data to JSON file"""
        data = {
            'game_id': self.game_id,
            'game_time': current_time,
            'collected_at': datetime.now().isoformat(),
            'activities': activities,
            'description': description,
            'activity_count': activity_count
        }
        
        # Create game-specific subdirectory
        game_dir = os.path.join(self.output_dir, self.game_id)
        os.makedirs(game_dir, exist_ok=True)
        
        # Create filename from time
        period, time_part = current_time.split(':', 1)
        time_str = time_part.replace(':', '_')
        filename = f"game_{self.game_id}_flow_{period}_{time_str}.json"
        filepath = os.path.join(game_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        return filepath

    @staticmethod
    def _get_time_seconds(activity: Dict) -> int:
        """Helper to get activity time in seconds for sorting"""
        time_str = activity.get('timeInPeriod', '00:00')
        try:
            mins, secs = map(int, time_str.split(':'))
            return mins * 60 + secs
        except:
            return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 live_data_collector.py GAME_ID [DURATION_MINUTES]")
        print("Example: python3 live_data_collector.py 2024020001 3")
        sys.exit(1)
    
    game_id = sys.argv[1]
    duration = float(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    collector = LiveDataCollector(game_id)
    collector.start_live_collection(duration) 