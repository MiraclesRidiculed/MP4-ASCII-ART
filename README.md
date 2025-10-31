# ASCII Video Converter (GUI)

A small Python utility to convert videos into ASCII-art — play in the terminal or save the result as a video. Includes an option to merge the original audio back into the saved ASCII video using FFmpeg.

This repository contains a single-file GUI application `ascii_video.py` that uses OpenCV, Pillow and NumPy.

## Features

- Convert any MP4/MOV/AVI into ASCII frames
- Play output directly in the terminal or save as MP4/AVI
- Merge original audio using FFmpeg (optional)
- Handles portrait (shorts) and landscape videos by fitting and padding frames

## Quick Start (Windows)

Prerequisites
- Python 3.8+ (3.13 tested)
- FFmpeg (optional, required for audio merging)
- Git (optional, for cloning)

1. Create and activate a virtual environment

```powershell
# PowerShell (recommended)
python -m venv ascii-env
.\ascii-env\Scripts\Activate.ps1
# or use activate.bat if using cmd.exe
```

2. Install dependencies

```powershell
pip install -r requirements.txt
```

3. Run the GUI

```powershell
python ascii_video.py
```

4. In the GUI
- Browse for a video file
- Choose an output file (default `ascii_out.mp4`)
- Choose columns, FPS and font size
- Select `Save as MP4` and optionally `Merge Original Audio (FFmpeg)`
- Click ▶ Start

If FFmpeg is not installed or not on PATH the audio merge will not be performed and you'll be shown a diagnostic message.

## Headless / CLI usage

You can import the core functions from `ascii_video.py` and run them headless. Example (replace paths):

```powershell
python - <<'PY'
from ascii_video import convert_video
convert_video(r"C:\path\to\input.mp4", r"C:\path\to\output.mp4", cols=120, fps=0, font_size=12, save_mode=True, merge_audio_opt=False)
PY
```

Note: The simple CLI usage above runs the same conversion logic without the GUI; it may still pop dialogs via `tkinter.messagebox` on errors.

## FFmpeg (audio merge)

On Windows, download a static build from https://ffmpeg.org/download.html or https://www.gyan.dev/ffmpeg/builds/ and add the `ffmpeg.exe` folder to your PATH. After adding it to PATH, restart the terminal and run:

```powershell
ffmpeg -version
```

The GUI will show FFmpeg stderr output if merging fails so you can diagnose issues (missing audio stream, wrong mapping, etc.).

## Troubleshooting

- "Failed to write frame" warnings from OpenCV/FFmpeg
  - Ensure the output writer opens successfully. The code falls back to an AVI+MJPG writer if MP4 (mp4v) fails.
  - Try a different `Output File` extension (e.g., `.avi`) in the GUI.

- Audio didn't merge
  - Verify FFmpeg is installed and on PATH.
  - Check the ffmpeg diagnostic message shown in the GUI; it usually indicates the reason.

- Font rendering looks wrong
  - The code tries common monospace fonts (`Consola`, `Lucon`, `DejaVuSansMono`). If you want a specific font, edit `candidates` in `ascii_video.py` or pass a path to a TTF.

## Files

- `ascii_video.py` — main application (GUI + conversion logic)
- `requirements.txt` — Python dependencies
- `.gitignore` — recommended ignores for git

## Attribution

If you publish this repository on GitHub, update the README author line or commit as yourself to reflect authorship.

## Next steps / Improvements

- Add a proper CLI entrypoint and disable tkinter dialogs for headless runs
- Allow selecting codec/quality in the GUI
- Add a progress bar and cancel button
- Produce smaller H.264 output using ffmpeg as the final encoder (write raw frames to ffmpeg stdin)

---

Happy ASCII-ing! 
