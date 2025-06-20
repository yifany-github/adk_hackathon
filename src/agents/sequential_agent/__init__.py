"""
NHL Sequential Agent - Simple workflow package
"""

from .sequential_agent import (
    create_nhl_sequential_agent,
    process_timestamp,
    test_sequential_agent
)

from .sequential_agent_v2 import (
    create_nhl_sequential_agent_v2,
    process_timestamp_v2,
    test_sequential_agent_v2,
    PersistentSequentialAgent
)

from .prompts import get_workflow_prompt
from .tools import extract_audio_from_result, save_result

__all__ = [
    'create_nhl_sequential_agent',
    'process_timestamp',
    'test_sequential_agent',
    'create_nhl_sequential_agent_v2',
    'process_timestamp_v2', 
    'test_sequential_agent_v2',
    'PersistentSequentialAgent',
    'get_workflow_prompt',
    'extract_audio_from_result',
    'save_result'
]