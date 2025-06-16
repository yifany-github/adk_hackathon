#!/usr/bin/env python3
"""
Live Game Board - Authoritative source of truth for NHL game state
Prevents context collapse by maintaining factual game data outside of AI memory
"""

import json
from typing import Dict, List, Set, Any, Optional
from datetime import datetime


class LiveGameBoard:
    """
    Authoritative source of truth for live game state.
    This class maintains all factual game data outside of AI memory.
    """
    
    def __init__(self, game_id: str, static_context: Dict):
        # Game Identity
        self.game_id = game_id
        self.away_team = static_context.get("away_team", "AWAY")
        self.home_team = static_context.get("home_team", "HOME")
        
        # Game State (Authoritative)
        self.current_score = {"away": 0, "home": 0}
        self.current_shots = {"away": 0, "home": 0}
        self.period = 1
        self.time_remaining = "20:00"
        self.game_situation = "even strength"
        
        # Event Tracking
        self.goals = []  # List of goal events with scorer, time, assists
        self.penalties = []  # Active penalties with expiration times
        self.last_goal_scorer = None
        self.last_goal_team = None
        
        # Goalie Performance (Critical for preventing "perfect" paradox)
        self.goalies = {
            "away": {"name": static_context.get("away_goalie", "Unknown"), "goals_allowed": 0},
            "home": {"name": static_context.get("home_goalie", "Unknown"), "goals_allowed": 0}
        }
        
        # Roster Lock (ABSOLUTE CONSTRAINT)
        self.team_rosters = {
            "away": set(static_context.get("away_players", [])),
            "home": set(static_context.get("home_players", []))
        }
        
        # Context Management
        self.processed_events = set()  # Prevent duplicate processing
        self.narrative_summary = ""  # Compact version of game story
        self.last_update_time = None
    
    def update_from_timestamp(self, timestamp_data: Dict) -> Dict[str, Any]:
        """
        Update board state from timestamp data and return validation report.
        This method is the SINGLE SOURCE OF TRUTH for state updates.
        """
        update_report = {
            "timestamp": timestamp_data.get("game_time", "Unknown"),
            "events_processed": 0,
            "new_goals": [],
            "new_penalties": [],
            "state_changes": []
        }
        
        activities = timestamp_data.get("activities", [])
        
        for activity in activities:
            event_id = activity.get("eventId")
            
            # Skip already processed events
            if event_id in self.processed_events:
                continue
                
            self.processed_events.add(event_id)
            update_report["events_processed"] += 1
            
            # Update basic game info
            self._update_basic_game_info(activity, update_report)
            
            # Process specific event types
            event_type = activity.get("typeDescKey", "")
            
            if event_type == "goal":
                self._process_goal_event(activity, update_report)
            elif event_type == "penalty":
                self._process_penalty_event(activity, update_report)
            elif event_type == "shot-on-goal":
                self._update_shot_counts(activity, update_report)
        
        self.last_update_time = datetime.now().isoformat()
        return update_report
    
    def _update_basic_game_info(self, activity: Dict, report: Dict):
        """Update period, time, and game situation"""
        period_desc = activity.get("periodDescriptor", {})
        new_period = period_desc.get("number", self.period)
        
        if new_period != self.period:
            self.period = new_period
            report["state_changes"].append(f"Period changed to {new_period}")
        
        # Update time remaining
        time_remaining = activity.get("timeRemaining", self.time_remaining)
        if time_remaining != self.time_remaining:
            self.time_remaining = time_remaining
        
        # Update game situation
        game_situation = activity.get("gameSituation", self.game_situation)
        if game_situation != self.game_situation:
            self.game_situation = game_situation
            report["state_changes"].append(f"Game situation: {game_situation}")
    
    def _process_goal_event(self, activity: Dict, report: Dict):
        """Process goal events and update scores"""
        details = activity.get("details", {})
        
        # Determine scoring team based on event owner
        event_owner_team_id = details.get("eventOwnerTeamId")
        scoring_team = self._get_team_from_id(event_owner_team_id)
        
        if scoring_team:
            # Update score
            self.current_score[scoring_team] += 1
            
            # Update goalie stats (opponent's goalie allowed goal)
            opponent_side = "home" if scoring_team == "away" else "away"
            self.goalies[opponent_side]["goals_allowed"] += 1
            
            # Record goal details
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
            self.last_goal_scorer = goal_info["scorer"]
            self.last_goal_team = scoring_team
            
            report["new_goals"].append(goal_info)
            report["state_changes"].append(f"GOAL: {goal_info['scorer']} ({scoring_team.upper()})")
    
    def _process_penalty_event(self, activity: Dict, report: Dict):
        """Process penalty events"""
        details = activity.get("details", {})
        
        penalty_info = {
            "player": details.get("committedByPlayerName", "Unknown"),
            "time": activity.get("timeRemaining", "Unknown"),
            "period": self.period,
            "minutes": details.get("duration", 2)
        }
        
        self.penalties.append(penalty_info)
        report["new_penalties"].append(penalty_info)
        report["state_changes"].append(f"PENALTY: {penalty_info['player']}")
    
    def _update_shot_counts(self, activity: Dict, report: Dict):
        """Update shot on goal counts"""
        details = activity.get("details", {})
        
        # Get updated shot counts from the activity
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
    
    def validate_player(self, player_name: str, team: str) -> bool:
        """
        Validate if player exists on specified team roster.
        Returns False if player doesn't exist or is on wrong team.
        """
        if team not in ["away", "home"]:
            return False
        
        return player_name in self.team_rosters[team]
    
    def get_authoritative_state(self) -> Dict:
        """
        Return current game state for injection into AI prompts.
        This becomes the "GAME STATE (AUTHORITATIVE)" section of prompts.
        """
        return {
            "game_id": self.game_id,
            "away_team": self.away_team,
            "home_team": self.home_team,
            "score": self.current_score.copy(),
            "shots": self.current_shots.copy(),
            "period": self.period,
            "time_remaining": self.time_remaining,
            "game_situation": self.game_situation,
            "last_goal": {
                "scorer": self.last_goal_scorer,
                "team": self.last_goal_team
            } if self.last_goal_scorer else None,
            "goalies": {
                "away": self.goalies["away"].copy(),
                "home": self.goalies["home"].copy()
            },
            "rosters": {
                "away": list(self.team_rosters["away"]),
                "home": list(self.team_rosters["home"])
            },
            "active_penalties": self.penalties[-3:] if self.penalties else [],  # Last 3 penalties
            "recent_goals": self.goals[-3:] if self.goals else []  # Last 3 goals
        }
    
    def get_narrative_context(self) -> str:
        """
        Return compact narrative summary of game so far.
        Used for context injection after session refresh.
        IMPLEMENTATION: Start with deterministic template, upgrade to LLM later if needed.
        """
        summary = f"Game: {self.away_team} @ {self.home_team}. "
        
        if self.goals:
            recent_goals = self.goals[-3:]  # Last 3 goals only
            goal_summary = ", ".join([f"{g['scorer']} ({g['team'].upper()}) at {g['time']}" for g in recent_goals])
            summary += f"Recent goals: {goal_summary}. "
        
        summary += f"Current score: {self.away_team} {self.current_score['away']} - {self.home_team} {self.current_score['home']}. "
        summary += f"Shots: {self.away_team} {self.current_shots['away']} - {self.home_team} {self.current_shots['home']}. "
        summary += f"Period {self.period}, {self.time_remaining} remaining."
        
        return summary
    
    def get_prompt_injection(self) -> str:
        """
        Generate the authoritative state section for AI prompts.
        This prevents phantom players, score contradictions, and goalie paradoxes.
        """
        state = self.get_authoritative_state()
        
        prompt = f"""GAME STATE (AUTHORITATIVE - DO NOT CONTRADICT):
Score: {state['away_team']} {state['score']['away']} - {state['home_team']} {state['score']['home']}
Shots: {state['away_team']} {state['shots']['away']} - {state['home_team']} {state['shots']['home']}
Period: {state['period']}, Time: {state['time_remaining']}
Game Situation: {state['game_situation']}
Last Goal: {state['last_goal']['scorer'] + ' (' + state['last_goal']['team'].upper() + ')' if state['last_goal'] else 'None'}

GOALIE PERFORMANCE:
{state['goalies']['away']['name']} ({state['away_team']}): {state['goalies']['away']['goals_allowed']} goals allowed
{state['goalies']['home']['name']} ({state['home_team']}): {state['goalies']['home']['goals_allowed']} goals allowed

ROSTER LOCK (ONLY mention players from these lists):
{state['away_team']} Players: {', '.join(state['rosters']['away'][:10])}{'...' if len(state['rosters']['away']) > 10 else ''}
{state['home_team']} Players: {', '.join(state['rosters']['home'][:10])}{'...' if len(state['rosters']['home']) > 10 else ''}

CRITICAL RULES:
1. NEVER contradict the authoritative game state above
2. NEVER mention players not in the roster lock
3. NEVER claim a goalie is "perfect" if they have goals_allowed > 0
4. Build analysis on this factual foundation
"""
        return prompt
    
    def export_state(self) -> Dict:
        """Export complete board state for debugging/monitoring"""
        return {
            "game_id": self.game_id,
            "teams": {"away": self.away_team, "home": self.home_team},
            "score": self.current_score,
            "shots": self.current_shots,
            "period": self.period,
            "time_remaining": self.time_remaining,
            "game_situation": self.game_situation,
            "goals": self.goals,
            "penalties": self.penalties,
            "goalies": self.goalies,
            "processed_events_count": len(self.processed_events),
            "last_update": self.last_update_time,
            "narrative_summary": self.get_narrative_context()
        }


def create_live_game_board(game_id: str, static_context_file: str) -> LiveGameBoard:
    """
    Factory function to create LiveGameBoard from static context file.
    """
    with open(static_context_file, 'r') as f:
        static_context = json.load(f)
    
    # Extract team and player info from actual static context structure
    game_info = static_context.get("game_info", {})
    rosters = static_context.get("rosters", {})
    
    # Get team names
    away_team = game_info.get("away_team", "AWAY")
    home_team = game_info.get("home_team", "HOME")
    
    # Extract player names from rosters
    away_players = []
    home_players = []
    away_goalies = []
    home_goalies = []
    
    # Process away team roster
    for player in rosters.get("away_players", []):
        player_name = player.get("name", "Unknown")
        away_players.append(player_name)
        
        # Identify goalies
        if player.get("position") == "G":
            away_goalies.append(player_name)
    
    # Process home team roster  
    for player in rosters.get("home_players", []):
        player_name = player.get("name", "Unknown")
        home_players.append(player_name)
        
        # Identify goalies
        if player.get("position") == "G":
            home_goalies.append(player_name)
    
    # Select primary goalies (first goalie in list, or most common starter)
    away_goalie = away_goalies[0] if away_goalies else "Unknown"
    home_goalie = home_goalies[0] if home_goalies else "Unknown"
    
    processed_context = {
        "away_team": away_team,
        "home_team": home_team,
        "away_goalie": away_goalie,
        "home_goalie": home_goalie,
        "away_players": away_players,
        "home_players": home_players
    }
    
    return LiveGameBoard(game_id, processed_context)