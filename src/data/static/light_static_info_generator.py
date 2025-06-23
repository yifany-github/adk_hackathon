#!/usr/bin/env python3
"""
Light Static Info Generator - Filters static context to 2 teams only
Simple filter on top of static_info_generator.py - pure data only
"""
import os
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional


class LightStaticInfoGenerator:
    """Filters full static context to focus on the 2 teams playing only"""
    
    def __init__(self, output_dir: str = None):
        if output_dir is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.join(script_dir, "..", "..", "..")
            self.output_dir = os.path.join(project_root, "data", "static")
            self.output_dir = os.path.abspath(self.output_dir)
        else:
            self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        print("🏒 Light Static Info Generator Ready")
    
    def create_minimal_static_context(self, game_id: str) -> str:
        """Filter full static context to 2 teams only"""
        print(f"\n🔧 Filtering static context for game {game_id} (2 teams only)")
        
        # Read full static context
        full_path = os.path.join(self.output_dir, f"game_{game_id}_static_context.json")
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Full static context not found: {full_path}")
        
        with open(full_path, 'r') as f:
            full_context = json.load(f)
        
        # Filter to minimal context
        minimal_context = self._filter_to_two_teams(full_context)
        
        # Save minimal context
        minimal_path = os.path.join(self.output_dir, f"game_{game_id}_minimal_context.json")
        with open(minimal_path, 'w') as f:
            json.dump(minimal_context, f, indent=2)
        
        # Calculate size reduction
        full_size = len(json.dumps(full_context))
        minimal_size = len(json.dumps(minimal_context))
        reduction_pct = ((full_size - minimal_size) / full_size) * 100
        
        print(f"✅ Minimal context created: {minimal_path}")
        print(f"   Full size: {full_size:,} chars")
        print(f"   Minimal size: {minimal_size:,} chars")
        print(f"   Size reduction: {reduction_pct:.1f}%")
        
        return minimal_path
    
    def _filter_to_two_teams(self, full_context: Dict[str, Any]) -> Dict[str, Any]:
        """Filter to essential data only for the 2 teams playing"""
        game_info = full_context.get('game_info', {})
        home_team = game_info.get('home_team')
        away_team = game_info.get('away_team')
        
        if not home_team or not away_team:
            raise ValueError("Could not identify home/away teams from game info")
        
        # Keep essential data only
        minimal_context = {
            "game_id": full_context.get('game_id'),
            "generated_at": full_context.get('generated_at'),
            "game_info": full_context.get('game_info'),
            "rosters": self._filter_rosters_essential_only(full_context.get('rosters', {})),
            "player_count": full_context.get('player_count')
        }
        
        # Filter standings to only the 2 teams playing
        filtered_standings = self._filter_standings_for_teams(
            full_context.get('standings', {}), 
            home_team, 
            away_team
        )
        minimal_context["standings"] = filtered_standings
        
        return minimal_context
    
    def _filter_standings_for_teams(self, standings: Dict[str, Any], home_team: str, away_team: str) -> Dict[str, Any]:
        """Filter standings to only include the 2 teams playing"""
        if 'standings' not in standings:
            return standings  # Return as-is if no standings data
        
        # Keep the metadata
        filtered_standings = {
            "wildCardIndicator": standings.get("wildCardIndicator"),
            "standingsDateTimeUtc": standings.get("standingsDateTimeUtc"),
            "standings": []
        }
        
        # Filter standings list to only the 2 teams
        for team_data in standings.get('standings', []):
            team_abbrev = team_data.get('teamAbbrev', {}).get('default', '')
            if team_abbrev in [home_team, away_team]:
                filtered_standings["standings"].append(team_data)
        
        return filtered_standings
    
    def _filter_rosters_essential_only(self, rosters: Dict[str, Any]) -> Dict[str, Any]:
        """Filter rosters to essential data only - name, position, jersey, basic stats, goalie flag"""
        filtered_rosters = {
            "home_players": [],
            "away_players": []
        }
        
        # Filter home players
        for player in rosters.get('home_players', []):
            essential_player = self._extract_essential_player_data(player)
            if essential_player:
                filtered_rosters["home_players"].append(essential_player)
        
        # Filter away players  
        for player in rosters.get('away_players', []):
            essential_player = self._extract_essential_player_data(player)
            if essential_player:
                filtered_rosters["away_players"].append(essential_player)
        
        return filtered_rosters
    
    def _extract_essential_player_data(self, player: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract only essential player data - pure data only"""
        nhl_data = player.get('nhl_data', {})
        name = player.get('name') or nhl_data.get('name', {}).get('default', 'Unknown')
        position = player.get('position') or nhl_data.get('position', 'Unknown')
        
        # Get jersey number
        jersey_number = nhl_data.get('sweaterNumber')
        if not jersey_number:
            jersey_number = player.get('jersey_number', 0)
        
        # Get basic stats only
        goals = nhl_data.get('goals', 0)
        assists = nhl_data.get('assists', 0)
        
        # Determine if goalie (as you mentioned this is useful)
        is_goalie = position == 'G'
        
        return {
            "name": name,
            "position": position,
            "jersey_number": jersey_number,
            "goals": goals,
            "assists": assists,
            "is_goalie": is_goalie
        }


def create_minimal_static_context(full_path: str, minimal_path: str) -> None:
    """Utility function for direct file-to-file conversion (for pipeline v2 compatibility)"""
    # Extract game_id from filename
    filename = os.path.basename(full_path)
    if 'game_' in filename and '_static_context.json' in filename:
        game_id = filename.replace('game_', '').replace('_static_context.json', '')
    else:
        raise ValueError(f"Could not extract game_id from filename: {filename}")
    
    # Create generator and process
    output_dir = os.path.dirname(minimal_path)
    generator = LightStaticInfoGenerator(output_dir)
    result_path = generator.create_minimal_static_context(game_id)
    
    # If different output path requested, copy the result
    if result_path != minimal_path:
        import shutil
        shutil.copy2(result_path, minimal_path)
        print(f"✅ Copied to requested path: {minimal_path}")


def main():
    """CLI interface"""
    if len(sys.argv) != 2:
        print("Usage: python light_static_info_generator.py GAME_ID")
        print("Example: python light_static_info_generator.py 2024030412")
        sys.exit(1)
    
    game_id = sys.argv[1]
    generator = LightStaticInfoGenerator()
    
    try:
        result_path = generator.create_minimal_static_context(game_id)
        print(f"\n🎉 Light static context generated successfully!")
        print(f"   Output: {result_path}")
        print(f"   Focus: 2 teams only ({game_id})")
        print(f"   Pure data - no generated commentary")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()