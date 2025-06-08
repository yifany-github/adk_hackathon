#!/usr/bin/env python3
"""
Audio Agent Configuration
Voice settings and TTS options for NHL commentary
"""
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class VoiceConfig:
    """Configuration for TTS voice settings"""
    name: str
    language_code: str
    gender: str
    description: str
    speaking_rate: float = 1.0
    pitch: float = 0.0
    volume_gain_db: float = 0.0


# Available voice configurations for NHL commentary
VOICE_CONFIGS = {
    # Professional sports commentator voices
    "play_by_play": VoiceConfig(
        name="en-US-Studio-M",
        language_code="en-US",
        gender="MALE",
        description="Deep, authoritative voice for play-by-play commentary",
        speaking_rate=1.1,
        pitch=0.0,
        volume_gain_db=2.0
    ),
    
    "color_commentary": VoiceConfig(
        name="en-US-Studio-O",
        language_code="en-US", 
        gender="MALE",
        description="Warm, conversational voice for analysis and insights",
        speaking_rate=0.95,
        pitch=-2.0,
        volume_gain_db=1.0
    ),
    
    "arena_announcer": VoiceConfig(
        name="en-US-Neural2-A",
        language_code="en-US",
        gender="MALE", 
        description="Booming arena announcer voice for goals and penalties",
        speaking_rate=0.9,
        pitch=2.0,
        volume_gain_db=4.0
    ),
    
    "radio_host": VoiceConfig(
        name="en-US-Neural2-D",
        language_code="en-US",
        gender="MALE",
        description="Clear radio-style voice for detailed descriptions",
        speaking_rate=1.0,
        pitch=0.0,
        volume_gain_db=0.0
    ),
    
    "analyst": VoiceConfig(
        name="en-US-Neural2-C",
        language_code="en-US",
        gender="FEMALE",
        description="Professional analyst voice for statistics and trends",
        speaking_rate=1.05,
        pitch=1.0,
        volume_gain_db=0.0
    )
}


# Audio encoding options
AUDIO_ENCODINGS = {
    "mp3": {
        "encoding": "MP3",
        "extension": "mp3",
        "description": "Standard MP3 format for web streaming",
        "bitrate": "64kbps"
    },
    "wav": {
        "encoding": "LINEAR16",
        "extension": "wav",
        "description": "High-quality WAV format for production",
        "bitrate": "1411kbps"
    },
    "ogg": {
        "encoding": "OGG_OPUS", 
        "extension": "ogg",
        "description": "Efficient OGG Opus for real-time streaming",
        "bitrate": "64kbps"
    }
}


# Audio processing settings for different scenarios
SCENARIO_SETTINGS = {
    "live_game": {
        "voice": "play_by_play",
        "encoding": "mp3",
        "websocket_port": 8765,
        "buffer_size": 5,  # seconds
        "quality": "standard"
    },
    
    "highlights": {
        "voice": "arena_announcer", 
        "encoding": "wav",
        "websocket_port": 8766,
        "buffer_size": 2,
        "quality": "high"
    },
    
    "analysis": {
        "voice": "analyst",
        "encoding": "mp3", 
        "websocket_port": 8767,
        "buffer_size": 10,
        "quality": "standard"
    },
    
    "radio_broadcast": {
        "voice": "radio_host",
        "encoding": "ogg",
        "websocket_port": 8768,
        "buffer_size": 3,
        "quality": "high"
    }
}


def get_voice_config(voice_type: str) -> Optional[VoiceConfig]:
    """Get voice configuration by type"""
    return VOICE_CONFIGS.get(voice_type)


def get_scenario_settings(scenario: str) -> Optional[Dict]:
    """Get complete settings for a commentary scenario"""
    return SCENARIO_SETTINGS.get(scenario)


def list_available_voices() -> List[str]:
    """List all available voice types"""
    return list(VOICE_CONFIGS.keys())


def list_available_scenarios() -> List[str]:
    """List all available commentary scenarios"""
    return list(SCENARIO_SETTINGS.keys())


# Commentary style prompts for different voice types
COMMENTARY_STYLES = {
    "play_by_play": {
        "style": "Fast-paced, energetic play-by-play commentary",
        "examples": [
            "McDavid breaks in alone! He shoots... HE SCORES!",
            "Face-off at center ice, puck drops, here we go!"
        ]
    },
    
    "color_commentary": {
        "style": "Analytical insights and background information",
        "examples": [
            "That's McDavid's 15th goal of the season, putting him on pace for another 50-goal campaign.",
            "You can see the chemistry developing between these linemates."
        ]
    },
    
    "arena_announcer": {
        "style": "Loud, enthusiastic arena-style announcements",
        "examples": [
            "GOOOOAL! Scored by number 97, CONNOR MCDAVID!",
            "Two minutes for slashing, number 44!"
        ]
    },
    
    "radio_host": {
        "style": "Descriptive radio-style commentary for listeners",
        "examples": [
            "The puck is behind the net, McDavid circles around looking for an opening.",
            "Draisaitl carries the puck up the left side, approaching the blue line."
        ]
    },
    
    "analyst": {
        "style": "Statistical analysis and tactical breakdown", 
        "examples": [
            "The Oilers are now 3-for-5 on the power play tonight.",
            "This line combination is generating significant offensive zone time."
        ]
    }
}


def get_commentary_style(voice_type: str) -> Optional[Dict]:
    """Get commentary style guidelines for a voice type"""
    return COMMENTARY_STYLES.get(voice_type) 