import re
from html import escape
from typing import List, Optional

from tools.art.palette import C

# System monospace fonts only: a CDN or web font would not render in GitHub, Docker Hub or CI.
FONT = "ui-monospace,'SF Mono',Menlo,Consolas,'DejaVu Sans Mono','Liberation Mono',monospace"
CHAR_WIDTH = 0.6

_LONG_FRACTION = re.compile(r"(?<![0-9A-Za-z#.])(-?\d+\.\d{3,})")


def esc(value) -> str:
    return escape(str(value))


def num(value) -> str:
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value)


def text_width(text: str, size: float) -> float:
    return len(text) * CHAR_WIDTH * size


def tidy(markup: str) -> str:
    """Round the long fractions left by coordinate arithmetic so the same drawing prints the same bytes."""
    return _LONG_FRACTION.sub(lambda m: num(round(float(m.group(1)), 2)), markup)


class Doc:
    def __init__(self, width: int, height: int, title: str, desc: str, body_font: bool = True):
        self.width = width
        self.height = height
        self.title = title
        self.desc = desc
        self.body_font = body_font
        self.defs: List[str] = []
        self.parts: List[str] = []

    def add(self, markup: str) -> None:
        self.parts.append(markup)

    def text(
        self,
        x: float,
        y: float,
        value,
        size: float = 18,
        fill: Optional[str] = None,
        weight: int = 400,
        anchor: str = "start",
        spacing: Optional[float] = None,
    ) -> None:
        extra = f' letter-spacing="{num(spacing)}"' if spacing else ""
        self.add(
            f'<text x="{num(x)}" y="{num(y)}" font-size="{num(size)}" font-weight="{weight}" '
            f'fill="{fill or C["text"]}" text-anchor="{anchor}"{extra}>{esc(value)}</text>'
        )

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: str,
        stroke: Optional[str] = None,
        rx: float = 12,
        sw: float = 1.5,
        dash: Optional[str] = None,
        opacity: Optional[float] = None,
    ) -> None:
        extra = f' stroke="{stroke}" stroke-width="{num(sw)}"' if stroke else ""
        extra += f' stroke-dasharray="{dash}"' if dash else ""
        extra += f' fill-opacity="{num(opacity)}"' if opacity is not None else ""
        self.add(
            f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" rx="{num(rx)}" fill="{fill}"{extra}/>'
        )

    def circle(self, cx: float, cy: float, r: float, fill: str = "none", stroke: Optional[str] = None, sw: float = 2):
        extra = f' stroke="{stroke}" stroke-width="{num(sw)}"' if stroke else ""
        self.add(f'<circle cx="{num(cx)}" cy="{num(cy)}" r="{num(r)}" fill="{fill}"{extra}/>')

    def line(self, x1: float, y1: float, x2: float, y2: float, stroke: str, sw: float = 2, dash: Optional[str] = None):
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(
            f'<line x1="{num(x1)}" y1="{num(y1)}" x2="{num(x2)}" y2="{num(y2)}" stroke="{stroke}" '
            f'stroke-width="{num(sw)}"{extra}/>'
        )

    def render(self) -> str:
        head = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}" role="img" aria-labelledby="t d">'
            f'<title id="t">{esc(self.title)}</title><desc id="d">{esc(self.desc)}</desc>'
        )
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        body = "\n".join(self.parts)
        wrapped = f'<g font-family="{FONT}">\n{body}\n</g>' if self.body_font else body
        return tidy(f"{head}{defs}\n{wrapped}\n</svg>\n")
