#!/usr/bin/env python3
"""
Static Info Generator - Generates static context once per game
Implements Phase 1 from NHL Live Streaming Data Architecture
"""
import os
import json
import sys
import requests
from datetime import datetime
from typing import Dict, Any


class StaticInfoGenerator:
    """Generates static context for a game - team info, rosters, historical stats"""
    
    def __init__(self, output_dir: str = "../../../data/static"):
        self.output_dir = output_dir
        self.base_url = "https://api-web.nhle.com/v1"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_static_context(self, game_id: str) -> str:
        """Generate static context for a game (run once)"""
        print(f"🏒 Generating static context for game {game_id}")
        
        # Get game info
        game_info = self._get_game_info(game_id)
        if not game_info:
            raise ValueError(f"Could not get game info for {game_id}")
        
        print(f"🏠 Home: {game_info['home_team']}")
        print(f"✈️  Away: {game_info['away_team']}")
        
        # Get standings
        standings = self._get_standings()
        
        # Build static context
        static_context = {
            'game_id': game_id,
            'generated_at': datetime.now().isoformat(),
            'game_info': game_info,
            'standings': standings
        }
        
        # Save static context
        filepath = os.path.join(self.output_dir, f"game_{game_id}_static_context.json")
        with open(filepath, 'w') as f:
            json.dump(static_context, f, indent=2)
        
        print(f"💾 Static context saved: {filepath}")
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


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 static_info_generator.py GAME_ID")
        print("Example: python3 static_info_generator.py 2023020001")
        sys.exit(1)
    
    game_id = sys.argv[1]
    generator = StaticInfoGenerator()
    generator.generate_static_context(game_id) 