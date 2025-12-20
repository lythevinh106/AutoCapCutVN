# Product Context: pyCapCut

## Why This Project Exists

### Problem Statement
Video editing is traditionally a manual, time-consuming process. CapCut is a popular video editor, but its interface requires manual interaction for each edit. For users needing to:
- Create many similar videos with different content
- Automate repetitive editing tasks
- Build video processing pipelines

...there was no programmatic solution for CapCut workflow automation.

### Solution
pyCapCut provides a Python API to generate CapCut-compatible draft files (`draft_content.json`), enabling:
- Automated video editing pipelines
- Template-based video generation
- Batch processing of video content

## How It Works

### Workflow Concept
```
[Python Script] → [Generate Draft JSON] → [CapCut Drafts Folder] → [Open in CapCut] → [Export]
```

1. **Script Creation**: Write Python code using pyCapCut API
2. **Draft Generation**: Script creates `draft_content.json` and copies materials
3. **Load in CapCut**: Open the generated draft in CapCut application
4. **Export**: Either manually or via automation (batch export feature)

### Key Concepts
- **ScriptFile**: Main class representing a CapCut draft
- **Materials**: Video, audio, image files referenced in the draft
- **Segments**: Clips placed on the timeline (VideoSegment, AudioSegment, TextSegment)
- **Tracks**: Layers in the timeline that hold segments
- **Effects/Filters/Animations**: Visual enhancements attached to segments

## User Experience Goals

### For Developers
- **Simple API**: Intuitive Python interfaces
- **Comprehensive Documentation**: Clear examples for all features
- **Flexible**: Support both simple and complex editing scenarios

### For End Users (of generated videos)
- **Quality**: Generated drafts should produce professional-quality output
- **Reliability**: Drafts should open without errors in CapCut
- **Feature Parity**: Support for CapCut's key editing features

## Integration Points
- **CapCut Application**: Windows version required for draft loading/export
- **JianYing (剪映)**: Chinese sister app, functionally similar
- **File System**: Manages draft folders and material files
