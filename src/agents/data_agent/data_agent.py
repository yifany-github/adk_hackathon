from typing import List, Dict, Any, Optional, AsyncGenerator
import json
import os
import glob
from datetime import datetime

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
try:
    from .tools import (load_static_context, load_timestamp_data, deduplicate_events, 
                       analyze_game_momentum, create_commentary_task, 
                       find_interesting_filler_topic, filter_new_events, 
                       get_player_name_from_static, create_specific_filler_content)
except ImportError:
    # For standalone testing
    import sys
    sys.path.append(os.path.dirname(__file__))
    from tools import (load_static_context, load_timestamp_data, deduplicate_events, 
                      analyze_game_momentum, create_commentary_task, 
                      find_interesting_filler_topic, filter_new_events, 
                      get_player_name_from_static, create_specific_filler_content)


class DataAgent(BaseAgent):
    """Enhanced data agent that processes multiple timestamps for better broadcast decisions."""

    # pydantic field required by BaseAgent
    name: str = "data_agent"

    # --- CONFIG -------------------------------------------------------------
    event_weights: Dict[str, int] = {
        "goal": 10, "fight": 9, "shot-on-goal": 8, "penalty": 7,
        "hit": 5, "giveaway": 4, "takeaway": 4, "zone-entry": 2, "faceoff": 1,
    }
    lull_threshold: int = 10                            # can also be set via ctor
    time_window_minutes: float = 2.0                    # Time series analysis window
    # ------------------------------------------------------------------------

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use object.__setattr__ to bypass Pydantic validation for internal state
        object.__setattr__(self, '_recent_event_ids', set())
        object.__setattr__(self, '_knowledge_base', {})
        object.__setattr__(self, '_knowledge_base_loaded', False)
        object.__setattr__(self, '_used_filler_topics', [])  # Track recent filler topics

    # ---------- helper methods (unchanged) ----------------------------------
    def score_window(self, events: List[Dict]) -> int:
        return sum(self.event_weights.get(e.get("typeDescKey", ""), 0) for e in events)

    def prioritize_events(self, events: List[Dict]) -> List[Dict]:
        return sorted(events, key=lambda e: self.event_weights.get(e.get("typeDescKey", ""), 0), reverse=True)

    def detect_corrections(self, events: List[Dict]) -> List[Dict]:
        corrections = []
        for e in events:
            eid = e.get("eventId")
            if eid in self._recent_event_ids and e.get("isCorrection"):
                corrections.append(e)
            self._recent_event_ids.add(eid)
        return corrections

    def select_filler(self, gc: Dict[str, Any]) -> str:
        """Legacy filler selection - updated to work with actual data structure"""
        # Try to extract score from available data
        if gc.get("activities"):
            # Look for game stats in the most recent activity
            for activity in reversed(gc["activities"]):
                game_stats = activity.get("gameStats", {}).get("teamStats", {})
                if game_stats:
                    home_score = game_stats.get("home", {}).get("score", 0)
                    away_score = game_stats.get("away", {}).get("score", 0)
                    home_team = game_stats.get("home", {}).get("teamName", "HOME")
                    away_team = game_stats.get("away", {}).get("teamName", "AWAY")
                    return f"Score: {away_team} {away_score} - {home_team} {home_score}"
        
        # Fallback
        return "No major events – time for a quick stat."

    # -------------  ENHANCED CORE LOGIC  ------------------------------------
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Enhanced processing logic with stateful event tracking."""
        
        # Get game_id from context
        payload: Dict[str, Any] = ctx.user_content.to_dict() if ctx.user_content else {}
        game_id = payload.get("game_id") or getattr(ctx.session_state, "game_id", "2024020001")
        
        try:
            # Step 1: Load static context/knowledge base if not already loaded
            if not self._knowledge_base_loaded:
                self._knowledge_base = load_static_context(game_id)
                object.__setattr__(self, '_knowledge_base_loaded', True)
            
            # Step 2: Process single timestamp with stateful filtering
            out = self._process_live_timestamp(payload, game_id)
                
        except Exception as e:
            print(f"Live analysis failed: {e}, falling back to basic analysis")
            out = self._enhanced_fallback_analysis(payload, game_id)

        # Save output for commentary agent
        self._save_output_for_commentary_agent(out, game_id)
        
        # Yield a single final Event that stores the result in session state
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"broadcast": out})
        )
    
    def _process_live_timestamp(self, payload: Dict[str, Any], game_id: str) -> Dict[str, Any]:
        """Process a single timestamp with stateful event tracking"""
        all_events = payload.get("activities", [])
        game_time = payload.get("game_time", "unknown")
        
        # STATEFUL FILTERING: Only process NEW events
        new_events, self._recent_event_ids = filter_new_events(all_events, self._recent_event_ids)
        
        # Extract game context from all events (not just new ones)
        game_context = self._extract_game_context_from_events(all_events)
        
        # Create unified momentum analysis from new events with context
        single_timestamp_momentum = {
            "unique_events": new_events,
            "deduplication_summary": f"Stateful filtering: {len(new_events)} new events from {len(all_events)} total",
            "total_original": len(all_events),
            "total_unique": len(new_events)
        }
        
        momentum_analysis = analyze_game_momentum(single_timestamp_momentum, game_context)
        
        # Enhanced commentary task based on whether we have new events
        if len(new_events) == 0:
            # No new events - provide varied filler content using static data
            game_situation = "power_play" if game_context.get("game_situation") == "power_play" else "normal"
            filler_content = self._get_varied_filler_content(game_situation)
            commentary_task = {
                "task_type": "CONTEXT_UPDATE",
                "priority": 3,
                "content_type": filler_content["type"],
                "content": filler_content["content"],
                "talking_points": filler_content["talking_points"],
                "context": f"No new events - continue coverage with {filler_content['type'].lower()}"
            }
        else:
            # New events - create normal commentary task
            commentary_task = create_commentary_task(momentum_analysis, self._knowledge_base)
            
            # Enhance with human-readable names from static data
            if commentary_task.get("key_event", {}).get("details"):
                details = commentary_task["key_event"]["details"]
                
                # Add readable player names using static context
                if "scoringPlayerId" in details:
                    details["scoringPlayerName"] = get_player_name_from_static(details["scoringPlayerId"], self._knowledge_base)
                if "shootingPlayerId" in details:
                    details["shootingPlayerName"] = get_player_name_from_static(details["shootingPlayerId"], self._knowledge_base)
                if "committedByPlayerId" in details:
                    details["committedByPlayerName"] = get_player_name_from_static(details["committedByPlayerId"], self._knowledge_base)
                if "drawnByPlayerId" in details:
                    details["drawnByPlayerName"] = get_player_name_from_static(details["drawnByPlayerId"], self._knowledge_base)
        
        return {
            "type": "live_timestamp_analysis",
            "game_id": game_id,
            "game_time": game_time,
            "momentum_score": momentum_analysis["total_momentum_score"],
            "recommendation": momentum_analysis["broadcast_recommendation"], 
            "focus": momentum_analysis["broadcast_focus"],
            "high_intensity_events": momentum_analysis["high_intensity_events"],
            "commentary_task": commentary_task,
            "events_processed": len(new_events),
            "new_events_found": len(new_events),
            "total_events_in_timestamp": len(all_events),
            "stateful_filtering": True,
            "game_context": game_context,
            "context_analysis": momentum_analysis["context_analysis"]
        }
    
    def _extract_game_context_from_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract current game context from events"""
        if not events:
            return {
                "period": 1,
                "time_remaining": "20:00",
                "home_score": 0,
                "away_score": 0,
                "game_situation": "even_strength",
                "periodType": "REG"
            }
        
        # Use the most recent event for current context
        latest_event = events[-1]
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
    
    def _enhanced_fallback_analysis(self, payload: Dict[str, Any], game_id: str) -> Dict[str, Any]:
        """Enhanced fallback analysis using new tools"""
        events = payload.get("activities", [])
        game_ctx = payload.get("game_context", {})
        
        # Load knowledge base if needed
        if not self._knowledge_base_loaded:
            self._knowledge_base = load_static_context(game_id)
            object.__setattr__(self, '_knowledge_base_loaded', True)

        if (corr := self.detect_corrections(events)):
            return {"type": "correction", "corrections": corr}
        else:
            # Use unified momentum analysis 
            momentum_data = {
                "unique_events": events,
                "deduplication_summary": f"Fallback analysis: {len(events)} events",
                "total_original": len(events),
                "total_unique": len(events)
            }
            momentum_analysis = analyze_game_momentum(momentum_data, game_ctx)
            
            if momentum_analysis["total_momentum_score"] >= self.lull_threshold:
                # Create action-focused task
                task = create_commentary_task(momentum_analysis, self._knowledge_base)
                return {
                    "type": "fallback_action", 
                    "momentum_score": momentum_analysis["total_momentum_score"],
                    "events": momentum_analysis["high_intensity_events"],
                    "commentary_task": task,
                    "context_analysis": momentum_analysis["context_analysis"]
                }
            else:
                # Use enhanced filler logic
                filler_topic = find_interesting_filler_topic(momentum_analysis, self._knowledge_base)
                return {
                    "type": "enhanced_filler", 
                    "momentum_score": momentum_analysis["total_momentum_score"],
                    "filler_topic": filler_topic,
                    "context_analysis": momentum_analysis["context_analysis"]
                }
    
    def _extract_game_context(self, timestamps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract current game context from timestamp data"""
        if not timestamps:
            return {}
        
        # Use the most recent timestamp for current context
        latest = timestamps[-1]
        
        # Extract context from the actual data structure
        latest_events = latest.get("events", [])
        if latest_events:
            latest_event = latest_events[-1]
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
        
        # Fallback if no events
        return {
            "period": 1,
            "time_remaining": "20:00",
            "home_score": 0,
            "away_score": 0,
            "game_situation": "even_strength",
            "periodType": "REG"
        }
    
    def _save_output_for_commentary_agent(self, analysis_output: Dict[str, Any], game_id: str):
        """Save data agent output for the commentary agent to consume"""
        try:
            # Create output directory
            output_dir = "data/data_agent_outputs"
            os.makedirs(output_dir, exist_ok=True)
            
            # Get game_time from analysis_output or fallback
            game_time = None
            # Try to extract from analysis_output or its subfields
            if "game_time" in analysis_output:
                game_time = analysis_output["game_time"]
            elif "input_summary" in analysis_output and "game_time" in analysis_output["input_summary"]:
                game_time = analysis_output["input_summary"]["game_time"]
            elif "timestamps" in analysis_output and analysis_output["timestamps"]:
                # Try to get from first timestamp if available
                first = analysis_output["timestamps"][0]
                game_time = first.get("game_time")
            # Fallback to UTC time if not found
            if not game_time:
                game_time = datetime.utcnow().strftime("%H_%M_%S")
            # Clean up game_time for filename (replace : with _)
            game_time_clean = str(game_time).replace(":", "_").replace(" ", "_")
            filename = f"{game_id}_{game_time_clean}_data_agent.json"
            filepath = os.path.join(output_dir, filename)
            
            # Create clean API contract for commentary agent
            output_for_commentary = {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "data_agent_version": "enhanced_v3.0",
                "game_id": game_id,
                "game_time": game_time,
                "knowledge_base_status": "loaded" if self._knowledge_base_loaded else "not_loaded",
                
                # CLEAN API CONTRACT FOR COMMENTARY AGENT
                "for_commentary_agent": {
                    "recommendation": analysis_output.get("recommendation", "FILLER_CONTENT"),
                    "priority_level": self._get_priority_level(analysis_output),
                    "momentum_score": analysis_output.get("momentum_score", 0),
                    "key_talking_points": self._extract_talking_points(analysis_output),
                    "context": analysis_output.get("focus", "General commentary"),
                    "game_context": analysis_output.get("game_context", {}),
                    "high_intensity_events": self._contextualize_events(analysis_output.get("high_intensity_events", []), analysis_output.get("game_context", {})),
                    "task_details": self._create_clean_task_details(analysis_output)
                },
                
                # DEBUG INFO (optional, can be ignored by commentary agent)
                "debug": {
                    "events_processed": analysis_output.get("events_processed", 0),
                    "total_events_in_timestamp": analysis_output.get("total_events_in_timestamp", 0),
                    "stateful_filtering": analysis_output.get("stateful_filtering", False),
                    "context_analysis": analysis_output.get("context_analysis", {})
                }
            }
            
            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output_for_commentary, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Data agent output saved: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ Error saving data agent output: {e}")
            return None
    
    def _get_priority_level(self, analysis_output: Dict[str, Any]) -> int:
        """Determine priority level for commentary agent (1=highest, 3=lowest)"""
        recommendation = analysis_output.get("recommendation", "FILLER_CONTENT")
        momentum_score = analysis_output.get("momentum_score", 0)
        
        if recommendation == "PLAY_BY_PLAY" or momentum_score >= 75:
            return 1  # High priority - immediate action needed
        elif recommendation == "MIXED_COVERAGE" or momentum_score >= 25:
            return 2  # Medium priority - moderate coverage
        else:
            return 3  # Low priority - filler content
    
    def _extract_talking_points(self, analysis_output: Dict[str, Any]) -> List[str]:
        """Extract key talking points for the commentary agent with rich narrative details"""
        talking_points = []
        game_context = analysis_output.get("game_context", {})
        
        # High-intensity events with broadcast-ready narratives
        high_intensity = analysis_output.get("high_intensity_events", [])
        for event in high_intensity[:3]:  # Top 3 events
            narrative = self._create_event_narrative(event, game_context)
            if narrative:
                talking_points.append(narrative)
        
        # Activity trends
        trends = analysis_output.get("activity_trend", [])
        if trends:
            recent_trend = trends[-1] if trends else {}
            if recent_trend.get("activity_level") == "high":
                talking_points.append("Recent high activity period - exciting hockey")
            elif recent_trend.get("activity_level") == "low":
                talking_points.append("Quiet period - good time for analysis or stats")
        
        # Momentum insights
        momentum = analysis_output.get("momentum_score", 0)
        if momentum >= 75:
            talking_points.append("High game momentum - keep focus on action")
        elif momentum < 25:
            talking_points.append("Low momentum - opportunity for background stories")
        
        return talking_points if talking_points else ["General game commentary"]
    
    def _create_event_narrative(self, event: Dict[str, Any], game_context: Dict[str, Any]) -> str:
        """Create broadcast-ready narrative for an event"""
        event_type = event.get('type', 'unknown')
        event_time = event.get('time', 'unknown')
        details = event.get('details', {})
        
        # Get team context
        home_team = self._knowledge_base.get("game_info", {}).get("home_team", "HOME")
        away_team = self._knowledge_base.get("game_info", {}).get("away_team", "AWAY")
        period = game_context.get("period", 1)
        time_remaining = game_context.get("time_remaining", "20:00")
        
        # Determine which team committed the event
        event_owner_team_id = details.get('eventOwnerTeamId')
        committing_team = self._get_team_from_id(event_owner_team_id)
        
        if event_type == "penalty":
            committer_name = get_player_name_from_static(details.get('committedByPlayerId'), self._knowledge_base)
            drawn_by_name = get_player_name_from_static(details.get('drawnByPlayerId'), self._knowledge_base)
            penalty_type = details.get('descKey', 'penalty').replace('-', ' ')
            duration = details.get('duration', 2)
            
            # Determine which team gets the power play (opposite of committing team)
            if committing_team == home_team:
                pp_team = away_team
            elif committing_team == away_team:
                pp_team = home_team
            else:
                pp_team = "the opposing team"
            
            return f"Penalty on {committing_team}'s {committer_name} for {penalty_type} against {drawn_by_name}. {pp_team} goes to the power play for {duration} minutes at {time_remaining} remaining in the {self._ordinal(period)}."
            
        elif event_type == "goal":
            scorer_name = get_player_name_from_static(details.get('scoringPlayerId'), self._knowledge_base)
            shot_type = details.get('shotType', 'shot')
            return f"GOAL! {scorer_name} scores with a {shot_type} at {event_time}. {committing_team} celebrates at {time_remaining} remaining in the {self._ordinal(period)}."
            
        elif event_type == "shot-on-goal":
            shooter_name = get_player_name_from_static(details.get('shootingPlayerId'), self._knowledge_base)
            shot_type = details.get('shotType', 'shot')
            return f"Quality scoring chance: {shooter_name} with a {shot_type} on goal at {event_time}."
            
        elif event_type == "hit":
            hitter_name = get_player_name_from_static(details.get('hittingPlayerId'), self._knowledge_base)
            hit_target_name = get_player_name_from_static(details.get('hitteePlayerId'), self._knowledge_base)
            location = details.get('spatialDescription', 'along the boards')
            return f"Big hit: {committing_team}'s {hitter_name} levels {hit_target_name} {location} at {event_time}."
            
        elif event_type == "fight":
            fighter1_name = get_player_name_from_static(details.get('fighter1PlayerId'), self._knowledge_base)
            fighter2_name = get_player_name_from_static(details.get('fighter2PlayerId'), self._knowledge_base)
            return f"Fight breaks out! {fighter1_name} and {fighter2_name} drop the gloves at {event_time}."
            
        else:
            # Fallback for other event types
            return f"{event_type.title().replace('-', ' ')} at {event_time}"
    
    def _get_team_from_id(self, team_id: int) -> str:
        """Map team ID to team abbreviation"""
        # In NHL data, team IDs are mapped to specific teams
        # For this implementation, we'll use a simple heuristic based on the game
        game_info = self._knowledge_base.get("game_info", {})
        home_team = game_info.get("home_team", "HOME")
        away_team = game_info.get("away_team", "AWAY")
        
        # This is a simplified mapping - in production you'd have a full team ID lookup
        if team_id == 22:  # Common ID pattern, Edmonton
            return home_team
        else:
            return away_team
    
    def _ordinal(self, n: int) -> str:
        """Convert number to ordinal (1st, 2nd, 3rd)"""
        if 10 <= n % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return f"{n}{suffix}"
    
    def _get_varied_filler_content(self, game_situation: str = "normal") -> Dict[str, Any]:
        """Get varied filler content avoiding recent repetition"""
        # Define filler topic hierarchy
        filler_options = [
            "TEAM_RECORD", "PLAYER_PERFORMANCE", "MATCHUP_CONTEXT", 
            "GOALIE_STATS", "POWER_PLAY_STATS", "RECENT_PERFORMANCE",
            "SEASON_STORYLINE", "HISTORICAL_MATCHUP"
        ]
        
        # Remove recently used topics (keep last 3)
        available_options = [opt for opt in filler_options if opt not in self._used_filler_topics[-3:]]
        
        # If we've used all topics recently, reset and use all options
        if not available_options:
            available_options = filler_options
            object.__setattr__(self, '_used_filler_topics', [])
        
        # Try each available option until we find one with data
        for topic_type in available_options:
            filler_content = self._create_specific_filler_by_type(topic_type, game_situation)
            if filler_content and filler_content.get("content"):
                # Track this topic as used
                self._used_filler_topics.append(topic_type)
                # Keep only last 5 used topics
                if len(self._used_filler_topics) > 5:
                    object.__setattr__(self, '_used_filler_topics', self._used_filler_topics[-5:])
                return filler_content
        
        # Fallback if nothing works
        return {
            "type": "GENERAL_FILLER",
            "content": "Continue game coverage with analysis",
            "talking_points": ["Discuss team performance and upcoming plays"]
        }
    
    def _create_specific_filler_by_type(self, topic_type: str, game_situation: str) -> Dict[str, Any]:
        """Create specific filler content by type"""
        try:
            if topic_type == "TEAM_RECORD":
                return self._get_team_record_filler()
            elif topic_type == "PLAYER_PERFORMANCE":
                return self._get_player_performance_filler()
            elif topic_type == "MATCHUP_CONTEXT":
                return self._get_matchup_context_filler()
            elif topic_type == "GOALIE_STATS":
                return self._get_goalie_stats_filler()
            elif topic_type == "POWER_PLAY_STATS":
                return self._get_power_play_stats_filler()
            elif topic_type == "RECENT_PERFORMANCE":
                return self._get_recent_performance_filler()
            else:
                return create_specific_filler_content(self._knowledge_base, game_situation)
        except:
            return None
    
    def _get_team_record_filler(self) -> Dict[str, Any]:
        """Get team record filler content"""
        standings = self._knowledge_base.get("standings", {}).get("standings", [])
        if standings:
            team_stats = standings[0]
            wins = team_stats.get("wins", 0)
            losses = team_stats.get("losses", 0)
            goals_for = team_stats.get("goalFor", 0)
            goals_against = team_stats.get("goalAgainst", 0)
            
            return {
                "type": "TEAM_RECORD",
                "content": f"Team record: {wins}-{losses}, {goals_for} goals for, {goals_against} against",
                "talking_points": [
                    f"Strong season with {wins} wins and {losses} losses",
                    f"Averaging {goals_for/82:.1f} goals per game" if wins > 0 else "Working to improve offensive production",
                    f"Goal differential of {goals_for - goals_against}"
                ]
            }
        return None
    
    def _get_player_performance_filler(self) -> Dict[str, Any]:
        """Get player performance filler content"""
        players = self._knowledge_base.get("rosters", {}).get("home_players", [])
        if players:
            # Find player with best stats
            best_player = None
            best_points = 0
            for player in players[:10]:  # Check first 10 players
                nhl_data = player.get("nhl_data", {})
                goals = nhl_data.get("goals", 0)
                assists = nhl_data.get("assists", 0)
                points = goals + assists
                if points > best_points:
                    best_points = points
                    best_player = player
            
            if best_player and best_points > 0:
                name = best_player.get("name", "Player")
                nhl_data = best_player.get("nhl_data", {})
                goals = nhl_data.get("goals", 0)
                assists = nhl_data.get("assists", 0)
                position = best_player.get("position", "")
                
                return {
                    "type": "PLAYER_PERFORMANCE",
                    "content": f"{name} leads with {goals} goals and {assists} assists this season",
                    "talking_points": [
                        f"{name} has been a key contributor with {best_points} points",
                        f"The {position} has {goals} goals and {assists} assists",
                        f"Consistent performance from {name} this season"
                    ]
                }
        return None
    
    def _get_matchup_context_filler(self) -> Dict[str, Any]:
        """Get matchup context filler content"""
        game_info = self._knowledge_base.get("game_info", {})
        home_team = game_info.get("home_team", "Home")
        away_team = game_info.get("away_team", "Away")
        venue = game_info.get("venue", "the arena")
        
        return {
            "type": "MATCHUP_CONTEXT",
            "content": f"{away_team} visiting {home_team} at {venue}",
            "talking_points": [
                f"{away_team} looking to earn valuable points on the road",
                f"{home_team} wants to protect their home ice advantage",
                f"Great atmosphere tonight at {venue}"
            ]
        }
    
    def _get_goalie_stats_filler(self) -> Dict[str, Any]:
        """Get goalie statistics filler content"""
        # This would ideally pull goalie stats from the knowledge base
        return {
            "type": "GOALIE_STATS",
            "content": "Goaltending has been a key factor in tonight's game",
            "talking_points": [
                "Both goalies showing sharp reflexes tonight",
                "Key saves keeping the game close",
                "Goaltending depth important for playoff push"
            ]
        }
    
    def _get_power_play_stats_filler(self) -> Dict[str, Any]:
        """Get power play statistics filler content"""
        return {
            "type": "POWER_PLAY_STATS", 
            "content": "Special teams play will be crucial tonight",
            "talking_points": [
                "Power play opportunities can change momentum",
                "Penalty kill units working hard",
                "Special teams often decide close games"
            ]
        }
    
    def _get_recent_performance_filler(self) -> Dict[str, Any]:
        """Get recent team performance filler content"""
        standings = self._knowledge_base.get("standings", {}).get("standings", [])
        if standings:
            team_stats = standings[0]
            wins = team_stats.get("wins", 0)
            games_played = team_stats.get("gamesPlayed", 82)
            
            return {
                "type": "RECENT_PERFORMANCE",
                "content": f"Team has {wins} wins in {games_played} games this season",
                "talking_points": [
                    f"Solid performance with {wins} wins so far",
                    f"Team consistency over {games_played} games",
                    "Building momentum for the stretch run"
                ]
            }
        return None
    
    def _contextualize_events(self, events: List[Dict[str, Any]], game_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Add human-readable summaries to high-intensity events"""
        contextualized_events = []
        
        for event in events:
            # Create human-readable summary using existing narrative logic
            summary = self._create_event_narrative(event, game_context)
            
            contextualized_event = {
                "summary": summary,
                "impact_score": event.get("score", 0),
                "event_type": event.get("type", "unknown"),
                "time": event.get("time", "unknown"),
                "raw_details": event.get("details", {})
            }
            
            contextualized_events.append(contextualized_event)
        
        return contextualized_events
    
    def _create_clean_task_details(self, analysis_output: Dict[str, Any]) -> Dict[str, Any]:
        """Create clean task details without duplication"""
        commentary_task = analysis_output.get("commentary_task", {})
        task_type = commentary_task.get("task_type", "FILLER")
        
        # Create minimal task details without duplicating data already in parent
        clean_details = {
            "task_type": task_type,
            "priority": commentary_task.get("priority", 3)
        }
        
        # Add task-specific details without duplication
        if task_type == "FILLER":
            clean_details.update({
                "topic_type": commentary_task.get("topic_type", "GENERAL"),
                "suggested_direction": commentary_task.get("suggested_direction", "Use filler content")
            })
        elif task_type == "CONTEXT_UPDATE":
            clean_details.update({
                "content_type": commentary_task.get("content_type", "TEAM_RECORD"),
                "content": commentary_task.get("content", "")
            })
        elif task_type in ["PBP", "MIXED"]:
            # For action tasks, just reference that events are available in high_intensity_events
            clean_details.update({
                "focus": commentary_task.get("focus", "Action coverage"),
                "event_count": len(analysis_output.get("high_intensity_events", []))
            })
        
        return clean_details

# ---------------------------------------------------------------------------
# Note: For testing, use the standalone test_data_agent.py script instead
# This avoids duplication and provides better testing capabilities