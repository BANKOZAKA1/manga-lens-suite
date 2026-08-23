"""Bootstrap the pinned manga-image-translator with MangaLens safety guards."""

from __future__ import annotations

import runpy
import os
import sys
import unicodedata
from pathlib import Path


mit_root = Path(os.environ.get("MANGALENS_MIT_ROOT", Path.cwd())).resolve()
if not (mit_root / "manga_translator").is_dir():
    raise SystemExit(f"manga-image-translator was not found: {mit_root}")
sys.path.insert(0, str(mit_root))


def _install_render_guard() -> None:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    import manga_translator.rendering as rendering
    import manga_translator.manga_translator as translator_module
    import manga_translator.rendering.text_render_pillow_eng as pillow_renderer
    from manga_translator.rendering.ballon_extractor import extract_ballon_region
    from manga_translator.utils import LANGUAGE_ORIENTATION_PRESETS

    try:
        from pythainlp.tokenize import word_tokenize
    except ImportError:  # The grapheme fallback remains fully offline.
        word_tokenize = None

    LANGUAGE_ORIENTATION_PRESETS["THA"] = "h"

    original_merge = pillow_renderer.merge_seg_eng
    if not getattr(original_merge, "_mangalens_thai", False):
        def merge_thai_lines(text, font, bbox_width, size_ratio=1.0):
            if not any("\u0e00" <= char <= "\u0e7f" for char in text):
                return original_merge(text, font, bbox_width, size_ratio)
            clusters: list[str] = []
            for char in text.replace("\n", " ").strip():
                category = unicodedata.category(char)
                if clusters and (unicodedata.combining(char) or category in {"Mn", "Mc", "Me"}):
                    clusters[-1] += char
                else:
                    clusters.append(char)
            max_width = max(float(bbox_width) * 0.9, float(font.size) * 2.0)
            lines: list[str] = []
            current = ""
            for cluster in clusters:
                candidate = current + cluster
                if current and font.getlength(candidate) > max_width:
                    lines.append(current.rstrip())
                    current = cluster.lstrip()
                else:
                    current = candidate
            if current.strip():
                lines.append(current.strip())
            return lines

        merge_thai_lines._mangalens_thai = True
        pillow_renderer.merge_seg_eng = merge_thai_lines

    async def dispatch_thai_pillow(
        img_canvas,
        original_img,
        text_regions,
        font_path="",
        line_spacing=0,
        disable_font_border=False,
    ):
        thai_font = font_path if font_path and Path(font_path).is_file() else str(
            Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "tahoma.ttf"
        )
        canvas = Image.fromarray(img_canvas).convert("RGB")
        draw = ImageDraw.Draw(canvas)
        image_height, image_width = img_canvas.shape[:2]
        page_font_cap = max(24, min(64, round((image_height + image_width) / 65)))

        def graphemes(value: str) -> list[str]:
            result: list[str] = []
            for char in value:
                category = unicodedata.category(char)
                if result and (unicodedata.combining(char) or category in {"Mn", "Mc", "Me"}):
                    result[-1] += char
                else:
                    result.append(char)
            return result

        def tokens(value: str) -> list[str]:
            if word_tokenize is not None:
                try:
                    return word_tokenize(value.replace("\n", " "), engine="newmm", keep_whitespace=True)
                except Exception:
                    pass
            return graphemes(value.replace("\n", " "))

        def wrapped_lines(value: str, font, max_width: int) -> list[str]:
            lines: list[str] = []
            current = ""
            for token in tokens(value):
                if not token:
                    continue
                candidate = current + token
                if current and font.getlength(candidate) > max_width:
                    lines.append(current.strip())
                    current = token.lstrip()
                else:
                    current = candidate
                if current and font.getlength(current) > max_width:
                    oversized = current
                    current = ""
                    fragment = ""
                    for cluster in graphemes(oversized):
                        trial = fragment + cluster
                        if fragment and font.getlength(trial) > max_width:
                            lines.append(fragment.strip())
                            fragment = cluster.lstrip()
                        else:
                            fragment = trial
                    current = fragment
            if current.strip():
                lines.append(current.strip())
            return [line for line in lines if line]

        for region in text_regions:
            text = region.translation.strip()
            if not text:
                continue
            try:
                balloon_mask, window = extract_ballon_region(
                    original_img,
                    region.xywh,
                    enlarge_ratio=min(max(region.xywh[2] / max(region.xywh[3], 1), region.xywh[3] / max(region.xywh[2], 1)) * 1.5, 3),
                )
                nonzero = cv2.findNonZero(balloon_mask)
                if nonzero is None:
                    raise ValueError("empty balloon mask")
                mask_x, mask_y, mask_width, mask_height = cv2.boundingRect(nonzero)
                x1 = int(window[0] + mask_x)
                y1 = int(window[1] + mask_y)
                x2 = int(x1 + mask_width)
                y2 = int(y1 + mask_height)
            except Exception:
                x1, y1, x2, y2 = [int(value) for value in region.xyxy]

            x1, x2 = sorted((max(0, x1), min(image_width, x2)))
            y1, y2 = sorted((max(0, y1), min(image_height, y2)))
            box_width, box_height = x2 - x1, y2 - y1
            if box_width < 8 or box_height < 8:
                continue
            pad_x = max(4, round(box_width * 0.08))
            pad_y = max(4, round(box_height * 0.08))
            usable_width = max(4, box_width - 2 * pad_x)
            usable_height = max(4, box_height - 2 * pad_y)

            low, high = 8, min(page_font_cap, max(8, int(region.font_size * 1.15)))
            best = None
            while low <= high:
                size = (low + high) // 2
                font = ImageFont.truetype(thai_font, size)
                lines = wrapped_lines(text, font, usable_width)
                spacing = max(1, size // 8)
                rendered = "\n".join(lines)
                bounds = draw.multiline_textbbox(
                    (0, 0), rendered, font=font, align="center", spacing=spacing, stroke_width=max(1, size // 24)
                )
                width = bounds[2] - bounds[0]
                height = bounds[3] - bounds[1]
                if lines and width <= usable_width and height <= usable_height:
                    best = (font, rendered, spacing, bounds)
                    low = size + 1
                else:
                    high = size - 1
            if best is None:
                font = ImageFont.truetype(thai_font, 8)
                rendered = "\n".join(wrapped_lines(text, font, usable_width))
                spacing = 1
                bounds = draw.multiline_textbbox((0, 0), rendered, font=font, align="center", spacing=spacing, stroke_width=1)
            else:
                font, rendered, spacing, bounds = best

            text_width = bounds[2] - bounds[0]
            text_height = bounds[3] - bounds[1]
            position = (
                x1 + (box_width - text_width) / 2 - bounds[0],
                y1 + (box_height - text_height) / 2 - bounds[1],
            )
            fg, _ = region.get_font_colors()
            fill = tuple(int(channel) for channel in fg)
            stroke_width = max(1, font.size // 24)
            draw.multiline_text(
                position,
                rendered,
                font=font,
                fill=fill,
                align="center",
                spacing=spacing,
                stroke_width=stroke_width,
                stroke_fill=(255, 255, 255),
            )

        return np.asarray(canvas)

    translator_module.dispatch_eng_render_pillow = dispatch_thai_pillow

    original_warp_perspective = cv2.warpPerspective
    if not getattr(original_warp_perspective, "_mangalens_guarded", False):
        def guarded_warp_perspective(src, matrix, dsize, *args, **kwargs):
            src_height, src_width = src.shape[:2]
            if max(src_height, src_width, *dsize) < 32767:
                return original_warp_perspective(src, matrix, dsize, *args, **kwargs)
            if max(dsize) >= 32767:
                raise RuntimeError(f"Destination canvas exceeds OpenCV limit: {dsize}")
            scale = min(16000 / src_width, 16000 / src_height, 1.0)
            safe_width = max(1, round(src_width * scale))
            safe_height = max(1, round(src_height * scale))
            resized = cv2.resize(src, (safe_width, safe_height), interpolation=cv2.INTER_AREA)
            scale_x = safe_width / src_width
            scale_y = safe_height / src_height
            inverse_scale = np.asarray(
                [[1.0 / scale_x, 0.0, 0.0], [0.0, 1.0 / scale_y, 0.0], [0.0, 0.0, 1.0]],
                dtype=np.float64,
            )
            adjusted_matrix = np.asarray(matrix, dtype=np.float64) @ inverse_scale
            sys.stderr.write(
                "[MangaLens] OpenCV canvas guard: resized intermediate canvas "
                f"{src_width}x{src_height} -> {safe_width}x{safe_height}\n"
            )
            return original_warp_perspective(
                resized, adjusted_matrix, dsize, *args, **kwargs
            )

        guarded_warp_perspective._mangalens_guarded = True
        cv2.warpPerspective = guarded_warp_perspective

    original_render = rendering.render
    if getattr(original_render, "_mangalens_guarded", False):
        return

    def guarded_render(img, region, dst_points, hyphenate, line_spacing, disable_font_border):
        try:
            return original_render(
                img, region, dst_points, hyphenate, line_spacing, disable_font_border
            )
        except cv2.error as exc:
            if "SHRT_MAX" not in str(exc) and "dst.cols <" not in str(exc):
                raise
            points = np.asarray(dst_points, dtype=np.float32)
            x, y, width, height = cv2.boundingRect(points.astype(np.int32))
            if width < 2 or height < 2:
                raise RuntimeError(
                    f"Degenerate render region {points.tolist()} for {region.text!r}"
                ) from exc
            safe_points = np.asarray(
                [
                    [x, y],
                    [x + width - 1, y],
                    [x + width - 1, y + height - 1],
                    [x, y + height - 1],
                ],
                dtype=np.float32,
            ).reshape(1, 4, 2)
            sys.stderr.write(
                "[MangaLens] OpenCV remap guard: retrying an axis-aligned "
                f"{width}x{height} region; text={region.text!r}\n"
            )
            return original_render(
                img, region, safe_points, hyphenate, line_spacing, disable_font_border
            )

    guarded_render._mangalens_guarded = True
    rendering.render = guarded_render
    sys.stderr.write("[MangaLens] renderer guard installed\n")


def main() -> None:
    _install_render_guard()
    runpy.run_module("manga_translator", run_name="__main__", alter_sys=True)


if __name__ == "__main__":
    main()
