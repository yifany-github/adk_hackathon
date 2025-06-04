#!/usr/bin/env python3
"""
Live Data Collector - Collects raw NHL API data in 5s intervals
Implements Step 2A from NHL Live Streaming Data Architecture
"""
import os
import json
import sys
import requests
import time
from datetime import datetime
from typing import Dict, Any, Optional

import google.generativeai as genai
from prompts import NARRATIVE_PROMPT


class LiveDataCollector:
    """Collects raw NHL API data with fast polling (5s intervals)"""
    
    def __init__(self, output_dir: str = "../../../data/live/raw"):
        self.output_dir = output_dir
        self.base_url = "https://api-web.nhle.com/v1"
        os.makedirs(self.output_dir, exist_ok=True)
        self._setup_llm()
    
    def _setup_llm(self):
        """Setup Gemini LLM"""
        genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
        self.llm = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        print("🧠 Gemini Model Ready")
    
    def collect_live_data(self, game_id: str, current_time: str) -> str:
        """Collect raw NHL API data for 30-second time window"""
        print(f"🔄 Collecting live data for game {game_id} at time {current_time}")
        
        # Get play-by-play data
        pbp_data = self._get_play_by_play(game_id)
        if not pbp_data:
            raise ValueError(f"Could not get play-by-play data for {game_id}")
        
        # Filter to 30-second window (still 30s window, but collected every 5s)
        filtered_plays = self._filter_time_window(pbp_data, current_time)
        
        # Generate narrative
        narrative = self._generate_description(filtered_plays)
        
        # Prepare raw data
        raw_data = {
            'game_id': game_id,
            'timestamp': current_time,
            'collected_at': datetime.now().isoformat(),
            'filtered_plays': filtered_plays,
            'plays_in_window': len(filtered_plays),
            'narrative': narrative
        }
        
        # Save raw data
        timestamp_str = current_time.replace(':', '_')
        filepath = os.path.join(self.output_dir, f"game_{game_id}_raw_{timestamp_str}.json")
        with open(filepath, 'w') as f:
            json.dump(raw_data, f, indent=2)
        
        print(f"💾 Raw data saved: {filepath} ({len(filtered_plays)} plays)")
        return filepath
    
    def start_live_collection(self, game_id: str, duration_minutes: int = 5):
        """Start fast live data collection (every 5 seconds)"""
        print(f"🚀 Starting FAST live collection for game {game_id}")
        print(f"⚡ Polling every 5 seconds (duration: {duration_minutes}m)")
        
        current_period = 1
        current_seconds = 0
        end_time = time.time() + (duration_minutes * 60)
        
        while time.time() < end_time:
            # Format time as P:MM:SS
            minutes = current_seconds // 60
            seconds = current_seconds % 60
            current_time = f"{current_period}:{minutes:02d}:{seconds:02d}"
            
            try:
                self.collect_live_data(game_id, current_time)
            except Exception as e:
                print(f"❌ Error at {current_time}: {e}")
            
            # Advance 5 seconds (much faster!)
            current_seconds += 5
            
            # Handle period transitions (20 min = 1200 sec per period)
            if current_seconds >= 1200:
                current_period += 1
                current_seconds = 0
                if current_period > 3:
                    print("🏁 Game complete (3 periods)")
                    break
            
            # Fast polling - only 0.5s pause
            time.sleep(0.5)
        
        print("✅ Fast live collection finished")
    
    def _get_play_by_play(self, game_id: str) -> Optional[Dict[str, Any]]:
        """Get play-by-play data from NHL API"""
        try:
            url = f"{self.base_url}/gamecenter/{game_id}/play-by-play"
            response = requests.get(url, timeout=3)  # Faster timeout
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error getting play-by-play: {e}")
            return None
    
    def _filter_time_window(self, pbp_data: Dict[str, Any], current_time: str) -> list:
        """Filter plays to 30-second window ending at current_time"""
        try:
            # Parse current time
            period, time_str = current_time.split(':', 1)
            period = int(period)
            minutes, seconds = map(int, time_str.split(':'))
            current_total = (minutes * 60) + seconds
            window_start = max(0, current_total - 30)
            
            # Filter plays
            filtered_plays = []
            for play in pbp_data.get('plays', []):
                play_period = play.get('periodDescriptor', {}).get('number', 0)
                play_time = play.get('timeInPeriod', '')
                
                if play_period == period and play_time:
                    try:
                        play_min, play_sec = map(int, play_time.split(':'))
                        play_total = (play_min * 60) + play_sec
                        
                        if window_start <= play_total <= current_total:
                            filtered_plays.append(play)
                    except (ValueError, AttributeError):
                        continue
            
            return filtered_plays
        except Exception as e:
            print(f"⚠️ Error filtering time window: {e}")
            return []

    def _generate_description(self, plays):
        """Generate narrative using Gemini"""
        plays_text = self._format_plays_for_prompt(plays)
        prompt = NARRATIVE_PROMPT.format(plays_data=plays_text)
        response = self.llm.generate_content(prompt)
        
        intensity = min(len(plays) + 1, 10) if plays else 1
        play_types = [play.get('typeDescKey', '') for play in plays]
        moment_type = "scoring_chance" if any('shot' in p.lower() for p in play_types) else "routine"
        
        return {"summary": response.text.strip(), "intensity": intensity, "moment_type": moment_type}

    def _format_plays_for_prompt(self, plays):
        """Format plays data for LLM prompt with rich details"""
        if not plays: 
            return "No plays in this 5-second window."
        
        formatted_plays = []
        for play in plays[:3]:  # Keep top 3 plays
            time_in_period = play.get('timeInPeriod', '?:??')
            play_type = play.get('typeDescKey', 'unknown')
            details = play.get('details', {})
            
            # Build rich description based on play type
            if play_type == 'shot-on-goal':
                shooter = details.get('shootingPlayerId', '?')
                goalie = details.get('goalieInNetId', '?')
                shot_type = details.get('shotType', 'shot')
                zone = details.get('zoneCode', '')
                zone_desc = {'O': 'offensive zone', 'D': 'defensive zone', 'N': 'neutral zone'}.get(zone, '')
                formatted_plays.append(f"[{time_in_period}] {shot_type} shot by player {shooter} on goalie {goalie} in {zone_desc}")
                
            elif play_type == 'hit':
                hitter = details.get('hittingPlayerId', '?')
                target = details.get('hitteePlayerId', '?')
                zone = details.get('zoneCode', '')
                zone_desc = {'O': 'offensive zone', 'D': 'defensive zone', 'N': 'neutral zone'}.get(zone, '')
                formatted_plays.append(f"[{time_in_period}] hit by player {hitter} on player {target} in {zone_desc}")
                
            elif play_type == 'blocked-shot':
                shooter = details.get('shootingPlayerId', '?')
                blocker = details.get('blockingPlayerId', '?')
                formatted_plays.append(f"[{time_in_period}] shot by player {shooter} blocked by player {blocker}")
                
            elif play_type == 'faceoff':
                winner = details.get('winningPlayerId', '?')
                loser = details.get('losingPlayerId', '?')
                zone = details.get('zoneCode', '')
                zone_desc = {'O': 'offensive zone', 'D': 'defensive zone', 'N': 'neutral zone'}.get(zone, 'center ice')
                formatted_plays.append(f"[{time_in_period}] faceoff won by player {winner} over player {loser} in {zone_desc}")
                
            elif play_type == 'missed-shot':
                shooter = details.get('shootingPlayerId', '?')
                shot_type = details.get('shotType', 'shot')
                reason = details.get('reason', 'missed')
                formatted_plays.append(f"[{time_in_period}] {shot_type} shot by player {shooter} goes {reason}")
                
            else:
                # Fallback for other play types
                formatted_plays.append(f"[{time_in_period}] {play_type}")
        
        return "\n".join(formatted_plays)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 live_data_collector.py GAME_ID [DURATION_MINUTES]")
        print("Example: python3 live_data_collector.py 2023020001 5")
        print("Note: Now polls every 5 seconds for faster live streaming!")
        sys.exit(1)
    
    game_id = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    collector = LiveDataCollector()
    collector.start_live_collection(game_id, duration) 