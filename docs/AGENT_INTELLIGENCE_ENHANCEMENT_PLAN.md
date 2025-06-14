# Agent Intelligence Enhancement Plan

## Overview

This document outlines the comprehensive plan to enhance the NHL Commentary System's three agents from template-based/hardcoded approaches to fully intelligent LLM-driven implementations. The goal is to leverage Google ADK and Gemini 2.0 Flash for intelligent decision-making, content generation, and adaptive responses.

## Current State Assessment

### Issue Identified
- **Commentary Agent**: Was using hardcoded template functions instead of LLM intelligence
- **Data Agent**: Uses hardcoded momentum calculation (`momentum_score = min(len(activities) * 5, 100)`)
- **Audio Agent**: Basic rule-based voice/emotion mapping

### Architecture Mismatch
The system was using Google ADK (intelligent agent framework) but tools were implementing hardcoded logic, creating a mismatch between the framework's capabilities and actual implementation.

## 3-Phase Enhancement Plan

---

## ✅ Phase 1: Commentary Agent Intelligence (COMPLETED)

### Status: **COMPLETED** ✅
**Completion Date**: June 14, 2025

### What Was Done

#### 1. Removed Template-Based Code (~80 lines)
**File**: `src/agents/commentary_agent/tools.py`

**Removed Functions**:
- `_generate_high_intensity_commentary()` 
- `_generate_mixed_coverage_commentary()`
- `_generate_filler_commentary()`
- `_generate_fallback_commentary()`

**Old Approach**:
```python
# Template-based hardcoded logic
if actual_type == "HIGH_INTENSITY":
    commentary_sequence = _generate_high_intensity_commentary(...)
elif actual_type == "MIXED_COVERAGE":
    commentary_sequence = _generate_mixed_coverage_commentary(...)
```

#### 2. Implemented Pure LLM Intelligence
**New Approach**:
```python
# Intelligent LLM-driven generation
intelligent_result = _generate_intelligent_commentary(
    situation_type=actual_type.lower(),
    context=full_context
)
```

#### 3. Added Structured Output System
**File**: `src/agents/commentary_agent/prompts.py`

**Key Components**:
- `COMMENTARY_JSON_SCHEMA`: Structured output specification
- `COMMENTARY_EXAMPLES`: 3 few-shot examples for different scenarios
- `INTELLIGENT_COMMENTARY_PROMPT`: LLM generation template

**Schema Example**:
```python
COMMENTARY_JSON_SCHEMA = '''
{
  "commentary_type": "string (period_start|play_by_play|penalty_analysis|...)",
  "commentary_sequence": [
    {
      "speaker": "Host|Analyst", 
      "text": "Natural commentary dialogue",
      "emotion": "excited|neutral|analytical|...",
      "timing": "0:15",
      "duration_estimate": 3.5,
      "pause_after": 0.8
    }
  ]
}
'''
```

#### 4. Validation Results
Generated 5 new intelligent commentary files demonstrating:
- **Contextual Dialogue**: "Well, the puck has dropped, and it looks like Barkov took the opening faceoff against Draisaitl."
- **Natural Flow**: Professional two-person broadcast style with session awareness
- **Varied Content**: Each timestamp produces unique, contextually appropriate commentary

### Technical Implementation

#### Key Function: `_generate_intelligent_commentary()`
```python
def _generate_intelligent_commentary(situation_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate intelligent commentary using LLM with structured output
    - Uses Gemini 2.0 Flash for reliable JSON generation
    - Few-shot prompting for consistent format
    - Context-aware content generation
    """
```

#### Session Management Integration
- Uses Google ADK sessions for conversation continuity
- Eliminates repetitive commentary across timestamps
- Maintains context for natural dialogue flow

---

## 🔄 Phase 2: Data Agent Intelligence (PENDING)

### Status: **PENDING**
**Target**: Next implementation phase

### Current Issues
**File**: `src/agents/data_agent/tools.py`

**Hardcoded Logic**:
```python
# Simple hardcoded momentum calculation
momentum_score = min(len(activities) * 5, 100)
```

### Proposed Enhancement

#### 1. Replace Hardcoded Momentum with LLM Analysis
**Current**:
```python
def calculate_momentum_score(activities):
    return min(len(activities) * 5, 100)  # Hardcoded
```

**Proposed**:
```python
def analyze_game_momentum(activities, game_context):
    """
    Use LLM to analyze game momentum based on:
    - Event types and intensity
    - Scoring situations
    - Player performance
    - Crowd energy indicators
    - Historical context
    """
    # LLM-driven analysis with structured output
```

#### 2. Intelligent Event Classification
- Replace simple event counting with contextual analysis
- Consider event impact, timing, and game situation
- Dynamic weighting based on game state

#### 3. Enhanced Talking Points Generation
- Move from basic event summaries to intelligent narrative generation
- Context-aware player spotlights
- Strategic analysis integration

### Implementation Plan
1. **Create momentum analysis prompts** with few-shot examples
2. **Implement structured output schema** for momentum assessment
3. **Replace hardcoded calculations** with LLM calls
4. **Add contextual event analysis** for better talking points
5. **Test with existing data** to ensure compatibility

---

## 🔄 Phase 3: Audio Agent Intelligence (PENDING)

### Status: **PENDING**
**Target**: Final implementation phase

### Current Issues
**File**: `src/agents/audio_agent/tool.py`

**Hardcoded Logic**:
```python
def _get_voice_style(speaker, emotion):
    """Map speaker and emotion to voice style"""
    if speaker == "pbp":
        return "enthusiastic" if emotion in ["excitement", "tension"] else "professional"
    else:  # color commentator
        return "analytical" if emotion == "analytical" else "conversational"
```

### Proposed Enhancement

#### 1. Context-Aware Voice Selection
**Current**: Simple rule-based mapping
**Proposed**: LLM-driven voice/emotion selection based on:
- Game momentum and intensity
- Commentary content and context
- Speaker personality and style
- Audience engagement optimization

#### 2. Dynamic Audio Processing
- Intelligent pause duration calculation
- Context-aware emphasis and intonation
- Adaptive speaking pace based on game intensity

#### 3. Enhanced TTS Integration
- Multiple voice personality options
- Context-driven emotional range
- Professional broadcast quality optimization

### Implementation Plan
1. **Analyze commentary context** for optimal voice selection
2. **Implement intelligent audio timing** based on content urgency
3. **Add voice personality system** with contextual switching
4. **Enhance TTS parameters** with LLM-driven optimization

---

## Architecture Benefits

### Before: Template-Based System
```
NHL API → Static Templates → Hardcoded Logic → Audio Output
```

### After: Fully Intelligent System
```
NHL API → LLM Analysis → Contextual Generation → Intelligent Audio → Professional Output
```

### Key Improvements
1. **Contextual Awareness**: Each component understands game context
2. **Adaptive Responses**: Content varies based on real game situations
3. **Professional Quality**: Natural, varied commentary eliminating repetition
4. **Scalability**: Easy to add new sports, scenarios, or features

## Technical Standards

### LLM Integration Pattern
```python
def intelligent_agent_function(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standard pattern for LLM-driven agent functions:
    1. Load context and configuration
    2. Format few-shot prompt with examples
    3. Generate structured output with Gemini 2.0 Flash
    4. Parse and validate JSON response
    5. Return standardized result format
    """
```

### Error Handling
- Graceful fallbacks for API failures
- Validation of LLM output structure
- Clear error reporting for debugging

### Session Management
- ADK session continuity for context preservation
- Persistent conversation history
- Production-ready session storage options

## Success Metrics

### Phase 1 Results ✅
- ✅ Eliminated 80+ lines of template code
- ✅ Generated contextual, varied commentary
- ✅ Maintained audio agent compatibility
- ✅ Session-aware conversation flow

### Phase 2 Targets
- [ ] Replace hardcoded momentum with intelligent analysis
- [ ] Generate contextual talking points
- [ ] Improve event impact assessment

### Phase 3 Targets
- [ ] Context-aware voice selection
- [ ] Intelligent audio timing
- [ ] Enhanced broadcast quality

## Next Steps

1. **Immediate**: Continue with Phase 2 (Data Agent enhancement)
2. **Testing**: Validate each phase with existing game data
3. **Integration**: Ensure seamless multi-agent coordination
4. **Optimization**: Fine-tune prompts and performance

---

**Document Created**: June 14, 2025  
**Phase 1 Completed**: June 14, 2025  
**Next Phase**: Data Agent Intelligence Enhancement