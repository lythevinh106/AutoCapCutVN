"""
Test Librosa Audio Analysis Service
====================================
Comprehensive test script for all audio analysis functions.

Test files:
1. Vũ Điệu Ánh Sáng (Vietnamese EDM)
2. 운명의 서곡 - File 1 (Korean Orchestral)
3. 운명의 서곡 - File 2 (Korean Orchestral) 
4. Đêm Remix (Vietnamese Remix)

Run:
    python test_librosa_service.py
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audio_analysis_service import (
    AudioAnalysisService,
    BeatInfo,
    OnsetInfo,
    EnergyInfo,
    SpectralInfo,
    HPSSInfo,
    FullAnalysisResult
)

# ============================================================
# TEST AUDIO FILES
# ============================================================

TEST_AUDIO_FILES = [
    r"F:\Automation Folder\SunoMusic\Vũ Điệu Ánh Sáng\Vũ Điệu Ánh Sáng-20251102_181338 (1).mp3",
    r"F:\Automation Folder\SunoMusic\운명의 서곡\운명의 서곡-20251029_165045 (1).mp3",
    r"F:\Automation Folder\SunoMusic\운명의 서곡\운명의 서곡-20251030_151039 (1).mp3",
    r"F:\Automation Folder\SunoMusic\Đêm Remix\Đêm Remix-20251102_181712 (2).mp3",
]


def print_separator(title: str):
    """Print a formatted separator"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_subsection(title: str):
    """Print a subsection header"""
    print(f"\n--- {title} ---")


def test_load_audio(service: AudioAnalysisService, file_path: str):
    """Test 1: Loading & Pre-processing"""
    print_subsection("1. LOADING & PRE-PROCESSING")
    
    # Test load_audio
    print("\n📂 load_audio()")
    y, sr = service.load_audio(file_path, mono=True)
    print(f"   ✓ Audio loaded successfully")
    print(f"   ✓ Sample rate: {sr} Hz")
    print(f"   ✓ Audio length: {len(y)} samples")
    print(f"   ✓ Data type: {y.dtype}")
    
    # Test get_duration_ms
    print("\n⏱️  get_duration_ms()")
    duration_ms = service.get_duration_ms(y, sr)
    duration_sec = duration_ms / 1000
    print(f"   ✓ Duration: {duration_ms:.2f} ms ({duration_sec:.2f} seconds)")
    
    # Test to_mono (already mono but test the function)
    print("\n🔊 to_mono()")
    y_mono = service.to_mono(y)
    print(f"   ✓ Mono conversion: {y_mono.shape}")
    
    # Test resample_audio
    print("\n🔄 resample_audio()")
    y_resampled = service.resample_audio(y, sr, 16000)
    print(f"   ✓ Resampled from {sr}Hz to 16000Hz")
    print(f"   ✓ New length: {len(y_resampled)} samples")
    
    return y, sr, duration_ms


def test_rhythm_tempo(service: AudioAnalysisService, y, sr):
    """Test 2: Rhythm & Tempo Detection"""
    print_subsection("2. RHYTHM & TEMPO")
    
    # Test detect_beats
    print("\n🥁 detect_beats()")
    beat_info = service.detect_beats(y, sr)
    print(f"   ✓ Tempo: {beat_info.tempo_bpm} BPM")
    print(f"   ✓ Total beats: {beat_info.beat_count}")
    print(f"   ✓ Average beat interval: {beat_info.average_beat_interval_ms:.2f} ms")
    print(f"   ✓ First 10 beat times (ms): {beat_info.beat_times_ms[:10]}")
    
    # Test detect_pulse
    print("\n💓 detect_pulse()")
    pulse_times = service.detect_pulse(y, sr)
    print(f"   ✓ Pulse points found: {len(pulse_times)}")
    print(f"   ✓ First 10 pulse times (ms): {pulse_times[:10]}")
    
    # Test frames_to_ms
    print("\n🔢 frames_to_ms()")
    import numpy as np
    test_frames = np.array([0, 100, 200, 300, 400, 500])
    times_ms = service.frames_to_ms(test_frames, sr)
    print(f"   ✓ Frames {test_frames.tolist()} -> {times_ms} ms")
    
    return beat_info


def test_onset_events(service: AudioAnalysisService, y, sr):
    """Test 3: Onset & Events Detection"""
    print_subsection("3. ONSET & EVENTS")
    
    # Test detect_onsets
    print("\n⚡ detect_onsets()")
    onset_info = service.detect_onsets(y, sr, strong_threshold=0.7, weak_threshold=0.3)
    print(f"   ✓ Total onsets: {onset_info.onset_count}")
    print(f"   ✓ Strong onsets (>0.7): {len(onset_info.strong_onsets_ms)}")
    print(f"   ✓ Weak onsets (<0.3): {len(onset_info.weak_onsets_ms)}")
    print(f"   ✓ First 10 onset times (ms): {onset_info.onset_times_ms[:10]}")
    print(f"   ✓ First 10 onset strengths: {onset_info.onset_strengths[:10]}")
    
    # Test get_onset_strength_curve
    print("\n📈 get_onset_strength_curve()")
    times_ms, strengths = service.get_onset_strength_curve(y, sr)
    print(f"   ✓ Curve points: {len(times_ms)}")
    print(f"   ✓ Time range: {times_ms[0]:.2f} - {times_ms[-1]:.2f} ms")
    print(f"   ✓ Strength range: {min(strengths):.3f} - {max(strengths):.3f}")
    
    return onset_info


def test_spectral_energy(service: AudioAnalysisService, y, sr):
    """Test 4: Spectral & Energy Analysis"""
    print_subsection("4. SPECTRAL & ENERGY")
    
    # Test analyze_energy
    print("\n📊 analyze_energy()")
    energy_info = service.analyze_energy(y, sr, drop_threshold=0.8, break_threshold=0.2)
    print(f"   ✓ Average RMS: {energy_info.average_rms:.4f}")
    print(f"   ✓ Peak RMS: {energy_info.peak_rms:.4f}")
    print(f"   ✓ Drop times (high energy): {len(energy_info.drop_times_ms)} points")
    print(f"   ✓ Break times (low energy): {len(energy_info.break_times_ms)} points")
    print(f"   ✓ First 5 drops (ms): {energy_info.drop_times_ms[:5]}")
    print(f"   ✓ First 5 breaks (ms): {energy_info.break_times_ms[:5]}")
    
    # Test analyze_mood
    print("\n🎨 analyze_mood()")
    spectral_info = service.analyze_mood(y, sr)
    print(f"   ✓ Spectral Centroid: {spectral_info.spectral_centroid_avg:.2f} Hz")
    print(f"   ✓ Spectral Bandwidth: {spectral_info.spectral_bandwidth_avg:.2f} Hz")
    print(f"   ✓ Mood: {spectral_info.mood}")
    print(f"   ✓ Suggested filters: {spectral_info.suggested_filter_style}")
    
    return energy_info, spectral_info


def test_hpss_decomposition(service: AudioAnalysisService, y, sr):
    """Test 5: HPSS Decomposition"""
    print_subsection("5. HPSS DECOMPOSITION (Harmonic-Percussive Separation)")
    
    print("\n🎸 separate_harmonic_percussive()")
    print("   ⏳ Processing... (this may take a moment)")
    
    hpss_info = service.separate_harmonic_percussive(y, sr)
    
    print(f"   ✓ Percussive tempo: {hpss_info.percussive_tempo_bpm} BPM")
    print(f"   ✓ Percussive beats: {len(hpss_info.percussive_beat_times_ms)}")
    print(f"   ✓ Harmonic events: {len(hpss_info.harmonic_beat_times_ms)}")
    print(f"   ✓ First 10 percussive beats (ms): {hpss_info.percussive_beat_times_ms[:10]}")
    print(f"   ✓ First 10 harmonic events (ms): {hpss_info.harmonic_beat_times_ms[:10]}")
    
    return hpss_info


def test_full_analysis(service: AudioAnalysisService, file_path: str):
    """Test Full Analysis (All-in-one)"""
    print_subsection("6. FULL ANALYSIS (All-in-one)")
    
    print("\n🚀 analyze_full()")
    print("   ⏳ Running complete analysis...")
    
    result = service.analyze_full(file_path, include_hpss=True)
    
    print(f"   ✓ Duration: {result.duration_ms:.2f} ms")
    print(f"   ✓ Sample rate: {result.sample_rate} Hz")
    print(f"   ✓ Beat count: {result.beat_info.beat_count}")
    print(f"   ✓ Tempo: {result.beat_info.tempo_bpm} BPM")
    print(f"   ✓ Onset count: {result.onset_info.onset_count}")
    print(f"   ✓ Mood: {result.spectral_info.mood}")
    
    if result.hpss_info:
        print(f"   ✓ HPSS percussive tempo: {result.hpss_info.percussive_tempo_bpm} BPM")
    
    return result


def test_keyframe_generation(service: AudioAnalysisService, beat_info: BeatInfo, onset_info: OnsetInfo):
    """Test Keyframe Generation Helpers"""
    print_subsection("7. KEYFRAME GENERATION HELPERS")
    
    # Test generate_zoom_keyframes_from_beats
    print("\n🎬 generate_zoom_keyframes_from_beats()")
    beat_keyframes = service.generate_zoom_keyframes_from_beats(
        beat_info.beat_times_ms[:20],  # First 20 beats
        base_scale=1.0,
        zoom_scale=1.15,
        property_name="scale_x"
    )
    print(f"   ✓ Generated {len(beat_keyframes)} keyframes from {min(20, beat_info.beat_count)} beats")
    print(f"   ✓ First 5 keyframes:")
    for kf in beat_keyframes[:5]:
        print(f"      {kf}")
    
    # Test generate_zoom_keyframes_from_onsets
    print("\n🎬 generate_zoom_keyframes_from_onsets()")
    onset_keyframes = service.generate_zoom_keyframes_from_onsets(
        onset_info,
        min_scale=1.0,
        max_scale=1.3
    )
    print(f"   ✓ Generated {len(onset_keyframes)} keyframes from {onset_info.onset_count} onsets")
    print(f"   ✓ First 6 keyframes:")
    for kf in onset_keyframes[:6]:
        print(f"      {kf}")
    
    return beat_keyframes, onset_keyframes


def test_json_serialization(result: FullAnalysisResult, output_path: str):
    """Test JSON Serialization"""
    print_subsection("8. JSON SERIALIZATION")
    
    # Test to_dict
    print("\n📦 to_dict()")
    result_dict = result.to_dict()
    print(f"   ✓ Keys: {list(result_dict.keys())}")
    
    # Test to_json
    print("\n📄 to_json()")
    result_json = result.to_json(indent=2)
    print(f"   ✓ JSON length: {len(result_json)} characters")
    
    # Save to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result_json)
    print(f"   ✓ Saved to: {output_path}")
    
    return result_json


def run_all_tests(file_path: str, output_dir: str = None):
    """Run all tests on a single audio file"""
    
    file_name = Path(file_path).stem
    print_separator(f"TESTING: {file_name}")
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"❌ ERROR: File not found: {file_path}")
        return None
    
    print(f"📁 File: {file_path}")
    print(f"📊 File size: {os.path.getsize(file_path) / 1024 / 1024:.2f} MB")
    
    # Initialize service
    service = AudioAnalysisService(sample_rate=22050, hop_length=512)
    print(f"⚙️  Service initialized (sr=22050, hop=512)")
    
    try:
        # Run all tests
        y, sr, duration_ms = test_load_audio(service, file_path)
        beat_info = test_rhythm_tempo(service, y, sr)
        onset_info = test_onset_events(service, y, sr)
        energy_info, spectral_info = test_spectral_energy(service, y, sr)
        hpss_info = test_hpss_decomposition(service, y, sr)
        result = test_full_analysis(service, file_path)
        beat_kf, onset_kf = test_keyframe_generation(service, beat_info, onset_info)
        
        # Save JSON output
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{file_name}_analysis.json")
        else:
            output_path = file_path.rsplit('.', 1)[0] + "_analysis.json"
        
        test_json_serialization(result, output_path)
        
        print_subsection("✅ ALL TESTS PASSED")
        
        return result
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_comparison_test():
    """Compare analysis results across all test files"""
    print_separator("COMPARISON ACROSS ALL FILES")
    
    results = []
    
    for file_path in TEST_AUDIO_FILES:
        if not os.path.exists(file_path):
            print(f"⚠️  Skipping (not found): {file_path}")
            continue
        
        file_name = Path(file_path).stem
        print(f"\n🎵 Analyzing: {file_name[:30]}...")
        
        try:
            service = AudioAnalysisService(sample_rate=22050)
            result = service.analyze_full(file_path, include_hpss=True)
            
            results.append({
                "name": file_name[:30],
                "duration_s": result.duration_ms / 1000,
                "tempo": result.beat_info.tempo_bpm,
                "beats": result.beat_info.beat_count,
                "onsets": result.onset_info.onset_count,
                "strong_onsets": len(result.onset_info.strong_onsets_ms),
                "mood": result.spectral_info.mood,
                "avg_rms": result.energy_info.average_rms,
                "percussive_tempo": result.hpss_info.percussive_tempo_bpm if result.hpss_info else 0
            })
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Print comparison table
    if results:
        print("\n" + "=" * 100)
        print("COMPARISON TABLE")
        print("=" * 100)
        
        # Header
        print(f"{'Name':<32} {'Duration':<10} {'Tempo':<8} {'Beats':<7} {'Onsets':<8} {'Strong':<8} {'Mood':<10} {'RMS':<8}")
        print("-" * 100)
        
        for r in results:
            print(f"{r['name']:<32} {r['duration_s']:.1f}s{'':<5} {r['tempo']:<8.1f} {r['beats']:<7} {r['onsets']:<8} {r['strong_onsets']:<8} {r['mood']:<10} {r['avg_rms']:.4f}")
        
        print("-" * 100)
    
    return results


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("  🎵 LIBROSA AUDIO ANALYSIS SERVICE - COMPREHENSIVE TEST")
    print("=" * 70)
    
    # Output directory for JSON results
    OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "test_output")
    
    # Check which test files exist
    print("\n📋 Checking test files...")
    available_files = []
    for f in TEST_AUDIO_FILES:
        exists = os.path.exists(f)
        status = "✓" if exists else "✗"
        print(f"   {status} {Path(f).name}")
        if exists:
            available_files.append(f)
    
    if not available_files:
        print("\n❌ No test files found! Please update TEST_AUDIO_FILES paths.")
        sys.exit(1)
    
    print(f"\n📊 Found {len(available_files)} test files")
    
    # Run mode selection
    print("\n" + "-" * 70)
    print("Select test mode:")
    print("  1. Test first available file (detailed)")
    print("  2. Test all files (detailed)")
    print("  3. Comparison test (summary)")
    print("  4. Quick test (first file, no HPSS)")
    print("-" * 70)
    
    try:
        choice = input("Enter choice (1-4) [default=1]: ").strip() or "1"
    except:
        choice = "1"
    
    if choice == "1":
        # Test first file in detail
        run_all_tests(available_files[0], OUTPUT_DIR)
        
    elif choice == "2":
        # Test all files
        for file_path in available_files:
            run_all_tests(file_path, OUTPUT_DIR)
        
    elif choice == "3":
        # Comparison test
        run_comparison_test()
        
    elif choice == "4":
        # Quick test without HPSS
        file_path = available_files[0]
        print_separator(f"QUICK TEST: {Path(file_path).name}")
        
        service = AudioAnalysisService(sample_rate=22050)
        y, sr = service.load_audio(file_path)
        
        print(f"\n⏱️  Duration: {service.get_duration_ms(y, sr) / 1000:.2f} seconds")
        
        beat_info = service.detect_beats(y, sr)
        print(f"🥁 Tempo: {beat_info.tempo_bpm} BPM, {beat_info.beat_count} beats")
        
        onset_info = service.detect_onsets(y, sr)
        print(f"⚡ Onsets: {onset_info.onset_count} (strong: {len(onset_info.strong_onsets_ms)})")
        
        spectral_info = service.analyze_mood(y, sr)
        print(f"🎨 Mood: {spectral_info.mood}")
        print(f"   Suggested: {spectral_info.suggested_filter_style}")
        
        print("\n✅ Quick test completed!")
    
    else:
        print("Invalid choice. Running default test...")
        run_all_tests(available_files[0], OUTPUT_DIR)
    
    print("\n" + "=" * 70)
    print("  🎉 TEST COMPLETED")
    print("=" * 70)
