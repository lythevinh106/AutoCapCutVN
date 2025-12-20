"""
API Utilities - Helper functions for the API server
"""

import os
from typing import Tuple, Optional


def hex_to_rgb(hex_color: str) -> Tuple[float, float, float]:
    """Convert hex color string to RGB tuple (0.0-1.0 range)
    
    Args:
        hex_color: Color in format '#RRGGBB' or 'RRGGBB'
        
    Returns:
        Tuple of (r, g, b) with values from 0.0 to 1.0
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")
    
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    
    return (r, g, b)


def rgb_to_hex(r: float, g: float, b: float) -> str:
    """Convert RGB tuple (0.0-1.0 range) to hex color string
    
    Args:
        r, g, b: Color components from 0.0 to 1.0
        
    Returns:
        Color in format '#RRGGBB'
    """
    return "#{:02X}{:02X}{:02X}".format(
        int(r * 255),
        int(g * 255),
        int(b * 255)
    )


def validate_file_path(file_path: str, allowed_extensions: Optional[Tuple[str, ...]] = None) -> Tuple[bool, str]:
    """Validate that a file exists and optionally has an allowed extension
    
    Args:
        file_path: Path to the file to validate
        allowed_extensions: Optional tuple of allowed extensions (e.g., ('.mp4', '.mov'))
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file_path:
        return False, "File path is empty"
    
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"
    
    if not os.path.isfile(file_path):
        return False, f"Path is not a file: {file_path}"
    
    if allowed_extensions:
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in allowed_extensions:
            return False, f"Invalid file extension '{ext}'. Allowed: {allowed_extensions}"
    
    return True, ""


def seconds_to_microseconds(seconds: float) -> int:
    """Convert seconds to microseconds (pyCapCut time format)"""
    return int(seconds * 1_000_000)


def microseconds_to_seconds(microseconds: int) -> float:
    """Convert microseconds to seconds"""
    return microseconds / 1_000_000


def parse_time(time_value) -> int:
    """Parse time value to microseconds
    
    Args:
        time_value: Can be int (microseconds), float (seconds), or string (e.g., "5s", "1.5s")
        
    Returns:
        Time in microseconds
    """
    if isinstance(time_value, int):
        # Already in microseconds if large, otherwise treat as seconds
        if time_value > 10000:  # Likely microseconds
            return time_value
        return seconds_to_microseconds(time_value)
    
    if isinstance(time_value, float):
        return seconds_to_microseconds(time_value)
    
    if isinstance(time_value, str):
        time_value = time_value.strip().lower()
        if time_value.endswith('s'):
            return seconds_to_microseconds(float(time_value[:-1]))
        if time_value.endswith('ms'):
            return int(float(time_value[:-2]) * 1000)
        return seconds_to_microseconds(float(time_value))
    
    raise ValueError(f"Cannot parse time value: {time_value}")


# Video file extensions
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.wmv', '.flv', '.m4v')

# Audio file extensions
AUDIO_EXTENSIONS = ('.mp3', '.wav', '.aac', '.m4a', '.flac', '.ogg', '.wma')

# Image file extensions
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff')
