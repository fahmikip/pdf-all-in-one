"""Generate docs/badges/coverage.svg from the local .coverage data file."""

from __future__ import annotations

from pathlib import Path

from coverage import Coverage

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "badges" / "coverage.svg"

LABEL = "coverage"
LEFT_WIDTH = 540
UNIT = 80


def color_for(percent: float) -> str:
    if percent >= 90:
        return "brightgreen"
    if percent >= 75:
        return "green"
    if percent >= 60:
        return "yellowgreen"
    if percent >= 40:
        return "yellow"
    if percent >= 20:
        return "orange"
    return "red"


def label_width(text: str) -> int:
    return LEFT_WIDTH + len(text) * UNIT + 8


def main() -> None:
    cov = Coverage(config_file=str(ROOT / "pyproject.toml"))
    cov.load()
    percent = cov.report(file=None, show_missing=False, skip_covered=True)
    value = f"{percent:.0f}%"
    color = color_for(percent)
    right_width = label_width(value) - LEFT_WIDTH
    total = LEFT_WIDTH + right_width
    value_x = LEFT_WIDTH + right_width // 2
    label_x = LEFT_WIDTH // 2
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="20">'
        '<linearGradient id="a" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/>'
        '<stop offset="1" stop-opacity=".1"/></linearGradient>'
        f'<rect width="{total}" height="20" rx="3" fill="#555"/>'
        f'<rect x="{LEFT_WIDTH}" width="{right_width}" height="20" rx="3" fill="{color}"/>'
        f'<rect x="{LEFT_WIDTH}" width="4" height="20" fill="{color}"/>'
        '<g fill="#fff" text-anchor="middle" font-family="Verdana" font-size="11">'
        f'<text x="{label_x}" y="15" fill="#010101" fill-opacity=".3">{LABEL}</text>'
        f'<text x="{label_x}" y="14">{LABEL}</text>'
        f'<text x="{value_x}" y="15" fill="#010101" fill-opacity=".3">{value}</text>'
        f'<text x="{value_x}" y="14">{value}</text></g></svg>'
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg, encoding="utf-8")
    print(f"Badge written to {OUT} ({value})")


if __name__ == "__main__":
    main()
