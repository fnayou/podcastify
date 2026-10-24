import os
import re
import shutil
import subprocess
import tempfile
import xml.dom.minidom
from pathlib import Path
from typing import Optional


class RenderError(Exception):
    pass


class Renderer:
    """Writes an SVG and, beside it, a PNG of the same base name rendered by rsvg-convert when it is installed.

    The pair is written together: the SVG is validated, the PNG is rendered from a temporary copy, and only then
    are both files moved into place, so a failure leaves the previous pair untouched.
    """

    SKIPPED = "PNG skipped: rsvg-convert not found"

    @staticmethod
    def _width(markup: str) -> Optional[int]:
        match = re.search(r'<svg[^>]*\swidth="(\d+)"', markup)
        return int(match.group(1)) if match else None

    @staticmethod
    def _temp(directory: Path, suffix: str) -> Path:
        fd, name = tempfile.mkstemp(prefix=".art-", suffix=suffix, dir=directory)
        os.close(fd)
        # mkstemp creates 0600 files; tracked images are world-readable
        os.chmod(name, 0o644)
        return Path(name)

    @staticmethod
    def _rsvg(src: Path, dst: Path, width: int) -> bool:
        exe = shutil.which("rsvg-convert")
        if exe is None:
            return False
        result = subprocess.run([exe, "-w", str(width), str(src), "-o", str(dst)], capture_output=True, text=True)
        if result.returncode != 0:
            raise RenderError(f"rsvg-convert failed: {result.stderr.strip()}")
        return True

    @staticmethod
    def validate(markup: str, name: str) -> None:
        try:
            xml.dom.minidom.parseString(markup)
        except Exception as e:
            raise RenderError(f"{name}: invalid SVG ({e})") from e

    @classmethod
    def write(cls, markup: str, svg_path: Path, png: bool = True, png_width: Optional[int] = None) -> str:
        svg_path = Path(svg_path)
        directory = svg_path.parent
        directory.mkdir(parents=True, exist_ok=True)
        cls.validate(markup, svg_path.name)
        tmp_svg = cls._temp(directory, ".svg")
        tmp_png = cls._temp(directory, ".png")
        try:
            tmp_svg.write_text(markup, encoding="utf-8")
            made_png = False
            if png:
                made_png = cls._rsvg(tmp_svg, tmp_png, png_width or cls._width(markup) or 1200)
            if made_png:
                os.replace(tmp_png, svg_path.with_suffix(".png"))
            os.replace(tmp_svg, svg_path)
            status = svg_path.name
            if made_png:
                status += f" + {svg_path.with_suffix('.png').name}"
            elif png:
                status += f"  ({cls.SKIPPED})"
            return status
        finally:
            for tmp in (tmp_svg, tmp_png):
                if tmp.exists():
                    tmp.unlink()
