from tools.art.banner import Parts
from tools.art.facts import Facts
from tools.art.palette import C
from tools.art.svg import Doc

WIDTH, HEIGHT = 1280, 640


class Social:
    """The GitHub social preview (1280x640): name, pitch and the docker run command to try it."""

    @classmethod
    def svg(cls, facts: Facts) -> str:
        doc = Doc(WIDTH, HEIGHT, facts.name, f"{facts.name}: {facts.pitch}")
        Parts.background(doc)
        Parts.mark(doc, 64, 56, 0.3)
        Parts.title(doc, 236, 150, facts.name, 72)
        for i, line in enumerate(facts.pitch_lines):
            doc.text(64, 248 + i * 42, line, 30, C["subtext0"])
        doc.rect(64, 320, WIDTH - 128, 226, C["mantle"], C["surface1"], rx=18, sw=2)
        for i, color in enumerate((C["red"], C["yellow"], C["green"])):
            doc.circle(96 + i * 26, 352, 7, color)
        doc.text(96, 410, "$", 26, C["blue"], 700)
        for i, line in enumerate(facts.run_hint):
            doc.text(128, 410 + i * 34, line, 26, C["text"])
        Parts.chips(doc, 64, 566, facts.media_types, 20)
        doc.text(WIDTH - 64, 594, f"docker.io/{facts.image}", 22, C["overlay1"], anchor="end")
        return doc.render()
