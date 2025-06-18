"""
NHL Sequential Agent - Simple workflow package
"""

from .sequential_agent import (
    create_nhl_sequential_agent,
    process_timestamp,
    test_sequential_agent
)

from .prompts import get_workflow_prompt
from .tools import extract_audio_from_result, save_result

__all__ = [
    'create_nhl_sequential_agent',
    'process_timestamp',
    'test_sequential_agent',
    'get_workflow_prompt',
    'extract_audio_from_result',
    'save_result'
]