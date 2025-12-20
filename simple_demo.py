"""
Demo đơn giản: Thêm video và text vào CapCut draft
Production mode - sử dụng pycapcut từ PyPI
"""

import pycapcut as cc
from pycapcut import trange, SEC

# Đường dẫn
DRAFT_FOLDER = r"C:\Users\VINH\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft"
VIDEO_PATH = r"F:\Automation Folder\Veo3Video\video1.mp4"

# Khởi tạo folder quản lý drafts
print("Initializing DraftFolder...")
draft_folder = cc.DraftFolder(DRAFT_FOLDER)

# Tạo draft mới 1920x1080, 30fps
print("Creating new draft: text_demo...")
script = draft_folder.create_draft("text_demo", 1920, 1080, fps=30, allow_replace=True)

# Thêm tracks
print("Adding tracks...")
script.add_track(cc.TrackType.video)
script.add_track(cc.TrackType.text)

# Tạo video material và segment
print(f"Loading video: {VIDEO_PATH}")
video_mat = cc.VideoMaterial(VIDEO_PATH)
video_duration = video_mat.duration
print(f"Video duration: {video_duration / SEC:.2f} seconds")

# Tạo video segment - toàn bộ video
video_seg = cc.VideoSegment(video_mat, trange(0, video_duration))
script.add_segment(video_seg)
print("Added video segment")

# Tạo text segment - hiển thị trên toàn bộ video
text_content = "Hello pyCapCut!\nDemo by Production Mode"
text_seg = cc.TextSegment(
    text_content,
    trange(0, video_duration),  # Hiển thị suốt video
    style=cc.TextStyle(
        size=8.0,  # Kích thước font
        color=(1.0, 1.0, 0.0),  # Màu vàng
    ),
    clip_settings=cc.ClipSettings(transform_y=-0.7)  # Vị trí phía dưới màn hình
)
script.add_segment(text_seg)
print("Added text segment")

# Lưu draft
script.save()
print(f"\n✅ Draft saved successfully!")
print(f"📁 Draft location: {DRAFT_FOLDER}\\text_demo")
print(f"\n📌 Để xem draft:")
print("   1. Mở CapCut")
print("   2. File → Open → Chọn folder draft")
print("   3. Hoặc copy folder 'text_demo' vào thư mục CapCut Drafts của bạn")
