import textwrap
from pathlib import PurePosixPath
from typing import List, Sequence, Tuple

from tools.art.facts import Facts, Module
from tools.art.palette import C
from tools.art.svg import CHAR_WIDTH, Doc, num, text_width

WIDTH = 1920
MARGIN = 24
GAP = 28
LINE_SIZE = 14
PAD = 28
HEAD = 70
BOX_H = 150
TAIL = 28
CHIP_H = 36
CHIP_SIZE = 16


class Architecture:
    """One technical picture of the repository, generated at docs build time and not committed.

    Only the order of the pipeline stages is described here; every module, role, class, path, port and setting
    is read from the repository, so a new module shows up on the next run in the support row.
    """

    CHAIN = ("parser", "media", "rss", "cli")

    @staticmethod
    def _box(
        doc: Doc,
        x: float,
        y: float,
        w: float,
        h: float,
        title: str,
        lines: Sequence[str],
        accent: str,
        dashed: bool = False,
    ) -> None:
        doc.rect(x, y, w, h, C["base"], accent, rx=14, sw=2, dash="7 5" if dashed else None)
        doc.text(x + 20, y + 36, title, 21, accent, 700)
        for i, line in enumerate(lines):
            doc.text(x + 20, y + 66 + i * 22, line, LINE_SIZE, C["subtext0"])

    @staticmethod
    def _wrap(text: str, width: float) -> List[str]:
        columns = max(8, int((width - 36) / (CHAR_WIDTH * LINE_SIZE)))
        return textwrap.wrap(text, columns) if text else []

    @staticmethod
    def _arrow(doc: Doc, x1: float, y: float, x2: float) -> None:
        doc.add(
            f'<path d="M{num(x1)},{num(y)} L{num(x2)},{num(y)}" stroke="{C["overlay1"]}" stroke-width="2.4" '
            f'fill="none" marker-end="url(#ah)"/>'
        )

    @staticmethod
    def _band(doc: Doc, y: float, h: float, number: int, title: str, sub: str) -> None:
        doc.rect(MARGIN, y, WIDTH - 2 * MARGIN, h, C["mantle"], C["surface1"], rx=18, sw=1.5)
        doc.rect(MARGIN, y, 9, h, C["blue"], None, rx=4)
        label = f"{number}  {title}"
        doc.text(MARGIN + 32, y + 40, label, 24, C["blue"], 700, spacing=2)
        doc.text(MARGIN + 32 + text_width(label, 24) + 28, y + 40, sub, 17, C["overlay1"])

    @classmethod
    def _module_box(cls, doc: Doc, module: Module, x: float, y: float, w: float, accent: str, dashed: bool) -> None:
        shown = list(module.classes[:2])
        if len(module.classes) > 2:
            shown.append(f"+{len(module.classes) - 2} more")
        lines = [*cls._wrap(module.role, w)[:2], *cls._wrap(", ".join(shown), w)[:2]]
        cls._box(doc, x, y, w, BOX_H, f"{module.name}.py", lines, accent, dashed)

    @classmethod
    def _split(cls, facts: Facts) -> Tuple[List[Module], List[Module]]:
        by_name = {m.name: m for m in facts.modules}
        chain = [by_name[n] for n in cls.CHAIN if n in by_name]
        return chain, [m for m in facts.modules if m.name not in cls.CHAIN]

    @classmethod
    def _pipeline_height(cls, facts: Facts) -> float:
        _, support = cls._split(facts)
        return HEAD + BOX_H + (62 + BOX_H if support else 0) + TAIL

    @classmethod
    def _pipeline(cls, doc: Doc, facts: Facts, y: float) -> None:
        chain, support = cls._split(facts)
        count = len(chain) + 3
        box_w = (WIDTH - 2 * MARGIN - 2 * PAD - GAP * (count - 1)) / count
        top = y + HEAD
        x0 = MARGIN + PAD
        sources = [
            facts.podcasts_root,
            "  <name>-podcast.yaml",
            f"{facts.public_root}/<name>/",
            "  " + " ".join(facts.media_types),
        ]
        cls._box(doc, x0, top, box_w, BOX_H, "sources", sources, C["lavender"])
        for i, module in enumerate(chain):
            cls._module_box(doc, module, x0 + (i + 1) * (box_w + GAP), top, box_w, C["blue"], False)
        feeds = [f"{facts.public_root}/<name>.xml", "iTunes RSS, atomic write"]
        cls._box(doc, x0 + (count - 2) * (box_w + GAP), top, box_w, BOX_H, "feeds", feeds, C["lavender"])
        caddy = [f":{facts.port}", f"serves {facts.public_root}"]
        cls._box(doc, x0 + (count - 1) * (box_w + GAP), top, box_w, BOX_H, "caddy", caddy, C["lavender"])
        for i in range(count - 1):
            left = x0 + i * (box_w + GAP) + box_w
            cls._arrow(doc, left + 4, top + BOX_H / 2, left + GAP - 4)
        if support:
            label_y = top + BOX_H + 38
            doc.text(x0, label_y, "SUPPORT", 16, C["overlay1"], 700, spacing=1.5)
            for i, module in enumerate(support):
                cls._module_box(doc, module, x0 + i * (box_w + GAP), label_y + 16, box_w, C["overlay1"], True)

    @classmethod
    def _container_height(cls) -> float:
        return HEAD + BOX_H + TAIL

    @classmethod
    def _container(cls, doc: Doc, facts: Facts, y: float) -> None:
        top = y + HEAD
        x = MARGIN + PAD
        image = [facts.base_image, f"+ {facts.caddy_image}", "caddy binary copied over"]
        cls._box(doc, x, top, 330, BOX_H, "image", image, C["lavender"])
        x += 330 + GAP
        steps = (
            (PurePosixPath(facts.entrypoint[0]).name, ["PID 1", "forwards signals"]),
            (PurePosixPath(facts.entrypoint[-1]).name, ["drops to PUID:PGID", "starts the generator"]),
        )
        for title, lines in steps:
            cls._arrow(doc, x - GAP + 4, top + BOX_H / 2, x - 4)
            cls._box(doc, x, top, 270, BOX_H, title, lines, C["blue"])
            x += 270 + GAP
        cls._arrow(doc, x - GAP + 4, top + BOX_H / 2, x - 4)
        cls._box(doc, x, top, 270, 68, "generator", ["python app.py"], C["blue"])
        cls._box(doc, x, top + 82, 270, 68, "caddy", [f":{facts.port} file server"], C["blue"])
        x += 270 + GAP
        volumes = (
            (facts.podcasts_root, "configs in"),
            (facts.public_root, "media in, feeds out"),
            (facts.cache_root, "duration cache"),
        )
        for i, (path, role) in enumerate(volumes):
            vy = top + i * 52
            doc.rect(x, vy, WIDTH - MARGIN - PAD - x, 46, C["base"], C["lavender"], rx=10, sw=1.5, dash="7 5")
            doc.text(x + 16, vy + 29, f"{path}  {role}", 15, C["subtext1"])

    @staticmethod
    def _chips(facts: Facts) -> List[Tuple[float, float, str, float]]:
        """Settings laid out in rows: (x, row offset, label, width)."""
        limit = WIDTH - MARGIN - PAD
        x0 = MARGIN + PAD
        placed, x, row = [], x0, 0
        for key, value in facts.settings:
            label = f"{key}={value}" if value else key
            width = text_width(label, CHIP_SIZE) + 32
            if x + width > limit:
                x, row = x0, row + 1
            placed.append((x, row * (CHIP_H + 10), label, width))
            x += width + 10
        return placed

    @classmethod
    def _settings_height(cls, facts: Facts) -> float:
        rows = max((offset for _, offset, _, _ in cls._chips(facts)), default=0)
        return HEAD - 4 + rows + CHIP_H + TAIL

    @classmethod
    def _settings(cls, doc: Doc, facts: Facts, y: float) -> None:
        for x, offset, label, width in cls._chips(facts):
            top = y + HEAD - 4 + offset
            doc.rect(x, top, width, CHIP_H, C["base"], C["surface1"], rx=CHIP_H / 2, sw=1.3)
            doc.text(x + 16, top + 24, label, CHIP_SIZE, C["text"])

    @classmethod
    def svg(cls, facts: Facts) -> str:
        sections = (
            (
                1,
                "PIPELINE",
                "YAML and media in, feed XML out, served by Caddy",
                cls._pipeline_height(facts),
                cls._pipeline,
            ),
            (
                2,
                "CONTAINER",
                "one image, tini as PID 1, the generator and Caddy",
                cls._container_height(),
                cls._container,
            ),
            (
                3,
                "SETTINGS",
                "environment variables of .env.example, all optional",
                cls._settings_height(facts),
                cls._settings,
            ),
        )
        header = 130
        total = header + sum(h + GAP for _, _, _, h, _ in sections) - GAP + 40
        doc = Doc(
            WIDTH,
            int(total),
            f"{facts.name}: architecture",
            f"Generated from the repository: {len(facts.modules)} modules, {len(facts.settings)} settings, "
            f"served by Caddy on port {facts.port}.",
        )
        doc.defs.append(
            f'<marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" '
            f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{C["overlay1"]}"/></marker>'
            f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C["mantle"]}"/>'
            f'<stop offset="1" stop-color="{C["crust"]}"/></linearGradient>'
        )
        doc.add(f'<rect width="{WIDTH}" height="{int(total)}" fill="url(#bg)"/>')
        doc.text(MARGIN + 16, 64, facts.name, 48, C["text"], 700)
        doc.text(
            MARGIN + 16 + text_width(facts.name, 48) + 24,
            64,
            "architecture, generated from the repository",
            22,
            C["subtext0"],
        )
        summary = f"{len(facts.modules)} modules · {len(facts.settings)} settings · {' '.join(facts.media_types)}"
        doc.text(MARGIN + 16, 98, summary, 18, C["overlay1"])
        y = float(header)
        for number, title, sub, height, draw in sections:
            cls._band(doc, y, height, number, title, sub)
            draw(doc, facts, y)
            y += height + GAP
        return doc.render()
