"""
Configuration for NHL Commentary Pipeline
"""

import os
from typing import Dict, Any


class PipelineConfig:
    """Centralized configuration for the NHL commentary pipeline"""
    
    # WebSocket Configuration
    WEBSOCKET_PORT = int(os.getenv("WEBSOCKET_PORT", "8765"))
    WEBSOCKET_HOST = os.getenv("WEBSOCKET_HOST", "localhost")
    
    # Session Management
    SESSION_REFRESH_INTERVAL = int(os.getenv("SESSION_REFRESH_INTERVAL", "10"))
    
    # Audio Processing
    AUDIO_BUFFER_DELAY = int(os.getenv("AUDIO_BUFFER_DELAY", "15"))
    AUDIO_BUFFER_SIZE = int(os.getenv("AUDIO_BUFFER_SIZE", "100"))
    
    # ADK Configuration
    ADK_TIMEOUT = float(os.getenv("ADK_TIMEOUT", "120.0"))
    
    # Model Configuration
    DATA_AGENT_MODEL = os.getenv("DATA_AGENT_MODEL", "gemini-2.0-flash")
    COMMENTARY_AGENT_MODEL = os.getenv("COMMENTARY_AGENT_MODEL", "gemini-2.0-flash")
    AUDIO_AGENT_MODEL = os.getenv("AUDIO_AGENT_MODEL", "gemini-2.0-flash")
    
    # Processing Configuration
    TIMESTAMP_PROCESSING_DELAY = float(os.getenv("TIMESTAMP_PROCESSING_DELAY", "1.0"))
    STATIC_CONTEXT_TIMEOUT = float(os.getenv("STATIC_CONTEXT_TIMEOUT", "30.0"))
    
    # File Paths
    DATA_BASE_PATH = os.getenv("DATA_BASE_PATH", "data")
    AUDIO_OUTPUT_PATH = os.getenv("AUDIO_OUTPUT_PATH", "audio_output")
    
    # NHL API Configuration
    NHL_API_BASE_URL = os.getenv("NHL_API_BASE_URL", "https://api-web.nhle.com/v1")
    NHL_API_TIMEOUT = float(os.getenv("NHL_API_TIMEOUT", "10.0"))
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """Get all configuration values as a dictionary"""
        return {
            attr: getattr(cls, attr) 
            for attr in dir(cls) 
            if not attr.startswith('_') and not callable(getattr(cls, attr))
        }
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate configuration values"""
        try:
            # Check required integer values are positive
            assert cls.WEBSOCKET_PORT > 0, "WEBSOCKET_PORT must be positive"
            assert cls.SESSION_REFRESH_INTERVAL > 0, "SESSION_REFRESH_INTERVAL must be positive"
            assert cls.AUDIO_BUFFER_DELAY >= 0, "AUDIO_BUFFER_DELAY must be non-negative"
            assert cls.ADK_TIMEOUT > 0, "ADK_TIMEOUT must be positive"
            
            # Check paths exist or can be created
            os.makedirs(cls.DATA_BASE_PATH, exist_ok=True)
            os.makedirs(cls.AUDIO_OUTPUT_PATH, exist_ok=True)
            
            return True
        except AssertionError as e:
            print(f"Configuration validation failed: {e}")
            return False
        except Exception as e:
            print(f"Configuration error: {e}")
            return False


# Create singleton instance
config = PipelineConfig()