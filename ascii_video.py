#!/usr/bin/env python3
"""
ASCII Video Converter - GUI Edition
-----------------------------------
Convert any MP4 video into ASCII art (terminal or saved video)
"""

import cv2
import numpy as np
from PIL import Image, ImageFont, ImageDraw
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import shutil
import os
import sys
import time
import threading

# --- ASCII set (dark → light) ---
ASCII_CHARS = ".:-=+*#%@/\\|"

def get_char_for_gray(val, chars=ASCII_CHARS):
    idx = int((val / 255) * (len(chars) - 1))
    return chars[idx]

def frame_to_ascii_lines(frame_gray, cols=120, scale=0.43, chars=ASCII_CHARS):
    h, w = frame_gray.shape
    new_w = cols
    tile_w = w / new_w
    tile_h = tile_w / scale
    new_h = max(1, int(h / tile_h))
    small = cv2.resize(frame_gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return ["".join(get_char_for_gray(small[r, c], chars) for c in range(new_w)) for r in range(new_h)]

def render_ascii_to_image(lines, font, bg=(0, 0, 0), fg=(255, 255, 255), padding=6):
    """Render ASCII lines to a Pillow image for saving as video frames.

    This function computes a fixed image size based on the font metrics and the
    number of columns/rows in `lines`. It ensures the output dimensions are even
    (many video encoders require this) and that every frame will have the same
    size so the OpenCV VideoWriter won't fail when writing frames.
    """
    # Create a temporary draw to measure text metrics
    tmp = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(tmp)

    # Determine character width/height using a typical character
    # Use 'M' since it's usually among the widest glyphs for monospace
    bbox = draw.textbbox((0, 0), "M", font=font)
    char_w = bbox[2] - bbox[0]
    char_h = bbox[3] - bbox[1]
    if char_w <= 0:
        char_w = 8
    if char_h <= 0:
        char_h = 16

    # Number of columns is length of the longest line (should be constant)
    max_cols = max((len(line) for line in lines), default=1)
    rows = max(1, len(lines))

    img_w = char_w * max_cols + padding * 2
    img_h = char_h * rows + padding * 2

    # Make dimensions even (required by most encoders)
    if img_w % 2 != 0:
        img_w += 1
    if img_h % 2 != 0:
        img_h += 1

    img = Image.new("RGB", (img_w, img_h), color=bg)
    draw = ImageDraw.Draw(img)

    y = padding
    for line in lines:
        draw.text((padding, y), line, font=font, fill=fg)
        y += char_h

    return img


def merge_audio(video_path, audio_src, output_path):
    """Merge the audio from audio_src into video_path and write to output_path.

    Returns (success: bool, message: str). The message contains ffmpeg stderr
    when available to help debugging.
    """
    ffmpeg_exe = shutil.which("ffmpeg")
    if ffmpeg_exe is None:
        msg = "FFmpeg not found in PATH. Install FFmpeg to enable audio merging."
        print("⚠️", msg)
        return False, msg

    cmd = [
        ffmpeg_exe, "-y",
        "-i", video_path,
        "-i", audio_src,
        "-c:v", "copy",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest", output_path
    ]
    try:
        proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True, proc.stderr
    except subprocess.CalledProcessError as e:
        # Return stderr for diagnostics
        return False, (e.stderr or str(e))

def convert_video(input_path, output_path, cols, fps, font_size, save_mode, merge_audio_opt):
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        messagebox.showerror("Error", f"Cannot open {input_path}")
        return

    in_fps = cap.get(cv2.CAP_PROP_FPS)
    fps = fps if fps > 0 else (in_fps if in_fps > 0 else 24.0)
    frame_delay = 1.0 / fps
    last_time = time.time()

    # Font setup
    font_path = None
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "C:\\Windows\\Fonts\\consola.ttf",
        "C:\\Windows\\Fonts\\lucon.ttf"
    ]
    for p in candidates:
        if os.path.exists(p):
            font_path = p
            break
    font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()

    # For saving
    writer = None
    if save_mode:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            lines = frame_to_ascii_lines(gray, cols=cols)

            if not save_mode:
                os.system('cls' if os.name == 'nt' else 'clear')
                print("\n".join(lines))
                elapsed = time.time() - last_time
                sleep_for = frame_delay - elapsed
                if sleep_for > 0:
                    time.sleep(sleep_for)
                last_time = time.time()
            else:
                img = render_ascii_to_image(lines, font)
                img_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                img_h, img_w = img_bgr.shape[:2]

                # Initialize writer on first frame using its (width,height)
                if writer is None:
                    out_w, out_h = img_w, img_h
                    writer = cv2.VideoWriter(output_path, fourcc, fps, (out_w, out_h))
                    if not writer.isOpened():
                        # Try alternative codec/container fallback (.avi with MJPG)
                        alt_path = os.path.splitext(output_path)[0] + ".avi"
                        alt_fourcc = cv2.VideoWriter_fourcc(*"MJPG")
                        try:
                            writer.release()
                        except Exception:
                            pass
                        writer = cv2.VideoWriter(alt_path, alt_fourcc, fps, (out_w, out_h))
                        if writer.isOpened():
                            output_path = alt_path
                        else:
                            # If still not opened, show error and abort saving
                            messagebox.showerror("Error", "Failed to open video writer with available codecs.")
                            cap.release()
                            return
                else:
                    # Use previously determined output size
                    out_w = int(writer.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                    out_h = int(writer.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
                    if out_w <= 0 or out_h <= 0:
                        out_w, out_h = img_w, img_h

                # If current frame differs from the writer canvas, scale down (preserve aspect)
                # and center the frame with black padding instead of stretching.
                if (img_w, img_h) != (out_w, out_h):
                    # compute scaling factor (fit within out_w/out_h)
                    scale = min(out_w / img_w, out_h / img_h)
                    if scale <= 0:
                        scale = 1.0
                    new_w = max(1, int(img_w * scale))
                    new_h = max(1, int(img_h * scale))
                    if (new_w, new_h) != (img_w, img_h):
                        frame_resized = cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
                    else:
                        frame_resized = img_bgr

                    canvas = np.zeros((out_h, out_w, 3), dtype=img_bgr.dtype)
                    x = (out_w - new_w) // 2
                    y = (out_h - new_h) // 2
                    canvas[y:y+new_h, x:x+new_w] = frame_resized
                    to_write = canvas
                else:
                    to_write = img_bgr

                try:
                    writer.write(to_write)
                except Exception:
                    print("⚠️ Failed to write a frame to the video writer.")

        if writer:
            writer.release()
        cap.release()

        if save_mode:
            messagebox.showinfo("Done", f"ASCII video saved to:\n{output_path}")
            if merge_audio_opt:
                out_with_audio = os.path.splitext(output_path)[0] + "_with_audio.mp4"
                success, msg = merge_audio(output_path, input_path, out_with_audio)
                if success:
                    messagebox.showinfo("Audio Merge", f"✅ Audio merged:\n{out_with_audio}")
                else:
                    # Show the diagnostic message from ffmpeg when available
                    messagebox.showwarning("Audio Merge", f"⚠️ Failed to merge audio.\n{msg}")

    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        if writer:
            writer.release()
        cap.release()

# --- GUI ---
def start_conversion():
    video = entry_video.get()
    if not os.path.exists(video):
        messagebox.showerror("Error", "Select a valid video file.")
        return
    output = entry_output.get() or "ascii_out.mp4"
    cols = int(entry_cols.get() or 120)
    fps = float(entry_fps.get() or 0)
    font_size = int(entry_font.get() or 12)
    save_mode = var_mode.get() == "save"
    merge_audio_opt = var_audio.get()

    threading.Thread(target=convert_video, args=(video, output, cols, fps, font_size, save_mode, merge_audio_opt), daemon=True).start()

def browse_video():
    path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.mov *.avi")])
    if path:
        entry_video.delete(0, tk.END)
        entry_video.insert(0, path)

def browse_output():
    path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4")])
    if path:
        entry_output.delete(0, tk.END)
        entry_output.insert(0, path)


def _run_headless(args):
    # Helper to run convert_video from CLI without GUI dialogs
    input_path = args.input
    output_path = args.output or "ascii_out.mp4"
    cols = args.cols or 120
    fps = args.fps or 0
    font_size = args.font_size or 12
    save_mode = True
    merge_audio_opt = args.merge_audio
    convert_video(input_path, output_path, cols, fps, font_size, save_mode, merge_audio_opt, show_dialogs=False)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="ASCII Video Converter (GUI + CLI)")
    parser.add_argument("--input", "-i", help="Input video path")
    parser.add_argument("--output", "-o", help="Output video path (default ascii_out.mp4)")
    parser.add_argument("--cols", type=int, default=120, help="Columns (width) for ASCII art")
    parser.add_argument("--fps", type=float, default=0, help="FPS (0 = use source fps)")
    parser.add_argument("--font-size", type=int, default=12, help="Font size used when saving frames as images")
    parser.add_argument("--merge-audio", action="store_true", help="Merge original audio using ffmpeg")
    parser.add_argument("--no-gui", action="store_true", help="Run in headless CLI mode (requires --input)")

    args = parser.parse_args()
    if args.no_gui:
        if not args.input:
            parser.error("--input is required when using --no-gui")
        _run_headless(args)
    else:
        # If input was provided without --no-gui, still launch GUI (user can use fields)
        run_gui()


if __name__ == "__main__":
    main()

def run_gui():
    root = tk.Tk()
    root.title("🎞 ASCII Video Converter")
    root.geometry("480x420")
    root.resizable(False, False)

    tk.Label(root, text="Video File:").pack(anchor="w", padx=10, pady=4)
    frame_video = tk.Frame(root)
    frame_video.pack(fill="x", padx=10)
    global entry_video
    entry_video = tk.Entry(frame_video)
    entry_video.pack(side="left", fill="x", expand=True)
    tk.Button(frame_video, text="Browse", command=browse_video).pack(side="right")

    tk.Label(root, text="Output File:").pack(anchor="w", padx=10, pady=4)
    frame_out = tk.Frame(root)
    frame_out.pack(fill="x", padx=10)
    global entry_output
    entry_output = tk.Entry(frame_out)
    entry_output.pack(side="left", fill="x", expand=True)
    tk.Button(frame_out, text="Browse", command=browse_output).pack(side="right")

    tk.Label(root, text="Columns (Width):").pack(anchor="w", padx=10, pady=2)
    global entry_cols
    entry_cols = tk.Entry(root)
    entry_cols.insert(0, "120")
    entry_cols.pack(fill="x", padx=10)

    tk.Label(root, text="FPS (0 = auto):").pack(anchor="w", padx=10, pady=2)
    global entry_fps
    entry_fps = tk.Entry(root)
    entry_fps.insert(0, "0")
    entry_fps.pack(fill="x", padx=10)

    tk.Label(root, text="Font Size (for save mode):").pack(anchor="w", padx=10, pady=2)
    global entry_font
    entry_font = tk.Entry(root)
    entry_font.insert(0, "12")
    entry_font.pack(fill="x", padx=10)

    global var_mode
    var_mode = tk.StringVar(value="terminal")
    tk.Label(root, text="Mode:").pack(anchor="w", padx=10, pady=4)
    tk.Radiobutton(root, text="Play in Terminal", variable=var_mode, value="terminal").pack(anchor="w", padx=20)
    tk.Radiobutton(root, text="Save as MP4", variable=var_mode, value="save").pack(anchor="w", padx=20)

    global var_audio
    var_audio = tk.BooleanVar(value=True)
    tk.Checkbutton(root, text="Merge Original Audio (FFmpeg)", variable=var_audio).pack(anchor="w", padx=20, pady=6)

    tk.Button(root, text="▶ Start", bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), command=start_conversion).pack(pady=10)

    root.mainloop()
