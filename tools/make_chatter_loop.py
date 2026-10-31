"""
make_chatter_loop.py — Build a looping background-chatter clip from a long radio recording.

Unlike find_loop.py (which picks the *steadiest* stretch, i.e. static), this picks the
stretch with the most continuous voice activity, so the ambience sounds like crew chatter.

Algorithm:
  1. Load audio, convert to mono.
  2. Mark 50 ms frames as "speech" when well above the noise floor.
  3. Choose the LOOP_SEC window with the most speech and the shortest silent gap.
  4. Nudge both ends to the nearest quiet frame so no word is cut.
  5. Even out loudness with a gentle compressor, normalise to TARGET_DBFS RMS.
  6. Equal-power crossfade the tail into the head for a seamless loop.
  7. Write a mono 22.05 kHz .ogg for pygame.

Usage:
    pixi run --environment dev python tools/make_chatter_loop.py <input> [output.ogg]
"""

import sys
from pathlib import Path

import numpy as np
import soundfile as sf

# --- Tunable parameters ---
LOOP_SEC = 45.0       # loop length; long enough that repetition isn't obvious
CROSSFADE_SEC = 1.5   # overlap at the loop seam
FRAME_SEC = 0.05      # analysis frame size
SPEECH_FACTOR = 3.0   # frame is "speech" when RMS > SPEECH_FACTOR × noise floor
SNAP_SEC = 2.0        # how far an endpoint may move to find a quiet frame
TARGET_DBFS = -26.0   # output RMS level (the game's volume setting scales this further)
OUT_RATE = 22_050


def frame_rms(mono: np.ndarray, frame: int) -> np.ndarray:
    n = len(mono) // frame
    return np.sqrt((mono[: n * frame].reshape(n, frame) ** 2).mean(axis=1)) + 1e-9


def longest_run(mask: np.ndarray) -> int:
    best = run = 0
    for v in mask:
        run = run + 1 if v else 0
        best = max(best, run)
    return best


def pick_window(energy: np.ndarray, sr_frames: float) -> tuple[int, int]:
    """Return (start_frame, end_frame) of the chattiest window."""
    speech = energy > np.percentile(energy, 20) * SPEECH_FACTOR
    win = int((LOOP_SEC + CROSSFADE_SEC) * sr_frames)
    best, best_score = 0, -np.inf
    for s in range(0, len(energy) - win, int(sr_frames)):  # 1 s steps
        chunk = speech[s : s + win]
        gap_sec = longest_run(~chunk) / sr_frames
        score = chunk.mean() - 0.02 * gap_sec  # favour steady chatter over bursts
        if score > best_score:
            best, best_score = s, score
    return best, best + win


def snap_to_quiet(energy: np.ndarray, idx: int, sr_frames: float) -> int:
    r = int(SNAP_SEC * sr_frames)
    lo, hi = max(0, idx - r), min(len(energy), idx + r)
    return lo + int(np.argmin(energy[lo:hi]))


def compress(x: np.ndarray, sr: int, threshold_db: float = -20.0, ratio: float = 3.0) -> np.ndarray:
    """Simple RMS-envelope compressor to tame sudden loud transmissions."""
    win = int(0.05 * sr)
    env = np.sqrt(np.convolve(x**2, np.ones(win) / win, mode="same")) + 1e-9
    env_db = 20 * np.log10(env)
    over = np.maximum(0.0, env_db - threshold_db)
    gain_db = -over * (1 - 1 / ratio)
    return x * 10 ** (gain_db / 20)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("chatter_loop.ogg")

    audio, sr = sf.read(src, always_2d=True)
    mono = audio.mean(axis=1)
    frame = int(FRAME_SEC * sr)
    energy = frame_rms(mono, frame)
    fps = 1.0 / FRAME_SEC

    s, e = pick_window(energy, fps)
    s = snap_to_quiet(energy, s, fps)
    e = snap_to_quiet(energy, e, fps)
    seg = mono[s * frame : e * frame].copy()
    print(f"Selected {s * FRAME_SEC:.1f}s – {e * FRAME_SEC:.1f}s ({len(seg) / sr:.1f}s)")

    # Resample to OUT_RATE (linear interpolation is fine for band-limited radio voice)
    t_out = np.arange(int(len(seg) * OUT_RATE / sr)) / OUT_RATE
    seg = np.interp(t_out, np.arange(len(seg)) / sr, seg)
    sr = OUT_RATE

    seg = seg - seg.mean()
    seg = compress(seg, sr)
    seg *= 10 ** (TARGET_DBFS / 20) / np.sqrt(np.mean(seg**2))

    # Seamless loop: fold the last CROSSFADE_SEC over the first, equal-power
    n = int(CROSSFADE_SEC * sr)
    body, tail = seg[:-n], seg[-n:]
    t = np.linspace(0, np.pi / 2, n)
    body[:n] = body[:n] * np.sin(t) + tail * np.cos(t)

    peak = np.max(np.abs(body))
    if peak > 0.98:
        body *= 0.98 / peak
    # Write in blocks: one large Vorbis write overflows libsndfile's stack on Windows
    with sf.SoundFile(dst, "w", sr, 1, format="OGG", subtype="VORBIS") as f:
        for i in range(0, len(body), 8192):
            f.write(body[i : i + 8192].astype(np.float32))
    rms_db = 20 * np.log10(np.sqrt(np.mean(body**2)))
    print(f"Wrote {dst}  {len(body) / sr:.1f}s  RMS {rms_db:.1f} dBFS")


if __name__ == "__main__":
    main()
