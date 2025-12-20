# Tech Context: pyCapCut

## Technology Stack

### Language
- **Python >= 3.8**

### Dependencies
| Package | Purpose |
|---------|---------|
| `pymediainfo` | Extract media file metadata (duration, dimensions, codec) |
| `imageio` | Image file handling |
| `uiautomation>=2` | Windows UI automation for batch export (Windows only) |

### Package Structure
- Distributed via PyPI: `pip install pycapcut`
- Current version: 0.0.3

## Development Setup

### Installation
```bash
# From PyPI
pip install pycapcut

# From source
git clone https://github.com/GuanYixuan/pycapcut.git
cd pycapcut
pip install -e .
```

### Running Demo
```bash
python demo.py
```
Requires CapCut installed with a valid drafts folder.

## Technical Constraints

### Platform Requirements
- **Draft Generation**: Cross-platform (Windows, Linux, MacOS)
- **Draft Export**: Windows only (CapCut Windows version required)
- **Batch Export Automation**: Windows only (uses `uiautomation`)

### CapCut Compatibility
- Drafts stored in `draft_content.json` format
- Materials referenced by path in draft JSON
- Draft folder structure:
  ```
  CapCut Drafts/
  └── [Draft Name]/
      ├── draft_content.json
      └── [copied materials]
  ```

### Known Limitations
- No curve-based speed ramping (only constant speed)
- Template mode: Cannot modify imported tracks beyond replacement
- Some effects may not work if not available in user's CapCut version

## File Formats

### Supported Media
- **Video**: MP4, MOV, AVI, etc. (anything CapCut supports)
- **Audio**: MP3, WAV, AAC, etc.
- **Image**: JPG, PNG, etc.
- **Subtitles**: SRT format for import

### Output
- `draft_content.json`: Main draft data file
- Draft folder with copied materials

## Code Quality

### Linting
- `.flake8` configuration present
- Follows Python code style guidelines

### Testing
- Demo script (`demo.py`) serves as integration test
- Manual verification in CapCut required for full testing

## External Integrations

### CapCut/JianYing Controller
- `jianying_controller.py` provides Windows automation
- Opens drafts, triggers exports, controls UI elements
- Uses `uiautomation` Python package

### Related Projects
- [PyJianYingDraft](https://github.com/GuanYixuan/pyJianYingDraft): Sister project for JianYing
- Same author, shared codebase origins
