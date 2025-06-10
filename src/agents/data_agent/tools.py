# data_agent/tools.py

import json
import os
import glob
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

def load_static_context(game_id: str = "2024020001") -> Dict[str, Any]:
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
    except Exception as e:
        return {"error": f"Failed to load static context: {str(e)}"}

def load_timestamp_data(game_id: str, time_window_minutes: float = 2.0) -> Dict[str, Any]:
    """
    Loads recent timestamp data files within the specified time window.
    
    Args:
        game_id: The game identifier
        time_window_minutes: How far back to look for timestamp files
        
    Returns:
        Dictionary containing timestamp data and metadata
    """
    try:
        data_dir = f"data/live/{game_id}"
        if not os.path.exists(data_dir):
            return {"error": f"No data directory found for game {game_id}"}
        
        # Get all timestamp files
        pattern = f"{data_dir}/{game_id}_*.json"
        files = sorted(glob.glob(pattern))
        
        if not files:
            return {"error": f"No timestamp files found for game {game_id}"}
        
        # Load the most recent files within time window
        timestamps = []
        for file_path in files[-12:]:  # Last 12 files (1 minute at 5-second intervals)
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    timestamps.append({
                        "file_path": file_path,
                        "game_time": data.get("game_time", "unknown"),
                        "events": data.get("activities", []),
                        "game_context": data.get("game_context", {})
                    })
            except Exception as e:
                continue
        
        return {
            "timestamps": timestamps,
            "total_files_analyzed": len(timestamps),
            "time_span_covered": f"{len(timestamps) * 5} seconds"
        }
    except Exception as e:
        return {"error": f"Failed to load timestamp data: {str(e)}"}

def deduplicate_events(timestamps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Removes duplicate events across overlapping timestamp windows.
    
    Args:
        timestamps: List of timestamp data dictionaries
        
    Returns:
        Dictionary with deduplicated events and summary
    """
    seen_event_ids = set()
    unique_events = []
    total_events = 0
    
    for timestamp in timestamps:
        for event in timestamp.get("events", []):
            total_events += 1
            event_id = event.get("eventId")
            if event_id and event_id not in seen_event_ids:
                seen_event_ids.add(event_id)
                unique_events.append(event)
    
    return {
        "unique_events": unique_events,
        "deduplication_summary": f"Reduced {total_events} events to {len(unique_events)} unique events",
        "total_original": total_events,
        "total_unique": len(unique_events)
    }


def _convert_time_to_seconds(time_str: str) -> int:
    """Convert time string like '12:34' to seconds"""
    try:
        if ':' in time_str:
            minutes, seconds = map(int, time_str.split(':'))
            return minutes * 60 + seconds
        return int(time_str)
    except:
        return 1200  # Default to 20 minutes

def analyze_game_momentum(deduplicated_data: Dict[str, Any], game_context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Unified momentum analysis with contextual multipliers for broadcast decision making.
    
    Args:
        deduplicated_data: Output from deduplicate_events tool  
        game_context: Current game state (period, time, score, etc.)
        
    Returns:
        Dictionary with momentum analysis and broadcast recommendations
    """
    events = deduplicated_data.get("unique_events", [])
    
    if not events:
        return {
            "total_momentum_score": 0,
            "broadcast_recommendation": "FILLER_CONTENT", 
            "broadcast_focus": "Find interesting storylines or statistics",
            "high_intensity_events": [],
            "recent_activity_trend": [],
            "context_analysis": {}
        }
    
    if game_context is None:
        game_context = {}
    
    # Base momentum scores
    momentum_scores = {
        "goal": 50, "fight": 45, "penalty": 35, "shot-on-goal": 15,
        "hit": 10, "missed-shot": 8, "faceoff": 2
    }
    
    # Get contextual modifiers
    period = game_context.get('period', 1)
    time_remaining = game_context.get('time_remaining', '20:00')
    score_diff = abs(game_context.get('home_score', 0) - game_context.get('away_score', 0))
    period_type = game_context.get('periodType', 'REG')
    
    # Convert time to seconds for calculations
    time_remaining_seconds = _convert_time_to_seconds(time_remaining)
    
    total_momentum = 0
    high_intensity_events = []
    
    for event in events:
        event_type = event.get('typeDescKey', '')
        base_score = momentum_scores.get(event_type, 0)
        
        # Apply contextual multipliers
        contextual_score = base_score
        
        # Late-game importance multiplier
        if period >= 3 and time_remaining_seconds < 300:  # Last 5 minutes
            contextual_score *= 1.5
        
        # Overtime multiplier  
        if period_type == 'OT':
            contextual_score *= 2.5
        
        # Close game multiplier
        if score_diff <= 1:
            contextual_score *= 1.3
        
        # Special event bonuses
        if event_type == 'missed-shot' and event.get('details', {}).get('reason') == 'hit-crossbar':
            contextual_score += 15
        
        # Power play goal bonus
        if event_type == 'goal' and game_context.get('game_situation') == 'power_play':
            contextual_score += 25
        
        total_momentum += contextual_score
        
        # Add to high-intensity if significant
        if contextual_score >= 15:
            high_intensity_events.append({
                "type": event_type,
                "time": event.get('timeInPeriod', 'unknown'),
                "score": int(contextual_score),
                "details": event.get('details', {})
            })
    
    # Determine broadcast recommendation
    if total_momentum >= 75:
        recommendation = "PLAY_BY_PLAY"
        focus = "Focus on the action - high intensity period"
    elif total_momentum >= 25:
        recommendation = "MIXED_COVERAGE" 
        focus = "Balance action coverage with analysis"
    else:
        recommendation = "FILLER_CONTENT"
        focus = "Use statistics, player stories, or historical context"
    
    return {
        "total_momentum_score": int(total_momentum),
        "broadcast_recommendation": recommendation,
        "broadcast_focus": focus,
        "high_intensity_events": high_intensity_events,
        "recent_activity_trend": _calculate_activity_trend(events),
        "context_analysis": {
            "period": period,
            "time_remaining": time_remaining,
            "score_differential": score_diff,
            "high_pressure_situation": period >= 3 and time_remaining_seconds < 300,
            "overtime": period_type == 'OT'
        }
    }

def _calculate_activity_trend(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculate activity trend over time"""
    if not events:
        return []
    
    # Group events by time periods (simplified)
    time_buckets = {}
    for event in events:
        time_key = event.get('timeInPeriod', '0:00')[:4]  # First 4 chars like "12:3"
        if time_key not in time_buckets:
            time_buckets[time_key] = []
        time_buckets[time_key].append(event)
    
    trends = []
    for time_key, time_events in sorted(time_buckets.items()):
        event_count = len(time_events)
        activity_level = "high" if event_count >= 3 else "medium" if event_count >= 2 else "low"
        trends.append({
            "game_time": time_key,
            "event_count": event_count,
            "activity_level": activity_level
        })
    
    return trends

def find_interesting_filler_topic(analysis_result: Dict[str, Any], knowledge_base: Dict[str, Any]) -> Dict[str, Any]:
    """
    Finds interesting filler content when game action is low.
    
    Args:
        analysis_result: The analysis from analyze_events_with_context
        knowledge_base: Static context and knowledge base
        
    Returns:
        Dictionary with suggested filler topic and details
    """
    # Check for recent player achievements in analysis
    events = analysis_result.get("prioritized_events", [])
    for event_data in events:
        event = event_data.get("event", {})
        if event.get('typeDescKey') == 'goal':
            player_name = event.get('details', {}).get('player', 'Unknown')
            return {
                "type": "RECENT_GOAL_ANALYSIS",
                "details": {
                    "player_name": player_name,
                    "context": "Analyze the recent goal and player performance"
                }
            }
    
    # Check knowledge base for storylines
    storylines = knowledge_base.get("season_storylines", [])
    if storylines:
        return {
            "type": "SEASON_STORYLINE",
            "details": storylines[0] if storylines else {"story": "Team performance this season"}
        }
    
    # Check for recent milestones
    milestones = knowledge_base.get("recent_milestones", [])
    if milestones:
        return {
            "type": "PLAYER_MILESTONE",
            "details": milestones[0] if milestones else {"milestone": "Player achievement"}
        }
    
    # Fallback to team stats
    teams = knowledge_base.get("teams", {})
    home_team = teams.get("home", {}).get("name", "Home team")
    return {
        "type": "TEAM_STATISTICS",
        "details": {
            "focus_team": home_team,
            "context": "Discuss team performance and statistics"
        }
    }

def create_commentary_task(momentum_analysis: Dict[str, Any], knowledge_base: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Creates a structured commentary task based on momentum analysis and available context.

    Args:
        momentum_analysis: The output from analyze_game_momentum tool
        knowledge_base: Static context for enhanced filler content

    Returns:
        A structured JSON task for the Commentary Agent
    """
    if knowledge_base is None:
        knowledge_base = {}
        
    recommendation = momentum_analysis.get("broadcast_recommendation", "FILLER_CONTENT")
    momentum_score = momentum_analysis.get("total_momentum_score", 0)
    high_intensity_events = momentum_analysis.get("high_intensity_events", [])
    
    if recommendation == "PLAY_BY_PLAY" and high_intensity_events:
        top_event = high_intensity_events[0]
        return {
            "task_type": "PBP",
            "priority": 1,
            "key_event": {
                "type": top_event["type"],
                "time_in_period": top_event["time"],
                "details": top_event.get("details", {})
            },
            "talking_points": [
                f"Major {top_event['type']} at {top_event['time']} - focus on the action",
                f"High intensity period with momentum score of {momentum_score}",
                "Stay with play-by-play coverage for this exciting sequence"
            ],
            "context": f"High momentum period (score: {momentum_score}) - focus on action",
            "momentum_score": momentum_score
        }
    
    elif recommendation == "MIXED_COVERAGE":
        return {
            "task_type": "MIXED",
            "priority": 2,
            "focus": momentum_analysis.get("broadcast_focus", "Balance action with analysis"),
            "high_intensity_events": high_intensity_events[:3],
            "talking_points": [
                f"Moderate activity period with {len(high_intensity_events)} notable events",
                f"Momentum score of {momentum_score} suggests balanced coverage",
                "Mix play-by-play with analysis and context"
            ],
            "context": f"Moderate activity (score: {momentum_score}) - mix action with context",
            "momentum_score": momentum_score
        }
    
    else:
        # Low intensity - use enhanced filler logic
        filler_topic = find_interesting_filler_topic(momentum_analysis, knowledge_base)
        return {
            "task_type": "FILLER",
            "priority": 3,
            "topic_type": filler_topic["type"],
            "topic_details": filler_topic["details"],
            "talking_points": [
                f"Low activity period - perfect time for {filler_topic['type'].lower()}",
                f"Momentum score of {momentum_score} indicates quiet period",
                "Use this lull to provide context and background information"
            ],
            "context": f"Low activity period (score: {momentum_score}) - use filler content",
            "momentum_score": momentum_score,
            "suggested_direction": momentum_analysis.get("broadcast_focus", "Find interesting storylines")
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

def get_team_name_from_static(team_abbrev: str, static_context: Dict[str, Any]) -> str:
    """Get team name from static context"""
    try:
        game_info = static_context.get("game_info", {})
        if team_abbrev == game_info.get("home_team"):
            return game_info.get("home_team_name", team_abbrev)
        elif team_abbrev == game_info.get("away_team"):
            return game_info.get("away_team_name", team_abbrev)
        return team_abbrev
    except:
        return team_abbrev

def filter_new_events(events: List[Dict[str, Any]], processed_event_ids: set) -> tuple[List[Dict[str, Any]], set]:
    """
    STATEFUL FILTERING: Filter out events that have already been processed
    
    Args:
        events: List of events from current timestamp
        processed_event_ids: Set of event IDs already processed
        
    Returns:
        Tuple of (new_events, updated_processed_event_ids)
    """
    new_events = []
    for event in events:
        event_id = event.get("eventId")
        if event_id and event_id not in processed_event_ids:
            new_events.append(event)
            processed_event_ids.add(event_id)
    
    return new_events, processed_event_ids

def create_specific_filler_content(static_context: Dict[str, Any], game_situation: str = "normal") -> Dict[str, Any]:
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