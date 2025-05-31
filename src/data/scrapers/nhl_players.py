#!/usr/bin/env python3
"""
NHL Players Data Fetcher
Fetches player statistics, performance data, and career information from NHL APIs.
"""
import requests
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

class NHLPlayersAPI:
    """Handler for NHL player-related API calls and data management"""
    
    def __init__(self, cache_dir: str = "../../../data/players_cache"):
        self.base_url = "https://api-web.nhle.com/v1"
        self.cache_dir = cache_dir
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """Create cache directory if it doesn't exist"""
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _make_request(self, url: str) -> Optional[Dict]:
        """Make API request with error handling"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request failed for {url}: {e}")
            return None
    
    def _cache_data(self, filename: str, data: Dict):
        """Save data to cache file"""
        filepath = os.path.join(self.cache_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_cache(self, filename: str) -> Optional[Dict]:
        """Load data from cache file"""
        filepath = os.path.join(self.cache_dir, filename)
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
    
    def fetch_player_profile(self, player_id: int, use_cache: bool = True) -> Dict[str, Any]:
        """
        Fetch comprehensive player profile including stats, career data, and recent performance
        """
        cache_file = f"player_profile_{player_id}.json"
        
        if use_cache:
            cached_data = self._load_cache(cache_file)
            if cached_data:
                print(f"Using cached profile for player {player_id}")
                return cached_data
        
        print(f"Fetching player profile for {player_id}...")
        
        profile_data = self._make_request(f"{self.base_url}/player/{player_id}/landing")
        if not profile_data:
            return {}
        
        # Structure the player data for commentary use
        structured_profile = {
            'player_id': player_id,
            'basic_info': {
                'name': f"{profile_data.get('firstName', {}).get('default', '') if isinstance(profile_data.get('firstName'), dict) else profile_data.get('firstName', '')} {profile_data.get('lastName', {}).get('default', '') if isinstance(profile_data.get('lastName'), dict) else profile_data.get('lastName', '')}",
                'first_name': profile_data.get('firstName', {}).get('default', '') if isinstance(profile_data.get('firstName'), dict) else profile_data.get('firstName', ''),
                'last_name': profile_data.get('lastName', {}).get('default', '') if isinstance(profile_data.get('lastName'), dict) else profile_data.get('lastName', ''),
                'jersey_number': profile_data.get('sweaterNumber'),
                'position': profile_data.get('position'),
                'team_abbrev': profile_data.get('currentTeamAbbrev'),
                'team_name': profile_data.get('fullTeamName', {}).get('default', ''),
                'height_inches': profile_data.get('heightInInches'),
                'weight_pounds': profile_data.get('weightInPounds'),
                'birth_date': profile_data.get('birthDate'),
                'birth_city': profile_data.get('birthCity', {}).get('default', ''),
                'birth_country': profile_data.get('birthCountry'),
                'shoots_catches': profile_data.get('shootsCatches'),
                'headshot': profile_data.get('headshot'),
                'is_active': profile_data.get('isActive', False)
            },
            'draft_info': profile_data.get('draftDetails', {}),
            'awards': profile_data.get('awards', []),
            'updated': datetime.now().isoformat()
        }
        
        # Extract current season stats
        season_totals = profile_data.get('seasonTotals', [])
        if season_totals:
            current_season = season_totals[0]  # Most recent season
            structured_profile['current_season_stats'] = {
                'season': current_season.get('season'),
                'league': current_season.get('leagueAbbrev'),
                'team': current_season.get('teamName', {}).get('default', ''),
                'games_played': current_season.get('gamesPlayed', 0),
                'goals': current_season.get('goals', 0),
                'assists': current_season.get('assists', 0),
                'points': current_season.get('points', 0),
                'plus_minus': current_season.get('plusMinus', 0),
                'penalty_minutes': current_season.get('pim', 0),
                'shots': current_season.get('shots', 0),
                'shooting_percentage': current_season.get('shootingPctg', 0),
                'avg_toi': current_season.get('avgToi', ''),
                'power_play_goals': current_season.get('powerPlayGoals', 0),
                'power_play_points': current_season.get('powerPlayPoints', 0),
                'short_handed_goals': current_season.get('shorthandedGoals', 0),
                'game_winning_goals': current_season.get('gameWinningGoals', 0),
                'faceoff_pct': current_season.get('faceoffWinPctg', 0) if current_season.get('faceoffWinPctg') else None
            }
        
        # Extract featured stats (highlights)
        featured_stats = profile_data.get('featuredStats', {})
        if featured_stats:
            structured_profile['featured_stats'] = {
                'season': featured_stats.get('season'),
                'regularSeason': featured_stats.get('regularSeason', {}),
                'playoffs': featured_stats.get('playoffs', {})
            }
        
        # Extract career totals
        career_totals = profile_data.get('careerTotals', {})
        if career_totals:
            regular_season = career_totals.get('regularSeason', {})
            playoffs = career_totals.get('playoffs', {})
            
            structured_profile['career_totals'] = {
                'regular_season': {
                    'seasons': regular_season.get('seasons', 0),
                    'games_played': regular_season.get('gamesPlayed', 0),
                    'goals': regular_season.get('goals', 0),
                    'assists': regular_season.get('assists', 0),
                    'points': regular_season.get('points', 0),
                    'plus_minus': regular_season.get('plusMinus', 0),
                    'penalty_minutes': regular_season.get('pim', 0)
                },
                'playoffs': {
                    'seasons': playoffs.get('seasons', 0),
                    'games_played': playoffs.get('gamesPlayed', 0),
                    'goals': playoffs.get('goals', 0),
                    'assists': playoffs.get('assists', 0),
                    'points': playoffs.get('points', 0)
                } if playoffs else {}
            }
        
        # Extract recent performance
        last_5_games = profile_data.get('last5Games', [])
        if last_5_games:
            structured_profile['recent_performance'] = {
                'last_5_games': last_5_games,
                'last_5_summary': self._summarize_recent_games(last_5_games)
            }
        
        # Cache the results
        self._cache_data(cache_file, structured_profile)
        print(f"Fetched profile for {structured_profile['basic_info']['name']}")
        
        return structured_profile
    
    def fetch_player_game_log(self, player_id: int, use_cache: bool = True) -> Dict[str, Any]:
        """
        Fetch detailed game-by-game performance log for current season
        """
        cache_file = f"player_gamelog_{player_id}.json"
        
        if use_cache:
            cached_data = self._load_cache(cache_file)
            if cached_data:
                print(f"Using cached game log for player {player_id}")
                return cached_data
        
        print(f"Fetching game log for player {player_id}...")
        
        gamelog_data = self._make_request(f"{self.base_url}/player/{player_id}/game-log/now")
        if not gamelog_data:
            return {}
        
        # Structure the game log data
        game_log = gamelog_data.get('gameLog', [])
        
        structured_gamelog = {
            'player_id': player_id,
            'season': gamelog_data.get('seasonId'),
            'game_type': gamelog_data.get('gameTypeId'),
            'total_games': len(game_log),
            'games': [],
            'updated': datetime.now().isoformat()
        }
        
        # Process each game
        for game in game_log:
            game_info = {
                'game_id': game.get('gameId'),
                'date': game.get('gameDate'),
                'team': game.get('teamAbbrev'),
                'opponent': game.get('opponentAbbrev'),
                'home_away': 'home' if game.get('homeRoadFlag') == 'H' else 'away',
                'stats': {
                    'goals': game.get('goals', 0),
                    'assists': game.get('assists', 0),
                    'points': game.get('points', 0),
                    'plus_minus': game.get('plusMinus', 0),
                    'shots': game.get('shots', 0),
                    'toi': game.get('toi', ''),
                    'shifts': game.get('shifts', 0),
                    'pim': game.get('pim', 0),
                    'power_play_goals': game.get('powerPlayGoals', 0),
                    'power_play_points': game.get('powerPlayPoints', 0),
                    'short_handed_goals': game.get('shorthandedGoals', 0),
                    'game_winning_goals': game.get('gameWinningGoals', 0),
                    'ot_goals': game.get('otGoals', 0)
                }
            }
            structured_gamelog['games'].append(game_info)
        
        # Add performance analysis
        structured_gamelog['performance_analysis'] = self._analyze_game_log(structured_gamelog['games'])
        
        # Cache the results
        self._cache_data(cache_file, structured_gamelog)
        print(f"Fetched {len(game_log)} games from log")
        
        return structured_gamelog
    
    def _summarize_recent_games(self, last_5_games: List[Dict]) -> Dict[str, Any]:
        """Summarize performance over last 5 games"""
        if not last_5_games:
            return {}
        
        total_goals = sum(game.get('goals', 0) for game in last_5_games)
        total_assists = sum(game.get('assists', 0) for game in last_5_games)
        total_points = total_goals + total_assists
        
        return {
            'games_played': len(last_5_games),
            'total_goals': total_goals,
            'total_assists': total_assists,
            'total_points': total_points,
            'avg_points': round(total_points / len(last_5_games), 2),
            'point_streak': self._calculate_point_streak(last_5_games)
        }
    
    def _calculate_point_streak(self, games: List[Dict]) -> int:
        """Calculate current point streak from recent games"""
        streak = 0
        for game in games:
            if game.get('points', 0) > 0:
                streak += 1
            else:
                break
        return streak
    
    def _analyze_game_log(self, games: List[Dict]) -> Dict[str, Any]:
        """Analyze performance trends from game log"""
        if not games:
            return {}
        
        # Recent form (last 10 games)
        recent_games = games[:10]
        total_points = sum(game['stats']['points'] for game in recent_games)
        
        # Home vs Away splits
        home_games = [g for g in games if g['home_away'] == 'home']
        away_games = [g for g in games if g['home_away'] == 'away']
        
        home_points = sum(g['stats']['points'] for g in home_games) if home_games else 0
        away_points = sum(g['stats']['points'] for g in away_games) if away_games else 0
        
        return {
            'recent_form': {
                'last_10_games': len(recent_games),
                'points_in_last_10': total_points,
                'ppg_last_10': round(total_points / len(recent_games), 2) if recent_games else 0
            },
            'home_away_splits': {
                'home_games': len(home_games),
                'home_points': home_points,
                'home_ppg': round(home_points / len(home_games), 2) if home_games else 0,
                'away_games': len(away_games),
                'away_points': away_points,
                'away_ppg': round(away_points / len(away_games), 2) if away_games else 0
            }
        }
    
    def get_team_players_stats(self, team_abbrev: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get current season stats for all players on a team
        """
        cache_file = f"team_players_stats_{team_abbrev.lower()}.json"
        
        if use_cache:
            cached_data = self._load_cache(cache_file)
            if cached_data:
                print(f"Using cached team player stats for {team_abbrev}")
                return cached_data
        
        print(f"Fetching team player stats for {team_abbrev}...")
        
        # Import NHLTeamsAPI to get roster
        from nhl_teams import NHLTeamsAPI
        teams_api = NHLTeamsAPI()
        
        # Get team roster to get player IDs
        roster = teams_api.fetch_team_roster(team_abbrev, use_cache=use_cache)
        if not roster:
            return {}
        
        team_stats = {
            'team_abbrev': team_abbrev,
            'players': {
                'forwards': [],
                'defensemen': [],
                'goalies': []
            },
            'updated': datetime.now().isoformat()
        }
        
        # Fetch stats for each player type
        for position_group in ['forwards', 'defensemen', 'goalies']:
            for player in roster.get(position_group, []):
                player_id = player.get('id')
                if player_id:
                    # Get basic profile (includes current season stats)
                    profile = self.fetch_player_profile(player_id, use_cache=use_cache)
                    if profile:
                        # Combine roster info with stats
                        player_with_stats = {
                            'roster_info': player,
                            'season_stats': profile.get('current_season_stats', {}),
                            'recent_performance': profile.get('recent_performance', {})
                        }
                        team_stats['players'][position_group].append(player_with_stats)
        
        # Cache the results
        self._cache_data(cache_file, team_stats)
        total_players = sum(len(team_stats['players'][pos]) for pos in team_stats['players'])
        print(f"Fetched stats for {total_players} players on {team_abbrev}")
        
        return team_stats

def main():
    """Test the NHL Players API functionality"""
    import argparse
    
    parser = argparse.ArgumentParser(description="NHL Players Data Fetcher")
    parser.add_argument('--player-id', type=int, help='Player ID to fetch (e.g., 8479318 for Matthews)')
    parser.add_argument('--team', type=str, help='Team abbreviation to get all player stats')
    parser.add_argument('--profile', action='store_true', help='Fetch player profile')
    parser.add_argument('--gamelog', action='store_true', help='Fetch player game log')
    parser.add_argument('--no-cache', action='store_true', help='Skip cache, fetch fresh data')
    
    args = parser.parse_args()
    
    api = NHLPlayersAPI()
    use_cache = not args.no_cache
    
    if args.player_id:
        if args.profile:
            profile = api.fetch_player_profile(args.player_id, use_cache=use_cache)
            if profile:
                print(f"\n{profile['basic_info']['name']} Profile:")
                print(f"Team: {profile['basic_info']['team_abbrev']}")
                print(f"Position: {profile['basic_info']['position']}")
                if 'current_season_stats' in profile:
                    stats = profile['current_season_stats']
                    print(f"Season Stats: {stats['goals']}G {stats['assists']}A {stats['points']}P in {stats['games_played']} GP")
                
        if args.gamelog:
            gamelog = api.fetch_player_game_log(args.player_id, use_cache=use_cache)
            if gamelog:
                print(f"\nGame Log Summary:")
                print(f"Games played: {gamelog['total_games']}")
                if 'performance_analysis' in gamelog:
                    analysis = gamelog['performance_analysis']
                    recent = analysis.get('recent_form', {})
                    print(f"Last 10 games: {recent.get('points_in_last_10')} points ({recent.get('ppg_last_10')} PPG)")
    
    if args.team:
        team_stats = api.get_team_players_stats(args.team.upper(), use_cache=use_cache)
        if team_stats:
            print(f"\n{args.team.upper()} Team Player Stats:")
            for position_group in ['forwards', 'defensemen', 'goalies']:
                players = team_stats['players'][position_group]
                print(f"\n{position_group.title()} ({len(players)}):")
                for player_data in players[:3]:  # Show top 3
                    roster_info = player_data['roster_info']
                    stats = player_data.get('season_stats', {})
                    name = roster_info['name']
                    points = stats.get('points', 0)
                    games = stats.get('games_played', 0)
                    print(f"  {name}: {points} pts in {games} games")

if __name__ == "__main__":
    main() 