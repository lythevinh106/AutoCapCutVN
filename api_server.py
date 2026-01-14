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

# Import Pydantic models for composite endpoint validation
from model import EditRequest
from pydantic import ValidationError

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
# COMPOSITE PROJECT API ENDPOINT
# ============================================================

@app.route('/create_amv_project_video', methods=['POST'])
def create_amv_project_video():
    """
    Create a complete video project from a single JSON request.
    
    This is a composite endpoint that:
    1. Validates the request using Pydantic models
    2. Creates a new draft
    3. Processes video_sequence (REQUIRED)
    4. Processes optional components: audios, effects, filters, images, texts
    5. Saves the draft and returns the result
    
    Request body: See EditRequest model in model.py
    
    Returns:
        200: Success with draft_id and project info
        400: Validation error with details
    """
    try:
        # ===== 1. GET RAW JSON =====
        raw_json = request.get_json()
        if not raw_json:
            return jsonify({
                "success": False,
                "output": "",
                "error": "Request body is required"
            }), 400
        
        # ===== 2. VALIDATE WITH PYDANTIC =====
        try:
            edit_request = EditRequest(**raw_json)
        except ValidationError as ve:
            # Format Pydantic validation errors
            errors = []
            for error in ve.errors():
                field = " -> ".join(str(loc) for loc in error['loc'])
                msg = error['msg']
                errors.append(f"{field}: {msg}")
            
            return jsonify({
                "success": False,
                "output": "",
                "error": f"Validation failed: {'; '.join(errors)}"
            }), 400
        
        # ===== 3. CREATE DRAFT =====
        canvas = edit_request.canvas_config
        draft_name = f"project_{generate_draft_id()[:8]}"
        draft_folder_path = DRAFT_FOLDER
        
        # Initialize DraftFolder
        draft_folder = cc.DraftFolder(draft_folder_path)
        
        # Create the draft with canvas config
        script = draft_folder.create_draft(
            draft_name,
            canvas.width,
            canvas.height,
            fps=canvas.fps,
            allow_replace=True
        )
        
        # Add default tracks
        script.add_track(cc.TrackType.video)
        script.add_track(cc.TrackType.audio)
        script.add_track(cc.TrackType.text)
        
        # Generate draft ID and store in cache
        draft_id = generate_draft_id()
        store_draft(draft_id, script, draft_folder_path, draft_name)
        
        # ===== 4. PROCESS EACH COMPONENT =====
        processing_results = {
            "video_sequence": {"count": 0, "status": "pending"},
            "per_video_effects": {"count": 0, "status": "pending"},
            "audios": {"count": 0, "status": "pending"},
            "effects": {"count": 0, "status": "pending"},
            "filters": {"count": 0, "status": "pending"},
            "images": {"count": 0, "status": "pending"},
            "texts": {"count": 0, "status": "pending"}
        }
        
        # --- 4.1 VIDEO SEQUENCE (Required) ---
        # Import animation types for video
        from pycapcut.metadata.video_intro import IntroType
        from pycapcut.metadata.video_outro import OutroType
        
        # Videos are added sequentially (concatenated on timeline)
        current_timeline_position = 0  # Track position in microseconds
        video_count = len(edit_request.video_sequence)
        video_segments_list = []  # Store segments for transition processing
        
        for idx, video_item in enumerate(edit_request.video_sequence):
            try:
                # Create video material
                video_mat = cc.VideoMaterial(video_item.source)
                
                # Calculate duration (ms to microseconds)
                # For speed > 1, max target = video_duration / speed
                effective_speed = video_item.speed if video_item.speed else 1.0
                if video_item.duration_ms:
                    segment_duration = video_item.duration_ms * 1000  # ms to us
                else:
                    # Auto-calculate max possible target duration based on speed
                    segment_duration = round(video_mat.duration / effective_speed)
                
                # Calculate source trim
                source_start = video_item.start_trim_ms * 1000 if video_item.start_trim_ms else 0
                
                # Create clip settings from transform
                transform = video_item.transform
                clip_settings = cc.ClipSettings(
                    transform_x=transform.x if transform else 0,
                    transform_y=transform.y if transform else 0,
                    scale_x=transform.scale_x if transform else 1.0,
                    scale_y=transform.scale_y if transform else 1.0,
                    rotation=transform.rotation if transform else 0,
                    alpha=transform.alpha if transform else 1.0,
                    flip_horizontal=transform.flip_horizontal if transform else False,
                    flip_vertical=transform.flip_vertical if transform else False
                )
                
                # Get speed curve meta if specified
                curve_meta = None
                if video_item.speed_curve:
                    from pycapcut.metadata.speed_curve_meta import SpeedCurveType
                    curve_meta = getattr(SpeedCurveType, video_item.speed_curve, None)
                
                # Create video segment
                video_seg = cc.VideoSegment(
                    video_mat,
                    trange(current_timeline_position, segment_duration),
                    source_timerange=trange(source_start, segment_duration) if source_start else None,
                    speed=video_item.speed if video_item.speed != 1.0 else None,
                    volume=video_item.volume,
                    clip_settings=clip_settings,
                    curve_meta=curve_meta
                )
                
                # --- Add intro animation ---
                if video_item.intro_animation:
                    intro_anim_type = getattr(IntroType, video_item.intro_animation.type, None)
                    if intro_anim_type:
                        duration_us = video_item.intro_animation.duration_ms * 1000 if video_item.intro_animation.duration_ms else None
                        video_seg.add_animation(intro_anim_type, duration_us)
                
                # --- Add outro animation ---
                if video_item.outro_animation:
                    outro_anim_type = getattr(OutroType, video_item.outro_animation.type, None)
                    if outro_anim_type:
                        duration_us = video_item.outro_animation.duration_ms * 1000 if video_item.outro_animation.duration_ms else None
                        video_seg.add_animation(outro_anim_type, duration_us)
                
                # --- Add background fill ---
                if video_item.background_fill:
                    bg = video_item.background_fill
                    fill_type = "blur" if bg.type == "blur" else "color"
                    blur_value = bg.intensity if bg.type == "blur" else 0
                    color_value = bg.color if hasattr(bg, 'color') and bg.color else "#00000000"
                    video_seg.add_background_filling(fill_type, blur=blur_value, color=color_value)
                
                # --- Add mask ---
                if video_item.mask:
                    mask_config = video_item.mask
                    mask_type = getattr(cc.MaskType, mask_config.type, None)
                    if mask_type:
                        try:
                            video_seg.add_mask(
                                mask_type,
                                center_x=mask_config.center_x if hasattr(mask_config, 'center_x') else 0,
                                center_y=mask_config.center_y if hasattr(mask_config, 'center_y') else 0,
                                size=mask_config.size,
                                rotation=mask_config.rotation if hasattr(mask_config, 'rotation') else 0,
                                feather=mask_config.feather,
                                invert=mask_config.invert,
                                round_corner=mask_config.round_corner if mask_config.round_corner else None
                            )
                        except Exception as mask_err:
                            pass  # Mask error shouldn't fail the request
                
                # Add to script
                script.add_segment(video_seg)
                video_segments_list.append(video_seg)
                
                # --- Add per-video effects ---
                if video_item.effects:
                    video_start_us = video_seg.target_timerange.start
                    video_duration_us = video_seg.target_timerange.duration
                    
                    for effect_idx, video_effect in enumerate(video_item.effects):
                        try:
                            # Get effect type based on category
                            effect_type = None
                            if video_effect.category == 'scene':
                                effect_type = getattr(cc.VideoSceneEffectType, video_effect.type, None)
                            else:
                                effect_type = getattr(cc.VideoCharacterEffectType, video_effect.type, None)
                            
                            if effect_type:
                                # Create unique track name for this video's effect
                                track_name = f"video_{idx:02d}_effect_{effect_idx:02d}"
                                try:
                                    script.add_track(cc.TrackType.effect, track_name=track_name)
                                except:
                                    pass
                                
                                # Calculate effect timing
                                effect_start_offset_us = video_effect.start_offset_ms * 1000  # ms to us
                                effect_start_us = video_start_us + effect_start_offset_us
                                
                                # Calculate effect duration
                                if video_effect.duration_ms:
                                    effect_duration_us = video_effect.duration_ms * 1000  # ms to us
                                else:
                                    # Default: effect lasts for video's remaining duration
                                    effect_duration_us = video_duration_us - effect_start_offset_us
                                
                                # Add effect at calculated position
                                script.add_effect(
                                    effect_type,
                                    trange(effect_start_us, effect_duration_us),
                                    track_name=track_name,
                                    params=video_effect.params
                                )
                        except Exception as ve_err:
                            pass  # Per-video effect error shouldn't fail the request
                
                # Update timeline position for next video (use ACTUAL segment duration)
                current_timeline_position += video_seg.target_timerange.duration
                
            except Exception as ve:
                processing_results["video_sequence"]["status"] = f"Error on video {idx}: {str(ve)}"
                raise ve
        
        # --- Add transitions (after all segments are added) ---
        for idx, video_item in enumerate(edit_request.video_sequence):
            if video_item.transition_to_next and idx < len(video_segments_list) - 1:
                try:
                    trans_config = video_item.transition_to_next
                    trans_type = getattr(cc.TransitionType, trans_config.type, None)
                    if trans_type:
                        duration_us = trans_config.duration_ms * 1000 if trans_config.duration_ms else None
                        video_segments_list[idx].add_transition(trans_type, duration=duration_us)
                        script.materials.transitions.append(video_segments_list[idx].transition)
                except Exception as te:
                    pass  # Transition error shouldn't fail the whole request
        
        processing_results["video_sequence"]["count"] = video_count
        processing_results["video_sequence"]["status"] = "completed"
        
        # Count per-video effects
        per_video_effects_count = sum(len(v.effects) for v in edit_request.video_sequence)
        processing_results["per_video_effects"]["count"] = per_video_effects_count
        processing_results["per_video_effects"]["status"] = "completed" if per_video_effects_count > 0 else "skipped (no per-video effects)"
        
        # Calculate total video duration
        total_video_duration_ms = current_timeline_position // 1000
        
        # --- 4.2 AUDIOS (Optional) ---
        audio_count = len(edit_request.audios)
        
        for idx, audio_item in enumerate(edit_request.audios):
            try:
                # Create audio material
                audio_mat = cc.AudioMaterial(audio_item.source)
                
                # Calculate duration
                if audio_item.duration_ms:
                    audio_duration = audio_item.duration_ms * 1000  # ms to us
                else:
                    audio_duration = audio_mat.duration  # Full audio duration
                
                # Calculate positions
                timeline_start = audio_item.start_ms * 1000  # ms to us
                source_start = audio_item.start_trim_ms * 1000 if audio_item.start_trim_ms else 0
                
                # Create audio segment
                audio_seg = cc.AudioSegment(
                    audio_mat,
                    trange(timeline_start, audio_duration),
                    source_timerange=trange(source_start, audio_duration) if source_start else None,
                    speed=audio_item.speed if audio_item.speed != 1.0 else None,
                    volume=audio_item.volume
                )
                
                # Add to script
                script.add_segment(audio_seg)
                
                # Apply fade in/out if specified
                if audio_item.fade_in_ms > 0 or audio_item.fade_out_ms > 0:
                    try:
                        audio_seg.set_audio_fade(
                            fade_in=audio_item.fade_in_ms / 1000.0,  # Convert to seconds
                            fade_out=audio_item.fade_out_ms / 1000.0
                        )
                    except:
                        pass  # Fade may not be supported
                
            except Exception as ae:
                processing_results["audios"]["status"] = f"Error on audio {idx}: {str(ae)}"
                # Continue with other audios, don't fail entire request
        
        processing_results["audios"]["count"] = audio_count
        processing_results["audios"]["status"] = "completed" if audio_count > 0 else "skipped (no audios)"
        
        # --- 4.3 EFFECTS (Optional) ---
        effects_count = len(edit_request.effects)
        
        for idx, effect_item in enumerate(edit_request.effects):
            try:
                # Get effect type
                effect_type = None
                if effect_item.category == 'scene':
                    effect_type = getattr(cc.VideoSceneEffectType, effect_item.type, None)
                else:
                    effect_type = getattr(cc.VideoCharacterEffectType, effect_item.type, None)
                
                if effect_type:
                    # Add effect track
                    track_name = f"effect_{idx:02d}"
                    try:
                        script.add_track(cc.TrackType.effect, track_name=track_name)
                    except:
                        pass
                    
                    # Add effect
                    script.add_effect(
                        effect_type,
                        trange(effect_item.start_ms * 1000, effect_item.duration_ms * 1000),
                        track_name=track_name,
                        params=effect_item.params
                    )
            except Exception as ee:
                processing_results["effects"]["status"] = f"Error on effect {idx}: {str(ee)}"
        
        processing_results["effects"]["count"] = effects_count
        processing_results["effects"]["status"] = "completed" if effects_count > 0 else "skipped (no effects)"
        
        # --- 4.4 FILTERS (Optional) ---
        filters_count = len(edit_request.filters)
        
        for idx, filter_item in enumerate(edit_request.filters):
            try:
                # Get filter type
                filter_type = getattr(cc.FilterType, filter_item.type, None)
                
                if filter_type:
                    # Add filter track
                    track_name = f"filter_{idx:02d}"
                    try:
                        script.add_track(cc.TrackType.filter, track_name=track_name)
                    except:
                        pass
                    
                    # Add filter
                    script.add_filter(
                        filter_type,
                        trange(filter_item.start_ms * 1000, filter_item.duration_ms * 1000),
                        track_name=track_name,
                        intensity=filter_item.intensity
                    )
            except Exception as fe:
                processing_results["filters"]["status"] = f"Error on filter {idx}: {str(fe)}"
        
        processing_results["filters"]["count"] = filters_count
        processing_results["filters"]["status"] = "completed" if filters_count > 0 else "skipped (no filters)"
        
        # --- 4.5 IMAGES (Optional) ---
        images_count = len(edit_request.images)
        
        for idx, image_item in enumerate(edit_request.images):
            try:
                # Create image material (images use VideoMaterial in pyCapCut)
                image_mat = cc.VideoMaterial(image_item.source)
                
                # Get position
                pos = image_item.position
                transform_x = pos.x if pos else 0
                transform_y = pos.y if pos else 0
                
                # Get scale
                scale_x = image_item.scale_x if image_item.scale_x else image_item.scale
                scale_y = image_item.scale_y if image_item.scale_y else image_item.scale
                
                # Create clip settings
                clip_settings = cc.ClipSettings(
                    transform_x=transform_x,
                    transform_y=transform_y,
                    scale_x=scale_x,
                    scale_y=scale_y
                )
                
                # Create image segment
                image_seg = cc.VideoSegment(
                    image_mat,
                    trange(image_item.start_ms * 1000, image_item.duration_ms * 1000),
                    clip_settings=clip_settings
                )
                
                # --- Add image intro animation ---
                if image_item.intro_animation:
                    intro_anim_type = getattr(IntroType, image_item.intro_animation.type, None)
                    if intro_anim_type:
                        duration_us = image_item.intro_animation.duration_ms * 1000 if image_item.intro_animation.duration_ms else None
                        image_seg.add_animation(intro_anim_type, duration_us)
                
                # --- Add image outro animation ---
                if image_item.outro_animation:
                    outro_anim_type = getattr(OutroType, image_item.outro_animation.type, None)
                    if outro_anim_type:
                        duration_us = image_item.outro_animation.duration_ms * 1000 if image_item.outro_animation.duration_ms else None
                        image_seg.add_animation(outro_anim_type, duration_us)
                
                # Add to script (on separate track for overlay)
                track_name = f"image_{idx:02d}"
                try:
                    script.add_track(cc.TrackType.video, track_name=track_name)
                except:
                    pass
                script.add_segment(image_seg, track_name=track_name)
                
            except Exception as ie:
                processing_results["images"]["status"] = f"Error on image {idx}: {str(ie)}"
        
        processing_results["images"]["count"] = images_count
        processing_results["images"]["status"] = "completed" if images_count > 0 else "skipped (no images)"
        
        # --- 4.6 TEXTS (Optional) ---
        texts_count = len(edit_request.texts)
        
        for idx, text_item in enumerate(edit_request.texts):
            try:
                # Get position
                pos = text_item.position
                transform_x = pos.x if pos else 0
                transform_y = pos.y if pos else 0
                
                # Get style
                style = text_item.style
                
                # Parse color
                color = hex_to_rgb(style.color if style else '#FFFFFF')
                
                # Create text style
                text_style = cc.TextStyle(
                    size=style.size if style else 8.0,
                    bold=style.bold if style else False,
                    italic=style.italic if style else False,
                    underline=style.underline if style else False,
                    color=color,
                    alpha=style.alpha if style else 1.0,
                    align=style.align if style else 1,
                    vertical=style.vertical if style else False,
                    letter_spacing=style.letter_spacing if style else 0,
                    line_spacing=style.line_spacing if style else 0,
                    auto_wrapping=style.auto_wrapping if style else False,
                    max_line_width=style.max_line_width if style else 0.82
                )
                
                # Create clip settings
                clip_settings = cc.ClipSettings(
                    transform_x=transform_x,
                    transform_y=transform_y
                )
                
                # Get font type if specified
                font_type = None
                if style and style.font:
                    try:
                        font_type = getattr(cc.FontType, style.font, None)
                    except:
                        pass
                
                # Parse border settings
                border = None
                if text_item.border:
                    border_color = hex_to_rgb(text_item.border.color)
                    border = cc.TextBorder(
                        alpha=text_item.border.alpha,
                        color=border_color,
                        width=text_item.border.width
                    )
                
                # Parse shadow settings
                shadow = None
                if text_item.shadow:
                    shadow_color = hex_to_rgb(text_item.shadow.color)
                    shadow = cc.TextShadow(
                        alpha=text_item.shadow.alpha,
                        color=shadow_color,
                        diffuse=text_item.shadow.diffuse,
                        distance=text_item.shadow.distance,
                        angle=text_item.shadow.angle
                    )
                
                # Parse background settings
                background = None
                if text_item.background:
                    background = cc.TextBackground(
                        color=text_item.background.color,
                        style=text_item.background.style,
                        alpha=text_item.background.alpha,
                        round_radius=text_item.background.round_radius,
                        height=text_item.background.height,
                        width=text_item.background.width,
                        horizontal_offset=text_item.background.horizontal_offset,
                        vertical_offset=text_item.background.vertical_offset
                    )
                
                # Create text segment
                text_seg = cc.TextSegment(
                    text_item.content,
                    trange(text_item.start_ms * 1000, text_item.duration_ms * 1000),
                    font=font_type,
                    style=text_style,
                    clip_settings=clip_settings,
                    border=border,
                    background=background,
                    shadow=shadow
                )
                
                # Add to script
                script.add_segment(text_seg)
                
                # --- Add text animations ---
                if text_item.animation:
                    try:
                        # Add intro animation FIRST (before loop)
                        if text_item.animation.intro:
                            intro_type = getattr(cc.TextIntro, text_item.animation.intro.type, None)
                            if intro_type:
                                duration_us = text_item.animation.intro.duration_ms * 1000 if text_item.animation.intro.duration_ms else 500000
                                text_seg.add_animation(intro_type, duration=duration_us)
                        
                        # Add outro animation BEFORE loop
                        if text_item.animation.outro:
                            outro_type = getattr(cc.TextOutro, text_item.animation.outro.type, None)
                            if outro_type:
                                duration_us = text_item.animation.outro.duration_ms * 1000 if text_item.animation.outro.duration_ms else 500000
                                text_seg.add_animation(outro_type, duration=duration_us)
                        
                        # Add loop animation LAST (after intro/outro)
                        if text_item.animation.loop:
                            loop_type = getattr(cc.TextLoopAnim, text_item.animation.loop.type, None)
                            if loop_type:
                                text_seg.add_animation(loop_type)
                        
                        # CRUCIAL: Add animation material to script materials list
                        if text_seg.animations_instance is not None:
                            if text_seg.animations_instance not in script.materials.animations:
                                script.materials.animations.append(text_seg.animations_instance)
                    except Exception as anim_err:
                        pass  # Animation import/apply error shouldn't fail the request
                
            except Exception as te:
                processing_results["texts"]["status"] = f"Error on text {idx}: {str(te)}"
        
        processing_results["texts"]["count"] = texts_count
        processing_results["texts"]["status"] = "completed" if texts_count > 0 else "skipped (no texts)"
        
        # --- 4.7 STICKERS (Optional) ---
        from pycapcut.metadata.sticker_meta import StickerType
        
        stickers_count = len(edit_request.stickers)
        processing_results["stickers"] = {"count": 0, "status": "pending"}
        
        # Add sticker track
        try:
            script.add_track(cc.TrackType.sticker, track_name="sticker_track")
        except:
            pass
        
        for idx, sticker_item in enumerate(edit_request.stickers):
            try:
                # Get sticker metadata from StickerType
                sticker_meta = getattr(StickerType, sticker_item.type, None)
                if not sticker_meta:
                    processing_results["stickers"]["status"] = f"Sticker type '{sticker_item.type}' not found"
                    continue
                
                # Get position
                pos = sticker_item.position
                transform_x = pos.x if pos else 0
                transform_y = pos.y if pos else 0
                
                # Create clip settings with scale
                clip_settings = cc.ClipSettings(
                    transform_x=transform_x,
                    transform_y=transform_y,
                    scale_x=sticker_item.scale,
                    scale_y=sticker_item.scale
                )
                
                # Create sticker segment - pass full EffectMeta for complete metadata export
                sticker_seg = cc.StickerSegment(
                    sticker_meta.value,  # Pass EffectMeta object, not just resource_id
                    trange(sticker_item.start_ms * 1000, sticker_item.duration_ms * 1000),
                    clip_settings=clip_settings
                )
                
                # Add to sticker track
                script.add_segment(sticker_seg, track_name="sticker_track")
                
            except Exception as se:
                processing_results["stickers"]["status"] = f"Error on sticker {idx}: {str(se)}"
        
        processing_results["stickers"]["count"] = stickers_count
        processing_results["stickers"]["status"] = "completed" if stickers_count > 0 else "skipped (no stickers)"
        
        # ===== 5. SAVE DRAFT =====
        script.save()
        
        # ===== 6. RETURN SUCCESS RESPONSE =====
        return jsonify({
            "success": True,
            "output": {
                "draft_id": draft_id,
                "draft_name": draft_name,
                "draft_folder": draft_folder_path,
                "canvas": {
                    "width": canvas.width,
                    "height": canvas.height,
                    "fps": canvas.fps,
                    "duration_ms": canvas.duration_ms
                },
                "processing_results": processing_results,
                "message": "Project created successfully. Note: Component processing is pending implementation."
            },
            "error": ""
        }), 200
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "output": "",
            "error": f"Error creating project: {str(e)}"
        }), 400


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
        underline (bool, optional): Underline text, default False
        vertical (bool, optional): Vertical text, default False
        align (int, optional): Text alignment 0=left, 1=center, 2=right, default 0
        letter_spacing (int, optional): Letter spacing, default 0
        line_spacing (int, optional): Line spacing, default 0
        auto_wrapping (bool, optional): Auto line wrapping, default False
        max_line_width (float, optional): Max line width ratio 0-1, default 0.82
        alpha (float, optional): Text opacity 0-1, default 1.0
        border (object, optional): Text border settings {color, alpha, width}
        background (object, optional): Text background settings {color, style, alpha, round_radius, height, width, horizontal_offset, vertical_offset}
        shadow (object, optional): Text shadow settings {color, alpha, diffuse, distance, angle}
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
        
        # Parse basic parameters
        start = data.get('start', 0)
        duration = data.get('duration', 5.0)
        font = data.get('font')
        font_size = data.get('font_size', data.get('size', 8.0))
        font_color = data.get('font_color', data.get('color', '#FFFFFF'))
        transform_x = data.get('transform_x', 0)
        transform_y = data.get('transform_y', 0)
        bold = data.get('bold', False)
        italic = data.get('italic', False)
        underline = data.get('underline', False)
        vertical = data.get('vertical', False)
        align = data.get('align', 0)
        letter_spacing = data.get('letter_spacing', 0)
        line_spacing = data.get('line_spacing', 0)
        auto_wrapping = data.get('auto_wrapping', False)
        max_line_width = data.get('max_line_width', 0.82)
        alpha = data.get('alpha', 1.0)
        track_name = data.get('track_name')
        
        # Parse color
        color = hex_to_rgb(font_color)
        
        # Create text style with all parameters
        text_style = cc.TextStyle(
            size=font_size,
            bold=bold,
            italic=italic,
            underline=underline,
            color=color,
            alpha=alpha,
            align=align,
            vertical=vertical,
            letter_spacing=letter_spacing,
            line_spacing=line_spacing,
            auto_wrapping=auto_wrapping,
            max_line_width=max_line_width
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
        
        # Parse border settings
        border = None
        border_config = data.get('border')
        if border_config:
            border_color = hex_to_rgb(border_config.get('color', '#000000'))
            border = cc.TextBorder(
                alpha=border_config.get('alpha', 1.0),
                color=border_color,
                width=border_config.get('width', 40.0)
            )
        
        # Parse background settings
        background = None
        bg_config = data.get('background')
        if bg_config:
            background = cc.TextBackground(
                color=bg_config.get('color', '#000000'),
                style=bg_config.get('style', 1),
                alpha=bg_config.get('alpha', 1.0),
                round_radius=bg_config.get('round_radius', 0.0),
                height=bg_config.get('height', 0.14),
                width=bg_config.get('width', 0.14),
                horizontal_offset=bg_config.get('horizontal_offset', 0.5),
                vertical_offset=bg_config.get('vertical_offset', 0.5)
            )
        
        # Parse shadow settings
        shadow = None
        shadow_config = data.get('shadow')
        if shadow_config:
            shadow_color = hex_to_rgb(shadow_config.get('color', '#000000'))
            shadow = cc.TextShadow(
                alpha=shadow_config.get('alpha', 1.0),
                color=shadow_color,
                diffuse=shadow_config.get('diffuse', 15.0),
                distance=shadow_config.get('distance', 5.0),
                angle=shadow_config.get('angle', -45.0)
            )
        
        # Create text segment
        text_seg = cc.TextSegment(
            text,
            trange(int(start * SEC), int(duration * SEC)),
            font=font_type,
            style=text_style,
            clip_settings=clip_settings,
            border=border,
            background=background,
            shadow=shadow
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


# ============================================================
# VIDEO ANIMATION ENDPOINTS
# ============================================================

@app.route('/add_video_animation', methods=['POST'])
def add_video_animation():
    """Add intro/outro/combo animation to a video segment
    
    Request body:
        draft_id (str): The draft ID
        animation_type (str): Animation type name (e.g., "Neon Love", "Snowflake_Veil")
        animation_category (str): "intro", "outro", or "combo"
        segment_index (int, optional): Index of the video segment (0-based), default 0
        duration (float, optional): Animation duration in seconds (uses default if not specified)
        track_name (str, optional): Video track name
    """
    try:
        from pycapcut.metadata.video_intro import IntroType
        from pycapcut.metadata.video_outro import OutroType
        from pycapcut.metadata.video_group_animation import GroupAnimationType
        
        data = request.get_json()
        draft_id = data.get('draft_id')
        animation_name = data.get('animation_type')
        animation_category = data.get('animation_category', 'intro').lower()
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        if not animation_name:
            return make_response(False, error="Missing required parameter 'animation_type'")
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, _, _ = draft_data
        
        # Parse parameters
        segment_index = data.get('segment_index', 0)
        track_name = data.get('track_name')
        duration = data.get('duration')
        
        # Get animation type from the appropriate category
        if animation_category == 'intro':
            anim_type = getattr(IntroType, animation_name, None)
            category_display = "intro"
        elif animation_category == 'outro':
            anim_type = getattr(OutroType, animation_name, None)
            category_display = "outro"
        elif animation_category == 'combo' or animation_category == 'group':
            anim_type = getattr(GroupAnimationType, animation_name, None)
            category_display = "combo"
        else:
            return make_response(False, error=f"Invalid animation_category '{animation_category}'. Valid: intro, outro, combo")
        
        if not anim_type:
            return make_response(False, error=f"Animation '{animation_name}' not found in {animation_category} animations")
        
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
            duration_us = int(duration * SEC)
            segment.add_animation(anim_type, duration_us)
        else:
            segment.add_animation(anim_type)
        
        return make_response(True, {
            "message": f"Video {category_display} animation added successfully",
            "animation": animation_name,
            "category": animation_category
        })
        
    except Exception as e:
        traceback.print_exc()
        return make_response(False, error=f"Error adding video animation: {str(e)}")


# ============================================================
# KEYFRAME ENDPOINTS
# ============================================================

@app.route('/add_keyframe', methods=['POST'])
def add_keyframe():
    """Add a keyframe to a video/image segment
    
    Request body:
        draft_id (str): The draft ID
        property (str): Keyframe property (position_x, position_y, rotation, scale_x, scale_y, uniform_scale, alpha, saturation, contrast, brightness, volume)
        time_offset (float): Time offset from segment start in seconds
        value (float): Value at this keyframe
        segment_index (int, optional): Index of the video segment (0-based), default 0
        track_name (str, optional): Video track name
    """
    try:
        from pycapcut.keyframe import KeyframeProperty
        
        data = request.get_json()
        draft_id = data.get('draft_id')
        property_name = data.get('property')
        time_offset = data.get('time_offset')
        value = data.get('value')
        
        if not draft_id:
            return make_response(False, error="Missing required parameter 'draft_id'")
        if not property_name:
            return make_response(False, error="Missing required parameter 'property'")
        if time_offset is None:
            return make_response(False, error="Missing required parameter 'time_offset'")
        if value is None:
            return make_response(False, error="Missing required parameter 'value'")
        
        draft_data = get_draft(draft_id)
        if not draft_data:
            return make_response(False, error=f"Draft {draft_id} not found in cache")
        
        script, _, _ = draft_data
        
        # Parse parameters
        segment_index = data.get('segment_index', 0)
        track_name = data.get('track_name')
        
        # Get keyframe property
        kf_property = getattr(KeyframeProperty, property_name, None)
        if not kf_property:
            valid_props = [p.name for p in KeyframeProperty]
            return make_response(False, error=f"Invalid property '{property_name}'. Valid: {valid_props}")
        
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
        
        # Convert time_offset from seconds to microseconds
        time_offset_us = int(time_offset * SEC)
        
        # Add keyframe to the segment
        segment = video_track.segments[segment_index]
        segment.add_keyframe(kf_property, time_offset_us, value)
        
        return make_response(True, {
            "message": f"Keyframe added successfully",
            "property": property_name,
            "time_offset": time_offset,
            "value": value
        })
        
    except Exception as e:
        traceback.print_exc()
        return make_response(False, error=f"Error adding keyframe: {str(e)}")


@app.route('/get_keyframe_properties', methods=['GET'])
def get_keyframe_properties():
    """Get list of available keyframe properties"""
    try:
        from pycapcut.keyframe import KeyframeProperty
        
        properties = {}
        for prop in KeyframeProperty:
            properties[prop.name] = {
                "value": prop.value,
                "description": prop.__doc__ if prop.__doc__ else ""
            }
        
        return make_response(True, {"properties": properties})
        
    except Exception as e:
        return make_response(False, error=f"Error getting keyframe properties: {str(e)}")


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
        center_x (float, optional): Mask center X position in pixels, default 0 (center)
        center_y (float, optional): Mask center Y position in pixels, default 0 (center)
        size (float, optional): Main size as ratio of material height, default 0.5
        rotation (float, optional): Rotation in degrees, default 0
        feather (float, optional): Feather amount 0-100, default 0
        invert (bool, optional): Invert the mask, default False
        rect_width (float, optional): Rectangle width (only for rectangle mask)
        round_corner (float, optional): Round corner 0-100 (only for rectangle mask)
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
        center_x = data.get('center_x', 0.0)
        center_y = data.get('center_y', 0.0)
        size = data.get('size', 0.5)
        rotation = data.get('rotation', 0.0)
        feather = data.get('feather', 0.0)
        invert = data.get('invert', False)
        rect_width = data.get('rect_width')
        round_corner = data.get('round_corner')
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
        
        # Add mask to the segment with all parameters
        segment = video_track.segments[segment_index]
        segment.add_mask(
            mask_type,
            center_x=center_x,
            center_y=center_y,
            size=size,
            rotation=rotation,
            feather=feather,
            invert=invert,
            rect_width=rect_width,
            round_corner=round_corner
        )
        
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
    """Add intro/outro/loop animation to a text segment
    
    Request body:
        draft_id (str): The draft ID
        animation_type (str): Animation type name from TextIntro, TextOutro, or TextLoopAnim
        animation_category (str, optional): 'intro', 'outro', or 'loop', default 'intro'
        segment_index (int, optional): Index of the text segment (0-based), default 0
        duration (float, optional): Animation duration in seconds (not used for loop)
        track_name (str, optional): Text track name
    
    Note: For loop animations, add intro/outro animations first, then add loop.
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
        
        # Get animation type based on category
        animation_type = None
        if animation_category == 'intro':
            animation_type = getattr(cc.TextIntro, animation_type_name, None)
        elif animation_category == 'outro':
            animation_type = getattr(cc.TextOutro, animation_type_name, None)
        elif animation_category == 'loop':
            animation_type = getattr(cc.TextLoopAnim, animation_type_name, None)
        
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
        if duration and animation_category != 'loop':
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
            "composite_project": [
                "POST /create_amv_project_video  (Create complete project from single JSON)"
            ],
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
            "keyframes": [
                "POST /add_keyframe",
                "GET /get_keyframe_properties"
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
    
    if DEBUG:
        # Development mode - use Flask dev server
        app.run(host='0.0.0.0', port=PORT, debug=True)
    else:
        # Production mode - use Waitress WSGI server
        from waitress import serve
        print("🚀 Running in PRODUCTION mode with Waitress WSGI server")
        serve(app, host='0.0.0.0', port=PORT, threads=4)

