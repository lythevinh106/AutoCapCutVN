# Active Context: pyCapCut

## Current Work Focus

### Status
Memory Bank initialized. Project ready for development work.

### Recent Changes
- Memory Bank structure created with core documentation files
- Project analyzed and documented

## Next Steps
- Review project requirements for specific development tasks
- Identify areas for enhancement or bug fixes
- Consider adding new features based on user needs

## Active Decisions

### Pending
- No active decisions pending at this time

### Made
- Memory Bank structure follows standard format with all 6 core files

## Important Notes

### Project State
- Version 0.0.3 (Beta)
- Recently migrated from PyJianYingDraft
- Active development with Discord community

### Key Entry Points
- `demo.py` - Example usage and testing
- `pycapcut/__init__.py` - Public API exports
- `pycapcut/script_file.py` - Main ScriptFile class

### Common Tasks
1. **Create a draft**: Use `DraftFolder` to create/manage drafts
2. **Add media**: Create `VideoSegment`/`AudioSegment` with materials
3. **Add text**: Create `TextSegment` with styling
4. **Add effects**: Use `add_effect()`, `add_filter()`, `add_animation()`
5. **Save draft**: Call `script.save()` to write to draft folder

## Current Considerations

### Template Mode
- Just completed migration
- May have compatibility issues - report via GitHub issues

### Effects/Animations
- Verify effect availability in CapCut before using
- Some effects from enum may not be available in all versions
