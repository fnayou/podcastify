from tools.art.banner import Parts
from tools.art.facts import Facts
from tools.art.palette import ACCENT, C
from tools.art.svg import Doc

WIDTH, HEIGHT = 1280, 640


class Social:
    """The GitHub social preview (1280x640): name, pitch, the docker run command to try it and four facts."""

    @classmethod
    def svg(cls, facts: Facts) -> str:
        doc = Doc(WIDTH, HEIGHT, facts.image, f"{facts.name}: {facts.pitch}")
        center = WIDTH / 2
        Parts.background(doc)
        Parts.card(doc, 32, 32, WIDTH - 64, HEIGHT - 64)
        Parts.headline(doc, facts, center, 150, 72, 100)
        Parts.subtitle(doc, facts.pitch_lines[0], center, 214, 30)
        doc.rect(260, 258, 760, 192, C["mantle"], C["surface1"], rx=16, sw=2, opacity=0.6)
        for i, color in enumerate((C["red"], C["yellow"], C["green"])):
            doc.circle(292 + i * 26, 288, 7, color)
        doc.text(292, 340, "$", 24, ACCENT, 700)
        for i, line in enumerate(facts.run_hint):
            doc.text(322, 340 + i * 30, line, 24, C["text"])
        for i, (value, label) in enumerate(Parts.stats(facts)):
            Parts.stat(doc, 190 + i * 300, 528, value, label, "middle", 42)
        return doc.render()
