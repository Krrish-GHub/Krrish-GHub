#!/usr/bin/env python3

from __future__ import annotations

import argparse
import math
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps


ASCII_CHARS = " .:-=+*#%@"


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def font_path() -> str:
    match = subprocess.run(
        ["fc-match", "-f", "%{file}\n", "Noto Sans Mono"],
        check=True,
        capture_output=True,
        text=True,
    )
    path = match.stdout.strip().splitlines()[0]
    if not path:
        raise RuntimeError("Could not resolve a monospace font")
    return path


def frame_to_ascii(image: Image.Image, width: int) -> str:
    gray = ImageOps.autocontrast(ImageOps.grayscale(image), cutoff=1)
    source_width, source_height = gray.size
    target_height = max(1, int(round(source_height / source_width * width * 0.5)))
    resized = gray.resize((width, target_height))
    pixels = resized.load()
    lines: list[str] = []
    for y in range(target_height):
        row = []
        for x in range(width):
            value = pixels[x, y]
            index = value * (len(ASCII_CHARS) - 1) // 255
            row.append(ASCII_CHARS[index])
        lines.append("".join(row))
    return "\n".join(lines)


def render_ascii_frame(text: str, font: ImageFont.FreeTypeFont, padding: int = 16) -> Image.Image:
    lines = text.splitlines() or [""]
    max_line_width = max(len(line) for line in lines)
    text = "\n".join(line.ljust(max_line_width) for line in lines)
    bbox_probe = Image.new("RGB", (1, 1), "black")
    probe_draw = ImageDraw.Draw(bbox_probe)
    bbox = probe_draw.multiline_textbbox((0, 0), "Ag", font=font, spacing=0)
    char_width = bbox[2] - bbox[0]
    char_height = bbox[3] - bbox[1]
    line_height = math.ceil(char_height * 1.1)
    image_width = padding * 2 + max_line_width * char_width
    image_height = padding * 2 + len(lines) * line_height
    image = Image.new("RGB", (image_width, image_height), "black")
    draw = ImageDraw.Draw(image)
    draw.multiline_text(
        (padding, padding),
        text,
        fill=(245, 245, 245),
        font=font,
        spacing=0,
    )
    return image


def content_bbox(frames: list[Image.Image], pad: int = 12) -> tuple[int, int, int, int] | None:
    background = Image.new("RGB", frames[0].size, "black")
    left = frames[0].width
    top = frames[0].height
    right = 0
    bottom = 0
    found = False
    for frame in frames:
        bbox = ImageChops.difference(frame, background).getbbox()
        if bbox is None:
            continue
        found = True
        left = min(left, bbox[0])
        top = min(top, bbox[1])
        right = max(right, bbox[2])
        bottom = max(bottom, bbox[3])
    if not found:
        return None
    return (
        max(0, left - pad),
        max(0, top - pad),
        min(frames[0].width, right + pad),
        min(frames[0].height, bottom + pad),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a video into an ASCII GIF")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--width", type=int, default=54)
    parser.add_argument("--fps", type=int, default=8)
    parser.add_argument("--font-size", type=int, default=12)
    parser.add_argument("--trim-content", action="store_true")
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}")

    font = ImageFont.truetype(font_path(), args.font_size)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        run([
            "ffmpeg",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(args.input),
            "-vf",
            f"fps={args.fps},scale={args.width}:-1:flags=lanczos",
            str(tmpdir_path / "frame_%03d.png"),
        ])

        frame_paths = sorted(tmpdir_path.glob("frame_*.png"))
        if not frame_paths:
            raise SystemExit("No frames were extracted from the video")

        frames = []
        for frame_path in frame_paths:
            with Image.open(frame_path) as image:
                ascii_text = frame_to_ascii(image, args.width)
            rendered = render_ascii_frame(ascii_text, font)
            frames.append(rendered)

        if args.trim_content:
            bbox = content_bbox(frames)
            if bbox is not None:
                frames = [frame.crop(bbox) for frame in frames]

        first, *rest = frames
        args.output.parent.mkdir(parents=True, exist_ok=True)
        first.save(
            args.output,
            save_all=True,
            append_images=rest,
            duration=max(40, int(round(1000 / args.fps))),
            loop=0,
            optimize=True,
            disposal=2,
        )


if __name__ == "__main__":
    main()