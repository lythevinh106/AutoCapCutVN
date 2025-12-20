"""
pyCapCut API Server
Flask-based REST API for creating and editing CapCut drafts

Usage:
    python api_server.py
    
Endpoints are similar to VectCutAPI for easy migration.
"""

from flask import Flask, request, jsonify
import os
import traceback

# Import pyCapCut modules
import pycapcut as cc
from pycapcut import trange, tim, SEC

# Import local modules
from draft_cache import (
    generate_draft_id, store_draft, get_draft, 
    remove_draft, list_cached_drafts
)
from api_utils import (
    hex_to_rgb, validate_file_path, parse_time,
    VIDEO_EXTENSIONS, AUDIO_EXTENSIONS, IMAGE_EXTENSIONS
)
from settings.local import PORT, DEBUG, DRAFT_FOLDER

app = Flask(__name__)


def make_response(success: bool, output=None, error: str = ""):
    """Create a standardized response"""
    return jsonify({
        "success": success,
        "output": output if output else "",
        "error": error
    })


# ============================================================
# DRAFT MANAGEMENT ENDPOINTS
# ============================================================

@app.route('/create_draft', methods=['POST'])
def create_draft():
    """Create a new CapCut draft
    
    Request body:
        draft_name (str): Name of the draft
        width (int, optional): Video width, default 1920
        height (int, optional): Video height, default 1080
        fps (int, optional): Frame rate, default 30
        draft_folder (str, optional): Custom draft folder path
    
    Returns:
        draft_id: Unique identifier for the draft
        draft_name: Name of the created draft
    """
    try:
        data = request.get_json()
        
        draft_name = data.get('draft_name', f'api_draft_{generate_draft_id()[:8]}')
        width = data.get('width', 1920)
        height = data.get('height', 1080)
        fps = data.get('fps', 30)
        draft_folder_path = data.get('draft_folder', DRAFT_FOLDER)
        
        # Initialize DraftFolder
        draft_folder = cc.DraftFolder(draft_folder_path)
        
        # Create the draft
        script = draft_folder.create_draft(
            draft_name, 
            width, 
            height, 
            fps=fps, 
            allow_replace=True
        )
        
        # Add default tracks
        script.add_track(cc.TrackType.video)
        script.add_track(cc.TrackType.audio)
        script.add_track(cc.TrackType.text)
        
        # Generate draft ID and store in cache
        draft_id = generate_draft_id()
        store_draft(draft_id, script, draft_folder_path, draft_name)
        
        return make_response(True, {
            "draft_id": draft_id,
            "draft_name": draft_name,
            "draft_folder": draft_folder_path,
            "width": width,
            "height": height,
            "fps": fps
        })
        
    except Exception as e:
        return make_response(False, error=f"Error creating draft: {str(e)}")


@app.route('/save_draft', methods=['POST'])
def save_draft():
    """Save a draft to disk
    
    Request body:
        draft_id (str): The draft ID to save
    """
    try:
        data = request.get_json()
        draft_id = data.get('draft_id')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, draft_folder_path, draft_name = draft_data
        
        # Save the script
        script.save()
        
        return make_response(True, {
            "draft_id": draft_id,
            "draft_name": draft_name,
            "message": "Draft saved successfully"
        })
        
    except Exception as e:
        return make_response(False, error=f"Error saving draft: {str(e)}")


@app.route('/list_drafts', methods=['GET'])
def list_drafts():
    """List all cached drafts"""
    try:
        drafts = list_cached_drafts()
        return make_response(True, {"drafts": drafts})
    except Exception as e:
        return make_response(False, error=f"Error listing drafts: {str(e)}")


# ============================================================
# VIDEO ENDPOINTS
# ============================================================

@app.route('/add_video', methods=['POST'])
def add_video():
    """Add a video segment to the draft
    
    Request body:
        draft_id (str): The draft ID
        video_path (str): Path to the video file
        start (float, optional): Start time in seconds, default 0
        duration (float, optional): Duration in seconds, default full video
        target_start (float, optional): Position on timeline in seconds, default 0
        transform_x (float, optional): X position (-1 to 1), default 0
        transform_y (float, optional): Y position (-1 to 1), default 0
        scale_x (float, optional): X scale, default 1
        scale_y (float, optional): Y scale, default 1
        volume (float, optional): Audio volume 0-1, default 1
        speed (float, optional): Playback speed, default 1
        track_name (str, optional): Track name, default auto
    """
    try:
        data = request.get_json()
        draft_id = data.get('draft_id')
        video_path = data.get('video_path') or data.get('video_url')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        if not video_path:
            return make_response(False, error="Missing required parameter 'video_path'")
        
        # Validate file
        is_valid, error = validate_file_path(video_path, VIDEO_EXTENSIONS + IMAGE_EXTENSIONS)
        if not is_valid:
            return make_response(False, error=error)
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, _, _ = draft_data
        
        # Parse parameters
        start = data.get('start', 0)
        target_start = data.get('target_start', 0)
        duration = data.get('duration')
        volume = data.get('volume', 1.0)
        speed = data.get('speed', 1.0)
        transform_x = data.get('transform_x', 0)
        transform_y = data.get('transform_y', 0)
        scale_x = data.get('scale_x', 1)
        scale_y = data.get('scale_y', 1)
        track_name = data.get('track_name')
        
        # Create video material
        video_mat = cc.VideoMaterial(video_path)
        
        # Calculate duration
        if duration:
            segment_duration = int(duration * SEC)
        else:
            segment_duration = video_mat.duration
        
        # Create source and target timeranges
        source_start = int(start * SEC) if start else 0
        target_start_us = int(target_start * SEC) if target_start else 0
        
        # Create clip settings
        clip_settings = cc.ClipSettings(
            transform_x=transform_x,
            transform_y=transform_y,
            scale_x=scale_x,
            scale_y=scale_y
        )
        
        # Create video segment
        video_seg = cc.VideoSegment(
            video_mat,
            trange(target_start_us, segment_duration),
            source_timerange=trange(source_start, segment_duration) if source_start else None,
            speed=speed if speed != 1.0 else None,
            volume=volume,
            clip_settings=clip_settings
        )
        
        # Add to script
        script.add_segment(video_seg, track_name=track_name)
        
        return make_response(True, {
            "message": "Video segment added successfully",
            "duration": segment_duration / SEC
        })
        
    except Exception as e:
        traceback.print_exc()
        return make_response(False, error=f"Error adding video: {str(e)}")


@app.route('/add_image', methods=['POST'])
def add_image():
    """Add an image segment to the draft
    
    Request body:
        draft_id (str): The draft ID
        image_path (str): Path to the image file
        start (float, optional): Position on timeline in seconds, default 0
        duration (float, optional): Display duration in seconds, default 3
        transform_x (float, optional): X position (-1 to 1), default 0
        transform_y (float, optional): Y position (-1 to 1), default 0
        scale_x (float, optional): X scale, default 1
        scale_y (float, optional): Y scale, default 1
        track_name (str, optional): Track name
    """
    try:
        data = request.get_json()
        draft_id = data.get('draft_id')
        image_path = data.get('image_path') or data.get('image_url')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        if not image_path:
            return make_response(False, error="Missing required parameter 'image_path'")
        
        # Validate file
        is_valid, error = validate_file_path(image_path, IMAGE_EXTENSIONS)
        if not is_valid:
            return make_response(False, error=error)
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, _, _ = draft_data
        
        # Parse parameters
        start = data.get('start', 0)
        duration = data.get('duration', 3.0)  # Default 3 seconds
        transform_x = data.get('transform_x', 0)
        transform_y = data.get('transform_y', 0)
        scale_x = data.get('scale_x', 1)
        scale_y = data.get('scale_y', 1)
        track_name = data.get('track_name')
        
        # Create video material (images use VideoMaterial in pyCapCut)
        image_mat = cc.VideoMaterial(image_path)
        
        # Create clip settings
        clip_settings = cc.ClipSettings(
            transform_x=transform_x,
            transform_y=transform_y,
            scale_x=scale_x,
            scale_y=scale_y
        )
        
        # Create segment
        image_seg = cc.VideoSegment(
            image_mat,
            trange(int(start * SEC), int(duration * SEC)),
            clip_settings=clip_settings
        )
        
        # Add to script
        script.add_segment(image_seg, track_name=track_name)
        
        return make_response(True, {
            "message": "Image segment added successfully",
            "duration": duration
        })
        
    except Exception as e:
        traceback.print_exc()
        return make_response(False, error=f"Error adding image: {str(e)}")


# ============================================================
# AUDIO ENDPOINTS
# ============================================================

@app.route('/add_audio', methods=['POST'])
def add_audio():
    """Add an audio segment to the draft
    
    Request body:
        draft_id (str): The draft ID
        audio_path (str): Path to the audio file
        start (float, optional): Source start time in seconds, default 0
        duration (float, optional): Duration in seconds, default full audio
        target_start (float, optional): Position on timeline in seconds, default 0
        volume (float, optional): Audio volume 0-1, default 1
        speed (float, optional): Playback speed, default 1
        track_name (str, optional): Track name
    """
    try:
        data = request.get_json()
        draft_id = data.get('draft_id')
        audio_path = data.get('audio_path') or data.get('audio_url')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        if not audio_path:
            return make_response(False, error="Missing required parameter 'audio_path'")
        
        # Validate file
        is_valid, error = validate_file_path(audio_path, AUDIO_EXTENSIONS)
        if not is_valid:
            return make_response(False, error=error)
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, _, _ = draft_data
        
        # Parse parameters
        start = data.get('start', 0)
        target_start = data.get('target_start', 0)
        duration = data.get('duration')
        volume = data.get('volume', 1.0)
        speed = data.get('speed', 1.0)
        track_name = data.get('track_name')
        
        # Create audio material
        audio_mat = cc.AudioMaterial(audio_path)
        
        # Calculate duration
        if duration:
            segment_duration = int(duration * SEC)
        else:
            segment_duration = audio_mat.duration
        
        # Create source and target timeranges
        source_start = int(start * SEC) if start else 0
        target_start_us = int(target_start * SEC) if target_start else 0
        
        # Create audio segment
        audio_seg = cc.AudioSegment(
            audio_mat,
            trange(target_start_us, segment_duration),
            source_timerange=trange(source_start, segment_duration) if source_start else None,
            speed=speed if speed != 1.0 else None,
            volume=volume
        )
        
        # Add to script
        script.add_segment(audio_seg, track_name=track_name)
        
        return make_response(True, {
            "message": "Audio segment added successfully",
            "duration": segment_duration / SEC
        })
        
    except Exception as e:
        traceback.print_exc()
        return make_response(False, error=f"Error adding audio: {str(e)}")


# ============================================================
# TEXT ENDPOINTS
# ============================================================

@app.route('/add_text', methods=['POST'])
def add_text():
    """Add a text segment to the draft
    
    Request body:
        draft_id (str): The draft ID
        text (str): Text content
        start (float, optional): Start time in seconds, default 0
        duration (float, optional): Duration in seconds, default 5
        font (str, optional): Font name from FontType
        font_size (float, optional): Font size, default 8.0
        font_color (str, optional): Hex color '#RRGGBB', default white
        transform_x (float, optional): X position (-1 to 1), default 0
        transform_y (float, optional): Y position (-1 to 1), default 0
        bold (bool, optional): Bold text, default False
        italic (bool, optional): Italic text, default False
        vertical (bool, optional): Vertical text, default False
        track_name (str, optional): Track name
    """
    try:
        data = request.get_json()
        draft_id = data.get('draft_id')
        text = data.get('text')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        if not text:
            return make_response(False, error="Missing required parameter 'text'")
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, _, _ = draft_data
        
        # Parse parameters
        start = data.get('start', 0)
        duration = data.get('duration', 5.0)
        font = data.get('font')
        font_size = data.get('font_size', data.get('size', 8.0))
        font_color = data.get('font_color', data.get('color', '#FFFFFF'))
        transform_x = data.get('transform_x', 0)
        transform_y = data.get('transform_y', 0)
        bold = data.get('bold', False)
        italic = data.get('italic', False)
        vertical = data.get('vertical', False)
        alpha = data.get('alpha', 1.0)
        track_name = data.get('track_name')
        
        # Parse color
        color = hex_to_rgb(font_color)
        
        # Create text style
        text_style = cc.TextStyle(
            size=font_size,
            bold=bold,
            italic=italic,
            color=color,
            alpha=alpha,
            vertical=vertical
        )
        
        # Create clip settings
        clip_settings = cc.ClipSettings(
            transform_x=transform_x,
            transform_y=transform_y
        )
        
        # Get font type if specified
        font_type = None
        if font:
            try:
                font_type = getattr(cc.FontType, font, None)
            except:
                pass
        
        # Create text segment
        text_seg = cc.TextSegment(
            text,
            trange(int(start * SEC), int(duration * SEC)),
            font=font_type,
            style=text_style,
            clip_settings=clip_settings
        )
        
        # Add to script
        script.add_segment(text_seg, track_name=track_name)
        
        return make_response(True, {
            "message": "Text segment added successfully"
        })
        
    except Exception as e:
        traceback.print_exc()
        return make_response(False, error=f"Error adding text: {str(e)}")


@app.route('/add_subtitle', methods=['POST'])
def add_subtitle():
    """Add subtitles from SRT file to the draft
    
    Request body:
        draft_id (str): The draft ID
        srt_path (str): Path to the SRT file
        font (str, optional): Font name from FontType
        font_size (float, optional): Font size, default 5.0
        font_color (str, optional): Hex color '#RRGGBB', default white
        transform_y (float, optional): Y position, default -0.8 (bottom)
        time_offset (float, optional): Time offset in seconds, default 0
        track_name (str, optional): Track name
    """
    try:
        data = request.get_json()
        draft_id = data.get('draft_id')
        srt_path = data.get('srt_path') or data.get('srt')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        if not srt_path:
            return make_response(False, error="Missing required parameter 'srt_path'")
        
        # Validate file
        is_valid, error = validate_file_path(srt_path, ('.srt',))
        if not is_valid:
            return make_response(False, error=error)
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, _, _ = draft_data
        
        # Parse parameters
        font_size = data.get('font_size', 5.0)
        font_color = data.get('font_color', '#FFFFFF')
        transform_y = data.get('transform_y', -0.8)
        time_offset = data.get('time_offset', 0)
        track_name = data.get('track_name', 'subtitle')
        
        # Parse color
        color = hex_to_rgb(font_color)
        
        # Create text style for subtitles
        text_style = cc.TextStyle(
            size=font_size,
            color=color,
            align=1,  # Center align
            auto_wrapping=True
        )
        
        # Create clip settings
        clip_settings = cc.ClipSettings(transform_y=transform_y)
        
        # Add subtitle track if not exists
        try:
            script.add_track(cc.TrackType.text, track_name=track_name)
        except:
            pass
        
        # Import SRT
        script.import_srt(
            srt_path,
            track_name=track_name,
            text_style=text_style,
            clip_settings=clip_settings
        )
        
        return make_response(True, {
            "message": "Subtitles imported successfully"
        })
        
    except Exception as e:
        traceback.print_exc()
        return make_response(False, error=f"Error adding subtitles: {str(e)}")


# ============================================================
# EFFECT ENDPOINTS
# ============================================================

@app.route('/add_effect', methods=['POST'])
def add_effect():
    """Add a video effect to the draft
    
    Request body:
        draft_id (str): The draft ID
        effect_type (str): Effect type name from VideoSceneEffectType or VideoCharacterEffectType
        effect_category (str, optional): 'scene' or 'character', default 'scene'
        start (float, optional): Start time in seconds, default 0
        duration (float, optional): Duration in seconds, default 3
        params (list, optional): Effect parameters 0-100
        track_name (str, optional): Effect track name
    """
    try:
        data = request.get_json()
        draft_id = data.get('draft_id')
        effect_type_name = data.get('effect_type')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        if not effect_type_name:
            return make_response(False, error="Missing required parameter 'effect_type'")
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, _, _ = draft_data
        
        # Parse parameters
        effect_category = data.get('effect_category', 'scene')
        start = data.get('start', 0)
        duration = data.get('duration', 3.0)
        params = data.get('params')
        track_name = data.get('track_name', 'effect_01')
        
        # Get effect type
        effect_type = None
        if effect_category == 'scene':
            effect_type = getattr(cc.VideoSceneEffectType, effect_type_name, None)
        else:
            effect_type = getattr(cc.VideoCharacterEffectType, effect_type_name, None)
        
        if not effect_type:
            return make_response(False, error=f"Effect type '{effect_type_name}' not found")
        
        # Add effect track if not exists
        try:
            script.add_track(cc.TrackType.effect, track_name=track_name)
        except:
            pass
        
        # Add effect
        script.add_effect(
            effect_type,
            trange(int(start * SEC), int(duration * SEC)),
            track_name=track_name,
            params=params
        )
        
        return make_response(True, {
            "message": "Effect added successfully"
        })
        
    except Exception as e:
        traceback.print_exc()
        return make_response(False, error=f"Error adding effect: {str(e)}")


@app.route('/add_filter', methods=['POST'])
def add_filter():
    """Add a filter to the draft
    
    Request body:
        draft_id (str): The draft ID
        filter_type (str): Filter type name from FilterType
        start (float, optional): Start time in seconds, default 0
        duration (float, optional): Duration in seconds, default 3
        intensity (float, optional): Filter intensity 0-100, default 100
        track_name (str, optional): Filter track name
    """
    try:
        data = request.get_json()
        draft_id = data.get('draft_id')
        filter_type_name = data.get('filter_type')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        if not filter_type_name:
            return make_response(False, error="Missing required parameter 'filter_type'")
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, _, _ = draft_data
        
        # Parse parameters
        start = data.get('start', 0)
        duration = data.get('duration', 3.0)
        intensity = data.get('intensity', 100.0)
        track_name = data.get('track_name', 'filter_01')
        
        # Get filter type
        filter_type = getattr(cc.FilterType, filter_type_name, None)
        if not filter_type:
            return make_response(False, error=f"Filter type '{filter_type_name}' not found")
        
        # Add filter track if not exists
        try:
            script.add_track(cc.TrackType.filter, track_name=track_name)
        except:
            pass
        
        # Add filter
        script.add_filter(
            filter_type,
            trange(int(start * SEC), int(duration * SEC)),
            track_name=track_name,
            intensity=intensity
        )
        
        return make_response(True, {
            "message": "Filter added successfully"
        })
        
    except Exception as e:
        traceback.print_exc()
        return make_response(False, error=f"Error adding filter: {str(e)}")


@app.route('/add_transition', methods=['POST'])
def add_transition():
    """Add a transition between video segments
    
    Request body:
        draft_id (str): The draft ID
        transition_type (str): Transition type name from TransitionType
        segment_index (int, optional): Index of the video segment to add transition to (0-based), default 0
        duration (float, optional): Transition duration in seconds, default uses transition's default
        track_name (str, optional): Video track name
    
    Note: Transitions are added to the END of a segment to transition to the NEXT segment.
    """
    try:
        data = request.get_json()
        draft_id = data.get('draft_id')
        transition_type_name = data.get('transition_type')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        if not transition_type_name:
            return make_response(False, error="Missing required parameter 'transition_type'")
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, _, _ = draft_data
        
        # Parse parameters
        segment_index = data.get('segment_index', 0)
        duration = data.get('duration')
        track_name = data.get('track_name')
        
        # Get transition type
        transition_type = getattr(cc.TransitionType, transition_type_name, None)
        if not transition_type:
            return make_response(False, error=f"Transition type '{transition_type_name}' not found")
        
        # Find the video track and segment
        video_track = None
        for name, track in script.tracks.items():
            if track.track_type == cc.TrackType.video:
                if track_name is None or name == track_name:
                    video_track = track
                    break
        
        if not video_track:
            return make_response(False, error="No video track found")
        
        if segment_index >= len(video_track.segments):
            return make_response(False, error=f"Segment index {segment_index} out of range (0-{len(video_track.segments)-1})")
        
        # Add transition to the segment
        segment = video_track.segments[segment_index]
        if duration:
            segment.add_transition(transition_type, duration=int(duration * SEC))
        else:
            segment.add_transition(transition_type)
        
        # Add transition material to script
        script.materials.transitions.append(segment.transition)
        
        return make_response(True, {
            "message": "Transition added successfully"
        })
        
    except Exception as e:
        traceback.print_exc()
        return make_response(False, error=f"Error adding transition: {str(e)}")


@app.route('/add_intro', methods=['POST'])
def add_intro_animation():
    """Add an intro animation to a video segment
    
    Request body:
        draft_id (str): The draft ID
        intro_type (str): Intro animation type name from IntroType
        segment_index (int, optional): Index of the video segment (0-based), default 0
        duration (float, optional): Animation duration in seconds, default uses animation's default
        track_name (str, optional): Video track name
    """
    try:
        data = request.get_json()
        draft_id = data.get('draft_id')
        intro_type_name = data.get('intro_type')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        if not intro_type_name:
            return make_response(False, error="Missing required parameter 'intro_type'")
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, _, _ = draft_data
        
        # Parse parameters
        segment_index = data.get('segment_index', 0)
        duration = data.get('duration')
        track_name = data.get('track_name')
        
        # Get intro type
        intro_type = getattr(cc.IntroType, intro_type_name, None)
        if not intro_type:
            return make_response(False, error=f"Intro type '{intro_type_name}' not found")
        
        # Find the video track and segment
        video_track = None
        for name, track in script.tracks.items():
            if track.track_type == cc.TrackType.video:
                if track_name is None or name == track_name:
                    video_track = track
                    break
        
        if not video_track:
            return make_response(False, error="No video track found")
        
        if segment_index >= len(video_track.segments):
            return make_response(False, error=f"Segment index {segment_index} out of range (0-{len(video_track.segments)-1})")
        
        # Add animation to the segment
        segment = video_track.segments[segment_index]
        if duration:
            segment.add_animation(intro_type, duration=int(duration * SEC))
        else:
            segment.add_animation(intro_type)
        
        # Add animation material to script
        if segment.animations_instance is not None:
            if segment.animations_instance not in script.materials.animations:
                script.materials.animations.append(segment.animations_instance)
        
        return make_response(True, {
            "message": "Intro animation added successfully"
        })
        
    except Exception as e:
        traceback.print_exc()
        return make_response(False, error=f"Error adding intro animation: {str(e)}")


@app.route('/add_audio_effect', methods=['POST'])
def add_audio_effect():
    """Add an audio effect to an audio segment
    
    Request body:
        draft_id (str): The draft ID
        effect_type (str): Audio effect type name from AudioSceneEffectType
        segment_index (int, optional): Index of the audio segment (0-based), default 0
        params (list, optional): Effect parameters 0-100
        track_name (str, optional): Audio track name
    """
    try:
        data = request.get_json()
        draft_id = data.get('draft_id')
        effect_type_name = data.get('effect_type')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        if not effect_type_name:
            return make_response(False, error="Missing required parameter 'effect_type'")
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, _, _ = draft_data
        
        # Parse parameters
        segment_index = data.get('segment_index', 0)
        params = data.get('params')
        track_name = data.get('track_name')
        
        # Get audio effect type
        effect_type = getattr(cc.AudioSceneEffectType, effect_type_name, None)
        if not effect_type:
            return make_response(False, error=f"Audio effect type '{effect_type_name}' not found")
        
        # Find the audio track and segment
        audio_track = None
        for name, track in script.tracks.items():
            if track.track_type == cc.TrackType.audio:
                if track_name is None or name == track_name:
                    audio_track = track
                    break
        
        if not audio_track:
            return make_response(False, error="No audio track found")
        
        if segment_index >= len(audio_track.segments):
            return make_response(False, error=f"Segment index {segment_index} out of range (0-{len(audio_track.segments)-1})")
        
        # Add effect to the segment
        segment = audio_track.segments[segment_index]
        segment.add_effect(effect_type, params=params)
        
        # Add effect material to script
        for effect in segment.effects:
            if effect not in script.materials.audio_effects:
                script.materials.audio_effects.append(effect)
        
        return make_response(True, {
            "message": "Audio effect added successfully"
        })
        
    except Exception as e:
        traceback.print_exc()
        return make_response(False, error=f"Error adding audio effect: {str(e)}")


@app.route('/add_tone_effect', methods=['POST'])
def add_tone_effect():
    """Add a tone/voice changer effect to an audio segment
    
    Request body:
        draft_id (str): The draft ID
        effect_type (str): Tone effect type name from ToneEffectType (e.g., "大叔", "女生", "机器人")
        segment_index (int, optional): Index of the audio segment (0-based), default 0
        params (list, optional): Effect parameters 0-100
        track_name (str, optional): Audio track name
    """
    try:
        from pycapcut.metadata.tone_effect import ToneEffectType
        
        data = request.get_json()
        draft_id = data.get('draft_id')
        effect_type_name = data.get('effect_type')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        if not effect_type_name:
            return make_response(False, error="Missing required parameter 'effect_type'")
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, _, _ = draft_data
        
        # Parse parameters
        segment_index = data.get('segment_index', 0)
        params = data.get('params')
        track_name = data.get('track_name')
        
        # Get tone effect type
        effect_type = getattr(ToneEffectType, effect_type_name, None)
        if not effect_type:
            return make_response(False, error=f"Tone effect type '{effect_type_name}' not found")
        
        # Find the audio track and segment
        audio_track = None
        for name, track in script.tracks.items():
            if track.track_type == cc.TrackType.audio:
                if track_name is None or name == track_name:
                    audio_track = track
                    break
        
        if not audio_track:
            return make_response(False, error="No audio track found")
        
        if segment_index >= len(audio_track.segments):
            return make_response(False, error=f"Segment index {segment_index} out of range (0-{len(audio_track.segments)-1})")
        
        # Add tone effect to the segment
        segment = audio_track.segments[segment_index]
        
        # Import AudioEffect to create the effect
        from pycapcut.audio_segment import AudioEffect
        effect_inst = AudioEffect(effect_type, params)
        
        # Check if this category already exists
        if effect_inst.category_id in [eff.category_id for eff in segment.effects]:
            return make_response(False, error="This audio segment already has a tone effect")
        
        segment.effects.append(effect_inst)
        segment.extra_material_refs.append(effect_inst.effect_id)
        
        # Add effect material to script
        if effect_inst not in script.materials.audio_effects:
            script.materials.audio_effects.append(effect_inst)
        
        return make_response(True, {
            "message": f"Tone effect '{effect_type_name}' added successfully"
        })
        
    except Exception as e:
        traceback.print_exc()
        return make_response(False, error=f"Error adding tone effect: {str(e)}")


@app.route('/add_speech_to_song', methods=['POST'])
def add_speech_to_song():
    """Add a speech-to-song effect to an audio segment
    
    Request body:
        draft_id (str): The draft ID
        effect_type (str): Speech-to-song type name from SpeechToSongType (e.g., "Lofi", "民谣", "嘻哈")
        segment_index (int, optional): Index of the audio segment (0-based), default 0
        params (list, optional): Effect parameters 0-100
        track_name (str, optional): Audio track name
    """
    try:
        from pycapcut.metadata.speech_to_song import SpeechToSongType
        
        data = request.get_json()
        draft_id = data.get('draft_id')
        effect_type_name = data.get('effect_type')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        if not effect_type_name:
            return make_response(False, error="Missing required parameter 'effect_type'")
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, _, _ = draft_data
        
        # Parse parameters
        segment_index = data.get('segment_index', 0)
        params = data.get('params')
        track_name = data.get('track_name')
        
        # Get speech to song type
        effect_type = getattr(SpeechToSongType, effect_type_name, None)
        if not effect_type:
            return make_response(False, error=f"Speech-to-song type '{effect_type_name}' not found")
        
        # Find the audio track and segment
        audio_track = None
        for name, track in script.tracks.items():
            if track.track_type == cc.TrackType.audio:
                if track_name is None or name == track_name:
                    audio_track = track
                    break
        
        if not audio_track:
            return make_response(False, error="No audio track found")
        
        if segment_index >= len(audio_track.segments):
            return make_response(False, error=f"Segment index {segment_index} out of range (0-{len(audio_track.segments)-1})")
        
        # Add speech-to-song effect to the segment
        segment = audio_track.segments[segment_index]
        
        # Import AudioEffect to create the effect
        from pycapcut.audio_segment import AudioEffect
        effect_inst = AudioEffect(effect_type, params)
        
        # Check if this category already exists
        if effect_inst.category_id in [eff.category_id for eff in segment.effects]:
            return make_response(False, error="This audio segment already has a speech-to-song effect")
        
        segment.effects.append(effect_inst)
        segment.extra_material_refs.append(effect_inst.effect_id)
        
        # Add effect material to script
        if effect_inst not in script.materials.audio_effects:
            script.materials.audio_effects.append(effect_inst)
        
        return make_response(True, {
            "message": f"Speech-to-song effect '{effect_type_name}' added successfully"
        })
        
    except Exception as e:
        traceback.print_exc()
        return make_response(False, error=f"Error adding speech-to-song effect: {str(e)}")


@app.route('/add_video_fade', methods=['POST'])
def add_video_fade():
    """Add audio fade in/out effect to a video segment (affects the video's audio track)
    
    Request body:
        draft_id (str): The draft ID
        fade_in (float, optional): Fade in duration in seconds, default 0
        fade_out (float, optional): Fade out duration in seconds, default 0
        segment_index (int, optional): Index of the video segment (0-based), default 0
        track_name (str, optional): Video track name
    """
    try:
        data = request.get_json()
        draft_id = data.get('draft_id')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, _, _ = draft_data
        
        # Parse parameters
        fade_in = data.get('fade_in', 0)
        fade_out = data.get('fade_out', 0)
        segment_index = data.get('segment_index', 0)
        track_name = data.get('track_name')
        
        if fade_in <= 0 and fade_out <= 0:
            return make_response(False, error="At least one of 'fade_in' or 'fade_out' must be greater than 0")
        
        # Find the video track and segment
        video_track = None
        for name, track in script.tracks.items():
            if track.track_type == cc.TrackType.video:
                if track_name is None or name == track_name:
                    video_track = track
                    break
        
        if not video_track:
            return make_response(False, error="No video track found")
        
        if segment_index >= len(video_track.segments):
            return make_response(False, error=f"Segment index {segment_index} out of range (0-{len(video_track.segments)-1})")
        
        # Add fade to the video segment
        segment = video_track.segments[segment_index]
        segment.add_fade(int(fade_in * SEC), int(fade_out * SEC))
        
        # Add fade material to script
        if segment.fade is not None:
            if segment.fade not in script.materials.audio_fades:
                script.materials.audio_fades.append(segment.fade)
        
        return make_response(True, {
            "message": "Video fade added successfully"
        })
        
    except Exception as e:
        traceback.print_exc()
        return make_response(False, error=f"Error adding video fade: {str(e)}")


@app.route('/add_background_filling', methods=['POST'])
def add_background_filling():
    """Add background filling to a video segment (blur or solid color background)
    
    Request body:
        draft_id (str): The draft ID
        fill_type (str): Fill type - 'blur' or 'color'
        blur (float, optional): Blur intensity 0.0-1.0, default 0.0625 (CapCut levels: 0.0625, 0.375, 0.75, 1.0)
        color (str, optional): Fill color in '#RRGGBBAA' format, default '#00000000'
        segment_index (int, optional): Index of the video segment (0-based), default 0
        track_name (str, optional): Video track name
    
    Note: Background filling only works on the bottom video track.
    """
    try:
        data = request.get_json()
        draft_id = data.get('draft_id')
        fill_type = data.get('fill_type')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        if not fill_type:
            return make_response(False, error="Missing required parameter 'fill_type'")
        if fill_type not in ['blur', 'color']:
            return make_response(False, error="fill_type must be 'blur' or 'color'")
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, _, _ = draft_data
        
        # Parse parameters
        blur = data.get('blur', 0.0625)
        color = data.get('color', '#00000000')
        segment_index = data.get('segment_index', 0)
        track_name = data.get('track_name')
        
        # Find the video track and segment
        video_track = None
        for name, track in script.tracks.items():
            if track.track_type == cc.TrackType.video:
                if track_name is None or name == track_name:
                    video_track = track
                    break
        
        if not video_track:
            return make_response(False, error="No video track found")
        
        if segment_index >= len(video_track.segments):
            return make_response(False, error=f"Segment index {segment_index} out of range (0-{len(video_track.segments)-1})")
        
        # Add background filling to the video segment
        segment = video_track.segments[segment_index]
        segment.add_background_filling(fill_type, blur=blur, color=color)
        
        # Add to materials (canvases)
        if segment.background_filling is not None:
            script.materials.canvases.append(segment.background_filling)
        
        return make_response(True, {
            "message": f"Background filling ({fill_type}) added successfully"
        })
        
    except Exception as e:
        traceback.print_exc()
        return make_response(False, error=f"Error adding background filling: {str(e)}")


@app.route('/add_video_effect', methods=['POST'])
def add_video_segment_effect():
    """Add a video effect directly to a video segment (instead of using effect track)
    
    Request body:
        draft_id (str): The draft ID
        effect_type (str): Effect type name from VideoSceneEffectType or VideoCharacterEffectType
        effect_category (str, optional): 'scene' or 'character', default 'scene'
        segment_index (int, optional): Index of the video segment (0-based), default 0
        params (list, optional): Effect parameters 0-100
        track_name (str, optional): Video track name
    """
    try:
        data = request.get_json()
        draft_id = data.get('draft_id')
        effect_type_name = data.get('effect_type')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        if not effect_type_name:
            return make_response(False, error="Missing required parameter 'effect_type'")
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, _, _ = draft_data
        
        # Parse parameters
        effect_category = data.get('effect_category', 'scene')
        segment_index = data.get('segment_index', 0)
        params = data.get('params')
        track_name = data.get('track_name')
        
        # Get effect type
        effect_type = None
        if effect_category == 'scene':
            effect_type = getattr(cc.VideoSceneEffectType, effect_type_name, None)
        else:
            effect_type = getattr(cc.VideoCharacterEffectType, effect_type_name, None)
        
        if not effect_type:
            return make_response(False, error=f"Effect type '{effect_type_name}' not found")
        
        # Find the video track and segment
        video_track = None
        for name, track in script.tracks.items():
            if track.track_type == cc.TrackType.video:
                if track_name is None or name == track_name:
                    video_track = track
                    break
        
        if not video_track:
            return make_response(False, error="No video track found")
        
        if segment_index >= len(video_track.segments):
            return make_response(False, error=f"Segment index {segment_index} out of range (0-{len(video_track.segments)-1})")
        
        # Add effect to the video segment
        segment = video_track.segments[segment_index]
        segment.add_effect(effect_type, params=params)
        
        # Add effect materials to script
        for effect in segment.effects:
            if effect not in script.materials.video_effects:
                script.materials.video_effects.append(effect)
        
        return make_response(True, {
            "message": f"Video effect '{effect_type_name}' added to segment successfully"
        })
        
    except Exception as e:
        traceback.print_exc()
        return make_response(False, error=f"Error adding video effect: {str(e)}")


@app.route('/add_outro', methods=['POST'])
def add_outro_animation():
    """Add an outro animation to a video segment
    
    Request body:
        draft_id (str): The draft ID
        outro_type (str): Outro animation type name from OutroType
        segment_index (int, optional): Index of the video segment (0-based), default 0
        duration (float, optional): Animation duration in seconds, default uses animation's default
        track_name (str, optional): Video track name
    """
    try:
        data = request.get_json()
        draft_id = data.get('draft_id')
        outro_type_name = data.get('outro_type')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        if not outro_type_name:
            return make_response(False, error="Missing required parameter 'outro_type'")
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, _, _ = draft_data
        
        # Parse parameters
        segment_index = data.get('segment_index', 0)
        duration = data.get('duration')
        track_name = data.get('track_name')
        
        # Get outro type
        outro_type = getattr(cc.OutroType, outro_type_name, None)
        if not outro_type:
            return make_response(False, error=f"Outro type '{outro_type_name}' not found")
        
        # Find the video track and segment
        video_track = None
        for name, track in script.tracks.items():
            if track.track_type == cc.TrackType.video:
                if track_name is None or name == track_name:
                    video_track = track
                    break
        
        if not video_track:
            return make_response(False, error="No video track found")
        
        if segment_index >= len(video_track.segments):
            return make_response(False, error=f"Segment index {segment_index} out of range (0-{len(video_track.segments)-1})")
        
        # Add animation to the segment
        segment = video_track.segments[segment_index]
        if duration:
            segment.add_animation(outro_type, duration=int(duration * SEC))
        else:
            segment.add_animation(outro_type)
        
        # Add animation material to script
        if segment.animations_instance is not None:
            if segment.animations_instance not in script.materials.animations:
                script.materials.animations.append(segment.animations_instance)
        
        return make_response(True, {
            "message": "Outro animation added successfully"
        })
        
    except Exception as e:
        traceback.print_exc()
        return make_response(False, error=f"Error adding outro animation: {str(e)}")


@app.route('/add_sticker', methods=['POST'])
def add_sticker():
    """Add a sticker segment to the draft
    
    Request body:
        draft_id (str): The draft ID
        resource_id (str): Sticker resource ID (from template inspection)
        start (float, optional): Position on timeline in seconds, default 0
        duration (float, optional): Display duration in seconds, default 3
        transform_x (float, optional): X position (-1 to 1), default 0
        transform_y (float, optional): Y position (-1 to 1), default 0
        scale_x (float, optional): X scale, default 1
        scale_y (float, optional): Y scale, default 1
        track_name (str, optional): Track name
    """
    try:
        data = request.get_json()
        draft_id = data.get('draft_id')
        resource_id = data.get('resource_id')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        if not resource_id:
            return make_response(False, error="Missing required parameter 'resource_id'")
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, _, _ = draft_data
        
        # Parse parameters
        start = data.get('start', 0)
        duration = data.get('duration', 3.0)
        transform_x = data.get('transform_x', 0)
        transform_y = data.get('transform_y', 0)
        scale_x = data.get('scale_x', 1)
        scale_y = data.get('scale_y', 1)
        track_name = data.get('track_name')
        
        # Create clip settings
        clip_settings = cc.ClipSettings(
            transform_x=transform_x,
            transform_y=transform_y,
            scale_x=scale_x,
            scale_y=scale_y
        )
        
        # Create sticker segment
        sticker_seg = cc.StickerSegment(
            resource_id,
            trange(int(start * SEC), int(duration * SEC)),
            clip_settings=clip_settings
        )
        
        # Add sticker track if needed
        try:
            script.add_track(cc.TrackType.sticker, track_name=track_name or 'sticker')
        except:
            pass
        
        # Add to script
        script.add_segment(sticker_seg, track_name=track_name or 'sticker')
        
        return make_response(True, {
            "message": "Sticker added successfully",
            "duration": duration
        })
        
    except Exception as e:
        traceback.print_exc()
        return make_response(False, error=f"Error adding sticker: {str(e)}")


@app.route('/add_mask', methods=['POST'])
def add_mask():
    """Add a mask to a video segment
    
    Request body:
        draft_id (str): The draft ID
        mask_type (str): Mask type name from MaskType
        segment_index (int, optional): Index of the video segment (0-based), default 0
        track_name (str, optional): Video track name
    """
    try:
        data = request.get_json()
        draft_id = data.get('draft_id')
        mask_type_name = data.get('mask_type')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        if not mask_type_name:
            return make_response(False, error="Missing required parameter 'mask_type'")
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, _, _ = draft_data
        
        # Parse parameters
        segment_index = data.get('segment_index', 0)
        track_name = data.get('track_name')
        
        # Get mask type
        mask_type = getattr(cc.MaskType, mask_type_name, None)
        if not mask_type:
            return make_response(False, error=f"Mask type '{mask_type_name}' not found")
        
        # Find the video track and segment
        video_track = None
        for name, track in script.tracks.items():
            if track.track_type == cc.TrackType.video:
                if track_name is None or name == track_name:
                    video_track = track
                    break
        
        if not video_track:
            return make_response(False, error="No video track found")
        
        if segment_index >= len(video_track.segments):
            return make_response(False, error=f"Segment index {segment_index} out of range (0-{len(video_track.segments)-1})")
        
        # Add mask to the segment
        segment = video_track.segments[segment_index]
        segment.add_mask(mask_type)
        
        # Add mask material to script
        if segment.mask is not None:
            if segment.mask not in script.materials.masks:
                script.materials.masks.append(segment.mask)
        
        return make_response(True, {
            "message": "Mask added successfully"
        })
        
    except Exception as e:
        traceback.print_exc()
        return make_response(False, error=f"Error adding mask: {str(e)}")


@app.route('/add_audio_fade', methods=['POST'])
def add_audio_fade():
    """Add fade in/out effect to an audio segment
    
    Request body:
        draft_id (str): The draft ID
        fade_in (float, optional): Fade in duration in seconds, default 0
        fade_out (float, optional): Fade out duration in seconds, default 0
        segment_index (int, optional): Index of the audio segment (0-based), default 0
        track_name (str, optional): Audio track name
    """
    try:
        data = request.get_json()
        draft_id = data.get('draft_id')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, _, _ = draft_data
        
        # Parse parameters
        fade_in = data.get('fade_in', 0)
        fade_out = data.get('fade_out', 0)
        segment_index = data.get('segment_index', 0)
        track_name = data.get('track_name')
        
        if fade_in <= 0 and fade_out <= 0:
            return make_response(False, error="At least one of 'fade_in' or 'fade_out' must be greater than 0")
        
        # Find the audio track and segment
        audio_track = None
        for name, track in script.tracks.items():
            if track.track_type == cc.TrackType.audio:
                if track_name is None or name == track_name:
                    audio_track = track
                    break
        
        if not audio_track:
            return make_response(False, error="No audio track found")
        
        if segment_index >= len(audio_track.segments):
            return make_response(False, error=f"Segment index {segment_index} out of range (0-{len(audio_track.segments)-1})")
        
        # Add fade to the segment
        segment = audio_track.segments[segment_index]
        segment.add_fade(int(fade_in * SEC), int(fade_out * SEC))
        
        # Add fade material to script
        if segment.fade is not None:
            if segment.fade not in script.materials.audio_fades:
                script.materials.audio_fades.append(segment.fade)
        
        return make_response(True, {
            "message": "Audio fade added successfully"
        })
        
    except Exception as e:
        traceback.print_exc()
        return make_response(False, error=f"Error adding audio fade: {str(e)}")


@app.route('/add_text_animation', methods=['POST'])
def add_text_animation():
    """Add intro/outro animation to a text segment
    
    Request body:
        draft_id (str): The draft ID
        animation_type (str): Animation type name from TextIntro or TextOutro
        animation_category (str, optional): 'intro' or 'outro', default 'intro'
        segment_index (int, optional): Index of the text segment (0-based), default 0
        duration (float, optional): Animation duration in seconds
        track_name (str, optional): Text track name
    """
    try:
        data = request.get_json()
        draft_id = data.get('draft_id')
        animation_type_name = data.get('animation_type')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        if not animation_type_name:
            return make_response(False, error="Missing required parameter 'animation_type'")
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, _, _ = draft_data
        
        # Parse parameters
        animation_category = data.get('animation_category', 'intro')
        segment_index = data.get('segment_index', 0)
        duration = data.get('duration')
        track_name = data.get('track_name')
        
        # Get animation type
        if animation_category == 'intro':
            animation_type = getattr(cc.TextIntro, animation_type_name, None)
        else:
            animation_type = getattr(cc.TextOutro, animation_type_name, None)
        
        if not animation_type:
            return make_response(False, error=f"Animation type '{animation_type_name}' not found in {animation_category}")
        
        # Find the text track and segment
        text_track = None
        for name, track in script.tracks.items():
            if track.track_type == cc.TrackType.text:
                if track_name is None or name == track_name:
                    text_track = track
                    break
        
        if not text_track:
            return make_response(False, error="No text track found")
        
        if segment_index >= len(text_track.segments):
            return make_response(False, error=f"Segment index {segment_index} out of range (0-{len(text_track.segments)-1})")
        
        # Add animation to the segment
        segment = text_track.segments[segment_index]
        if duration:
            segment.add_animation(animation_type, duration=int(duration * SEC))
        else:
            segment.add_animation(animation_type)
        
        # Add animation material to script
        if segment.animations_instance is not None:
            if segment.animations_instance not in script.materials.animations:
                script.materials.animations.append(segment.animations_instance)
        
        return make_response(True, {
            "message": f"Text {animation_category} animation added successfully"
        })
        
    except Exception as e:
        traceback.print_exc()
        return make_response(False, error=f"Error adding text animation: {str(e)}")


@app.route('/delete_draft', methods=['POST'])
def delete_draft():
    """Delete a draft from cache
    
    Request body:
        draft_id (str): The draft ID to delete
    """
    try:
        data = request.get_json()
        draft_id = data.get('draft_id')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        
        success = remove_draft(draft_id)
        if not success:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        return make_response(True, {
            "message": f"Draft {draft_id} deleted successfully"
        })
        
    except Exception as e:
        return make_response(False, error=f"Error deleting draft: {str(e)}")


@app.route('/get_draft_info', methods=['POST'])
def get_draft_info():
    """Get information about a draft
    
    Request body:
        draft_id (str): The draft ID
    """
    try:
        data = request.get_json()
        draft_id = data.get('draft_id')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, draft_folder_path, draft_name = draft_data
        
        # Count segments in each track
        track_info = {}
        for name, track in script.tracks.items():
            track_info[name] = {
                "type": track.track_type.name,
                "segments": len(track.segments)
            }
        
        return make_response(True, {
            "draft_id": draft_id,
            "draft_name": draft_name,
            "draft_folder": draft_folder_path,
            "width": script.width,
            "height": script.height,
            "fps": script.fps,
            "duration": script.duration / SEC,
            "tracks": track_info
        })
        
    except Exception as e:
        return make_response(False, error=f"Error getting draft info: {str(e)}")


@app.route('/get_filter_types', methods=['GET'])
def get_filter_types():
    """Get available filter types"""
    try:
        filter_types = [{"name": name} for name in cc.FilterType.__members__.keys()]
        return make_response(True, filter_types)
    except Exception as e:
        return make_response(False, error=f"Error getting filter types: {str(e)}")


@app.route('/get_text_loop_types', methods=['GET'])
def get_text_loop_types():
    """Get available text loop animation types"""
    try:
        animation_types = [{"name": name} for name in cc.TextLoopAnim.__members__.keys()]
        return make_response(True, animation_types)
    except Exception as e:
        return make_response(False, error=f"Error getting text loop types: {str(e)}")


@app.route('/get_video_scene_effect_types', methods=['GET'])
def get_video_scene_effect_types():
    """Get available video scene effect types"""
    try:
        effect_types = [{"name": name, "is_vip": cc.VideoSceneEffectType[name].value.is_vip} 
                        for name in cc.VideoSceneEffectType.__members__.keys()]
        return make_response(True, effect_types)
    except Exception as e:
        return make_response(False, error=f"Error getting video scene effect types: {str(e)}")


@app.route('/get_video_character_effect_types', methods=['GET'])
def get_video_character_effect_types():
    """Get available video character effect types (face effects)"""
    try:
        effect_types = [{"name": name, "is_vip": cc.VideoCharacterEffectType[name].value.is_vip} 
                        for name in cc.VideoCharacterEffectType.__members__.keys()]
        return make_response(True, effect_types)
    except Exception as e:
        return make_response(False, error=f"Error getting video character effect types: {str(e)}")


@app.route('/get_audio_effect_types', methods=['GET'])
def get_audio_effect_types():
    """Get available audio scene effect types"""
    try:
        effect_types = [{"name": name, "is_vip": cc.AudioSceneEffectType[name].value.is_vip} 
                        for name in cc.AudioSceneEffectType.__members__.keys()]
        return make_response(True, effect_types)
    except Exception as e:
        return make_response(False, error=f"Error getting audio effect types: {str(e)}")


@app.route('/get_tone_effect_types', methods=['GET'])
def get_tone_effect_types():
    """Get available tone effect types (voice changer effects)"""
    try:
        from pycapcut.metadata.tone_effect import ToneEffectType
        tone_types = [{"name": name, "is_vip": ToneEffectType[name].value.is_vip} 
                      for name in ToneEffectType.__members__.keys()]
        return make_response(True, tone_types)
    except Exception as e:
        return make_response(False, error=f"Error getting tone effect types: {str(e)}")


@app.route('/get_speech_to_song_types', methods=['GET'])
def get_speech_to_song_types():
    """Get available speech-to-song effect types"""
    try:
        from pycapcut.metadata.speech_to_song import SpeechToSongType
        song_types = [{"name": name, "is_vip": SpeechToSongType[name].value.is_vip} 
                      for name in SpeechToSongType.__members__.keys()]
        return make_response(True, song_types)
    except Exception as e:
        return make_response(False, error=f"Error getting speech to song types: {str(e)}")


# ============================================================
# METADATA QUERY ENDPOINTS
# ============================================================

@app.route('/get_intro_animation_types', methods=['GET'])
def get_intro_animation_types():
    """Get available intro animation types"""
    try:
        animation_types = [{"name": name} for name in cc.IntroType.__members__.keys()]
        return make_response(True, animation_types)
    except Exception as e:
        return make_response(False, error=f"Error getting intro animation types: {str(e)}")


@app.route('/get_outro_animation_types', methods=['GET'])
def get_outro_animation_types():
    """Get available outro animation types"""
    try:
        animation_types = [{"name": name} for name in cc.OutroType.__members__.keys()]
        return make_response(True, animation_types)
    except Exception as e:
        return make_response(False, error=f"Error getting outro animation types: {str(e)}")


@app.route('/get_combo_animation_types', methods=['GET'])
def get_combo_animation_types():
    """Get available combo/group animation types"""
    try:
        animation_types = [{"name": name} for name in cc.GroupAnimationType.__members__.keys()]
        return make_response(True, animation_types)
    except Exception as e:
        return make_response(False, error=f"Error getting combo animation types: {str(e)}")


@app.route('/get_transition_types', methods=['GET'])
def get_transition_types():
    """Get available transition types"""
    try:
        transition_types = [{"name": name} for name in cc.TransitionType.__members__.keys()]
        return make_response(True, transition_types)
    except Exception as e:
        return make_response(False, error=f"Error getting transition types: {str(e)}")


@app.route('/get_font_types', methods=['GET'])
def get_font_types():
    """Get available font types"""
    try:
        font_types = [{"name": name} for name in cc.FontType.__members__.keys()]
        return make_response(True, font_types)
    except Exception as e:
        return make_response(False, error=f"Error getting font types: {str(e)}")


@app.route('/get_mask_types', methods=['GET'])
def get_mask_types():
    """Get available mask types"""
    try:
        mask_types = [{"name": name} for name in cc.MaskType.__members__.keys()]
        return make_response(True, mask_types)
    except Exception as e:
        return make_response(False, error=f"Error getting mask types: {str(e)}")


@app.route('/get_text_intro_types', methods=['GET'])
def get_text_intro_types():
    """Get available text intro animation types"""
    try:
        animation_types = [{"name": name} for name in cc.TextIntro.__members__.keys()]
        return make_response(True, animation_types)
    except Exception as e:
        return make_response(False, error=f"Error getting text intro types: {str(e)}")


@app.route('/get_text_outro_types', methods=['GET'])
def get_text_outro_types():
    """Get available text outro animation types"""
    try:
        animation_types = [{"name": name} for name in cc.TextOutro.__members__.keys()]
        return make_response(True, animation_types)
    except Exception as e:
        return make_response(False, error=f"Error getting text outro types: {str(e)}")


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return make_response(True, {"status": "healthy", "service": "pyCapCut API Server"})


@app.route('/', methods=['GET'])
def index():
    """API info endpoint"""
    return make_response(True, {
        "service": "pyCapCut API Server",
        "version": "2.0.0",
        "endpoints": {
            "draft_management": [
                "POST /create_draft",
                "POST /save_draft",
                "POST /delete_draft",
                "POST /get_draft_info",
                "GET /list_drafts"
            ],
            "media": [
                "POST /add_video",
                "POST /add_audio",
                "POST /add_image",
                "POST /add_sticker"
            ],
            "text": [
                "POST /add_text",
                "POST /add_subtitle",
                "POST /add_text_animation"
            ],
            "effects": [
                "POST /add_effect",
                "POST /add_video_effect",
                "POST /add_filter",
                "POST /add_transition",
                "POST /add_intro",
                "POST /add_outro",
                "POST /add_mask",
                "POST /add_background_filling",
                "POST /add_audio_effect",
                "POST /add_tone_effect",
                "POST /add_speech_to_song",
                "POST /add_audio_fade",
                "POST /add_video_fade"
            ],
            "metadata": [
                "GET /get_font_types",
                "GET /get_filter_types",
                "GET /get_mask_types",
                "GET /get_transition_types",
                "GET /get_intro_animation_types",
                "GET /get_outro_animation_types",
                "GET /get_combo_animation_types",
                "GET /get_video_scene_effect_types",
                "GET /get_video_character_effect_types",
                "GET /get_audio_effect_types",
                "GET /get_tone_effect_types",
                "GET /get_speech_to_song_types",
                "GET /get_text_intro_types",
                "GET /get_text_outro_types",
                "GET /get_text_loop_types"
            ],
            "system": [
                "GET /health"
            ]
        }
    })


if __name__ == '__main__':
    print(f"🚀 pyCapCut API Server starting on port {PORT}...")
    print(f"📁 Default draft folder: {DRAFT_FOLDER}")
    print(f"🔧 Debug mode: {DEBUG}")
    print(f"\n📖 API documentation available at: http://localhost:{PORT}/")
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)
