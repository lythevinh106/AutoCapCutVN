"""
Pydantic models for Composite Edit API Request
Defines the schema for the /edit_draft_composite endpoint
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

# ==========================================
# 1. BASE / SHARED MODELS
# ==========================================

class Position(BaseModel):
    """Vị trí trên canvas (-1 to 1)"""
    x: float = 0
    y: float = 0


class Transform(BaseModel):
    """Transform settings cho video/image"""
    x: float = Field(default=0, description="Horizontal position (-1 to 1)")
    y: float = Field(default=0, description="Vertical position (-1 to 1)")
    scale_x: float = Field(default=1.0, description="Horizontal scale")
    scale_y: float = Field(default=1.0, description="Vertical scale")
    rotation: float = Field(default=0, description="Rotation in degrees (clockwise)")
    alpha: float = Field(default=1.0, description="Opacity (0-1)")
    flip_horizontal: bool = False
    flip_vertical: bool = False


class AnimationConfig(BaseModel):
    """Cấu hình animation (intro/outro/loop)"""
    type: str = Field(..., description="Animation type name")
    duration_ms: Optional[int] = Field(default=None, description="Duration in ms, null for default")


class Animations(BaseModel):
    """Animation settings cho text"""
    intro: Optional[AnimationConfig] = None
    loop: Optional[AnimationConfig] = None
    outro: Optional[AnimationConfig] = None


class Keyframe(BaseModel):
    """Keyframe cho animation properties"""
    time_offset_ms: int = Field(..., description="Time offset from segment start")
    property: Optional[str] = Field(default=None, description="Property name (for video/image)")
    value: Optional[float] = Field(default=None, description="Property value (for video/image)")
    volume: Optional[float] = Field(default=None, description="Volume value (for audio)")


class Mask(BaseModel):
    """Mask settings cho video"""
    type: str = Field(..., description="Mask type from GET /get_mask_types")
    center_x: float = Field(default=0, description="Center X in pixels")
    center_y: float = Field(default=0, description="Center Y in pixels")
    size: float = Field(default=0.5, description="Size ratio of height (0-1)")
    rotation: float = Field(default=0, description="Rotation in degrees")
    feather: float = Field(default=0, description="Feather amount (0-100)")
    invert: bool = Field(default=False, description="Invert mask")
    rect_width: Optional[float] = Field(default=None, description="Rectangle width (矩形 only)")
    round_corner: Optional[float] = Field(default=None, description="Round corner (矩形 only, 0-100)")


class BackgroundFill(BaseModel):
    """Background fill settings cho video"""
    type: str = Field(..., description="'blur' or 'color'")
    intensity: float = Field(default=0.375, description="Blur intensity (0.0625, 0.375, 0.75, 1.0)")
    color: str = Field(default="#000000FF", description="Color in #RRGGBBAA format")


class AudioEffect(BaseModel):
    """Audio effect settings"""
    type: str = Field(..., description="Effect type from GET /get_audio_effect_types")
    params: Optional[List[float]] = Field(default=None, description="Effect parameters [0-100, ...]")


# ==========================================
# 2. SPECIFIC COMPONENT MODELS
# ==========================================

class CanvasConfig(BaseModel):
    """Canvas configuration"""
    width: int = Field(..., description="Video width in pixels")
    height: int = Field(..., description="Video height in pixels")
    fps: int = Field(default=30, description="Frames per second")
    duration_ms: Optional[int] = Field(default=None, description="Total duration, auto-calculated if null")


class AudioItem(BaseModel):
    """Audio track item"""
    timeline_priority: int = Field(default=1, description="Render order (1 = bottom)")
    source: str = Field(..., description="Audio file path")
    start_ms: int = Field(default=0, description="Position on timeline")
    start_trim_ms: int = Field(default=0, description="Trim from source start")
    duration_ms: Optional[int] = Field(default=None, description="Duration, null for full audio")
    volume: float = Field(default=1.0, description="Volume (0-1)")
    speed: float = Field(default=1.0, description="Playback speed")
    fade_in_ms: int = Field(default=0, description="Fade in duration")
    fade_out_ms: int = Field(default=0, description="Fade out duration")
    effects: List[AudioEffect] = Field(default_factory=list, description="Audio effects")
    keyframes: List[Keyframe] = Field(default_factory=list, description="Volume keyframes")


class VideoItem(BaseModel):
    """Video sequence item"""
    timeline_priority: int = Field(default=2, description="Render order")
    source: str = Field(..., description="Video file path")
    start_trim_ms: int = Field(default=0, description="Trim from source start")
    duration_ms: Optional[int] = Field(default=None, description="Duration, null for full video")
    volume: float = Field(default=1.0, description="Audio volume (0-1)")
    speed: float = Field(default=1.0, description="Playback speed")
    transform: Optional[Transform] = Field(default_factory=Transform, description="Transform settings")
    intro_animation: Optional[AnimationConfig] = Field(default=None, description="Intro animation")
    outro_animation: Optional[AnimationConfig] = Field(default=None, description="Outro animation")
    transition_to_next: Optional[AnimationConfig] = Field(default=None, description="Transition to next video")
    background_fill: Optional[BackgroundFill] = Field(default=None, description="Background fill")
    mask: Optional[Mask] = Field(default=None, description="Mask settings")
    keyframes: List[Keyframe] = Field(default_factory=list, description="Animation keyframes")


class EffectItem(BaseModel):
    """Video effect item"""
    timeline_priority: int = Field(default=3, description="Render order")
    type: str = Field(..., description="Effect type from GET /get_video_scene_effect_types")
    category: str = Field(default="scene", description="'scene' or 'character'")
    start_ms: int = Field(default=0, description="Start time on timeline")
    duration_ms: int = Field(..., description="Effect duration")
    params: Optional[List[float]] = Field(default=None, description="Effect parameters [0-100, ...]")


class FilterItem(BaseModel):
    """Filter item"""
    timeline_priority: int = Field(default=4, description="Render order")
    type: str = Field(..., description="Filter type from GET /get_filter_types")
    start_ms: int = Field(default=0, description="Start time on timeline")
    duration_ms: int = Field(..., description="Filter duration")
    intensity: float = Field(default=100, description="Filter intensity (0-100)")


class ImageItem(BaseModel):
    """Image overlay item"""
    timeline_priority: int = Field(default=5, description="Render order")
    source: str = Field(..., description="Image file path")
    start_ms: int = Field(default=0, description="Start time on timeline")
    duration_ms: int = Field(default=3000, description="Display duration")
    position: Optional[Position] = Field(default_factory=Position, description="Position on canvas")
    scale: float = Field(default=1.0, description="Uniform scale")
    scale_x: Optional[float] = Field(default=None, description="Horizontal scale (overrides scale)")
    scale_y: Optional[float] = Field(default=None, description="Vertical scale (overrides scale)")
    rotation: float = Field(default=0, description="Rotation in degrees")
    alpha: float = Field(default=1.0, description="Opacity (0-1)")
    flip_horizontal: bool = Field(default=False, description="Flip horizontally")
    flip_vertical: bool = Field(default=False, description="Flip vertically")
    intro_animation: Optional[AnimationConfig] = Field(default=None, description="Intro animation")
    outro_animation: Optional[AnimationConfig] = Field(default=None, description="Outro animation")
    keyframes: List[Keyframe] = Field(default_factory=list, description="Animation keyframes")


# --- Text Helper Classes ---

class TextStyle(BaseModel):
    """Text styling options"""
    font: Optional[str] = Field(default=None, description="Font type from GET /get_font_types")
    size: float = Field(default=8.0, description="Font size")
    color: str = Field(default="#FFFFFF", description="Text color #RRGGBB")
    alpha: float = Field(default=1.0, description="Text opacity (0-1)")
    bold: bool = Field(default=False, description="Bold text")
    italic: bool = Field(default=False, description="Italic text")
    underline: bool = Field(default=False, description="Underlined text")
    vertical: bool = Field(default=False, description="Vertical text layout")
    align: int = Field(default=1, description="Alignment: 0=left, 1=center, 2=right")
    letter_spacing: float = Field(default=0, description="Letter spacing")
    line_spacing: float = Field(default=0, description="Line spacing")
    auto_wrapping: bool = Field(default=False, description="Auto wrap text")
    max_line_width: float = Field(default=0.82, description="Max line width ratio (0-1)")


class TextBorder(BaseModel):
    """Text border/stroke settings"""
    color: str = Field(default="#000000", description="Border color #RRGGBB")
    width: float = Field(default=40, description="Border width (0-100)")
    alpha: float = Field(default=1.0, description="Border opacity (0-1)")


class TextShadow(BaseModel):
    """Text shadow settings"""
    color: str = Field(default="#000000", description="Shadow color #RRGGBB")
    alpha: float = Field(default=1.0, description="Shadow opacity (0-1)")
    distance: float = Field(default=5, description="Shadow distance (0-100)")
    diffuse: float = Field(default=15, description="Shadow blur (0-100)")
    angle: float = Field(default=-45, description="Shadow angle (-180 to 180)")


class TextBackground(BaseModel):
    """Text background settings"""
    color: str = Field(..., description="Background color #RRGGBB")
    alpha: float = Field(default=1.0, description="Background opacity (0-1)")
    style: int = Field(default=1, description="Background style (1 or 2)")
    round_radius: float = Field(default=0, description="Corner radius (0-1)")
    height: float = Field(default=0.14, description="Background height (0-1)")
    width: float = Field(default=0.14, description="Background width (0-1)")
    horizontal_offset: float = Field(default=0.5, description="Horizontal offset (0-1)")
    vertical_offset: float = Field(default=0.5, description="Vertical offset (0-1)")


class TextItem(BaseModel):
    """Text overlay item"""
    timeline_priority: int = Field(default=6, description="Render order (6 = top layer)")
    content: str = Field(..., description="Text content")
    start_ms: int = Field(default=0, description="Start time on timeline")
    duration_ms: int = Field(..., description="Display duration")
    position: Optional[Position] = Field(default_factory=Position, description="Position on canvas")
    style: Optional[TextStyle] = Field(default_factory=TextStyle, description="Text styling")
    border: Optional[TextBorder] = Field(default=None, description="Text border/stroke")
    shadow: Optional[TextShadow] = Field(default=None, description="Text shadow")
    background: Optional[TextBackground] = Field(default=None, description="Text background")
    animation: Optional[Animations] = Field(default=None, description="Text animations")


class StickerItem(BaseModel):
    """Sticker overlay item (emoji, GIFs, animated stickers)"""
    timeline_priority: int = Field(default=5, description="Render order (5 = sticker layer)")
    type: str = Field(..., description="Sticker type from sticker_meta.py (e.g. 'Pets_EN___Cute_Cat')")
    start_ms: int = Field(default=0, description="Start time on timeline")
    duration_ms: int = Field(..., description="Display duration")
    position: Optional[Position] = Field(default_factory=Position, description="Position on canvas (-1 to 1)")
    scale: float = Field(default=1.0, description="Sticker scale")


# ==========================================
# 3. ROOT MODEL (Main Request)
# ==========================================

class EditRequest(BaseModel):
    """
    Main request model for /edit_draft_composite endpoint
    """
    # CanvasConfig là BẮT BUỘC (Field ... nghĩa là required)
    canvas_config: CanvasConfig = Field(..., description="Canvas configuration")

    # Video Sequence là BẮT BUỘC (Field ...)
    video_sequence: List[VideoItem] = Field(..., description="Video sequence - REQUIRED")

    # Các trường còn lại là TÙY CHỌN. Nếu thiếu key, tự động gán []
    audios: List[AudioItem] = Field(default_factory=list, description="Audio tracks")
    effects: List[EffectItem] = Field(default_factory=list, description="Video effects")
    filters: List[FilterItem] = Field(default_factory=list, description="Filters")
    images: List[ImageItem] = Field(default_factory=list, description="Image overlays")
    texts: List[TextItem] = Field(default_factory=list, description="Text overlays")
    stickers: List[StickerItem] = Field(default_factory=list, description="Sticker overlays")

    @field_validator('video_sequence')
    @classmethod
    def video_sequence_must_not_be_empty(cls, v: List[VideoItem]) -> List[VideoItem]:
        """Kiểm tra video_sequence không được là list rỗng"""
        if not v:
            raise ValueError('video_sequence is required and must contain at least 1 video item')
        return v