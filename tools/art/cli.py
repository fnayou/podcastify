import fnmatch
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

from tools.art.banner import Banner
from tools.art.facts import Facts, FactsReader
from tools.art.logo import Favicon, Logo
from tools.art.render import Renderer
from tools.art.social import Social

ROOT = Path(__file__).resolve().parents[2]
IMAGES = "website/assets/images"
FIX = "task art:build"

# A change to any of these can alter an image, so only then is a stale SVG worth a reminder.
INPUT_GLOBS = (
    "tools/art/*",
    "website/assets/images/*",
    "podcastify/*.py",
    "docker/podcastify/Dockerfile",
    ".env.example",
    ".github/workflows/release.yml",
    "AGENTS.md",
)


@dataclass(frozen=True)
class Output:
    name: str
    base: str
    committed: bool
    make: Callable[[Facts], str]


class ArtCli:
    OUTPUTS: Tuple[Output, ...] = (
        Output("logo", "podcastify-logo", True, lambda facts: Logo.svg()),
        Output("favicon", "favicon", True, lambda facts: Favicon.svg()),
        Output("banner", "podcastify-readme-banner", True, Banner.svg),
        Output("social", "podcastify-social-preview", True, Social.svg),
    )

    def __init__(self, root: Path = ROOT, out=print, err=None):
        self.root = Path(root)
        self.images = self.root / IMAGES
        self.out = out
        self.err = err or (lambda message: print(message, file=sys.stderr))

    def _names(self) -> List[str]:
        return [o.name for o in self.OUTPUTS]

    def _select(self, names: Sequence[str]) -> List[Output]:
        known = {o.name: o for o in self.OUTPUTS}
        unknown = [n for n in names if n not in known]
        if unknown:
            raise ValueError(f"unknown image '{unknown[0]}' (one of: {', '.join(self._names())})")
        return [known[n] for n in names]

    def build(self, names: Sequence[str], png: bool = True) -> int:
        facts = FactsReader(self.root).read()
        for output in self._select(names):
            status = Renderer.write(output.make(facts), self.images / f"{output.base}.svg", png=png)
            self.out(f"wrote {status}")
        return 0

    def stale(self) -> List[str]:
        facts = FactsReader(self.root).read()
        found = []
        for output in self.OUTPUTS:
            if not output.committed:
                continue
            path = self.images / f"{output.base}.svg"
            if not path.exists() or path.read_text(encoding="utf-8") != output.make(facts):
                found.append(path.relative_to(self.root).as_posix())
        return found

    def check(self) -> int:
        found = self.stale()
        for path in found:
            self.err(f"stale: {path}")
        if found:
            self.err(f"Regenerate with: {FIX}")
        return 1 if found else 0

    def _changed_files(self, args: Sequence[str]) -> List[str]:
        if args[:1] == ["--staged"]:
            command = ["git", "diff", "--cached", "--name-only"]
        elif args[:1] == ["--working"]:
            command = ["git", "diff", "HEAD", "--name-only"]
        elif len(args) == 2 and args[0] == "--range":
            span = args[1] if "..." in args[1] else args[1].replace("..", "...")
            command = ["git", "diff", "--name-only", span]
        else:
            raise ValueError("usage: remind [--staged | --working | --range A..B]")
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True, check=True)
        return [line for line in result.stdout.splitlines() if line]

    def remind(self, args: Sequence[str]) -> int:
        """Print a reminder when an art input changed and a committed SVG is stale. Read-only, never fails."""
        try:
            files = self._changed_files(args or ["--working"])
            if not any(fnmatch.fnmatch(f, g) for f in files for g in INPUT_GLOBS):
                return 0
            found = self.stale()
            if not found:
                return 0
            self.out(f"MANUAL STEP: the generated art is out of date ({', '.join(Path(p).name for p in found)})")
            self.out(f"  {FIX}")
            self.out(f"  git add {IMAGES}")
            self.out("(This reminder changes nothing. The art freshness test fails until the SVGs are current.)")
        except Exception:
            # a reminder must never block the commit it is about
            pass
        return 0

    def parse_build(self, args: Sequence[str]) -> Tuple[List[str], bool]:
        names = self._names()
        png = True
        i = 0
        while i < len(args):
            if args[i] == "--no-png":
                png = False
            elif args[i] == "--only" and i + 1 < len(args):
                i += 1
                names = args[i].split(",")
            else:
                raise ValueError(f"unknown option '{args[i]}'")
            i += 1
        return names, png

    def run(self, argv: Sequence[str]) -> int:
        if not argv:
            self.err("usage: python3 -m tools.art build [--only NAME[,NAME]] [--no-png] | logo | check | remind")
            return 2
        command, rest = argv[0], list(argv[1:])
        try:
            if command == "build":
                names, png = self.parse_build(rest)
                return self.build(names, png)
            if command == "logo":
                return self.build(["logo", "favicon"], png=True)
            if command == "check":
                return self.check()
            if command == "remind":
                return self.remind(rest)
        except Exception as e:
            self.err(f"art: {e}")
            return 1
        self.err(f"art: unknown command '{command}'")
        return 2


def main(argv: Optional[Sequence[str]] = None) -> int:
    return ArtCli().run(sys.argv[1:] if argv is None else argv)
