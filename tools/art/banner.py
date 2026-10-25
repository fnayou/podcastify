from typing import List, Sequence, Tuple

from tools.art.facts import Facts
from tools.art.palette import ACCENT, C
from tools.art.svg import Doc, esc, num, text_width

WIDTH, HEIGHT = 1670, 558
HIGHLIGHTS = ("self-hosted", "RSS")


class Parts:
    """Pieces shared by the banner and the social preview."""

    @staticmethod
    def background(doc: Doc) -> None:
        doc.defs.append(
            f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{C["mantle"]}"/><stop offset="1" stop-color="{C["crust"]}"/>'
            f"</linearGradient>"
            f'<linearGradient id="card" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{C["base"]}"/><stop offset="1" stop-color="{C["mantle"]}"/>'
            f"</linearGradient>"
            f'<linearGradient id="edge" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{ACCENT}" stop-opacity=".55"/>'
            f'<stop offset="1" stop-color="{C["peach"]}" stop-opacity=".35"/>'
            f"</linearGradient>"
        )
        doc.add(f'<rect width="{doc.width}" height="{doc.height}" fill="url(#bg)"/>')

    @staticmethod
    def card(doc: Doc, x: float, y: float, w: float, h: float) -> None:
        doc.add(
            f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" rx="30" fill="url(#card)" '
            f'stroke="url(#edge)" stroke-width="2"/>'
        )

    @staticmethod
    def sparkle(doc: Doc, x: float, y: float) -> None:
        d = (
            f"M{num(x)},{num(y - 18)} C{num(x + 4)},{num(y - 4)} {num(x + 4)},{num(y - 4)} {num(x + 18)},{num(y)} "
            f"C{num(x + 4)},{num(y + 4)} {num(x + 4)},{num(y + 4)} {num(x)},{num(y + 18)} "
            f"C{num(x - 4)},{num(y + 4)} {num(x - 4)},{num(y + 4)} {num(x - 18)},{num(y)} "
            f"C{num(x - 4)},{num(y - 4)} {num(x - 4)},{num(y - 4)} {num(x)},{num(y - 18)}Z"
        )
        doc.add(f'<path d="{d}" fill="{C["peach"]}"/>')

    @classmethod
    def headline(cls, doc: Doc, facts: Facts, center: float, y: float, size: float, edge: float) -> None:
        owner, _, name = facts.image.rpartition("/")
        owner = f"{owner}/" if owner else ""
        width = text_width(owner + name, size)
        left, right = center - width / 2, center + width / 2
        doc.add(
            f'<text x="{num(center)}" y="{num(y)}" text-anchor="middle" font-size="{num(size)}" font-weight="500">'
            f'<tspan fill="{C["lavender"]}">{esc(owner)}</tspan><tspan fill="{ACCENT}">{esc(name)}</tspan></text>'
        )
        line_y = y - size * 0.4
        doc.line(edge + 34, line_y, left - 40, line_y, C["overlay0"], 2)
        doc.line(right + 40, line_y, 2 * center - edge - 34, line_y, C["overlay0"], 2)
        cls.sparkle(doc, edge, line_y + 5)
        cls.sparkle(doc, 2 * center - edge, line_y + 5)

    @staticmethod
    def subtitle(doc: Doc, text: str, center: float, y: float, size: float) -> None:
        segments: List[Tuple[str, bool]] = [(text, False)]
        for word in HIGHLIGHTS:
            split: List[Tuple[str, bool]] = []
            for chunk, lit in segments:
                if lit or word not in chunk:
                    split.append((chunk, lit))
                    continue
                head, _, tail = chunk.partition(word)
                split += [(head, False), (word, True), (tail, False)]
            segments = split
        spans = "".join(
            f'<tspan fill="{ACCENT}">{esc(chunk)}</tspan>' if lit else esc(chunk) for chunk, lit in segments if chunk
        )
        doc.add(
            f'<text x="{num(center)}" y="{num(y)}" text-anchor="middle" font-size="{num(size)}" '
            f'fill="{C["subtext0"]}">{spans}</text>'
        )

    @staticmethod
    def stat(doc: Doc, x: float, y: float, value, label: str, anchor: str, size: float = 46) -> None:
        doc.text(x, y, value, size, ACCENT, 700, anchor)
        doc.text(x, y + size * 0.65, label.upper(), size * 0.46, C["overlay1"], 400, anchor, spacing=1)

    @staticmethod
    def stats(facts: Facts) -> Sequence[Tuple[str, str]]:
        return (
            (str(len(facts.modules)), "modules"),
            (str(len(facts.settings)), "settings"),
            (str(facts.decisions), "decision records"),
            (str(len(facts.media_types)), "audio formats"),
        )


class Banner:
    @classmethod
    def svg(cls, facts: Facts) -> str:
        doc = Doc(WIDTH, HEIGHT, facts.image, f"{facts.name}: {facts.pitch}")
        center = WIDTH / 2
        Parts.background(doc)
        Parts.card(doc, 38, 40, WIDTH - 76, HEIGHT - 82)
        Parts.headline(doc, facts, center, 196, 88, 136)
        Parts.subtitle(doc, facts.pitch_lines[0], center, 272, 35)
        doc.rect(430, 330, 808, 158, C["mantle"], C["surface1"], rx=16, sw=2, opacity=0.6)
        step = 44 * 0.6
        home = "~/podcastify"
        doc.text(470, 400, home, 44, ACCENT)
        on_x = 470 + text_width(home, 44) + step
        doc.text(on_x, 400, "on", 44, C["green"])
        doc.text(on_x + text_width("on", 44) + step, 400, f":{facts.port}", 44, C["green"])
        command = "task docker:up"
        doc.text(472, 462, "❯", 44, C["peach"], 700)
        doc.text(540, 462, command, 44, C["text"])
        doc.add(
            f'<rect x="{num(540 + text_width(command, 44) + 12)}" y="426" width="26" height="46" fill="{C["rosewater"]}">'
            f'<animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;.5;.5;.95;1" dur="1.2s" '
            f'repeatCount="indefinite"/></rect>'
        )
        (a, la), (b, lb), (c, lc), (d, ld) = Parts.stats(facts)
        Parts.stat(doc, 330, 380, a, la, "end")
        Parts.stat(doc, 330, 462, b, lb, "end")
        Parts.stat(doc, 1340, 380, c, lc, "start")
        Parts.stat(doc, 1340, 462, d, ld, "start")
        return doc.render()
