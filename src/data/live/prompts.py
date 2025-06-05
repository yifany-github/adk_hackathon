#!/usr/bin/env python3
"""
NHL Live Data Collection - Game Commentary Prompts
"""

DESCRIPTION_PROMPT = """
Generate a professional, factual description of recent NHL action based on the play-by-play data and enhanced statistics provided.

Guidelines:
- Write 1-2 sentences describing the flow of recent events
- Use player names, positions, and performance context when available
- Include relevant performance metrics ONLY when contextually appropriate for the game time
- Reference spatial context and game situations when meaningful
- Use appropriate temporal language: "moments earlier", "seconds before", "earlier in the period"
- Handle simultaneous events (same timeInPeriod) as concurrent action
- For period starts (0:00), avoid saying "moments earlier" - describe as action develops
- If no recent events, state: "No significant events in the recent action"
- Be factual and observational, not analytical or conversational

TEMPORAL LOGIC:
- Early period (0:00-5:00): Focus on immediate action, minimal cumulative stats
- Mid/late period (5:00+): Include relevant cumulative stats when they add context
- Only mention cumulative stats if they're meaningful to the current event
- Avoid repeating the same information from previous timestamps

Enhanced Data Available:
- Player stats: goals, assists, points, +/-, penalty minutes, hits, shots on goal, ice time, blocked shots, faceoff %, giveaways/takeaways
- Goalie stats: saves, shots against, save %, goals against, decision status
- Team stats: current score, shots on goal totals
- Game situation context and spatial descriptions

Activity Data: {activity_data}
Current Game Time: {game_time}

Examples:

Input: [
  {
    "timeInPeriod": "00:00",
    "typeDescKey": "period-start",
    "periodDescriptor": {"number": 1}
  }
]
Output: The first period begins with both teams looking to establish their forecheck and create offensive opportunities.

Input: [
  {
    "timeInPeriod": "00:15",
    "typeDescKey": "faceoff",
    "details": {
      "winningPlayerName": "N. Hischier (C, away)",
      "losingPlayerName": "S. Lafferty (C, home)",
      "spatialDescription": "at center ice"
    },
    "gameStats": {
      "playerStats": {
        "winningPlayerId": {
          "name": "Nico Hischier", "position": "C", "team": "away"
        }
      }
    }
  }
]
Output: Nico Hischier wins the opening faceoff against Sam Lafferty at center ice.

Input: [
  {
    "timeInPeriod": "08:15", 
    "typeDescKey": "shot-on-goal",
    "details": {
      "shootingPlayerName": "Stefan Noesen (R, away)",
      "goalieInNetName": "Jacob Markstrom (G, home)",
      "shotType": "Wrist Shot",
      "spatialDescription": "from the right circle"
    },
    "gameStats": {
      "playerStats": {
        "shootingPlayerId": {
          "name": "Stefan Noesen", "shotsOnGoal": 4, "goals": 1, "timeOnIce": "13:11", "team": "away"
        },
        "goalieInNetId": {
          "name": "Jacob Markstrom", "saves": 18, "shotsAgainst": 20, "savePct": 0.900, "team": "home"
        }
      }
    }
  }
]
Output: Stefan Noesen fires a wrist shot from the right circle that Markstrom turns aside, with Noesen's fourth shot of the game as he continues his active night with over 13 minutes of ice time.

Input: []
Output: No significant events in the recent action.
""" 