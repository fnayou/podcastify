from tools.art.facts import Facts
from tools.art.logo import Logo
from tools.art.palette import C
from tools.art.svg import Doc, num, text_width

WIDTH, HEIGHT = 1280, 400
ACCENT_LETTERS = 3


class Parts:
    """Pieces shared by the banner and the social preview."""

    @staticmethod
    def background(doc: Doc, gradient_id: str = "bg") -> None:
        doc.defs.append(
            f'<linearGradient id="{gradient_id}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{C["mantle"]}"/><stop offset="1" stop-color="{C["crust"]}"/>'
            f"</linearGradient>"
        )
        doc.add(f'<rect width="{doc.width}" height="{doc.height}" fill="url(#{gradient_id})"/>')

    @staticmethod
    def mark(doc: Doc, x: float, y: float, scale: float) -> None:
        doc.add(
            f'<g transform="translate({num(x - 16 * scale)},{num(y - 16 * scale)}) scale({num(scale)})">{Logo.mark()}</g>'
        )

    @staticmethod
    def title(doc: Doc, x: float, y: float, name: str, size: float) -> None:
        head, tail = name[:-ACCENT_LETTERS], name[-ACCENT_LETTERS:]
        doc.text(x, y, head, size, C["text"], 700)
        doc.text(x + text_width(head, size), y, tail, size, C["blue"], 700)

    @staticmethod
    def chips(doc: Doc, x: float, y: float, labels, size: float = 20) -> float:
        for label in labels:
            width = text_width(label, size) + 36
            doc.rect(x, y, width, size + 20, C["base"], C["surface1"], rx=(size + 20) / 2, sw=1.5)
            doc.text(x + 18, y + size + 3, label, size, C["subtext1"])
            x += width + 12
        return x


class Banner:
    @classmethod
    def svg(cls, facts: Facts) -> str:
        doc = Doc(
            WIDTH,
            HEIGHT,
            facts.name,
            f"{facts.name}: {facts.pitch}",
        )
        Parts.background(doc)
        doc.rect(24, 24, WIDTH - 48, HEIGHT - 48, C["base"], C["surface1"], rx=28, sw=2)
        Parts.mark(doc, 72, 72, 0.5)
        Parts.title(doc, 372, 168, facts.name, 96)
        for i, line in enumerate(facts.pitch_lines):
            doc.text(372, 226 + i * 40, line, 28, C["subtext0"])
        Parts.chips(doc, 372, 292, facts.media_types)
        return doc.render()
