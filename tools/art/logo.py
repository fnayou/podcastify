from tools.art.palette import ACCENT, C
from tools.art.svg import Doc

SIZE = 512


class Logo:
    """The mark: a microphone with the feed symbol raised beside it, like an exponent, on a rounded dark square."""

    STROKE = 24
    FEED_DOT = (366, 196)
    FEED_RADII = (38, 72)
    FEED_STROKE = 18

    @classmethod
    def _feed_arc(cls, radius: int) -> str:
        cx, cy = cls.FEED_DOT
        return (
            f'<path d="M{cx},{cy - radius} A{radius},{radius} 0 0 1 {cx + radius},{cy}" fill="none" '
            f'stroke="{ACCENT}" stroke-width="{cls.FEED_STROKE}" stroke-linecap="round"/>'
        )

    @classmethod
    def mark(cls) -> str:
        cx, cy = cls.FEED_DOT
        parts = [
            f'<rect x="16" y="16" width="480" height="480" rx="112" fill="{C["mantle"]}" '
            f'stroke="{C["surface1"]}" stroke-width="8"/>',
            f'<rect x="216" y="100" width="80" height="150" rx="40" fill="{ACCENT}"/>',
            f'<path d="M186,206 A70,70 0 0 0 326,206" fill="none" stroke="{ACCENT}" '
            f'stroke-width="{cls.STROKE}" stroke-linecap="round"/>',
            f'<path d="M256,276 V372 M196,384 H316" fill="none" stroke="{ACCENT}" '
            f'stroke-width="{cls.STROKE}" stroke-linecap="round"/>',
            f'<circle cx="{cx}" cy="{cy}" r="12" fill="{ACCENT}"/>',
        ]
        parts += [cls._feed_arc(r) for r in cls.FEED_RADII]
        return "\n".join(parts)

    @classmethod
    def svg(cls) -> str:
        doc = Doc(
            SIZE,
            SIZE,
            "podcastify",
            "Logo of podcastify: a microphone with the feed symbol beside it on a dark rounded square.",
            body_font=False,
        )
        doc.add(cls.mark())
        return doc.render()


class Favicon:
    """The same mark at 64 px: the drawing is scaled down, its strokes stay thick enough to read."""

    SIZE = 64

    @classmethod
    def svg(cls) -> str:
        doc = Doc(
            cls.SIZE,
            cls.SIZE,
            "podcastify",
            "Favicon of podcastify: a microphone with the feed symbol beside it on a dark rounded square.",
            body_font=False,
        )
        doc.add(f'<g transform="scale(0.125)">{Logo.mark()}</g>')
        return doc.render()
