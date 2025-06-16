#!/usr/bin/env python3
"""
Basic Validator - Minimal validation for technical errors only
With deterministic board state injection, content validation is unnecessary
"""

from typing import Dict, List, Any


class BasicValidator:
    """
    Minimal validation for technical errors only.
    With deterministic board state injection, content validation is unnecessary.
    """
    
    def __init__(self):
        self.validation_errors = []
        self.validation_warnings = []
    
    def validate_json_structure(self, commentary_data: Dict) -> bool:
        """
        Verify JSON structure is correct for downstream processing.
        """
        try:
            required_fields = ['commentary_sequence', 'commentary_type']
            missing_fields = [field for field in required_fields if field not in commentary_data]
            
            if missing_fields:
                self.validation_errors.append(f"Missing required fields: {missing_fields}")
                return False
            
            # Validate commentary_sequence structure
            if not isinstance(commentary_data['commentary_sequence'], list):
                self.validation_errors.append("commentary_sequence must be a list")
                return False
            
            for i, sequence in enumerate(commentary_data['commentary_sequence']):
                if not isinstance(sequence, dict):
                    self.validation_errors.append(f"commentary_sequence[{i}] must be a dict")
                    return False
                
                required_sequence_fields = ['speaker', 'text']
                missing_sequence_fields = [field for field in required_sequence_fields if field not in sequence]
                
                if missing_sequence_fields:
                    self.validation_errors.append(f"commentary_sequence[{i}] missing fields: {missing_sequence_fields}")
                    return False
            
            return True
            
        except Exception as e:
            self.validation_errors.append(f"JSON structure validation failed: {str(e)}")
            return False
    
    def validate_speaker_format(self, commentary_data: Dict) -> bool:
        """
        Ensure speakers are properly formatted for audio processing.
        """
        try:
            valid_speakers = {'Alex Chen', 'Mike Rodriguez'}
            
            for i, sequence in enumerate(commentary_data.get('commentary_sequence', [])):
                speaker = sequence.get('speaker')
                
                if speaker not in valid_speakers:
                    self.validation_errors.append(f"Invalid speaker at sequence[{i}]: '{speaker}'. Must be 'Alex Chen' or 'Mike Rodriguez'")
                    return False
            
            return True
            
        except Exception as e:
            self.validation_errors.append(f"Speaker format validation failed: {str(e)}")
            return False
    
    def validate_timing_fields(self, commentary_data: Dict) -> bool:
        """
        Ensure timing fields are present and valid for audio synchronization.
        """
        try:
            for i, sequence in enumerate(commentary_data.get('commentary_sequence', [])):
                # Check for duration_estimate
                if 'duration_estimate' in sequence:
                    duration = sequence['duration_estimate']
                    if not isinstance(duration, (int, float)) or duration <= 0:
                        self.validation_warnings.append(f"Invalid duration_estimate at sequence[{i}]: {duration}")
                
                # Check for emotion field
                if 'emotion' not in sequence:
                    self.validation_warnings.append(f"Missing emotion field at sequence[{i}]")
            
            return True
            
        except Exception as e:
            self.validation_errors.append(f"Timing validation failed: {str(e)}")
            return False
    
    def validate_commentary_output(self, commentary_data: Dict) -> Dict[str, Any]:
        """
        Run all validation checks and return comprehensive report.
        """
        self.validation_errors = []
        self.validation_warnings = []
        
        # Run all validations
        json_valid = self.validate_json_structure(commentary_data)
        speaker_valid = self.validate_speaker_format(commentary_data)
        timing_valid = self.validate_timing_fields(commentary_data)
        
        overall_valid = json_valid and speaker_valid and timing_valid
        
        return {
            "valid": overall_valid,
            "errors": self.validation_errors.copy(),
            "warnings": self.validation_warnings.copy(),
            "checks": {
                "json_structure": json_valid,
                "speaker_format": speaker_valid,
                "timing_fields": timing_valid
            }
        }
    
    def get_validation_summary(self) -> str:
        """
        Get human-readable validation summary.
        """
        if not self.validation_errors and not self.validation_warnings:
            return "✅ All validations passed"
        
        summary = ""
        if self.validation_errors:
            summary += f"❌ {len(self.validation_errors)} errors: {'; '.join(self.validation_errors)}"
        
        if self.validation_warnings:
            if summary:
                summary += " | "
            summary += f"⚠️ {len(self.validation_warnings)} warnings: {'; '.join(self.validation_warnings)}"
        
        return summary


def validate_commentary_safely(commentary_data: Any) -> Dict[str, Any]:
    """
    Safe validation wrapper that handles malformed input gracefully.
    """
    validator = BasicValidator()
    
    try:
        # Handle non-dict input
        if not isinstance(commentary_data, dict):
            return {
                "valid": False,
                "errors": [f"Commentary data must be a dict, got {type(commentary_data)}"],
                "warnings": [],
                "checks": {
                    "json_structure": False,
                    "speaker_format": False,
                    "timing_fields": False
                }
            }
        
        return validator.validate_commentary_output(commentary_data)
        
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Validation crashed: {str(e)}"],
            "warnings": [],
            "checks": {
                "json_structure": False,
                "speaker_format": False,
                "timing_fields": False
            }
        }