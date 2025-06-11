"""
Configuration file for the Hockey Data Agent
Contains all configurable values for momentum analysis and scoring
"""

# Momentum scoring configuration
MOMENTUM_SCORES = {
    "goal": 50,
    "fight": 45, 
    "penalty": 35,
    "shot-on-goal": 15,
    "hit": 10,
    "missed-shot": 8,
    "faceoff": 2
}

# Momentum thresholds for recommendations
MOMENTUM_THRESHOLDS = {
    "high": 75,    # PLAY_BY_PLAY threshold
    "medium": 25   # MIXED_COVERAGE threshold (below this = FILLER_CONTENT)
}

# Contextual multipliers
CONTEXTUAL_MULTIPLIERS = {
    "late_game_minutes": 5,      # Last 5 minutes of period
    "late_game_multiplier": 1.5,
    "overtime_multiplier": 2.5,
    "close_game_multiplier": 1.3,  # When score diff <= 1
    "crossbar_bonus": 15,           # Additional points for hitting crossbar
    "power_play_goal_bonus": 25     # Additional points for PP goals
}

# High intensity event threshold
HIGH_INTENSITY_THRESHOLD = 15

# Default model configuration
DEFAULT_MODEL = 'gemini-2.0-flash'