#!/usr/bin/env python3
"""
Static Info Generator - Generates static context once per game
Implements Phase 1 from NHL Live Streaming Data Architecture
Enhanced with Hockey Reference player data integration
"""
import os
import json
import sys
import requests
import time
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import quote


class StaticInfoGenerator:
    """Generates static context for a game - team info, rosters, enhanced player stats"""
    
    def __init__(self, output_dir: str = None):
        if output_dir is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.join(script_dir, "..", "..", "..")
            self.output_dir = os.path.join(project_root, "data", "static")
            self.output_dir = os.path.abspath(self.output_dir)
        else:
            self.output_dir = output_dir
        self.base_url = "https://api-web.nhle.com/v1"
        self.hr_base_url = "https://hockey-reference.com"
        self.player_cache = {}  # Cache for Hockey Reference mappings
        os.makedirs(self.output_dir, exist_ok=True)
        print("🏒 Static Info Generator Ready")
    
    def generate_static_context(self, game_id: str) -> str:
        """Generate enhanced static context for a game (run once)"""
        print(f"\n🏒 Generating enhanced static context for game {game_id}")
        game_info = self._get_game_info(game_id)
        if not game_info:
            raise ValueError(f"Could not get game info for {game_id}")
        standings = self._get_standings()
        rosters = self._get_enhanced_rosters(game_id, game_info)
        static_context = {
            'game_id': game_id,
            'generated_at': datetime.now().isoformat(),
            'game_info': game_info,
            'standings': standings,
            'rosters': rosters,
            'player_count': len(rosters.get('home_players', [])) + len(rosters.get('away_players', []))
        }
        filepath = os.path.join(self.output_dir, f"game_{game_id}_static_context.json")
        with open(filepath, 'w') as f:
            json.dump(static_context, f, indent=2)
        print(f"\n💾 Enhanced static context saved: {filepath}")
        return filepath
    
    def _get_game_info(self, game_id: str) -> Dict[str, Any]:
        """Get basic game information"""
        try:
            url = f"{self.base_url}/gamecenter/{game_id}/boxscore"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            return {
                'date': data.get('gameDate'),
                'season': data.get('season'),
                'venue': data.get('venue', {}).get('default'),
                'home_team': data.get('homeTeam', {}).get('abbrev'),
                'away_team': data.get('awayTeam', {}).get('abbrev'),
                'home_team_name': data.get('homeTeam', {}).get('name', {}).get('default'),
                'away_team_name': data.get('awayTeam', {}).get('name', {}).get('default')
            }
        except Exception as e:
            print(f"❌ Error getting game info: {e}")
            return None
    
    def _get_standings(self) -> Dict[str, Any]:
        """Get current standings"""
        try:
            url = f"{self.base_url}/standings/now"
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️ Warning: Could not get standings: {e}")
            return {'error': str(e)}
    
    def _get_enhanced_rosters(self, game_id: str, game_info: Dict) -> Dict[str, Any]:
        """Get rosters with enhanced Hockey Reference data"""
        rosters = {
            'home_players': [],
            'away_players': [],
            'enhanced_count': 0,
            'cache_hits': 0
        }
        try:
            url = f"{self.base_url}/gamecenter/{game_id}/boxscore"
            response = requests.get(url)
            response.raise_for_status()
            boxscore = response.json()
            home_players = boxscore.get('playerByGameStats', {}).get('homeTeam', {}).get('forwards', [])
            home_players += boxscore.get('playerByGameStats', {}).get('homeTeam', {}).get('defense', [])
            home_players += boxscore.get('playerByGameStats', {}).get('homeTeam', {}).get('goalies', [])
            for player in home_players:
                enhanced_player = self._enhance_player_data(player)
                rosters['home_players'].append(enhanced_player)
                if enhanced_player.get('hockey_reference'):
                    rosters['enhanced_count'] += 1
            away_players = boxscore.get('playerByGameStats', {}).get('awayTeam', {}).get('forwards', [])
            away_players += boxscore.get('playerByGameStats', {}).get('awayTeam', {}).get('defense', [])
            away_players += boxscore.get('playerByGameStats', {}).get('awayTeam', {}).get('goalies', [])
            for player in away_players:
                enhanced_player = self._enhance_player_data(player)
                rosters['away_players'].append(enhanced_player)
                if enhanced_player.get('hockey_reference'):
                    rosters['enhanced_count'] += 1
        except Exception as e:
            print(f"⚠️ Warning: Could not get enhanced rosters: {e}")
            rosters['error'] = str(e)
        return rosters
    
    def _enhance_player_data(self, player: Dict) -> Dict[str, Any]:
        """Enhance player data with Hockey Reference stats"""
        player_id = str(player.get('playerId', ''))
        player_name = player.get('name', {}).get('default', '')
        enhanced_player = {
            'player_id': player_id,
            'name': player_name,
            'position': player.get('position'),
            'nhl_data': player
        }
        if player_name and player_id:
            hr_data = self._get_hockey_reference_data(player_name, player_id)
            if hr_data:
                enhanced_player['hockey_reference'] = hr_data
                enhanced_player['enhanced_context'] = self._generate_player_context(hr_data)
        return enhanced_player
    
    def _get_hockey_reference_data(self, player_name: str, player_id: str) -> Optional[Dict]:
        """Get Hockey Reference data for a player (mock for demo)"""
        if player_id in self.player_cache:
            return self.player_cache[player_id]
        try:
            hr_data = self._search_hockey_reference(player_name)
            self.player_cache[player_id] = hr_data
            time.sleep(0.5)
            return hr_data
        except Exception as e:
            print(f"⚠️ Could not get Hockey Reference data for {player_name}: {e}")
            return None
    
    def _search_hockey_reference(self, player_name: str) -> Optional[Dict]:
        """Search Hockey Reference for player stats (mock for demo)"""
        try:
            mock_data = {
                'season_stats': f'Mock stats for {player_name}',
                'recent_form': 'Strong recent performance',
                'career_highlights': 'Notable achievements',
                'search_attempted': True,
                'mock_data': True
            }
            return mock_data
        except Exception as e:
            print(f"❌ Hockey Reference search failed for {player_name}: {e}")
            return None
    
    def _generate_player_context(self, hr_data: Dict) -> str:
        """Generate context string for enhanced commentary"""
        if hr_data.get('mock_data'):
            return f"Enhanced player with {hr_data.get('recent_form', 'unknown form')}"
        return "Enhanced player context"

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 static_info_generator.py GAME_ID")
        print("Example: python3 static_info_generator.py 2023020001")
        sys.exit(1)
    game_id = sys.argv[1]
    generator = StaticInfoGenerator()
    generator.generate_static_context(game_id) 