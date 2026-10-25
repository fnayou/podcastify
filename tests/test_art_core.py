#!/usr/bin/env python3
"""Tests for the art generator core: palette, SVG builder and the SVG + PNG writer."""

import stat
import xml.etree.ElementTree as ET

import pytest

from tools.art.palette import C, Palette
from tools.art.render import RenderError, Renderer
from tools.art.svg import FONT, Doc, esc, num, text_width, tidy

MACCHIATO = {
    "rosewater": "#f4dbd6",
    "flamingo": "#f0c6c6",
    "pink": "#f5bde6",
    "mauve": "#c6a0f6",
    "red": "#ed8796",
    "maroon": "#ee99a0",
    "peach": "#f5a97f",
    "yellow": "#eed49f",
    "green": "#a6da95",
    "teal": "#8bd5ca",
    "sky": "#91d7e3",
    "sapphire": "#7dc4e4",
    "blue": "#8aadf4",
    "lavender": "#b7bdf8",
    "text": "#cad3f5",
    "subtext1": "#b8c0e0",
    "subtext0": "#a5adcb",
    "overlay2": "#939ab7",
    "overlay1": "#8087a2",
    "overlay0": "#6e738d",
    "surface2": "#5b6078",
    "surface1": "#494d64",
    "surface0": "#363a4f",
    "base": "#24273a",
    "mantle": "#1e2030",
    "crust": "#181926",
}


class TestPalette:
    def test_matches_catppuccin_macchiato(self):
        assert Palette.COLORS == MACCHIATO

    def test_accent_is_yellow(self):
        assert Palette.ACCENT == "yellow"
        assert C[Palette.ACCENT] == "#eed49f"

    def test_every_value_is_a_lowercase_hex_colour(self):
        assert all(len(v) == 7 and v.startswith("#") and v == v.lower() for v in C.values())

    def test_colours_are_unique(self):
        assert len(set(C.values())) == len(C)


class TestHelpers:
    def test_num_formats_floats_with_at_most_two_decimals(self):
        assert num(3.0) == "3"
        assert num(3.5) == "3.5"
        assert num(3.14159) == "3.14"
        assert num(7) == "7"

    def test_tidy_rounds_long_fractions_only(self):
        assert tidy('x="12.34567" y="3.5" c="#8aadf4"') == 'x="12.35" y="3.5" c="#8aadf4"'

    def test_esc_escapes_markup(self):
        assert esc('<a & "b">') == "&lt;a &amp; &quot;b&quot;&gt;"

    def test_text_width_uses_the_monospace_advance(self):
        assert text_width("abcd", 10) == pytest.approx(24)

    def test_font_stack_has_no_web_font(self):
        assert "http" not in FONT and "url(" not in FONT
        assert FONT.endswith("monospace")


class TestDoc:
    def _doc(self):
        doc = Doc(200, 100, "Title <1>", "Desc & more")
        doc.rect(10, 10, 50.123456, 20, C["base"], C["surface1"], rx=4)
        doc.text(20, 50, "hello & <world>", 16, C["text"], 700, "middle", spacing=1)
        doc.circle(30, 30, 5, C["blue"], C["surface0"])
        doc.line(0, 0, 10, 10, C["overlay0"], dash="4 2")
        return doc

    def test_render_is_well_formed_with_the_view_box(self):
        root = ET.fromstring(self._doc().render())
        assert root.tag == "{http://www.w3.org/2000/svg}svg"
        assert root.get("viewBox") == "0 0 200 100"
        assert (root.get("width"), root.get("height")) == ("200", "100")

    def test_title_and_description_are_escaped(self):
        markup = self._doc().render()
        assert "Title &lt;1&gt;" in markup
        assert "Desc &amp; more" in markup
        assert "hello &amp; &lt;world&gt;" in markup

    def test_render_is_deterministic_and_ends_with_a_newline(self):
        assert self._doc().render() == self._doc().render()
        assert self._doc().render().endswith("</svg>\n")

    def test_long_fractions_are_rounded_in_the_output(self):
        assert 'width="50.12"' in self._doc().render()

    def test_body_font_group_is_optional(self):
        assert "font-family" in Doc(10, 10, "t", "d").render()
        assert "font-family" not in Doc(10, 10, "t", "d", body_font=False).render()

    def test_defs_are_emitted_when_present(self):
        doc = Doc(10, 10, "t", "d")
        doc.defs.append('<linearGradient id="g"/>')
        assert '<defs><linearGradient id="g"/></defs>' in doc.render()


FAKE_RSVG = """#!/bin/sh
while [ $# -gt 0 ]; do
  case "$1" in
    -w) shift 2 ;;
    -o) out="$2"; shift 2 ;;
    *) src="$1"; shift ;;
  esac
done
/bin/cp "$src" "$out"
"""

RECORDING = '#!/bin/sh\necho "$@" > "{log}"\n/bin/cp "$3" "$5"\n'

FAILING_RSVG = """#!/bin/sh
echo "boom" >&2
exit 1
"""

SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"></svg>\n'


@pytest.fixture
def tool_path(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    monkeypatch.setenv("PATH", str(bin_dir))

    def install(script):
        exe = bin_dir / "rsvg-convert"
        exe.write_text(script, encoding="utf-8")
        exe.chmod(exe.stat().st_mode | stat.S_IEXEC)

    return install


class TestRenderer:
    def test_writes_the_svg_and_skips_the_png_without_rsvg(self, tool_path, tmp_path):
        target = tmp_path / "out" / "logo.svg"
        status = Renderer.write(SVG, target)
        assert target.read_text(encoding="utf-8") == SVG
        assert not target.with_suffix(".png").exists()
        assert "PNG skipped: rsvg-convert not found" in status

    def test_writes_the_pair_when_rsvg_is_installed(self, tool_path, tmp_path):
        tool_path(FAKE_RSVG)
        target = tmp_path / "logo.svg"
        status = Renderer.write(SVG, target)
        assert target.with_suffix(".png").read_text(encoding="utf-8") == SVG
        assert status == "logo.svg + logo.png"

    def test_no_png_option_writes_only_the_svg(self, tool_path, tmp_path):
        tool_path(FAKE_RSVG)
        target = tmp_path / "logo.svg"
        status = Renderer.write(SVG, target, png=False)
        assert target.exists() and not target.with_suffix(".png").exists()
        assert status == "logo.svg"

    def test_invalid_svg_changes_nothing(self, tool_path, tmp_path):
        target = tmp_path / "logo.svg"
        target.write_text("old", encoding="utf-8")
        with pytest.raises(RenderError, match="invalid SVG"):
            Renderer.write("<svg", target)
        assert target.read_text(encoding="utf-8") == "old"

    def test_renderer_failure_keeps_the_previous_pair(self, tool_path, tmp_path):
        target = tmp_path / "logo.svg"
        target.write_text("old-svg", encoding="utf-8")
        target.with_suffix(".png").write_text("old-png", encoding="utf-8")
        tool_path(FAILING_RSVG)
        with pytest.raises(RenderError, match="rsvg-convert failed: boom"):
            Renderer.write(SVG, target)
        assert target.read_text(encoding="utf-8") == "old-svg"
        assert target.with_suffix(".png").read_text(encoding="utf-8") == "old-png"

    def test_no_temporary_files_are_left_behind(self, tool_path, tmp_path):
        tool_path(FAKE_RSVG)
        Renderer.write(SVG, tmp_path / "logo.svg")
        assert sorted(p.name for p in tmp_path.iterdir() if p.is_file()) == ["logo.png", "logo.svg"]

    def test_written_files_are_world_readable(self, tool_path, tmp_path):
        tool_path(FAKE_RSVG)
        target = tmp_path / "logo.svg"
        Renderer.write(SVG, target)
        assert target.stat().st_mode & 0o777 == 0o644
        assert target.with_suffix(".png").stat().st_mode & 0o777 == 0o644

    def test_png_width_defaults_to_the_svg_width(self, tool_path, tmp_path):
        tool_path(RECORDING.format(log=tmp_path / "args"))
        Renderer.write(SVG, tmp_path / "logo.svg")
        assert (tmp_path / "args").read_text(encoding="utf-8").split()[:2] == ["-w", "64"]

    def test_explicit_png_width_wins(self, tool_path, tmp_path):
        tool_path(RECORDING.format(log=tmp_path / "args"))
        Renderer.write(SVG, tmp_path / "logo.svg", png_width=256)
        assert (tmp_path / "args").read_text(encoding="utf-8").split()[:2] == ["-w", "256"]

    def test_png_width_falls_back_when_the_svg_has_no_width(self, tool_path, tmp_path):
        tool_path(RECORDING.format(log=tmp_path / "args"))
        Renderer.write('<svg xmlns="http://www.w3.org/2000/svg"></svg>', tmp_path / "x.svg")
        assert (tmp_path / "args").read_text(encoding="utf-8").split()[:2] == ["-w", "1200"]
