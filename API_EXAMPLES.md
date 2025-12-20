# pyCapCut API Server - cURL Examples

## Create Draft
```bash
curl -X POST http://localhost:8000/create_draft \
  -H "Content-Type: application/json" \
  -d "{\"draft_name\": \"my_video\", \"width\": 1920, \"height\": 1080}"
```

## Add Video
```bash
curl -X POST http://localhost:8000/add_video \
  -H "Content-Type: application/json" \
  -d "{\"draft_id\": \"YOUR_DRAFT_ID\", \"video_path\": \"C:/path/to/video.mp4\", \"start\": 0, \"duration\": 10}"
```

## Add Audio
```bash
curl -X POST http://localhost:8000/add_audio \
  -H "Content-Type: application/json" \
  -d "{\"draft_id\": \"YOUR_DRAFT_ID\", \"audio_path\": \"C:/path/to/audio.mp3\", \"volume\": 0.8}"
```

## Add Text
```bash
curl -X POST http://localhost:8000/add_text \
  -H "Content-Type: application/json" \
  -d "{\"draft_id\": \"YOUR_DRAFT_ID\", \"text\": \"Hello World!\", \"start\": 0, \"duration\": 5, \"font_size\": 8, \"font_color\": \"#FFFF00\", \"transform_y\": -0.7}"
```

## Add Image
```bash
curl -X POST http://localhost:8000/add_image \
  -H "Content-Type: application/json" \
  -d "{\"draft_id\": \"YOUR_DRAFT_ID\", \"image_path\": \"C:/path/to/image.png\", \"start\": 0, \"duration\": 3}"
```

## Add Subtitles (SRT)
```bash
curl -X POST http://localhost:8000/add_subtitle \
  -H "Content-Type: application/json" \
  -d "{\"draft_id\": \"YOUR_DRAFT_ID\", \"srt_path\": \"C:/path/to/subtitles.srt\"}"
```

## Save Draft
```bash
curl -X POST http://localhost:8000/save_draft \
  -H "Content-Type: application/json" \
  -d "{\"draft_id\": \"YOUR_DRAFT_ID\"}"
```

## Get Available Animation Types
```bash
curl http://localhost:8000/get_intro_animation_types
curl http://localhost:8000/get_outro_animation_types
curl http://localhost:8000/get_transition_types
curl http://localhost:8000/get_font_types
```

## Health Check
```bash
curl http://localhost:8000/health
```

## API Info
```bash
curl http://localhost:8000/
```

---

## Windows PowerShell Examples

### Create Draft
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/create_draft" -Method POST -ContentType "application/json" -Body '{"draft_name": "my_video", "width": 1920, "height": 1080}'
```

### Add Video
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/add_video" -Method POST -ContentType "application/json" -Body '{"draft_id": "YOUR_DRAFT_ID", "video_path": "C:/path/to/video.mp4"}'
```

### Save Draft
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/save_draft" -Method POST -ContentType "application/json" -Body '{"draft_id": "YOUR_DRAFT_ID"}'
```
