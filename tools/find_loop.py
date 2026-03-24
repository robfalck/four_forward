"""
find_loop.py — Extract a seamlessly looping ambient clip from a longer audio file.

Algorithm:
  1. Load audio, convert to mono.
  2. Find the "steadiest" region (lowest RMS variance over time).
  3. Within that region, use cross-correlation to find the loop endpoint
     where the end of the segment best matches the beginning.
  4. Apply a short crossfade at the loop boundary to remove any click.
  5. Write the result as a .ogg file ready for pygame.

Usage:
    pixi run --environment dev python tools/find_loop.py <input.ogg> [output.ogg] [start_sec] [end_sec]

    start_sec / end_sec — restrict the search to this time window (default: 0 to SEARCH_SEC)

Options (edit the constants below):
    MIN_LOOP_SEC   — minimum loop duration to consider (seconds)
    MAX_LOOP_SEC   — maximum loop duration to consider (seconds)
    CROSSFADE_MS   — crossfade length at loop boundary (milliseconds)
    SEARCH_SEC     — how many seconds of clip to scan for the steadiest region
"""

import sys
from pathlib import Path

import numpy as np
import soundfile as sf

# --- Tunable parameters ---
MIN_LOOP_SEC = 4.0
MAX_LOOP_SEC = 12.0
CROSSFADE_MS = 80
SEARCH_SEC = 60.0  # only scan the first N seconds of the file
FRAME_SEC = 0.05   # RMS analysis frame size


def rms(signal: np.ndarray) -> float:
    return float(np.sqrt(np.mean(signal**2)))


def find_steady_region(mono: np.ndarray, sr: int) -> tuple[int, int]:
    """Return (start_sample, end_sample) of the steadiest MIN_LOOP_SEC window."""
    frame = int(FRAME_SEC * sr)
    n_frames = int(len(mono) / frame)
    rms_frames = np.array([rms(mono[i * frame:(i + 1) * frame]) for i in range(n_frames)])

    # Sliding window of MIN_LOOP_SEC: find where variance is lowest
    window_frames = int(MIN_LOOP_SEC / FRAME_SEC)
    best_var = np.inf
    best_start = 0
    for i in range(n_frames - window_frames):
        var = float(np.var(rms_frames[i:i + window_frames]))
        if var < best_var:
            best_var = var
            best_start = i

    start = best_start * frame
    # Extend the search region up to MAX_LOOP_SEC or SEARCH_SEC boundary
    search_end = min(len(mono), int(SEARCH_SEC * sr))
    end = min(search_end, start + int(MAX_LOOP_SEC * sr))
    return start, end


def find_loop_point(mono: np.ndarray, start: int, end: int, sr: int) -> tuple[int, int]:
    """
    Given a candidate region [start, end], find the best (loop_start, loop_end)
    pair such that the waveform at loop_end matches the waveform at loop_start.
    Uses normalized cross-correlation on short windows at the boundary.
    """
    window = int(0.05 * sr)  # 50 ms comparison window
    min_len = int(MIN_LOOP_SEC * sr)
    max_len = end - start

    region = mono[start:end]
    ref = region[:window].astype(np.float64)
    ref -= ref.mean()
    ref_norm = np.linalg.norm(ref)

    best_score = -1.0
    best_offset = min_len  # offset from start = loop length

    for offset in range(min_len, max_len - window, int(0.01 * sr)):
        candidate = region[offset:offset + window].astype(np.float64)
        candidate -= candidate.mean()
        c_norm = np.linalg.norm(candidate)
        if ref_norm < 1e-10 or c_norm < 1e-10:
            continue
        score = float(np.dot(ref, candidate) / (ref_norm * c_norm))
        if score > best_score:
            best_score = score
            best_offset = offset

    print(f"  Best loop length: {best_offset / sr:.2f}s  (correlation score: {best_score:.4f})")
    return start, start + best_offset


def apply_crossfade(mono: np.ndarray, loop_start: int, loop_end: int, sr: int) -> np.ndarray:
    """Overlap-add crossfade at the loop boundary."""
    fade_samples = int(CROSSFADE_MS / 1000 * sr)
    loop = mono[loop_start:loop_end].copy()

    if fade_samples * 2 >= len(loop):
        return loop

    fade_out = np.linspace(1.0, 0.0, fade_samples)
    fade_in = np.linspace(0.0, 1.0, fade_samples)

    # Blend the end of the loop over the beginning
    tail = loop[-fade_samples:] * fade_out
    head = loop[:fade_samples] * fade_in
    blended = head + tail

    result = loop.copy()
    result[:fade_samples] = blended
    result = result[:-fade_samples]  # trim the tail we blended away
    return result


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    # Second arg is output path only if it doesn't look like a number
    arg2 = sys.argv[2] if len(sys.argv) > 2 else None
    if arg2 and not arg2.replace(".", "").isdigit():
        output_path = Path(arg2)
        time_args = sys.argv[3:]
    else:
        output_path = input_path.with_stem(input_path.stem + "_loop")
        time_args = sys.argv[2:]

    output_path = output_path.with_suffix(".ogg")
    search_start_sec = float(time_args[0]) if len(time_args) > 0 else 0.0
    search_end_sec = float(time_args[1]) if len(time_args) > 1 else None

    print(f"Loading: {input_path}")
    audio, sr = sf.read(str(input_path), always_2d=True)
    print(f"  {len(audio) / sr:.1f}s  {sr} Hz  {audio.shape[1]} ch")

    mono = audio.mean(axis=1)
    scan_start = int(search_start_sec * sr)
    if search_end_sec is not None:
        scan_end = min(len(mono), int(search_end_sec * sr))
    else:
        scan_end = min(len(mono), scan_start + int(SEARCH_SEC * sr))
    mono_scan = mono[scan_start:scan_end]
    print(f"  Searching {search_start_sec:.1f}s – {scan_end / sr:.1f}s")

    print("Finding steadiest region...")
    rel_start, rel_end = find_steady_region(mono_scan, sr)
    start = scan_start + rel_start
    end = scan_start + rel_end
    print(f"  Region: {start / sr:.2f}s – {end / sr:.2f}s")

    print("Finding best loop point...")
    loop_start, loop_end = find_loop_point(mono, start, end, sr)

    print("Applying crossfade...")
    loop_mono = apply_crossfade(mono, loop_start, loop_end, sr)

    # Normalize to avoid clipping
    peak = np.max(np.abs(loop_mono))
    if peak > 0:
        loop_mono = loop_mono / peak * 0.9

    # Write stereo OGG (duplicate mono to both channels)
    loop_stereo = np.stack([loop_mono, loop_mono], axis=1)
    sf.write(str(output_path), loop_stereo, sr, format="OGG", subtype="VORBIS")
    print(f"Saved: {output_path}  ({len(loop_mono) / sr:.2f}s)")
    print("Done. Test with: pygame.mixer.music.play(loops=-1)")


if __name__ == "__main__":
    main()
