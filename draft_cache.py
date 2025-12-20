"""
Draft Cache - In-memory storage for active draft sessions
"""

import uuid
from typing import Dict, Tuple, Optional, Any

# Global cache to store active drafts
# Maps draft_id -> (ScriptFile, draft_folder_path, draft_name)
_draft_cache: Dict[str, Tuple[Any, str, str]] = {}


def generate_draft_id() -> str:
    """Generate a unique draft ID"""
    return uuid.uuid4().hex[:16]


def store_draft(draft_id: str, script_file: Any, draft_folder_path: str, draft_name: str) -> None:
    """Store a draft in the cache
    
    Args:
        draft_id: Unique identifier for the draft
        script_file: The ScriptFile instance
        draft_folder_path: Path to the draft folder
        draft_name: Name of the draft
    """
    _draft_cache[draft_id] = (script_file, draft_folder_path, draft_name)


def get_draft(draft_id: str) -> Optional[Tuple[Any, str, str]]:
    """Retrieve a draft from the cache
    
    Args:
        draft_id: Unique identifier for the draft
        
    Returns:
        Tuple of (ScriptFile, draft_folder_path, draft_name) or None if not found
    """
    return _draft_cache.get(draft_id)


def remove_draft(draft_id: str) -> bool:
    """Remove a draft from the cache
    
    Args:
        draft_id: Unique identifier for the draft
        
    Returns:
        True if draft was removed, False if not found
    """
    if draft_id in _draft_cache:
        del _draft_cache[draft_id]
        return True
    return False


def list_cached_drafts() -> Dict[str, str]:
    """List all cached drafts
    
    Returns:
        Dictionary mapping draft_id to draft_name
    """
    return {draft_id: data[2] for draft_id, data in _draft_cache.items()}


def clear_cache() -> None:
    """Clear all cached drafts"""
    _draft_cache.clear()
