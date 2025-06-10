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
                       analyze_events_with_context, analyze_game_momentum, 
                       create_commentary_task, find_interesting_filler_topic,
                       filter_new_events, get_player_name_from_static, 
                       create_specific_filler_content)
except ImportError:
    # For standalone testing
    import sys
    sys.path.append(os.path.dirname(__file__))
    from tools import (load_static_context, load_timestamp_data, deduplicate_events, 
                      analyze_events_with_context, analyze_game_momentum, 
                      create_commentary_task, find_interesting_filler_topic,
                      filter_new_events, get_player_name_from_static,
                      create_specific_filler_content)


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
        
        # Analyze only new events
        event_analysis = analyze_events_with_context(new_events, self._knowledge_base, game_context)
        
        # Create momentum analysis from new events
        single_timestamp_momentum = {
            "unique_events": new_events,
            "deduplication_summary": f"Stateful filtering: {len(new_events)} new events from {len(all_events)} total",
            "total_original": len(all_events),
            "total_unique": len(new_events)
        }
        
        momentum_analysis = analyze_game_momentum(single_timestamp_momentum)
        
        # Enhanced commentary task based on whether we have new events
        if len(new_events) == 0:
            # No new events - provide specific filler content using static data
            game_situation = "power_play" if game_context.get("game_situation") == "power_play" else "normal"
            filler_content = create_specific_filler_content(self._knowledge_base, game_situation)
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
            "narrative_score": event_analysis["narrative_score"],
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
            "context_analysis": event_analysis["context_analysis"]
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
            # Use enhanced event analysis
            event_analysis = analyze_events_with_context(events, self._knowledge_base, game_ctx)
            
            if event_analysis["narrative_score"] >= self.lull_threshold:
                # Create action-focused task
                mock_momentum = {
                    "total_momentum_score": event_analysis["narrative_score"],
                    "broadcast_recommendation": "PLAY_BY_PLAY",
                    "broadcast_focus": "Focus on recent action",
                    "high_intensity_events": [{
                        "type": event["event"].get("typeDescKey", "unknown"),
                        "time": event["event"].get("timeInPeriod", "unknown"),
                        "score": event["contextual_score"]
                    } for event in event_analysis["prioritized_events"][:3]],
                    "recent_activity_trend": []
                }
                task = create_commentary_task(mock_momentum, self._knowledge_base)
                return {
                    "type": "fallback_action", 
                    "narrative_score": event_analysis["narrative_score"],
                    "events": event_analysis["prioritized_events"],
                    "commentary_task": task
                }
            else:
                # Use enhanced filler logic
                filler_topic = find_interesting_filler_topic(event_analysis, self._knowledge_base)
                return {
                    "type": "enhanced_filler", 
                    "narrative_score": event_analysis["narrative_score"],
                    "filler_topic": filler_topic,
                    "context_analysis": event_analysis["context_analysis"]
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
            
            # Add metadata for commentary agent
            output_for_commentary = {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "data_agent_version": "enhanced_v2.0",
                "game_id": game_id,
                "game_time": game_time,
                "analysis": analysis_output,
                "knowledge_base_status": "loaded" if self._knowledge_base_loaded else "not_loaded",
                "for_commentary_agent": {
                    "should_focus_on": analysis_output.get("recommendation", "FILLER_CONTENT"),
                    "priority_level": self._get_priority_level(analysis_output),
                    "key_talking_points": self._extract_talking_points(analysis_output),
                    "context_for_commentator": analysis_output.get("focus", "General commentary"),
                    "commentary_task": analysis_output.get("commentary_task", {})
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
        """Extract key talking points for the commentary agent with player details"""
        talking_points = []
        
        # High-intensity events with rich details
        high_intensity = analysis_output.get("high_intensity_events", [])
        for event in high_intensity[:3]:  # Top 3 events
            event_type = event.get('type', 'unknown')
            event_time = event.get('time', 'unknown')
            details = event.get('details', {})
            
            # Create human-readable event descriptions
            if event_type == "penalty":
                player_name = get_player_name_from_static(details.get('committedByPlayerId'), self._knowledge_base)
                penalty_type = details.get('descKey', 'penalty')
                duration = details.get('duration', 2)
                talking_points.append(f"Penalty: {player_name} {penalty_type} at {event_time} ({duration} min)")
                
            elif event_type == "goal":
                scorer_name = get_player_name_from_static(details.get('scoringPlayerId'), self._knowledge_base)
                shot_type = details.get('shotType', 'shot')
                talking_points.append(f"Goal: {scorer_name} {shot_type} at {event_time}")
                
            elif event_type == "shot-on-goal":
                shooter_name = get_player_name_from_static(details.get('shootingPlayerId'), self._knowledge_base)
                shot_type = details.get('shotType', 'shot')
                talking_points.append(f"Shot: {shooter_name} {shot_type} at {event_time}")
                
            elif event_type == "hit":
                hitter_name = get_player_name_from_static(details.get('hittingPlayerId'), self._knowledge_base)
                hit_target_name = get_player_name_from_static(details.get('hitteePlayerId'), self._knowledge_base)
                talking_points.append(f"Hit: {hitter_name} on {hit_target_name} at {event_time}")
                
            elif event_type == "fight":
                fighter1_name = get_player_name_from_static(details.get('fighter1PlayerId'), self._knowledge_base)
                fighter2_name = get_player_name_from_static(details.get('fighter2PlayerId'), self._knowledge_base)
                talking_points.append(f"Fight: {fighter1_name} vs {fighter2_name} at {event_time}")
                
            else:
                # Fallback for other event types
                talking_points.append(f"{event_type.title()} at {event_time}")
        
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

# ---------------------------------------------------------------------------
# Note: For testing, use the standalone test_data_agent.py script instead
# This avoids duplication and provides better testing capabilities