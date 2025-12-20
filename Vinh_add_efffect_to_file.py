"""
Script tự động đồng bộ Video Effects từ CapCut draft vào video_scene_effect.py
- Đọc draft_content.json từ project CapCut
- Lấy danh sách video effects
- Kiểm tra trùng lặp theo tên
- Thêm effect mới vào cuối file video_scene_effect.py
"""

import json
import os
import re

# ============ CẤU HÌNH ============
DRAFT_FOLDER = r"C:\Users\VINH\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft"
DRAFT_NAME = "effect_library"  # Tên project trong CapCut

# Đường dẫn file video_scene_effect.py
EFFECT_FILE = os.path.join(os.path.dirname(__file__), "pycapcut", "metadata", "video_scene_effect.py")


# ============ HELPER FUNCTIONS ============
def sanitize_effect_name(name: str) -> str:
    """Chuyển tên effect thành tên biến Python hợp lệ"""
    # Replace spaces and special chars with underscore
    sanitized = re.sub(r'[^\w\u4e00-\u9fff]', '_', name)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    # Ensure it doesn't start with a number
    if sanitized and sanitized[0].isdigit():
        sanitized = '_' + sanitized
    return sanitized or 'Unknown'


def get_existing_effect_names(file_path: str) -> set:
    """Lấy danh sách tên effects đã có trong file"""
    existing_names = set()
    
    if not os.path.exists(file_path):
        return existing_names
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Tìm tất cả các EffectMeta("name", ...)
    # Pattern: EffectMeta("TênEffect", ...)
    pattern = r'EffectMeta\("([^"]+)"'
    matches = re.findall(pattern, content)
    
    for match in matches:
        existing_names.add(match)
    
    return existing_names


def generate_effect_code(effect: dict) -> str:
    """Generate code cho một effect"""
    name = effect.get('name', 'Unknown')
    effect_id = effect.get('effect_id', '')
    resource_id = effect.get('resource_id', '')
    category_id = effect.get('category_id', '')
    
    var_name = sanitize_effect_name(name)
    
    # Pad variable name for alignment
    padded_var = f"{var_name:<20}"
    
    return f'    {padded_var} = EffectMeta("{name}", False, "{effect_id}", "{resource_id}", "{category_id}", [])'


def add_effects_to_file(effects: list, file_path: str, existing_names: set):
    """Thêm effects mới vào file"""
    new_effects = []
    skipped = []
    
    for effect in effects:
        name = effect.get('name', '')
        if not name:
            continue
            
        if name in existing_names:
            skipped.append(name)
        else:
            new_effects.append(effect)
            existing_names.add(name)
    
    if not new_effects:
        return 0, skipped
    
    # Đọc file hiện tại
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Tìm vị trí cuối cùng của class (trước dấu """ cuối cùng hoặc cuối file)
    # Thêm effects mới trước dòng cuối của class
    
    # Generate code cho các effects mới
    new_code_lines = ["\n    # === VINH AUTO-IMPORTED EFFECTS ==="]
    for effect in new_effects:
        new_code_lines.append(generate_effect_code(effect))
    
    new_code = "\n".join(new_code_lines)
    
    # Tìm vị trí để chèn (cuối file, trước dòng trống cuối cùng)
    # Append vào cuối file
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(new_code + "\n")
    
    return len(new_effects), skipped


# ============ MAIN ============
def sync_effects_from_draft(draft_folder: str, draft_name: str):
    """Đồng bộ video effects từ draft vào video_scene_effect.py"""
    
    print("=" * 80)
    print("🔄 SYNC VIDEO EFFECTS FROM CAPCUT DRAFT")
    print("=" * 80)
    
    # 1. Đọc draft
    draft_path = os.path.join(draft_folder, draft_name, "draft_content.json")
    
    if not os.path.exists(draft_path):
        print(f"❌ Không tìm thấy: {draft_path}")
        print(f"\n� Các drafts có sẵn:")
        for name in os.listdir(draft_folder):
            if os.path.isdir(os.path.join(draft_folder, name)):
                print(f"   - {name}")
        return
    
    print(f"📂 Draft: {draft_name}")
    print(f"📄 File: {draft_path}")
    
    with open(draft_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    materials = data.get("materials", {})
    video_effects = materials.get("video_effects", [])
    
    print(f"\n🎬 Tìm thấy {len(video_effects)} video effects trong draft")
    
    if not video_effects:
        print("⚠️ Không có video effects nào trong draft!")
        return
    
    # 2. Lấy danh sách effects đã có
    print(f"\n📖 Đọc file: {EFFECT_FILE}")
    existing_names = get_existing_effect_names(EFFECT_FILE)
    print(f"   Đã có {len(existing_names)} effects trong file")
    
    # 3. Thêm effects mới
    print("\n🔍 Kiểm tra và thêm effects mới...")
    
    added_count, skipped = add_effects_to_file(video_effects, EFFECT_FILE, existing_names)
    
    # 4. Báo cáo
    print("\n" + "=" * 80)
    print("📊 KẾT QUẢ:")
    print("=" * 80)
    
    if skipped:
        print(f"\n⏭️ BỎ QUA ({len(skipped)} effects đã tồn tại):")
        for name in skipped:
            print(f"   - {name}")
    
    if added_count > 0:
        print(f"\n✅ ĐÃ THÊM {added_count} effects mới vào file!")
        print(f"   File: {EFFECT_FILE}")
    else:
        print("\n✅ Không có effect mới cần thêm!")
    
    print("=" * 80)


if __name__ == "__main__":
    sync_effects_from_draft(DRAFT_FOLDER, DRAFT_NAME)