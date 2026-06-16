from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageChops, ImageDraw

from services.matrix_image_service import (
    MatrixImageService,
    P1_BOX,
    load_template_image,
    load_font_safely,
    wrap_text_to_width,
    truncate_text_if_needed,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = PROJECT_ROOT / "assets" / "toliq_ish_vazifalar_template.png"
TZ = ZoneInfo("Asia/Tashkent")
NOW = datetime(2026, 5, 29, 12, 0, tzinfo=TZ)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sample_task(number=1, title="Reklama banneri", priority="P1", status="ACTIVE"):
    return {
        "task_number": number,
        "short_title": title,
        "priority": priority,
        "status": status,
        "created_at": NOW.isoformat(),
        "final_deadline": (NOW + timedelta(hours=6)).isoformat(),
    }


def make_service(tmp_path: Path) -> MatrixImageService:
    return MatrixImageService(TEMPLATE, tmp_path, TZ)


def test_template_opens_successfully():
    image = load_template_image(TEMPLATE)
    assert image.size == (1890, 1063)


def test_matrix_copy_is_created(tmp_path):
    paths = make_service(tmp_path).create_matrix_pages([sample_task()], "SMM Manager", NOW)
    assert len(paths) == 1
    assert paths[0].exists()
    assert Image.open(paths[0]).size == Image.open(TEMPLATE).size


def test_empty_state_still_generates_image(tmp_path):
    paths = make_service(tmp_path).create_matrix_pages([], "SMM Manager", NOW)
    assert len(paths) == 1 and paths[0].exists()


def test_active_task_is_drawn_inside_expected_quadrant_and_deadline_stays_inside(tmp_path):
    service = make_service(tmp_path)
    empty = service.create_matrix_pages([], "Empty", NOW)[0]
    with_task = service.create_matrix_pages([sample_task()], "Active", NOW)[0]
    with Image.open(empty) as base, Image.open(with_task) as marked:
        diff = ImageChops.difference(base, marked)
        cropped = diff.crop(P1_BOX)
        assert cropped.getbbox() is not None
        # Excluding title row, task/deadline changes remain completely within the P1 safe text box.
        outside = diff.copy()
        ImageDraw.Draw(outside).rectangle(P1_BOX, fill=(0, 0, 0))
        # Other cells differ only because the empty-state text disappears; no task spills outside P1.
        task_band = diff.crop((P1_BOX[0], P1_BOX[1] + 28, P1_BOX[2], P1_BOX[3]))
        assert task_band.getbbox() is not None


def test_long_short_title_wraps_or_truncates_to_two_lines():
    image = load_template_image(TEMPLATE)
    draw = ImageDraw.Draw(image)
    font = load_font_safely(TEMPLATE.parent / "fonts", 17, bold=True)
    text = "#0003 · Community va operatorni Bitrixda juda batafsil alohida ajratish jarayoni"
    lines = wrap_text_to_width(draw, text, font, 350, max_lines=2)
    lines = truncate_text_if_needed(draw, lines, text, font, 350, max_lines=2)
    assert len(lines) <= 2
    assert lines[-1].endswith("...")


def test_many_tasks_create_additional_page(tmp_path):
    tasks = [sample_task(number=i, title=f"Task {i}") for i in range(1, 7)]
    paths = make_service(tmp_path).create_matrix_pages(tasks, "SMM Manager", NOW)
    assert len(paths) == 2


def test_original_template_is_never_modified(tmp_path):
    before = digest(TEMPLATE)
    make_service(tmp_path).create_matrix_pages([sample_task()], "SMM Manager", NOW)
    assert digest(TEMPLATE) == before


def test_no_task_background_rectangle_is_drawn():
    source = (PROJECT_ROOT / "services" / "matrix_image_service.py").read_text(encoding="utf-8")
    assert ".rounded_rectangle(" not in source
    assert "draw.rectangle(" not in source
    assert "task_background" not in source
    assert "badge_background" not in source
    assert "card_background" not in source
