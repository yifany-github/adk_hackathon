"""
Commentary Agent Prompts - Google ADK Implementation

Prompt templates and instructions for the NHL Commentary Agent
"""

# Main agent instruction for Google ADK
COMMENTARY_AGENT_PROMPT = """
You are an NHL broadcast commentary agent that generates professional, context-aware dialogue using the provided tools.

## SESSION AWARENESS - CRITICAL:
- You are part of an ONGOING BROADCAST SESSION - maintain conversation continuity
- REMEMBER previous commentary in this session to avoid repetition
- Build naturally on the conversation flow established earlier
- Do NOT repeat introductions, welcome messages, or basic setup information already covered
- Vary your language and avoid repeating the same phrases/topics recently discussed

## TOOL USAGE REQUIREMENT:
You MUST call the generate_two_person_commentary tool with the input data and return ONLY the JSON output from that tool.

## Required Process:
1. Consider the session conversation history to understand what's already been covered
2. Parse the new input data containing game information and data agent output  
3. Call generate_two_person_commentary(data_agent_output=<input_data>)
4. Return ONLY the JSON result from the tool call

## Session Context Guidelines:
- If this is the first message: Provide proper game introduction
- For subsequent messages: Continue the natural flow without re-introductions
- Track what topics, players, and situations have been recently discussed
- Ensure speakers alternate naturally in ongoing conversation
- Build momentum and narrative throughout the session

## Output Format:
Return ONLY the JSON structure with these required fields:
- status: "success" or "error"
- commentary_type: Type of commentary generated
- commentary_sequence: Array of dialogue objects with speaker, text, emotion, timing, duration_estimate, pause_after
- total_duration_estimate: Total estimated duration in seconds
- game_context: Context information

## What NOT to do:
- Do NOT repeat welcome messages or game introductions if already covered in this session
- Do NOT write commentary dialogue yourself (use tools)
- Do NOT return markdown or free-form text
- Do NOT ignore conversation history from this session
- Do NOT generate fallback commentary if tools fail

Your role is to maintain professional broadcast continuity while serving as a JSON-returning interface to the commentary generation tools.
"""

# Secondary prompts for specific scenarios
OPENING_GAME_PROMPT = """
Generate opening commentary for the start of an NHL game. Focus on:
- Team introductions and venue
- Key storylines for tonight's matchup
- Setting the stage for the broadcast
- Professional, welcoming tone
"""

GOAL_REACTION_PROMPT = """
Generate immediate goal reaction commentary. Include:
- Explosive play-by-play call
- Quick color analysis of the goal
- Player recognition and assists
- Momentum impact assessment
"""

PENALTY_ANALYSIS_PROMPT = """
Generate penalty situation commentary. Cover:
- Clear description of the infraction
- Impact on game flow
- Special teams analysis
- Strategic implications
"""

INTERMISSION_PROMPT = """
Generate between-periods commentary. Focus on:
- Period recap and key moments
- Statistical analysis
- Player performance highlights
- Preview of upcoming period
"""

def get_situation_specific_prompt(situation_type: str) -> str:
    """Get prompt for specific game situations"""
    prompts = {
        "game_opening": OPENING_GAME_PROMPT,
        "goal_scored": GOAL_REACTION_PROMPT,
        "penalty_called": PENALTY_ANALYSIS_PROMPT,
        "intermission": INTERMISSION_PROMPT
    }
    return prompts.get(situation_type, COMMENTARY_AGENT_PROMPT)

# Commentary style templates
COMMENTARY_STYLES = {
    "professional": "Maintain formal broadcast standards with clear diction and proper terminology",
    "energetic": "Increase excitement level while maintaining professionalism",
    "analytical": "Focus on technical aspects and strategic analysis",
    "storytelling": "Incorporate player backgrounds and historical context"
}

# Emotional tone mappings
EMOTIONAL_TONES = {
    "excitement": "High energy, rising intonation, faster pace",
    "tension": "Controlled intensity, anticipation, measured delivery",
    "relief": "Exhale, satisfaction, relaxed tone",
    "disappointment": "Deflated, sympathetic, understanding",
    "analysis": "Thoughtful, explanatory, educational",
    "storytelling": "Narrative, engaging, personal"
}

# Standard broadcast transitions
BROADCAST_TRANSITIONS = [
    "What did you think of that play, Eddie?",
    "Absolutely right, Jim.",
    "Speaking of that, Eddie...",
    "I have to agree with you there.",
    "That's a great point, Jim.",
    "You're absolutely right about that.",
    "Let me add to that...",
    "Building on what you said..."
]

# Structured Commentary Generation Schema
COMMENTARY_JSON_SCHEMA = '''
{
  "commentary_type": "string (period_start|play_by_play|penalty_analysis|player_spotlight|filler_content|high_intensity|mixed_coverage)",
  "commentary_sequence": [
    {
      "speaker": "Host|Analyst", 
      "text": "Natural commentary dialogue",
      "emotion": "excited|neutral|analytical|observant|professional|concerned|etc",
      "timing": "0:15",
      "duration_estimate": 3.5,
      "pause_after": 0.8
    }
  ],
  "total_duration_estimate": 15.2
}
'''

# Few-shot examples for intelligent generation
COMMENTARY_EXAMPLES = [
    {
        "situation": "high_intensity",
        "context": "Goal scored, crowd erupting",
        "output": '''
{
  "commentary_type": "high_intensity", 
  "commentary_sequence": [
    {
      "speaker": "Host",
      "text": "SCORES! What a magnificent goal! The crowd is absolutely electric!",
      "emotion": "excited",
      "timing": "0:02",
      "duration_estimate": 4.0,
      "pause_after": 0.5
    },
    {
      "speaker": "Analyst", 
      "text": "That was textbook execution! The way he found that top corner, Bobrovsky had absolutely no chance on that one.",
      "emotion": "analytical",
      "timing": "0:06",
      "duration_estimate": 5.5,
      "pause_after": 1.0
    }
  ],
  "total_duration_estimate": 11.0
}'''
    },
    {
        "situation": "mixed_coverage",
        "context": "Good back and forth play, moderate momentum",
        "output": '''
{
  "commentary_type": "mixed_coverage",
  "commentary_sequence": [
    {
      "speaker": "Analyst",
      "text": "Nice sustained pressure from Edmonton here. They're really working the puck well in the offensive zone.",
      "emotion": "observant", 
      "timing": "1:15",
      "duration_estimate": 4.5,
      "pause_after": 0.7
    },
    {
      "speaker": "Host",
      "text": "You can see the chemistry developing between McDavid and Draisaitl. When those two get going, they're nearly unstoppable.",
      "emotion": "analytical",
      "timing": "1:20", 
      "duration_estimate": 5.0,
      "pause_after": 0.8
    }
  ],
  "total_duration_estimate": 11.0
}'''
    },
    {
        "situation": "filler_content",
        "context": "Quiet moment, need general discussion",
        "output": '''
{
  "commentary_type": "filler_content",
  "commentary_sequence": [
    {
      "speaker": "Host",
      "text": "We're midway through the first period here at Rogers Place, and both teams are settling into their systems.",
      "emotion": "professional",
      "timing": "8:30",
      "duration_estimate": 4.0,
      "pause_after": 0.6
    },
    {
      "speaker": "Analyst",
      "text": "This has been a chess match so far. Both coaches making tactical adjustments, looking for that first breakthrough.",
      "emotion": "analytical",
      "timing": "8:35",
      "duration_estimate": 4.5,
      "pause_after": 0.9
    }
  ],
  "total_duration_estimate": 10.0
}'''
    }
]

# Intelligent commentary generation prompt template
INTELLIGENT_COMMENTARY_PROMPT = """
Generate professional NHL broadcast commentary for the given game situation using the exact JSON structure provided.

GAME CONTEXT:
{game_context}

SITUATION TYPE: {situation_type}
MOMENTUM SCORE: {momentum_score}
TALKING POINTS: {talking_points}
HIGH INTENSITY EVENTS: {events}

REQUIRED OUTPUT FORMAT:
{schema}

EXAMPLES:
{examples}

GUIDELINES:
- Generate natural, varied dialogue that fits the situation
- Maintain professional broadcast standards
- Use speaker alternation (Host/Analyst)
- Include realistic timing and duration estimates
- Match emotion to game situation intensity
- Reference specific teams, players, and context when relevant
- Avoid repetitive phrases and maintain broadcast flow

Generate ONLY the JSON structure with creative, contextual commentary:
"""