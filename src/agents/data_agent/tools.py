# data_agent/tools.py

import json
import os
import glob
from typing import List, Dict, Any, Optional
from datetime import datetime
from .config import (
    MOMENTUM_SCORES, 
    MOMENTUM_THRESHOLDS, 
    CONTEXTUAL_MULTIPLIERS, 
    HIGH_INTENSITY_THRESHOLD
)

def load_static_context(game_id: str) -> Dict[str, Any]:
    """
    Loads static game context including team info, player stats, and historical data.
    
    Args:
        game_id: The game identifier
        
    Returns:
        Dictionary containing static context and knowledge base information
    """
    try:
        # Try to load static context file with correct naming pattern
        static_context_path = f"data/static/game_{game_id}_static_context.json"
        if os.path.exists(static_context_path):
            with open(static_context_path, 'r') as f:
                return json.load(f)
        
        # Fallback - try old naming pattern
        static_context_path = f"data/static/static_context_{game_id}.json"
        if os.path.exists(static_context_path):
            with open(static_context_path, 'r') as f:
                return json.load(f)
        
        # Fallback to basic structure if no file exists
        return {
            "teams": {"home": {"name": "Unknown", "stats": {}}, "away": {"name": "Unknown", "stats": {}}},
            "players": {},
            "season_storylines": [],
            "recent_milestones": [],
            "historical_matchups": []
        }
    except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
        print(f"Warning: Failed to load static context for {game_id}: {e}")
        return {
            "teams": {"home": {"name": "Unknown", "stats": {}}, "away": {"name": "Unknown", "stats": {}}},
            "players": {},
            "season_storylines": [],
            "recent_milestones": [],
            "historical_matchups": []
        }







# ============= ENHANCED HELPER FUNCTIONS =================

def get_player_name_from_static(player_id: int, static_context: Dict[str, Any]) -> str:
    """Get human-readable player name from static context data"""
    try:
        # Check both home and away players in rosters
        rosters = static_context.get("rosters", {})
        all_players = rosters.get("home_players", []) + rosters.get("away_players", [])
        
        for player in all_players:
            if player.get("player_id") == str(player_id) or player.get("nhl_data", {}).get("playerId") == player_id:
                # Try to get full name first, then fallback to default name
                full_name = player.get("nhl_data", {}).get("name", {}).get("default")
                if full_name:
                    return full_name
                return player.get("name", f"Player #{player_id}")
        
        # Fallback - try legacy players structure
        players = static_context.get("players", [])
        for player in players:
            if player.get("player_id") == str(player_id) or player.get("nhl_data", {}).get("playerId") == player_id:
                return player.get("name", f"Player #{player_id}")
                
        return f"Player #{player_id}"
    except Exception as e:
        return f"Player #{player_id}"


def _resolve_player_names_in_details(details: Dict[str, Any], static_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve player IDs to names in event details
    
    Args:
        details: Raw event details with player IDs
        static_context: Static context containing player mappings
        
    Returns:
        Enhanced details with player names
    """
    enhanced_details = details.copy()
    
    # Common player ID fields in NHL API events
    player_id_fields = [
        "shootingPlayerId",
        "goalieInNetId", 
        "committedByPlayerId",
        "drawnByPlayerId",
        "winningPlayerId",
        "losingPlayerId",
        "hittingPlayerId",
        "hitteePlayerId"
    ]
    
    for field in player_id_fields:
        if field in enhanced_details:
            player_id = enhanced_details[field]
            if isinstance(player_id, int):
                player_name = get_player_name_from_static(player_id, static_context)
                # Add resolved name alongside ID
                name_field = field.replace("Id", "Name")
                enhanced_details[name_field] = player_name
    
    return enhanced_details


def _calculate_activity_trend(activities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculate activity trend from recent events
    
    Args:
        activities: List of game events
        
    Returns:
        List of trend indicators showing activity progression
    """
    if not activities:
        return []
    
    try:
        # Group events by time periods (last 5 events, etc.)
        trend_data = []
        
        # Get event types and timing
        for i, event in enumerate(activities[-5:]):  # Last 5 events for trend
            event_type = event.get("typeDescKey", "unknown")
            time_in_period = event.get("timeInPeriod", "0:00")
            
            trend_data.append({
                "sequence": i + 1,
                "event_type": event_type,
                "time": time_in_period,
                "intensity": 1 if event_type in ["goal", "penalty", "hit"] else 0.5
            })
        
        return trend_data
        
    except Exception:
        return []



# ============= ADK-COMPATIBLE TOOLS =================

def analyze_hockey_momentum_adk(game_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    ADK Tool: Analyze hockey game data and calculate momentum.
    
    Args:
        game_data: Raw hockey game data including events and context
        
    Returns:
        Dict with momentum analysis including score, recommendation, events
    """
    try:
        # Load static context for player name resolution
        game_id = game_data.get("game_id")  # Extract from data
        if not game_id:
            raise ValueError("game_id is required in game_data")
        static_context = load_static_context(game_id)
        # Extract events and context
        activities = game_data.get("activities", [])
        game_context = {
            "period": 1,
            "time_remaining": "20:00", 
            "home_score": 0,
            "away_score": 0,
            "game_situation": "even_strength",
            "periodType": "REG"
        }
        
        # Extract actual game context if available
        if activities:
            latest_event = activities[-1]
            period_desc = latest_event.get("periodDescriptor", {})
            game_stats = latest_event.get("gameStats", {}).get("teamStats", {})
            
            game_context.update({
                "period": period_desc.get("number", 1),
                "time_remaining": latest_event.get("timeRemaining", "20:00"),
                "home_score": game_stats.get("home", {}).get("score", 0),
                "away_score": game_stats.get("away", {}).get("score", 0),
                "game_situation": latest_event.get("gameSituation", "even_strength"),
                "periodType": period_desc.get("periodType", "REG")
            })
        
        # Calculate basic momentum score from event count and types
        momentum_score = min(len(activities) * 5, 100)  # Basic scoring
        
        # Identify high intensity events with resolved player names
        high_intensity_events = []
        for event in activities:
            event_type = event.get("typeDescKey", "")
            if event_type in ["goal", "penalty", "hit", "shot-on-goal"]:
                # Get raw details and resolve player names
                details = event.get("details", {})
                enhanced_details = _resolve_player_names_in_details(details, static_context)
                
                high_intensity_events.append({
                    "type": event_type,
                    "time": event.get("timeInPeriod", "0:00"),
                    "description": enhanced_details
                })
        
        momentum_result = {
            "total_momentum_score": momentum_score,
            "high_intensity_events": high_intensity_events,
            "recent_activity_trend": _calculate_activity_trend(activities),
            "context_analysis": {"event_count": len(activities)}
        }
        
        # Return only analysis data - let LLM make recommendations
        return {
            "momentum_score": momentum_result.get("total_momentum_score", 0),
            "high_intensity_events": momentum_result.get("high_intensity_events", []),
            "game_context": game_context,
            "activity_trend": momentum_result.get("recent_activity_trend", []),
            "context_analysis": momentum_result.get("context_analysis", {}),
            "event_count": len(activities),
            "analysis_summary": f"Processed {len(activities)} events with momentum score {momentum_result.get('total_momentum_score', 0)}"
        }
        
    except Exception as e:
        return {
            "momentum_score": 0,
            "high_intensity_events": [],
            "game_context": game_context,
            "activity_trend": [],
            "context_analysis": {},
            "event_count": 0,
            "error": str(e),
            "analysis_summary": "Error in analysis - no momentum data available"
        }


def extract_game_context_adk(game_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    ADK Tool: Extract current game context (period, time, score, situation).
    
    Args:
        game_data: Raw hockey game data
        
    Returns:
        Dict with current game state information
    """
    activities = game_data.get("activities", [])
    
    if not activities:
        return {
            "period": 1,
            "time_remaining": "20:00",
            "home_score": 0,
            "away_score": 0,
            "game_situation": "even_strength",
            "periodType": "REG"
        }
    
    # Use the most recent event for current context
    latest_event = activities[-1]
    period_desc = latest_event.get("periodDescriptor", {})
    game_stats = latest_event.get("gameStats", {}).get("teamStats", {})
    
    return {
        "period": period_desc.get("number", 1),
        "time_remaining": latest_event.get("timeRemaining", "20:00"),
        "home_score": game_stats.get("home", {}).get("score", 0),
        "away_score": game_stats.get("away", {}).get("score", 0),
        "game_situation": latest_event.get("gameSituation", "even_strength"),
        "periodType": period_desc.get("periodType", "REG")
    }


def generate_filler_content_adk(static_context: Dict[str, Any], used_topics: Optional[List[str]]) -> Dict[str, Any]:
    """
    ADK Tool: Generate varied filler content avoiding repetition.
    
    Args:
        static_context: Game's static context data
        used_topics: Recently used filler topics to avoid
        
    Returns:
        Dict with filler content type, content, and talking points
    """
    # Simple topic rotation to avoid repetition
    available_topics = ["TEAM_RECORD", "PLAYER_PERFORMANCE", "MATCHUP_CONTEXT", 
                       "GOALIE_STATS", "POWER_PLAY_STATS"]
    
    if used_topics:
        available_topics = [t for t in available_topics if t not in used_topics[-2:]]
    
    if not available_topics:
        available_topics = ["TEAM_RECORD"]
    
    # Use the first available topic
    topic_type = available_topics[0]
    
    return create_specific_filler_content(static_context, "normal")


def create_game_specific_get_player_information(static_context: Dict[str, Any]):
    """Create a game-specific player information tool with pre-loaded context"""
    def get_player_information(player_id: int) -> str:
        """Get player name from this game's static context"""
        return get_player_name_from_static(player_id, static_context)
    return get_player_information


def create_game_specific_generate_filler_content(static_context: Dict[str, Any]):
    """Create a game-specific filler content tool with pre-loaded context"""
    def generate_filler_content(used_topics: List[str]) -> Dict[str, Any]:
        """Generate filler content using this game's static context"""
        return generate_filler_content_adk(static_context, used_topics)
    return generate_filler_content


def create_specific_filler_content(static_context: Dict[str, Any], game_situation: str) -> Dict[str, Any]:
    """
    Create specific, actionable filler content using actual static data
    
    Args:
        static_context: Loaded static context data
        game_situation: Current game situation (power_play, penalty_kill, normal)
        
    Returns:
        Specific filler content with talking points
    """
    try:
        # Check for interesting player stats
        players = static_context.get("players", [])
        if players:
            # Find players with interesting stats
            for player in players[:5]:  # Check first 5 players
                nhl_data = player.get("nhl_data", {})
                goals = nhl_data.get("goals", 0)
                assists = nhl_data.get("assists", 0)
                points = goals + assists
                
                if points > 10:  # Player with decent stats
                    return {
                        "type": "PLAYER_PERFORMANCE",
                        "content": f"{player.get('name', 'Player')} has {goals} goals and {assists} assists",
                        "talking_points": [
                            f"{player.get('name', 'Player')} leads the team with {points} points",
                            f"Breaking down their {goals} goals and {assists} assists",
                            f"Key contributor in the {player.get('position', '')} position"
                        ]
                    }
        
        # Team stats from standings
        standings = static_context.get("standings", {}).get("standings", [])
        if standings:
            team_stats = standings[0]  # First team in standings
            wins = team_stats.get("wins", 0)
            losses = team_stats.get("losses", 0)
            goals_for = team_stats.get("goalFor", 0)
            goals_against = team_stats.get("goalAgainst", 0)
            
            return {
                "type": "TEAM_RECORD",
                "content": f"Team record: {wins}-{losses}, {goals_for} goals for, {goals_against} against",
                "talking_points": [
                    f"Strong season with {wins} wins and {losses} losses",
                    f"Averaging {goals_for/82:.1f} goals per game" if wins > 0 else "Looking to improve offensive production",
                    f"Goal differential of {goals_for - goals_against}"
                ]
            }
        
        # Fallback storyline
        game_info = static_context.get("game_info", {})
        home_team = game_info.get("home_team", "Home")
        away_team = game_info.get("away_team", "Away")
        
        return {
            "type": "MATCHUP_CONTEXT",
            "content": f"{away_team} visiting {home_team} at {game_info.get('venue', 'the arena')}",
            "talking_points": [
                f"{away_team} looking to get points on the road",
                f"{home_team} wants to protect home ice",
                f"Playing at {game_info.get('venue', 'a great venue')}"
            ]
        }
        
    except Exception as e:
        return {
            "type": "GENERIC_FILLER",
            "content": "Continue game coverage",
            "talking_points": ["Discuss team performance and upcoming plays"]
        }