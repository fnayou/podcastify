import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple


class FactsError(Exception):
    pass


@dataclass(frozen=True)
class Module:
    name: str
    classes: Tuple[str, ...]
    role: str


@dataclass(frozen=True)
class Facts:
    name: str
    image: str
    pitch: str
    media_types: Tuple[str, ...]
    modules: Tuple[Module, ...]
    settings: Tuple[Tuple[str, str], ...]
    port: int
    base_image: str
    caddy_image: str
    podcasts_root: str
    public_root: str
    cache_root: str
    entrypoint: Tuple[str, ...]
    decisions: int

    @property
    def pitch_lines(self) -> Tuple[str, ...]:
        head, separator, tail = self.pitch.partition(": ")
        if not separator:
            return (self.pitch,)
        return (head, tail[:1].upper() + tail[1:])

    @property
    def run_hint(self) -> Tuple[str, ...]:
        return (
            f"docker run -d -p {self.port}:{self.port} \\",
            f"  -v ./podcasts:{self.podcasts_root} \\",
            f"  -v ./public:{self.public_root} \\",
            f"  {self.image}",
        )


class FactsReader:
    """Reads what the images show from files of the working tree, never from git, so a run is reproducible."""

    NOT_SETTINGS = {"HOST_PORT"}

    def __init__(self, root: Path):
        self.root = Path(root)

    def _text(self, relative: str) -> str:
        path = self.root / relative
        if not path.is_file():
            raise FactsError(f"{relative} not found")
        return path.read_text(encoding="utf-8")

    def _match(self, relative: str, pattern: str, text: str) -> str:
        found = re.search(pattern, text, re.MULTILINE)
        if not found:
            raise FactsError(f"{relative}: no match for {pattern}")
        return found.group(1)

    def _release(self) -> Tuple[str, str]:
        relative = ".github/workflows/release.yml"
        text = self._text(relative)
        image = self._match(relative, r"^  IMAGE_NAME: (\S+)", text)
        pitch = self._match(relative, r'^  IMAGE_DESCRIPTION: "(.*)"', text)
        return image, pitch

    def _media_types(self) -> Tuple[str, ...]:
        tree = ast.parse(self._text("podcastify/config.py"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "Config":
                for stmt in node.body:
                    targets = [t.id for t in getattr(stmt, "targets", []) if isinstance(t, ast.Name)]
                    if "MEDIA_TYPES" in targets and isinstance(stmt.value, ast.Dict):
                        return tuple(sorted(ast.literal_eval(key) for key in stmt.value.keys))
        raise FactsError("podcastify/config.py: Config.MEDIA_TYPES not found")

    def _roles(self) -> Dict[str, str]:
        roles: Dict[str, str] = {}
        row = re.compile(r"^\|[^|]+\|\s*`(\w+)\.py`\s*\|\s*([^|]+?)\s*\|\s*$")
        for line in self._text("AGENTS.md").splitlines():
            found = row.match(line)
            if found:
                roles[found.group(1)] = found.group(2)
        return roles

    def _modules(self) -> Tuple[Module, ...]:
        roles = self._roles()
        package = self.root / "podcastify"
        modules = []
        for path in sorted(package.glob("*.py")):
            if path.name == "__init__.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            classes = tuple(n.name for n in tree.body if isinstance(n, ast.ClassDef) and not n.name.startswith("_"))
            doc = (ast.get_docstring(tree) or "").splitlines()
            modules.append(Module(path.stem, classes, roles.get(path.stem) or (doc[0] if doc else "")))
        return tuple(modules)

    def _settings(self) -> Tuple[Tuple[str, str], ...]:
        pairs = {}
        for line in self._text(".env.example").splitlines():
            found = re.match(r"^([A-Z][A-Z0-9_]*)=(.*)$", line)
            if found and found.group(1) not in self.NOT_SETTINGS:
                pairs[found.group(1)] = found.group(2)
        return tuple(sorted(pairs.items()))

    def _container(self) -> Dict[str, object]:
        relative = "docker/podcastify/Dockerfile"
        text = self._text(relative)
        entrypoint = self._match(relative, r"^ENTRYPOINT (\[.*\])", text)
        return {
            "port": int(self._match(relative, r"^EXPOSE (\d+)", text)),
            "base_image": self._match(relative, r"^FROM (python:\S+)", text),
            "caddy_image": self._match(relative, r"^FROM (caddy:\S+)", text),
            "podcasts_root": self._match(relative, r"PODCASTS_ROOT=(\S+)", text),
            "public_root": self._match(relative, r"PUBLIC_ROOT=(\S+)", text),
            "cache_root": self._match(relative, r"CACHE_ROOT=(\S+)", text),
            "entrypoint": tuple(json.loads(entrypoint)),
        }

    def _decisions(self) -> int:
        return len(list((self.root / "docs" / "adr").glob("[0-9][0-9][0-9][0-9]-*.md")))

    def read(self) -> Facts:
        image, pitch = self._release()
        return Facts(
            name=image.split("/")[-1],
            image=image,
            pitch=pitch,
            media_types=self._media_types(),
            modules=self._modules(),
            settings=self._settings(),
            decisions=self._decisions(),
            **self._container(),
        )
