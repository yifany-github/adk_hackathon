#!/usr/bin/env python3
"""
Live Game Board - Pure dynamic state tracker for NHL games
Tracks only live game state, references static context when needed for validation
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime


class LiveGameBoard:
    """
    Pure dynamic state tracker for live NHL games.
    Stores only changing game state, not static context.
    """
    
    def __init__(self, game_id: str):
        # Game Identity
        self.game_id = game_id
        
        # Core Game State (Dynamic Only)
        self.current_score = {"away": 0, "home": 0}
        self.current_shots = {"away": 0, "home": 0}
        self.period = 1
        self.time_remaining = "20:00"
        self.game_situation = "even_strength"
        
        # Event History (for anti-hallucination)
        self.goals = []  # [{scorer, team, time, assists}]
        self.penalties = []  # [{player, team, time, minutes}]
        
        # Simple Performance Tracking
        self.goalie_stats = {
            "away": {"goals_allowed": 0},
            "home": {"goals_allowed": 0}
        }
        
        # Technical Tracking
        self.processed_events = set()  # Prevent duplicate processing
        self.last_update_time = None
    
    def update_from_timestamp(self, timestamp_data: Dict) -> Dict[str, Any]:
        """
        Update board state from timestamp data.
        Pure state tracking - no interpretation.
        """
        update_report = {
            "timestamp": timestamp_data.get("game_time", "Unknown"),
            "events_processed": 0,
            "new_goals": [],
            "new_penalties": []
        }
        
        activities = timestamp_data.get("activities", [])
        
        for activity in activities:
            event_id = activity.get("eventId")
            
            # Skip already processed events
            if event_id in self.processed_events:
                continue
                
            self.processed_events.add(event_id)
            update_report["events_processed"] += 1
            
            # Update basic game state
            self._update_game_state(activity)
            
            # Process events
            event_type = activity.get("typeDescKey", "")
            
            if event_type == "goal":
                goal_info = self._track_goal(activity)
                if goal_info:
                    update_report["new_goals"].append(goal_info)
            elif event_type == "penalty":
                penalty_info = self._track_penalty(activity)
                if penalty_info:
                    update_report["new_penalties"].append(penalty_info)
            elif event_type == "shot-on-goal":
                self._update_shot_counts(activity)
        
        self.last_update_time = datetime.now().isoformat()
        return update_report
    
    def _update_game_state(self, activity: Dict):
        """Update basic game state (period, time, situation)"""
        period_desc = activity.get("periodDescriptor", {})
        new_period = period_desc.get("number", self.period)
        if new_period != self.period:
            self.period = new_period
        
        # Update time and situation
        self.time_remaining = activity.get("timeRemaining", self.time_remaining)
        self.game_situation = activity.get("gameSituation", self.game_situation)
    
    def _track_goal(self, activity: Dict) -> Optional[Dict]:
        """Track goal event - pure state tracking"""
        details = activity.get("details", {})
        
        # Determine scoring team
        event_owner_team_id = details.get("eventOwnerTeamId")
        scoring_team = self._get_team_from_id(event_owner_team_id)
        
        if scoring_team:
            # Update score
            self.current_score[scoring_team] += 1
            
            # Update goalie stats
            opponent_side = "home" if scoring_team == "away" else "away"
            self.goalie_stats[opponent_side]["goals_allowed"] += 1
            
            # Record goal
            goal_info = {
                "scorer": details.get("scoringPlayerName", "Unknown"),
                "team": scoring_team,
                "time": activity.get("timeRemaining", "Unknown"),
                "period": self.period,
                "assists": []
            }
            
            # Add assists
            if details.get("assist1PlayerName"):
                goal_info["assists"].append(details.get("assist1PlayerName"))
            if details.get("assist2PlayerName"):
                goal_info["assists"].append(details.get("assist2PlayerName"))
            
            self.goals.append(goal_info)
            return goal_info
        
        return None
    
    def _track_penalty(self, activity: Dict) -> Dict:
        """Track penalty event - pure state tracking"""
        details = activity.get("details", {})
        
        penalty_info = {
            "player": details.get("committedByPlayerName", "Unknown"),
            "team": self._get_team_from_id(details.get("eventOwnerTeamId", 0)),
            "time": activity.get("timeRemaining", "Unknown"),
            "period": self.period,
            "minutes": details.get("duration", 2),
            "infraction": details.get("typeDescKey", "Unknown")
        }
        
        self.penalties.append(penalty_info)
        return penalty_info
    
    def _update_shot_counts(self, activity: Dict):
        """Update shot on goal counts"""
        details = activity.get("details", {})
        
        # Get updated shot counts
        away_shots = details.get("awaySOG", self.current_shots["away"])
        home_shots = details.get("homeSOG", self.current_shots["home"])
        
        # Only update if shots increased (prevent regression)
        if away_shots > self.current_shots["away"]:
            self.current_shots["away"] = away_shots
        if home_shots > self.current_shots["home"]:
            self.current_shots["home"] = home_shots
    
    def _get_team_from_id(self, team_id: int) -> Optional[str]:
        """Map team ID to home/away designation"""
        # This would need to be enhanced with actual team ID mapping
        # For now, use a simple heuristic based on common team IDs
        # In a real implementation, this would reference the static context
        return "home" if team_id and team_id % 2 == 1 else "away"
    
    def get_state(self) -> Dict:
        """Return current dynamic game state"""
        return {
            "game_id": self.game_id,
            "score": self.current_score.copy(),
            "shots": self.current_shots.copy(),
            "period": self.period,
            "time_remaining": self.time_remaining,
            "game_situation": self.game_situation,
            "goals": self.goals.copy(),
            "penalties": self.penalties.copy(),
            "goalie_stats": self.goalie_stats.copy(),
            "last_update": self.last_update_time
        }
    
    def to_session_state(self) -> Dict:
        """Export for session.state storage"""
        return self.get_state()
    
    @classmethod
    def from_session_state(cls, game_id: str, state_data: Dict):
        """Restore board from session.state"""
        board = cls(game_id)
        board.current_score = state_data.get("score", {"away": 0, "home": 0})
        board.current_shots = state_data.get("shots", {"away": 0, "home": 0})
        board.period = state_data.get("period", 1)
        board.time_remaining = state_data.get("time_remaining", "20:00")
        board.game_situation = state_data.get("game_situation", "even_strength")
        board.goals = state_data.get("goals", [])
        board.penalties = state_data.get("penalties", [])
        board.goalie_stats = state_data.get("goalie_stats", {"away": {"goals_allowed": 0}, "home": {"goals_allowed": 0}})
        board.last_update_time = state_data.get("last_update")
        return board


def create_live_game_board(game_id: str) -> LiveGameBoard:
    """
    Factory function to create clean LiveGameBoard.
    Static context should be handled separately in ADK memory.
    """
    return LiveGameBoard(game_id)