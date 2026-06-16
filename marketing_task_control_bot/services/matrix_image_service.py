"""Generate Eisenhower matrix report images using the supplied original template only."""
from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

from services.priority_service import sort_tasks_for_matrix
from utils.datetime_utils import format_deadline
from utils.text_utils import task_display_id

logger = logging.getLogger(__name__)

# Safe internal text areas determined from the uploaded 1890×1063 template.
# Values reserve the original axes and quadrant separators.
P2_BOX = (235, 252, 905, 492)   # yuqori chap: rejalashtirish
P1_BOX = (1018, 252, 1688, 492) # yuqori o‘ng: muhim + shoshilinch
P4_BOX = (235, 595, 905, 835)   # pastki chap: keyinroq
P3_BOX = (1018, 595, 1688, 835) # pastki o‘ng: tez bajarish
QUADRANT_BOXES = {"P1": P1_BOX, "P2": P2_BOX, "P3": P3_BOX, "P4": P4_BOX}
QUADRANT_TITLES = {
    "P1": "MUHIM + SHOSHILINCH",
    "P2": "MUHIM · REJALASHTIRISH",
    "P3": "TEZ BAJARISH",
    "P4": "KEYINROQ",
}
TASKS_PER_QUADRANT_PER_PAGE = 5
TEXT_COLOR = (25, 25, 25)
OVERDUE_COLOR = (115, 0, 0)


def _field(task: Any, field: str, default=None):
    return task.get(field, default) if isinstance(task, dict) else getattr(task, field, default)


def load_template_image(template_path: Path) -> Image.Image:
    with Image.open(template_path) as opened:
        return opened.convert("RGB").copy()


def load_font_safely(fonts_dir: Path, size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    filenames = ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold else ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
    search_roots = [
        fonts_dir,
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/share/fonts/truetype/liberation2"),
        Path("/usr/share/fonts/truetype/liberation"),
    ]
    for root in search_roots:
        for filename in filenames:
            candidate = root / filename
            if candidate.exists():
                return ImageFont.truetype(str(candidate), size=size)
    logger.warning("Unicode TTF font topilmadi; default shrift ishlatilmoqda.")
    return ImageFont.load_default()


def _measure(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def wrap_text_to_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int, max_lines: int = 2) -> list[str]:
    words = text.strip().split()
    if not words:
        return [""]
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or _measure(draw, candidate, font) <= max_width:
            current = candidate
            continue
        lines.append(current)
        current = word
        if len(lines) == max_lines:
            break
    if len(lines) < max_lines and current:
        lines.append(current)
    return lines[:max_lines]


def truncate_text_if_needed(draw: ImageDraw.ImageDraw, lines: list[str], original_text: str, font: ImageFont.ImageFont, max_width: int, max_lines: int = 2) -> list[str]:
    result = list(lines[:max_lines])
    visible = " ".join(result).strip()
    if visible == original_text.strip():
        return result
    if not result:
        result = [""]
    last = result[-1]
    while last and _measure(draw, f"{last}...", font) > max_width:
        last = last[:-1].rstrip()
    result[-1] = f"{last}..." if last else "..."
    return result


def group_tasks_by_priority(tasks: Iterable[Any]) -> dict[str, list[Any]]:
    grouped = {"P1": [], "P2": [], "P3": [], "P4": []}
    for task in tasks:
        priority = _field(task, "priority", "P4")
        grouped.setdefault(priority, []).append(task)
    return grouped


def calculate_font_sizes(max_items_in_cell: int) -> dict[str, int]:
    if max_items_in_cell <= 3:
        return {"heading": 18, "task": 17, "deadline": 13, "gap": 8, "line_gap": 2}
    return {"heading": 15, "task": 12, "deadline": 10, "gap": 4, "line_gap": 1}


def draw_quadrant_titles(draw: ImageDraw.ImageDraw, fonts_dir: Path, sizes: dict[str, int]) -> None:
    font = load_font_safely(fonts_dir, sizes["heading"], bold=True)
    for priority, title in QUADRANT_TITLES.items():
        x1, y1, _, _ = QUADRANT_BOXES[priority]
        draw.text((x1, y1), title, font=font, fill=TEXT_COLOR)


def draw_task_text_without_background(
    draw: ImageDraw.ImageDraw,
    task: Any,
    cursor_y: int,
    box: tuple[int, int, int, int],
    fonts_dir: Path,
    sizes: dict[str, int],
    timezone: ZoneInfo,
) -> int:
    x1, _, x2, _ = box
    task_font = load_font_safely(fonts_dir, sizes["task"], bold=True)
    deadline_font = load_font_safely(fonts_dir, sizes["deadline"], bold=False)
    overdue_font = load_font_safely(fonts_dir, sizes["deadline"], bold=True)
    prefix = f"{task_display_id(_field(task, 'task_number'))} · "
    content = prefix + str(_field(task, "short_title", ""))
    lines = wrap_text_to_width(draw, content, task_font, x2 - x1, max_lines=2)
    lines = truncate_text_if_needed(draw, lines, content, task_font, x2 - x1, max_lines=2)
    title_text = "\n".join(lines)
    draw.multiline_text((x1, cursor_y), title_text, font=task_font, fill=TEXT_COLOR, spacing=sizes["line_gap"])
    title_box = draw.multiline_textbbox((x1, cursor_y), title_text, font=task_font, spacing=sizes["line_gap"])
    deadline_y = title_box[3] + 2
    deadline_text = format_deadline(_field(task, "final_deadline"), timezone)
    if _field(task, "status") == "OVERDUE":
        draw.text((x1, deadline_y), f"KECHIKKAN · {deadline_text}", font=overdue_font, fill=OVERDUE_COLOR)
    else:
        draw.text((x1, deadline_y), deadline_text, font=deadline_font, fill=TEXT_COLOR)
    deadline_box = draw.textbbox((x1, deadline_y), deadline_text, font=deadline_font)
    return deadline_box[3] + sizes["gap"]


def draw_empty_state_without_background(draw: ImageDraw.ImageDraw, fonts_dir: Path) -> None:
    text = "Faol topshiriqlar mavjud emas"
    font = load_font_safely(fonts_dir, 27, bold=True)
    box = P4_BOX
    bbox = draw.textbbox((0, 0), text, font=font)
    x = box[0] + ((box[2] - box[0]) - (bbox[2] - bbox[0])) // 2
    y = box[1] + ((box[3] - box[1]) - (bbox[3] - bbox[1])) // 2
    draw.text((x, y), text, font=font, fill=TEXT_COLOR)


class MatrixImageService:
    def __init__(self, template_path: Path, reports_dir: Path, timezone: ZoneInfo):
        self.template_path = template_path
        self.reports_dir = reports_dir
        self.timezone = timezone
        self.fonts_dir = template_path.parent / "fonts"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def create_matrix_pages(self, tasks: Iterable[Any], employee_role: str, updated_at: datetime | None = None) -> list[Path]:
        updated_at = updated_at or datetime.now(self.timezone)
        grouped = group_tasks_by_priority(tasks)
        for priority, rows in grouped.items():
            grouped[priority] = sort_tasks_for_matrix(rows, updated_at, self.timezone)
        page_count = max(1, max((math.ceil(len(rows) / TASKS_PER_QUADRANT_PER_PAGE) for rows in grouped.values()), default=1))
        paths: list[Path] = []
        for page_index in range(page_count):
            image = load_template_image(self.template_path)
            draw = ImageDraw.Draw(image)
            page_grouped = {
                p: rows[page_index * TASKS_PER_QUADRANT_PER_PAGE:(page_index + 1) * TASKS_PER_QUADRANT_PER_PAGE]
                for p, rows in grouped.items()
            }
            maximum_items = max((len(rows) for rows in page_grouped.values()), default=0)
            sizes = calculate_font_sizes(maximum_items)
            draw_quadrant_titles(draw, self.fonts_dir, sizes)
            if not any(page_grouped.values()):
                draw_empty_state_without_background(draw, self.fonts_dir)
            else:
                for priority in ("P2", "P1", "P4", "P3"):
                    x1, y1, x2, y2 = QUADRANT_BOXES[priority]
                    cursor_y = y1 + sizes["heading"] + 10
                    for task in page_grouped[priority]:
                        cursor_y = draw_task_text_without_background(draw, task, cursor_y, (x1, y1, x2, y2), self.fonts_dir, sizes, self.timezone)
                        if cursor_y > y2:
                            raise RuntimeError(f"{priority} katak matni xavfsiz chegaradan chiqdi.")
            filename = f"matrix_{employee_role.replace(' ', '_').lower()}_{uuid.uuid4().hex}_{page_index + 1}.png"
            path = self.reports_dir / filename
            image.save(path, "PNG")
            paths.append(path)
        return paths

    @staticmethod
    def cleanup_generated_files(paths: Iterable[Path]) -> None:
        for path in paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logger.exception("Vaqtinchalik grafikni o‘chirish imkoni bo‘lmadi: %s", path)


def create_matrix_pages(service: MatrixImageService, tasks: Iterable[Any], employee_role: str, updated_at: datetime | None = None) -> list[Path]:
    return service.create_matrix_pages(tasks, employee_role, updated_at)


def cleanup_generated_files(paths: Iterable[Path]) -> None:
    MatrixImageService.cleanup_generated_files(paths)
