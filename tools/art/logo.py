from typing import List

from tools.art.palette import C
from tools.art.svg import Doc, num

SIZE = 512


class Logo:
    """The mark: broadcast arcs (the feed) next to a waveform (the audio), on a rounded dark square."""

    DOT = (150, 362)
    ARC_RADII = (100, 180)
    BARS = ((330, 90), (368, 170), (406, 130), (444, 60))
    BAR_CENTER = 200
    BAR_WIDTH = 20

    @classmethod
    def _arc(cls, radius: int, width: int) -> str:
        cx, cy = cls.DOT
        return (
            f'<path d="M{cx},{cy - radius} A{radius},{radius} 0 0 1 {cx + radius},{cy}" fill="none" '
            f'stroke="{C["blue"]}" stroke-width="{width}" stroke-linecap="round"/>'
        )

    @classmethod
    def mark(cls) -> str:
        cx, cy = cls.DOT
        parts: List[str] = [
            f'<rect x="16" y="16" width="480" height="480" rx="112" fill="{C["mantle"]}" '
            f'stroke="{C["surface1"]}" stroke-width="8"/>',
            f'<circle cx="{cx}" cy="{cy}" r="32" fill="{C["blue"]}"/>',
        ]
        parts += [cls._arc(r, 36) for r in cls.ARC_RADII]
        for x, height in cls.BARS:
            top = num(cls.BAR_CENTER - height / 2)
            parts.append(
                f'<rect x="{x}" y="{top}" width="{cls.BAR_WIDTH}" height="{height}" rx="{cls.BAR_WIDTH // 2}" '
                f'fill="{C["subtext0"]}"/>'
            )
        return "\n".join(parts)

    @classmethod
    def svg(cls) -> str:
        doc = Doc(
            SIZE,
            SIZE,
            "podcastify",
            "Logo of podcastify: broadcast arcs next to an audio waveform on a dark rounded square.",
            body_font=False,
        )
        doc.add(cls.mark())
        return doc.render()


class Favicon:
    """The mark reduced to what stays readable at 64 px: a dot and two thick arcs."""

    SIZE = 64

    @classmethod
    def svg(cls) -> str:
        doc = Doc(
            cls.SIZE,
            cls.SIZE,
            "podcastify",
            "Favicon of podcastify: a dot with two broadcast arcs on a dark rounded square.",
            body_font=False,
        )
        doc.add(f'<rect x="2" y="2" width="60" height="60" rx="14" fill="{C["mantle"]}"/>')
        doc.add(f'<circle cx="20" cy="44" r="5" fill="{C["blue"]}"/>')
        for radius in (14, 28):
            doc.add(
                f'<path d="M20,{44 - radius} A{radius},{radius} 0 0 1 {20 + radius},44" fill="none" '
                f'stroke="{C["blue"]}" stroke-width="6" stroke-linecap="round"/>'
            )
        return doc.render()
