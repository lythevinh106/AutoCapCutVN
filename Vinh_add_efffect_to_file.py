"""
Script tự động đồng bộ Effects từ CapCut draft
- Đọc draft_content.json từ project CapCut
- TỰ ĐỘNG phân loại dựa vào key nguồn trong JSON
- Thêm vào đúng file tương ứng:
  - video_effects -> video_scene_effect.py
  - effects (filters) -> filter_meta.py
  - audio_effects -> audio_scene_effect.py
  - transitions -> transition_meta.py
  - texts/fonts -> font_meta.py
  - material_animations (loop) -> text_loop.py
"""

import json
import os
import re

# ============ CẤU HÌNH ============
DRAFT_FOLDER = r"C:\Users\VINH\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft"
DRAFT_NAME = "effect_library"  # Tên project trong CapCut

# Đường dẫn các file metadata
METADATA_DIR = os.path.join(os.path.dirname(__file__), "pycapcut", "metadata")
EFFECT_FILE = os.path.join(METADATA_DIR, "video_scene_effect.py")
FILTER_FILE = os.path.join(METADATA_DIR, "filter_meta.py")
AUDIO_EFFECT_FILE = os.path.join(METADATA_DIR, "audio_scene_effect.py")
TRANSITION_FILE = os.path.join(METADATA_DIR, "transition_meta.py")
FONT_FILE = os.path.join(METADATA_DIR, "font_meta.py")
TEXT_LOOP_FILE = os.path.join(METADATA_DIR, "text_loop.py")
TEXT_INTRO_FILE = os.path.join(METADATA_DIR, "text_intro.py")
TEXT_OUTRO_FILE = os.path.join(METADATA_DIR, "text_outro.py")
VIDEO_INTRO_FILE = os.path.join(METADATA_DIR, "video_intro.py")
VIDEO_OUTRO_FILE = os.path.join(METADATA_DIR, "video_outro.py")
COMBO_ANIM_FILE = os.path.join(METADATA_DIR, "combo_animation.py")


# ============ HELPER FUNCTIONS ============
def sanitize_effect_name(name: str) -> str:
    """Chuyển tên effect thành tên biến Python hợp lệ"""
    sanitized = re.sub(r'[^\w\u4e00-\u9fff]', '_', name)
    sanitized = sanitized.strip('_')
    if sanitized and sanitized[0].isdigit():
        sanitized = '_' + sanitized
    return sanitized or 'Unknown'


def get_existing_names(file_path: str) -> set:
    """Lấy danh sách tên đã có trong file"""
    existing_names = set()
    
    if not os.path.exists(file_path):
        return existing_names
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Tìm EffectMeta("name", ...) hoặc TransitionMeta("name", ...) hoặc AnimationMeta("name", ...)
    pattern = r'(?:EffectMeta|TransitionMeta|AnimationMeta)\("([^"]+)"'
    matches = re.findall(pattern, content)
    
    for match in matches:
        existing_names.add(match)
    
    return existing_names


def generate_effect_code(item: dict) -> str:
    """Generate code cho EffectMeta (effects, filters, audio effects)"""
    name = item.get('name', 'Unknown')
    effect_id = item.get('effect_id', '')
    resource_id = item.get('resource_id', '')
    category_id = item.get('category_id', '')
    category_name = item.get('category_name', '')
    path = item.get('path', '').replace('\\', '/')
    source_platform = item.get('source_platform', 0)
    request_id = item.get('request_id', '')
    
    var_name = sanitize_effect_name(name)
    padded_var = f"{var_name:<20}"
    
    # Build kwargs
    kwargs = []
    if path:
        kwargs.append(f'path="{path}"')
    if category_name:
        kwargs.append(f'category_name="{category_name}"')
    if category_id:
        kwargs.append(f'category_id="{category_id}"')
    if source_platform:
        kwargs.append(f'source_platform={source_platform}')
    if request_id:
        kwargs.append(f'request_id="{request_id}"')
    
    code = f'    {padded_var} = EffectMeta("{name}", False, "{resource_id}", "{effect_id}", "{category_id}", []'
    if kwargs:
        code += ', ' + ', '.join(kwargs)
    code += ')'
    return code


def generate_font_code(item: dict) -> str:
    """Generate code cho FontType (fonts)"""
    name = item.get('name', 'Unknown')
    resource_id = item.get('resource_id', '')
    effect_id = item.get('effect_id', resource_id)  # Fonts often use same value
    md5 = item.get('file_md5', '') or item.get('category_id', '')
    
    var_name = sanitize_effect_name(name)
    padded_var = f"{var_name:<20}"
    
    code = f'    {padded_var} = EffectMeta("{name}", False, "{resource_id}", "{effect_id}", "{md5}", [])'
    return code


def generate_text_loop_code(item: dict) -> str:
    """Generate code cho TextLoopAnim (text loop animations)"""
    name = item.get('name', 'Unknown')
    resource_id = item.get('resource_id', '')
    effect_id = item.get('effect_id', resource_id)
    
    # Get path - CRITICAL for animation to work in CapCut
    path = item.get('path', '').replace('\\', '/')
    
    # Try to get MD5 from different sources:
    # 1. file_md5 field directly
    # 2. Extract from path (format: .../resource_id/md5_hash)
    md5 = item.get('file_md5', '')
    if not md5:
        if path:
            # Path format: C:/Users/.../Cache/effect/resource_id/md5_hash
            path_parts = path.replace('\\', '/').rstrip('/').split('/')
            if len(path_parts) >= 1 and len(path_parts[-1]) == 32:
                md5 = path_parts[-1]
    
    # Duration from CapCut is in microseconds, convert to seconds
    duration_us = item.get('duration', 500000)  # Default 0.5s
    duration_sec = duration_us / 1_000_000 if duration_us > 1000 else duration_us
    
    var_name = sanitize_effect_name(name)
    padded_var = f"{var_name:<20}"
    
    # Generate code WITH path for CapCut compatibility
    # Format: AnimationMeta(title, is_vip, duration, resource_id, effect_id, md5, *, path=...)
    if path:
        code = f'    {padded_var} = AnimationMeta("{name}", False, {duration_sec:.3f}, "{resource_id}", "{effect_id}", "{md5}", path="{path}")'
    else:
        code = f'    {padded_var} = AnimationMeta("{name}", False, {duration_sec:.3f}, "{resource_id}", "{effect_id}", "{md5}")'
    return code


def generate_text_anim_code(item: dict) -> str:
    """Generate code cho Text Intro/Outro animations (type='in'/'out' for text elements)"""
    name = item.get('name', 'Unknown')
    resource_id = item.get('resource_id', '')
    effect_id = item.get('effect_id', '') or resource_id
    
    # Get path - CRITICAL for animation to work in CapCut
    path = item.get('path', '').replace('\\', '/')
    
    # Try to get MD5 from different sources
    md5 = item.get('file_md5', '')
    if not md5 and path:
        path_parts = path.replace('\\', '/').rstrip('/').split('/')
        if len(path_parts) >= 1 and len(path_parts[-1]) == 32:
            md5 = path_parts[-1]
    
    # Duration from CapCut is in microseconds, convert to seconds
    duration_us = item.get('duration', 500000)  # Default 0.5s
    duration_sec = duration_us / 1_000_000 if duration_us > 1000 else duration_us
    
    var_name = sanitize_effect_name(name)
    padded_var = f"{var_name:<20}"
    
    # Generate code WITH path for CapCut compatibility
    if path:
        code = f'    {padded_var} = AnimationMeta("{name}", False, {duration_sec:.3f}, "{resource_id}", "{effect_id}", "{md5}", path="{path}")'
    else:
        code = f'    {padded_var} = AnimationMeta("{name}", False, {duration_sec:.3f}, "{resource_id}", "{effect_id}", "{md5}")'
    return code


def generate_video_anim_code(item: dict) -> str:
    """Generate code cho Video Intro/Outro/Combo animations"""
    name = item.get('name', 'Unknown')
    resource_id = item.get('resource_id', '')
    effect_id = item.get('id', '') or resource_id
    
    # Get path - CRITICAL for animation to work in CapCut
    path = item.get('path', '').replace('\\', '/')
    
    # Try to get MD5 from path (format: .../resource_id/md5_hash)
    md5 = item.get('file_md5', '')
    if not md5 and path:
        path_parts = path.replace('\\', '/').rstrip('/').split('/')
        if len(path_parts) >= 1 and len(path_parts[-1]) == 32:
            md5 = path_parts[-1]
    
    # Duration from CapCut is in microseconds, convert to seconds
    duration_us = item.get('duration', 500000)  # Default 0.5s
    duration_sec = duration_us / 1_000_000 if duration_us > 1000 else duration_us
    
    var_name = sanitize_effect_name(name)
    padded_var = f"{var_name:<20}"
    
    # Generate code WITH path for CapCut compatibility
    if path:
        code = f'    {padded_var} = AnimationMeta("{name}", False, {duration_sec:.3f}, "{resource_id}", "{effect_id}", "{md5}", path="{path}")'
    else:
        code = f'    {padded_var} = AnimationMeta("{name}", False, {duration_sec:.3f}, "{resource_id}", "{effect_id}", "{md5}")'
    return code


def generate_transition_code(item: dict) -> str:
    """Generate code cho TransitionMeta (transitions)"""
    name = item.get('name', 'Unknown')
    effect_id = item.get('effect_id', '')
    resource_id = item.get('resource_id', '')
    category_id = item.get('category_id', '')
    category_name = item.get('category_name', '')
    path = item.get('path', '').replace('\\', '/')
    source_platform = item.get('source_platform', 0)
    request_id = item.get('request_id', '')
    # Duration từ CapCut draft là microseconds, cần convert sang seconds
    duration_us = item.get('duration', 500000)  # Default 0.5s in microseconds
    duration_sec = duration_us / 1_000_000  # Convert to seconds
    is_overlap = item.get('is_overlap', True)
    
    var_name = sanitize_effect_name(name)
    padded_var = f"{var_name:<20}"
    
    # TransitionMeta signature: (name, is_vip, resource_id, effect_id, md5, duration_in_seconds, is_overlap, *, path, category_name, category_id, source_platform, request_id)
    code = f'    {padded_var} = TransitionMeta("{name}", False, "{resource_id}", "{effect_id}", "{category_id}", {duration_sec:.3f}, {is_overlap}'
    
    # Build kwargs
    kwargs = []
    if path:
        kwargs.append(f'path="{path}"')
    if category_name:
        kwargs.append(f'category_name="{category_name}"')
    if category_id:
        kwargs.append(f'category_id="{category_id}"')
    if source_platform:
        kwargs.append(f'source_platform={source_platform}')
    if request_id:
        kwargs.append(f'request_id="{request_id}"')
    
    if kwargs:
        code += ', ' + ', '.join(kwargs)
    code += ')'
    return code


def add_items_to_file(items: list, file_path: str, existing_names: set, 
                       item_type: str, code_generator) -> tuple:
    """Thêm items mới vào file"""
    new_items = []
    skipped = []
    
    for item in items:
        name = item.get('name', '')
        if not name:
            continue
            
        if name in existing_names:
            skipped.append(name)
        else:
            new_items.append(item)
            existing_names.add(name)
    
    if not new_items:
        return 0, skipped
    
    # Generate code
    new_code_lines = [f"\n    # === VINH AUTO-IMPORTED {item_type.upper()}S ==="]
    for item in new_items:
        new_code_lines.append(code_generator(item))
    
    new_code = "\n".join(new_code_lines)
    
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(new_code + "\n")
    
    return len(new_items), skipped


def print_section(title: str):
    print(f"\n" + "-" * 40)
    print(f"📁 {title}")
    print("-" * 40)


def print_results(added: int, skipped: list, item_type: str):
    if skipped:
        print(f"\n⏭️ Bỏ qua {len(skipped)} {item_type} đã tồn tại:")
        for name in skipped[:3]:
            print(f"   - {name}")
        if len(skipped) > 3:
            print(f"   ... và {len(skipped) - 3} {item_type} khác")
    
    if added > 0:
        print(f"\n✅ Đã thêm {added} {item_type} mới!")
    else:
        print(f"\n✅ Không có {item_type} mới cần thêm")


# ============ MAIN ============
def sync_all_from_draft(draft_folder: str, draft_name: str):
    """Đồng bộ tất cả: video effects, filters, audio effects, transitions, fonts, text loops"""
    
    print("=" * 80)
    print("🔄 SYNC ALL EFFECTS FROM CAPCUT DRAFT")
    print("   ├─ Video Effects → video_scene_effect.py")
    print("   ├─ Filters → filter_meta.py")
    print("   ├─ Audio Effects → audio_scene_effect.py")
    print("   ├─ Transitions → transition_meta.py")
    print("   ├─ Fonts → font_meta.py")
    print("   ├─ Text Loop Anims → text_loop.py")
    print("   ├─ Text Intros → text_intro.py")
    print("   ├─ Text Outros → text_outro.py")
    print("   ├─ Video Intros → video_intro.py")
    print("   ├─ Video Outros → video_outro.py")
    print("   └─ Combo Anims → combo_animation.py")
    print("=" * 80)
    
    # 1. Đọc draft
    draft_path = os.path.join(draft_folder, draft_name, "draft_content.json")
    
    if not os.path.exists(draft_path):
        print(f"❌ Không tìm thấy: {draft_path}")
        print(f"\n📂 Các drafts có sẵn:")
        for name in os.listdir(draft_folder):
            if os.path.isdir(os.path.join(draft_folder, name)):
                print(f"   - {name}")
        return
    
    print(f"📂 Draft: {draft_name}")
    print(f"📄 File: {draft_path}")
    
    with open(draft_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    materials = data.get("materials", {})
    
    # 2. Thu thập items từ các nguồn
    video_effects = materials.get("video_effects", [])
    filters = materials.get("effects", [])  # "effects" key thường là filters
    audio_effects = materials.get("audio_effects", [])
    transitions = materials.get("transitions", [])
    
    # Extract fonts from text segments - check MULTIPLE sources
    fonts = []
    texts = materials.get("texts", [])
    seen_fonts = set()
    
    for text in texts:
        font_found = False
        
        # === SOURCE 1: Top-level text fields ===
        top_font_name = text.get("font_name", "")
        top_font_id = text.get("font_id", "") or text.get("global_font_source_id", "")
        top_font_path = text.get("font_path", "")
        
        # If font_name is empty but path exists, extract from path
        if not top_font_name and top_font_path:
            # Path: C:/Users/.../Cache/effect/resource_id/md5/fontname.ttf
            path_basename = os.path.basename(top_font_path)
            top_font_name = path_basename.replace('.ttf', '').replace('.otf', '').replace('.TTF', '').replace('.OTF', '')
            
            # Also try to extract resource_id from path
            if not top_font_id:
                path_parts = top_font_path.replace('\\', '/').split('/')
                for part in path_parts:
                    if part.isdigit() and len(part) > 10:
                        top_font_id = part
                        break
        
        if top_font_name and top_font_name not in seen_fonts:
            fonts.append({
                "name": top_font_name,
                "resource_id": top_font_id,
                "effect_id": top_font_id,
                "file_md5": ""
            })
            seen_fonts.add(top_font_name)
            font_found = True
        
        # === SOURCE 2: content.styles.font ===
        content_raw = text.get("content", {})
        if isinstance(content_raw, str):
            try:
                content_parsed = json.loads(content_raw)
            except json.JSONDecodeError:
                content_parsed = {}
        else:
            content_parsed = content_raw
        
        for style in content_parsed.get("styles", []):
            font_info = style.get("font", {})
            # Try multiple name fields
            font_name = font_info.get("name", "") or font_info.get("title", "")
            
            # If no name, extract from path
            if not font_name and font_info.get("path"):
                font_name = os.path.basename(font_info.get("path", "")).replace('.ttf', '').replace('.otf', '').replace('.TTF', '').replace('.OTF', '')
            
            resource_id = font_info.get("id", "") or font_info.get("resource_id", "")
            
            if font_name and font_name not in seen_fonts:
                fonts.append({
                    "name": font_name,
                    "resource_id": resource_id,
                    "effect_id": resource_id,
                    "file_md5": font_info.get("file_md5", "")
                })
                seen_fonts.add(font_name)
        
        # === SOURCE 3: text.fonts[] array ===
        # CapCut stores fonts in a dedicated fonts array with 'title' as the name field
        fonts_array = text.get("fonts", [])
        for font_item in fonts_array:
            # Use 'title' field for font name (not 'name')
            font_name = font_item.get("title", "") or font_item.get("name", "")
            resource_id = font_item.get("resource_id", "")
            
            # If no name, try to extract from path
            if not font_name and font_item.get("path"):
                font_path = font_item.get("path", "")
                font_name = os.path.basename(font_path).replace('.ttf', '').replace('.otf', '').replace('.TTF', '').replace('.OTF', '')
            
            if font_name and font_name not in seen_fonts:
                fonts.append({
                    "name": font_name,
                    "resource_id": resource_id,
                    "effect_id": resource_id,
                    "file_md5": font_item.get("file_md5", "")
                })
                seen_fonts.add(font_name)
    
    # Extract animations from material_animations
    # NOTE: Animations are nested inside material_animations[].animations[]
    text_loops = []
    text_intros = []
    text_outros = []
    seen_loops = set()
    seen_text_intros = set()
    seen_text_outros = set()
    animations = materials.get("material_animations", [])
    for anim_container in animations:
        # Check inner animations array
        inner_anims = anim_container.get("animations", [])
        for inner in inner_anims:
            anim_type = inner.get("type", "")
            category = inner.get("category_name", "").lower()
            name = inner.get("name", "")
            resource_id = inner.get("resource_id", "")
            
            if not name or not resource_id:
                continue
            
            anim_data = {
                "name": name,
                "resource_id": resource_id,
                "effect_id": inner.get("effect_id", "") or resource_id,
                "file_md5": inner.get("file_md5", ""),
                "path": inner.get("path", ""),
                "duration": inner.get("duration", 500000)
            }
            
            # Classify animations by type
            if anim_type == "loop" or "loop" in category:
                if name not in seen_loops:
                    text_loops.append(anim_data)
                    seen_loops.add(name)
            elif anim_type == "in" and name not in seen_text_intros:
                text_intros.append(anim_data)
                seen_text_intros.add(name)
            elif anim_type == "out" and name not in seen_text_outros:
                text_outros.append(anim_data)
                seen_text_outros.add(name)
    
    # Extract video intro/outro/combo animations from material_animations
    video_intros = []
    video_outros = []
    combo_anims = []
    seen_intros = set()
    seen_outros = set()
    seen_combos = set()
    
    for anim_container in animations:
        inner_anims = anim_container.get("animations", [])
        for inner in inner_anims:
            anim_type = inner.get("type", "")
            name = inner.get("name", "")
            resource_id = inner.get("resource_id", "")
            
            if not name or not resource_id:
                continue
            
            anim_data = {
                "name": name,
                "resource_id": resource_id,
                "id": inner.get("id", ""),
                "file_md5": inner.get("file_md5", ""),
                "path": inner.get("path", ""),
                "duration": inner.get("duration", 500000)
            }
            
            if anim_type == "in" and name not in seen_intros:
                video_intros.append(anim_data)
                seen_intros.add(name)
            elif anim_type == "out" and name not in seen_outros:
                video_outros.append(anim_data)
                seen_outros.add(name)
            elif anim_type == "group" and name not in seen_combos:
                combo_anims.append(anim_data)
                seen_combos.add(name)
    
    print(f"\n📊 Tìm thấy trong draft:")
    print(f"   ├─ video_effects: {len(video_effects)}")
    print(f"   ├─ filters (effects): {len(filters)}")
    print(f"   ├─ audio_effects: {len(audio_effects)}")
    print(f"   ├─ transitions: {len(transitions)}")
    print(f"   ├─ fonts: {len(fonts)}")
    print(f"   ├─ text_loops: {len(text_loops)}")
    print(f"   ├─ text_intros: {len(text_intros)}")
    print(f"   ├─ text_outros: {len(text_outros)}")
    print(f"   ├─ video_intros: {len(video_intros)}")
    print(f"   ├─ video_outros: {len(video_outros)}")
    print(f"   └─ combo_anims: {len(combo_anims)}")
    
    total_added = 0
    
    # 3. XỬ LÝ VIDEO EFFECTS
    if video_effects:
        print_section("XỬ LÝ VIDEO EFFECTS")
        print(f"📖 File đích: {os.path.basename(EFFECT_FILE)}")
        
        existing = get_existing_names(EFFECT_FILE)
        print(f"   Đã có: {len(existing)} effects")
        
        added, skipped = add_items_to_file(
            video_effects, EFFECT_FILE, existing, "effect", generate_effect_code
        )
        print_results(added, skipped, "effects")
        total_added += added
    
    # 4. XỬ LÝ FILTERS
    if filters:
        print_section("XỬ LÝ FILTERS")
        print(f"📖 File đích: {os.path.basename(FILTER_FILE)}")
        
        existing = get_existing_names(FILTER_FILE)
        print(f"   Đã có: {len(existing)} filters")
        
        added, skipped = add_items_to_file(
            filters, FILTER_FILE, existing, "filter", generate_effect_code
        )
        print_results(added, skipped, "filters")
        total_added += added
    
    # 5. XỬ LÝ AUDIO EFFECTS
    if audio_effects:
        print_section("XỬ LÝ AUDIO EFFECTS")
        print(f"📖 File đích: {os.path.basename(AUDIO_EFFECT_FILE)}")
        
        existing = get_existing_names(AUDIO_EFFECT_FILE)
        print(f"   Đã có: {len(existing)} audio effects")
        
        added, skipped = add_items_to_file(
            audio_effects, AUDIO_EFFECT_FILE, existing, "audio effect", generate_effect_code
        )
        print_results(added, skipped, "audio effects")
        total_added += added
    
    # 6. XỬ LÝ TRANSITIONS
    if transitions:
        print_section("XỬ LÝ TRANSITIONS")
        print(f"📖 File đích: {os.path.basename(TRANSITION_FILE)}")
        
        existing = get_existing_names(TRANSITION_FILE)
        print(f"   Đã có: {len(existing)} transitions")
        
        added, skipped = add_items_to_file(
            transitions, TRANSITION_FILE, existing, "transition", generate_transition_code
        )
        print_results(added, skipped, "transitions")
        total_added += added
    
    # 7. XỬ LÝ FONTS
    if fonts:
        print_section("XỬ LÝ FONTS")
        print(f"📖 File đích: {os.path.basename(FONT_FILE)}")
        
        existing = get_existing_names(FONT_FILE)
        print(f"   Đã có: {len(existing)} fonts")
        
        added, skipped = add_items_to_file(
            fonts, FONT_FILE, existing, "font", generate_font_code
        )
        print_results(added, skipped, "fonts")
        total_added += added
    
    # 8. XỬ LÝ TEXT LOOP ANIMATIONS
    if text_loops:
        print_section("XỬ LÝ TEXT LOOP ANIMATIONS")
        print(f"📖 File đích: {os.path.basename(TEXT_LOOP_FILE)}")
        
        existing = get_existing_names(TEXT_LOOP_FILE)
        print(f"   Đã có: {len(existing)} text loops")
        
        added, skipped = add_items_to_file(
            text_loops, TEXT_LOOP_FILE, existing, "text loop", generate_text_loop_code
        )
        print_results(added, skipped, "text loops")
        total_added += added
    
    # 9. XỬ LÝ TEXT INTRO ANIMATIONS
    if text_intros:
        print_section("XỬ LÝ TEXT INTRO ANIMATIONS")
        print(f"📖 File đích: {os.path.basename(TEXT_INTRO_FILE)}")
        
        existing = get_existing_names(TEXT_INTRO_FILE)
        print(f"   Đã có: {len(existing)} text intros")
        
        added, skipped = add_items_to_file(
            text_intros, TEXT_INTRO_FILE, existing, "text intro", generate_text_anim_code
        )
        print_results(added, skipped, "text intros")
        total_added += added
    
    # 10. XỬ LÝ TEXT OUTRO ANIMATIONS
    if text_outros:
        print_section("XỬ LÝ TEXT OUTRO ANIMATIONS")
        print(f"📖 File đích: {os.path.basename(TEXT_OUTRO_FILE)}")
        
        existing = get_existing_names(TEXT_OUTRO_FILE)
        print(f"   Đã có: {len(existing)} text outros")
        
        added, skipped = add_items_to_file(
            text_outros, TEXT_OUTRO_FILE, existing, "text outro", generate_text_anim_code
        )
        print_results(added, skipped, "text outros")
        total_added += added
    
    # 11. XỬ LÝ VIDEO INTROS
    if video_intros:
        print_section("XỬ LÝ VIDEO INTROS")
        print(f"📖 File đích: {os.path.basename(VIDEO_INTRO_FILE)}")
        
        existing = get_existing_names(VIDEO_INTRO_FILE)
        print(f"   Đã có: {len(existing)} video intros")
        
        added, skipped = add_items_to_file(
            video_intros, VIDEO_INTRO_FILE, existing, "video intro", generate_video_anim_code
        )
        print_results(added, skipped, "video intros")
        total_added += added
    
    # 12. XỬ LÝ VIDEO OUTROS
    if video_outros:
        print_section("XỬ LÝ VIDEO OUTROS")
        print(f"📖 File đích: {os.path.basename(VIDEO_OUTRO_FILE)}")
        
        existing = get_existing_names(VIDEO_OUTRO_FILE)
        print(f"   Đã có: {len(existing)} video outros")
        
        added, skipped = add_items_to_file(
            video_outros, VIDEO_OUTRO_FILE, existing, "video outro", generate_video_anim_code
        )
        print_results(added, skipped, "video outros")
        total_added += added
    
    # 13. XỬ LÝ COMBO ANIMATIONS
    if combo_anims:
        print_section("XỬ LÝ COMBO ANIMATIONS")
        print(f"📖 File đích: {os.path.basename(COMBO_ANIM_FILE)}")
        
        existing = get_existing_names(COMBO_ANIM_FILE)
        print(f"   Đã có: {len(existing)} combo anims")
        
        added, skipped = add_items_to_file(
            combo_anims, COMBO_ANIM_FILE, existing, "combo anim", generate_video_anim_code
        )
        print_results(added, skipped, "combo anims")
        total_added += added
    
    # 14. Tổng kết
    print("\n" + "=" * 80)
    if total_added > 0:
        print(f"🎉 HOÀN THÀNH! Đã thêm tổng cộng {total_added} items mới!")
    else:
        all_empty = not (video_effects or filters or audio_effects or transitions or fonts or text_loops or text_intros or text_outros or video_intros or video_outros or combo_anims)
        if all_empty:
            print(f"⚠️ Không tìm thấy effects/animations nào trong draft!")
        else:
            print(f"✅ HOÀN THÀNH! Tất cả items đã được đồng bộ trước đó.")
    print("=" * 80)


if __name__ == "__main__":
    sync_all_from_draft(DRAFT_FOLDER, DRAFT_NAME)