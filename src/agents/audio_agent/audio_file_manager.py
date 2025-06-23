#!/usr/bin/env python3
"""
音频文件管理器
负责音频文件的命名、序列号管理和防覆盖机制
按照全局计数器顺序命名：1_GAME_ID_TIMESTAMP_SPEAKER_STYLE.wav
"""

import os
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path


class AudioFileManager:
    """音频文件管理器 - 确保文件名唯一性和正确顺序"""
    
    def __init__(self):
        self._lock = threading.Lock()
        # 全局计数器 - 跨所有游戏的全局序列号
        self._global_counter = 0
        self._game_sequences = {}  # game_id -> sequence info
        self._session_sequences = {}  # session_id -> sequence info
        
    def get_unique_filename(
        self, 
        game_id: str,
        game_timestamp: str, 
        speaker: str, 
        voice_style: str,
        session_id: str = None,
        audio_id: str = None
    ) -> tuple[str, int]:
        """
        生成唯一的音频文件名，确保不会覆盖
        新格式：{counter}_{game_id}_{timestamp}_{speaker}_{style}.wav
        
        Args:
            game_id: 游戏ID
            game_timestamp: 游戏时间戳 (如 "1_00_00")
            speaker: 播音员名称
            voice_style: 声音风格
            session_id: 会话ID (可选)
            audio_id: 音频ID (可选)
            
        Returns:
            (filename, sequence_number): 文件名和序列号
        """
        with self._lock:
            # 递增全局计数器
            self._global_counter += 1
            counter = self._global_counter
            
            # 创建基础文件名组件
            speaker_clean = speaker.lower().replace(" ", "").replace(".", "") if speaker else "commentary"
            
            # 获取或创建游戏序列信息
            if game_id not in self._game_sequences:
                self._game_sequences[game_id] = {
                    'global_sequence': 0,
                    'timestamp_sequences': {},
                    'speaker_sequences': {},
                    'files_created': []
                }
            
            game_seq = self._game_sequences[game_id]
            
            # 游戏内序列号
            game_seq['global_sequence'] += 1
            game_global_seq = game_seq['global_sequence']
            
            # 时间戳特定序列号
            timestamp_key = f"{game_timestamp}"
            if timestamp_key not in game_seq['timestamp_sequences']:
                game_seq['timestamp_sequences'][timestamp_key] = 0
            game_seq['timestamp_sequences'][timestamp_key] += 1
            timestamp_seq = game_seq['timestamp_sequences'][timestamp_key]
            
            # 播音员特定序列号
            speaker_key = f"{speaker_clean}_{voice_style}"
            if speaker_key not in game_seq['speaker_sequences']:
                game_seq['speaker_sequences'][speaker_key] = 0
            game_seq['speaker_sequences'][speaker_key] += 1
            speaker_seq = game_seq['speaker_sequences'][speaker_key]
            
            # 生成新格式的文件名
            # 格式: {counter}_{game_id}_{timestamp}_{speaker}_{style}.wav
            filename = f"{counter}_{game_id}_{game_timestamp}_{speaker_clean}_{voice_style}.wav"
            
            # 如果文件已存在，添加额外标识符
            output_dir = os.path.join("audio_output", game_id)
            full_path = os.path.join(output_dir, filename)
            
            duplicate_counter = 1
            original_filename = filename
            while os.path.exists(full_path):
                base_name = original_filename.replace('.wav', '')
                filename = f"{base_name}_dup{duplicate_counter:02d}.wav"
                full_path = os.path.join(output_dir, filename)
                duplicate_counter += 1
            
            # 记录创建的文件信息
            file_info = {
                'filename': filename,
                'global_counter': counter,
                'game_timestamp': game_timestamp,
                'speaker': speaker,
                'voice_style': voice_style,
                'game_sequence': game_global_seq,
                'timestamp_sequence': timestamp_seq,
                'speaker_sequence': speaker_seq,
                'created_at': datetime.now().isoformat(),
                'audio_id': audio_id,
                'session_id': session_id
            }
            
            game_seq['files_created'].append(file_info)
            
            return filename, counter
    
    def get_game_sequence_info(self, game_id: str) -> Dict:
        """获取游戏的序列信息"""
        with self._lock:
            return self._game_sequences.get(game_id, {})
    
    def get_files_for_game(self, game_id: str) -> List[Dict]:
        """获取游戏的所有文件信息"""
        with self._lock:
            game_seq = self._game_sequences.get(game_id, {})
            return game_seq.get('files_created', [])
    
    def save_manifest(self, game_id: str) -> str:
        """保存音频文件清单"""
        with self._lock:
            output_dir = os.path.join("audio_output", game_id)
            os.makedirs(output_dir, exist_ok=True)
            
            # 直接获取文件信息，避免调用会导致死锁的方法
            game_seq = self._game_sequences.get(game_id, {})
            files_created = game_seq.get('files_created', [])
            
            manifest_data = {
                'game_id': game_id,
                'generated_at': datetime.now().isoformat(),
                'sequence_info': game_seq,
                'total_files': len(files_created),
                'files': files_created
            }
            
            manifest_path = os.path.join(output_dir, 'audio_files_manifest.json')
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest_data, f, indent=2, ensure_ascii=False)
            
            return manifest_path
    
    def cleanup_game_sequences(self, game_id: str):
        """清理游戏序列信息（用于测试或重置）"""
        with self._lock:
            if game_id in self._game_sequences:
                del self._game_sequences[game_id]
    
    def get_next_files_for_timestamp(self, game_id: str, game_timestamp: str) -> List[Dict]:
        """获取特定时间戳的下一批文件"""
        with self._lock:
            game_seq = self._game_sequences.get(game_id, {})
            files = game_seq.get('files_created', [])
            return [f for f in files if f['game_timestamp'] == game_timestamp]
    
    def validate_file_uniqueness(self, game_id: str) -> Dict:
        """验证文件名唯一性"""
        with self._lock:
            game_seq = self._game_sequences.get(game_id, {})
            files = game_seq.get('files_created', [])
            filenames = [f['filename'] for f in files]
            
            duplicates = []
            seen = set()
            for filename in filenames:
                if filename in seen:
                    duplicates.append(filename)
                seen.add(filename)
            
            return {
                'total_files': len(files),
                'unique_files': len(seen),
                'duplicates': duplicates,
                'is_valid': len(duplicates) == 0
            }


# 全局音频文件管理器实例
audio_file_manager = AudioFileManager()


def get_audio_file_manager() -> AudioFileManager:
    """获取全局音频文件管理器实例"""
    return audio_file_manager


def generate_unique_audio_filename(
    game_id: str,
    game_timestamp: str, 
    speaker: str, 
    voice_style: str,
    session_id: str = None,
    audio_id: str = None
) -> tuple[str, int]:
    """
    生成唯一的音频文件名 - 便捷函数
    
    Returns:
        (filename, sequence_number)
    """
    return audio_file_manager.get_unique_filename(
        game_id=game_id,
        game_timestamp=game_timestamp,
        speaker=speaker,
        voice_style=voice_style,
        session_id=session_id,
        audio_id=audio_id
    )


def save_audio_files_manifest_for_game(game_id: str) -> str:
    """保存游戏的音频文件清单 - 便捷函数"""
    return audio_file_manager.save_manifest(game_id)


def get_audio_sequence_info(game_id: str) -> Dict:
    """获取音频序列信息 - 便捷函数"""
    return audio_file_manager.get_game_sequence_info(game_id) 