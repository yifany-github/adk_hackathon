#!/usr/bin/env python3
"""
NHL Teams Data Fetcher
Fetches team rosters, information, arena details, and statistics from NHL APIs.
"""
import requests
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

class NHLTeamsAPI:
    """Handler for NHL team-related API calls and data management"""
    
    def __init__(self, cache_dir: str = "../../../data/teams_cache"):
        self.base_url = "https://api-web.nhle.com/v1"
        self.stats_url = "https://api.nhle.com/stats/rest/en"
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
    
    def fetch_all_teams(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Fetch basic information for all NHL teams
        """
        cache_file = "all_teams.json"
        
        if use_cache:
            cached_data = self._load_cache(cache_file)
            if cached_data:
                print("Using cached teams data")
                return cached_data
        
        print("Fetching all NHL teams...")
        
        # Get teams from standings (includes basic team info)
        standings_data = self._make_request(f"{self.base_url}/standings/now")
        if not standings_data:
            return {}
        
        teams_info = {}
        
        # Extract teams from standings
        for standing in standings_data.get('standings', []):
            # Fix: teamAbbrev might be nested or have different structure
            team_abbrev = standing.get('teamAbbrev')
            if isinstance(team_abbrev, dict):
                team_abbrev = team_abbrev.get('default', '')
            
            if team_abbrev:
                # Extract team name properly
                team_name = standing.get('teamName', {})
                if isinstance(team_name, dict):
                    team_name = team_name.get('default', '')
                
                team_data = {
                    'id': standing.get('teamCommonName', {})
                        .get('default', '') if isinstance(standing.get('teamCommonName'), dict) else standing.get('teamCommonName', ''),
                    'name': team_name,
                    'abbrev': team_abbrev,
                    'logo': standing.get('teamLogo', ''),
                    'conference': standing.get('conferenceName', ''),
                    'division': standing.get('divisionName', ''),
                    'standings': {
                        'wins': standing.get('wins', 0),
                        'losses': standing.get('losses', 0),
                        'points': standing.get('points', 0),
                        'games_played': standing.get('gamesPlayed', 0)
                    },
                    'updated': datetime.now().isoformat()
                }
                teams_info[team_abbrev] = team_data
        
        # Cache the results
        self._cache_data(cache_file, teams_info)
        print(f"Fetched {len(teams_info)} teams")
        
        return teams_info
    
    def fetch_team_roster(self, team_abbrev: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Fetch current roster for a specific team
        """
        cache_file = f"roster_{team_abbrev.lower()}.json"
        
        if use_cache:
            cached_data = self._load_cache(cache_file)
            if cached_data:
                print(f"Using cached roster for {team_abbrev}")
                return cached_data
        
        print(f"Fetching roster for {team_abbrev}...")
        
        roster_data = self._make_request(f"{self.base_url}/roster/{team_abbrev}/current")
        if not roster_data:
            return {}
        
        # Structure the roster data
        structured_roster = {
            'team_abbrev': team_abbrev,
            'forwards': [],
            'defensemen': [],
            'goalies': [],
            'updated': datetime.now().isoformat()
        }
        
        # Process forwards
        for forward in roster_data.get('forwards', []):
            player_info = {
                'id': forward.get('id'),
                'name': f"{forward.get('firstName', {}).get('default', '')} {forward.get('lastName', {}).get('default', '')}",
                'jersey_number': forward.get('sweaterNumber'),
                'position': forward.get('positionCode'),
                'shoots': forward.get('shootsCatches'),
                'height': forward.get('heightInInches'),
                'weight': forward.get('weightInPounds'),
                'birth_date': forward.get('birthDate'),
                'birth_city': forward.get('birthCity', {}).get('default', ''),
                'birth_country': forward.get('birthCountry'),
                'headshot': forward.get('headshot')
            }
            structured_roster['forwards'].append(player_info)
        
        # Process defensemen
        for defenseman in roster_data.get('defensemen', []):
            player_info = {
                'id': defenseman.get('id'),
                'name': f"{defenseman.get('firstName', {}).get('default', '')} {defenseman.get('lastName', {}).get('default', '')}",
                'jersey_number': defenseman.get('sweaterNumber'),
                'position': defenseman.get('positionCode'),
                'shoots': defenseman.get('shootsCatches'),
                'height': defenseman.get('heightInInches'),
                'weight': defenseman.get('weightInPounds'),
                'birth_date': defenseman.get('birthDate'),
                'birth_city': defenseman.get('birthCity', {}).get('default', ''),
                'birth_country': defenseman.get('birthCountry'),
                'headshot': defenseman.get('headshot')
            }
            structured_roster['defensemen'].append(player_info)
        
        # Process goalies
        for goalie in roster_data.get('goalies', []):
            player_info = {
                'id': goalie.get('id'),
                'name': f"{goalie.get('firstName', {}).get('default', '')} {goalie.get('lastName', {}).get('default', '')}",
                'jersey_number': goalie.get('sweaterNumber'),
                'position': goalie.get('positionCode'),
                'catches': goalie.get('shootsCatches'),
                'height': goalie.get('heightInInches'),
                'weight': goalie.get('weightInPounds'),
                'birth_date': goalie.get('birthDate'),
                'birth_city': goalie.get('birthCity', {}).get('default', ''),
                'birth_country': goalie.get('birthCountry'),
                'headshot': goalie.get('headshot')
            }
            structured_roster['goalies'].append(player_info)
        
        # Cache the results
        self._cache_data(cache_file, structured_roster)
        print(f"Fetched roster: {len(structured_roster['forwards'])} F, {len(structured_roster['defensemen'])} D, {len(structured_roster['goalies'])} G")
        
        return structured_roster
    
    def fetch_team_stats(self, team_abbrev: str, season: str = "20242025") -> Dict[str, Any]:
        """
        Fetch team statistics for current or specified season
        """
        print(f"Fetching team stats for {team_abbrev} in season {season}...")
        
        # Team stats endpoint
        stats_data = self._make_request(f"{self.stats_url}/team")
        if not stats_data:
            return {}
        
        # Find our team in the stats
        team_stats = {}
        for team in stats_data.get('data', []):
            if team.get('triCode') == team_abbrev:
                team_stats = {
                    'team_abbrev': team_abbrev,
                    'season': season,
                    'games_played': team.get('gamesPlayed', 0),
                    'wins': team.get('wins', 0),
                    'losses': team.get('losses', 0),
                    'ot_losses': team.get('otLosses', 0),
                    'points': team.get('points', 0),
                    'goals_for': team.get('goalsFor', 0),
                    'goals_against': team.get('goalsAgainst', 0),
                    'goal_differential': team.get('goalsFor', 0) - team.get('goalsAgainst', 0),
                    'shots_for': team.get('shotsForPerGame', 0),
                    'shots_against': team.get('shotsAgainstPerGame', 0),
                    'pp_percentage': team.get('powerPlayPct', 0),
                    'pk_percentage': team.get('penaltyKillPct', 0),
                    'updated': datetime.now().isoformat()
                }
                break
        
        if team_stats:
            # Cache team-specific stats
            cache_file = f"stats_{team_abbrev.lower()}_{season}.json"
            self._cache_data(cache_file, team_stats)
            print(f"Team stats: {team_stats['wins']}-{team_stats['losses']}-{team_stats['ot_losses']}, {team_stats['points']} pts")
        
        return team_stats
    
    def get_team_context(self, team_abbrev: str) -> Dict[str, Any]:
        """
        Get comprehensive team context combining roster, stats, and basic info
        """
        print(f"Building comprehensive context for {team_abbrev}...")
        
        # Get all teams info first
        teams_info = self.fetch_all_teams()
        team_basic = teams_info.get(team_abbrev, {})
        
        # Get roster
        roster = self.fetch_team_roster(team_abbrev)
        
        # Get stats
        stats = self.fetch_team_stats(team_abbrev)
        
        # Combine into comprehensive context
        context = {
            'basic_info': team_basic,
            'roster_summary': {
                'total_forwards': len(roster.get('forwards', [])),
                'total_defensemen': len(roster.get('defensemen', [])),
                'total_goalies': len(roster.get('goalies', [])),
                'key_players': self._identify_key_players(roster)
            },
            'current_stats': stats,
            'roster_details': roster,
            'context_generated': datetime.now().isoformat()
        }
        
        return context
    
    def _identify_key_players(self, roster: Dict) -> Dict[str, List]:
        """
        Identify key players from roster (simplified - could be enhanced with stats)
        """
        key_players = {
            'top_forwards': [],
            'top_defensemen': [],
            'starting_goalie': []
        }
        
        # Get first few forwards (in practice, you'd sort by stats)
        forwards = roster.get('forwards', [])
        if forwards:
            key_players['top_forwards'] = forwards[:6]  # Top 6 forwards
        
        # Get top defensemen
        defensemen = roster.get('defensemen', [])
        if defensemen:
            key_players['top_defensemen'] = defensemen[:4]  # Top 4 D
        
        # Get goalies
        goalies = roster.get('goalies', [])
        if goalies:
            key_players['starting_goalie'] = goalies[:2]  # Top 2 goalies
        
        return key_players

def main():
    """Test the NHL Teams API functionality"""
    import argparse
    
    parser = argparse.ArgumentParser(description="NHL Teams Data Fetcher")
    parser.add_argument('--team', type=str, help='Team abbreviation (e.g., TOR, BOS)')
    parser.add_argument('--all-teams', action='store_true', help='Fetch all teams data')
    parser.add_argument('--roster', action='store_true', help='Fetch team roster')
    parser.add_argument('--stats', action='store_true', help='Fetch team stats')
    parser.add_argument('--context', action='store_true', help='Get full team context')
    parser.add_argument('--no-cache', action='store_true', help='Skip cache, fetch fresh data')
    
    args = parser.parse_args()
    
    api = NHLTeamsAPI()
    use_cache = not args.no_cache
    
    if args.all_teams:
        teams = api.fetch_all_teams(use_cache=use_cache)
        print(f"\nFetched {len(teams)} teams:")
        for abbrev, team in teams.items():
            print(f"  {abbrev}: {team['name']} ({team['conference']} - {team['division']})")
    
    if args.team:
        team_abbrev = args.team.upper()
        
        if args.roster:
            roster = api.fetch_team_roster(team_abbrev, use_cache=use_cache)
            if roster:
                print(f"\n{team_abbrev} Roster Summary:")
                print(f"Forwards: {len(roster['forwards'])}")
                print(f"Defensemen: {len(roster['defensemen'])}")
                print(f"Goalies: {len(roster['goalies'])}")
        
        if args.stats:
            stats = api.fetch_team_stats(team_abbrev)
            if stats:
                print(f"\n{team_abbrev} Season Stats:")
                print(f"Record: {stats['wins']}-{stats['losses']}-{stats['ot_losses']}")
                print(f"Points: {stats['points']}")
                print(f"Goals For/Against: {stats['goals_for']}/{stats['goals_against']}")
        
        if args.context:
            context = api.get_team_context(team_abbrev)
            print(f"\n{team_abbrev} Full Context:")
            print(f"Team: {context['basic_info'].get('name', 'Unknown')}")
            print(f"Division: {context['basic_info'].get('division', 'Unknown')}")
            print(f"Current Record: {context['current_stats'].get('wins', 0)}-{context['current_stats'].get('losses', 0)}")
            print(f"Roster Size: {context['roster_summary']['total_forwards']}F + {context['roster_summary']['total_defensemen']}D + {context['roster_summary']['total_goalies']}G")

if __name__ == "__main__":
    main() 