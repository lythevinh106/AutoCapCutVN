# Project Brief: pyCapCut

## Overview
pyCapCut is a lightweight, flexible, and easy-to-use Python tool for generating and exporting CapCut drafts. It enables building fully automated video editing/remix pipelines.

## Origins
Migrated from [PyJianYingDraft](https://github.com/GuanYixuan/pyJianYingDraft) - the sister project for JianYing (Chinese version of CapCut).

## Core Requirements

### Primary Goal
Enable programmatic generation of CapCut draft files that can be opened and further edited in CapCut, or exported directly.

### Key Features
1. **Template Mode** - Load existing drafts as templates, replace materials/text, import tracks
2. **Batch Export** - Control CapCut to open and export drafts at specified resolutions/framerates
3. **Video/Image** - Add local media, customize timing/speed, add animations/effects/filters/masks
4. **Stickers** - Add stickers with resource IDs, support keyframes
5. **Audio** - Add audio with fade effects, volume control, scene audio effects
6. **Tracks** - Multi-track support with layer ordering
7. **Effects/Filters/Transitions** - Segment-attached and independent track effects
8. **Text/Subtitles** - Text with fonts/styles, animations, SRT import

## Target Users
- Developers building automated video editing pipelines
- Content creators needing batch video processing
- Anyone wanting programmatic control over CapCut drafts

## Technical Constraints
- Generated drafts require Windows CapCut for export
- Linux/MacOS can generate drafts but need Windows for final export
- Python >= 3.8 required

## Success Metrics
- Drafts open correctly in CapCut without errors
- All features (effects, animations, text styling) render as expected
- Stable API for programmatic video editing workflows
