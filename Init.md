# pyCapCut - Hướng Dẫn Cài Đặt (Init Guide)

Tài liệu hướng dẫn cài đặt và chạy pyCapCut trong môi trường **Development** và **Production**.

---

## 📋 Yêu Cầu Hệ Thống

| Yêu cầu | Chi tiết |
|---------|----------|
| **Python** | >= 3.8 |
| **OS** | Windows (bắt buộc để export draft), Linux/macOS (chỉ tạo draft) |
| **CapCut** | Windows version (để mở và export các draft đã tạo) |

### Dependencies
```
pymediainfo      # Đọc metadata của file media (duration, dimensions)
imageio          # Xử lý file ảnh
uiautomation>=2  # Tự động hóa UI Windows (chỉ Windows, cho batch export)
```

---

## 🔧 Development Mode

### 1. Clone và Cài Đặt

```bash
# Clone repository
git clone https://github.com/GuanYixuan/pycapcut.git
cd pycapcut

# Cài đặt ở chế độ development (editable mode)
pip install -e .
```

### 2. Cấu Hình CapCut Drafts Path

Tìm thư mục lưu draft của CapCut:
- Mở CapCut → **Settings** → **Drafts Location**
- Thường có dạng: `C:\Users\<username>\CapCut Drafts\`

### 3. Chạy Demo

Sửa file `demo.py`, thay thế đường dẫn:

```python
# Trước
draft_folder = cc.DraftFolder(r"<你的草稿文件夹>")

# Sau (ví dụ)
draft_folder = cc.DraftFolder(r"C:\Users\YourName\Documents\CapCut Drafts")
```

Chạy demo:

```bash
python demo.py
```

### 4. Kiểm Tra Kết Quả

1. Mở CapCut
2. Tìm draft tên **"demo"** trong danh sách
3. Nếu không thấy: vào/ra một draft khác hoặc restart CapCut để refresh
4. Mở draft và kiểm tra timeline

### 5. Development Workflow

```python
import pycapcut as cc
from pycapcut import trange, SEC

# Khởi tạo folder quản lý drafts
draft_folder = cc.DraftFolder(r"<CapCut Drafts Path>")

# Tạo draft mới
script = draft_folder.create_draft("my_draft", 1920, 1080, fps=30, allow_replace=True)

# Thêm tracks
script.add_track(cc.TrackType.video)
script.add_track(cc.TrackType.audio)
script.add_track(cc.TrackType.text)

# Thêm segments
video_seg = cc.VideoSegment("path/to/video.mp4", trange("0s", "5s"))
script.add_segment(video_seg)

# Lưu draft
script.save()
```

---

## 🚀 Production Mode

### 1. Cài Đặt Từ PyPI

```bash
pip install pycapcut
```

### 2. Kiểm Tra Cài Đặt

```bash
python -c "import pycapcut; print('pycapcut installed successfully')"
```

### 3. Sử Dụng Trong Production

#### 3.1 Tạo Draft Tự Động

```python
import pycapcut as cc
from pycapcut import trange

def create_video_draft(draft_folder_path: str, draft_name: str, video_path: str, audio_path: str = None):
    """Tạo một draft đơn giản với video và audio tùy chọn"""
    
    # Khởi tạo
    folder = cc.DraftFolder(draft_folder_path)
    script = folder.create_draft(draft_name, 1920, 1080, allow_replace=True)
    
    # Thêm tracks
    script.add_track(cc.TrackType.video)
    if audio_path:
        script.add_track(cc.TrackType.audio)
    
    # Thêm video
    video_mat = cc.VideoMaterial(video_path)
    video_seg = cc.VideoSegment(video_mat, trange(0, video_mat.duration))
    script.add_segment(video_seg)
    
    # Thêm audio nếu có
    if audio_path:
        audio_mat = cc.AudioMaterial(audio_path)
        audio_seg = cc.AudioSegment(audio_mat, trange(0, audio_mat.duration))
        script.add_segment(audio_seg)
    
    # Lưu
    script.save()
    return script

# Sử dụng
create_video_draft(
    draft_folder_path=r"C:\Users\YourName\Documents\CapCut Drafts",
    draft_name="my_production_video",
    video_path=r"C:\path\to\video.mp4",
    audio_path=r"C:\path\to\audio.mp3"
)
```

#### 3.2 Template Mode (Dùng Draft Có Sẵn Làm Mẫu)

```python
import pycapcut as cc

folder = cc.DraftFolder(r"<CapCut Drafts Path>")

# Tải template và tạo bản sao
script = folder.duplicate_as_template("template_name", "new_draft_name", allow_replace=True)

# Thay thế media bằng tên
new_video = cc.VideoMaterial("new_video.mp4")
script.replace_material_by_name("old_video.mp4", new_video)

# Thay thế text
text_track = script.get_imported_track(cc.TrackType.text, index=0)
script.replace_text(text_track, 0, "Nội dung mới")

# Lưu
script.save()
```

#### 3.3 Batch Export (Windows Only, CapCut Phải Đang Mở)

```python
from pycapcut.jianying_controller import JianyingController, ExportResolution, ExportFramerate

# CapCut phải đang mở ở trang Home
controller = JianyingController()

# Export draft
controller.export_draft(
    draft_name="my_draft",
    output_path=r"C:\output\my_video.mp4",
    resolution=ExportResolution.RES_1080P,
    framerate=ExportFramerate.FR_30,
    timeout=1200  # seconds
)
```

---

## 📁 Cấu Trúc Thư Mục Draft

```
CapCut Drafts/
└── my_draft/
    ├── draft_content.json    # File chính chứa dữ liệu draft
    ├── draft_meta_info.json  # Metadata của draft
    └── [các file media được copy vào]
```

---

## 🔍 Debugging

### Kiểm Tra Draft JSON

```python
import json

with open(r"<CapCut Drafts>\my_draft\draft_content.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    print(json.dumps(data, indent=2, ensure_ascii=False))
```

### Trích Xuất Metadata Của Stickers/Effects

```python
folder = cc.DraftFolder(r"<CapCut Drafts Path>")
folder.inspect_material("draft_name")  # In ra resource_id của stickers, bubbles, etc.
```

---

## ⚠️ Lưu Ý Quan Trọng

| Vấn đề | Giải pháp |
|--------|-----------|
| Draft không hiện trong CapCut | Restart CapCut hoặc vào/ra một draft khác |
| Video đen | Kiểm tra đường dẫn file, đảm bảo file tồn tại |
| Effect không hoạt động | Kiểm tra effect có sẵn trong phiên bản CapCut của bạn |
| Batch export lỗi | Đảm bảo CapCut đang mở tại trang Home, không phải trong edit mode |
| Template mode mất nội dung | Một số tính năng phức tạp có thể không được hỗ trợ hoàn toàn |

---

## 📚 Tham Khảo Thêm

- [README tiếng Việt/Trung](README.md)
- [English README](english_readme.md)
- [Demo Code](demo.py)
- [Discord Community](https://discord.gg/WfHgGQvhyW)
- [GitHub Issues](https://github.com/GuanYixuan/pycapcut/issues)
