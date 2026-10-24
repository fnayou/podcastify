#!/usr/bin/env python3
"""Render the configuration field tables from the pydantic models into a Markdown page.

Run from the repository root with PYTHONPATH=. (`task docs:reference` does).
"""

import argparse
import difflib
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple, Union, get_args, get_origin

from podcastify.parser import EpisodeModel, PodcastChannelModel

DEFAULT_PAGE = Path(__file__).resolve().parent.parent / "docs" / "configuration.md"


class MarkersError(Exception):
    pass


class ConfigReference:
    BEGIN = "<!-- BEGIN GENERATED: fields -->"
    END = "<!-- END GENERATED -->"
    HEADER = "| Key | Type | Required | Default | Description |\n|---|---|---|---|---|"
    # The models still accept these keys; the schema has no way to say they are legacy.
    DEPRECATED = {"author": "author-name"}
    SCALARS = {str: "string", int: "integer", bool: "boolean", datetime: "date-time", date: "date"}

    def __init__(self, page: Path):
        self.page = page

    @classmethod
    def type_name(cls, annotation: Any) -> str:
        origin = get_origin(annotation)
        if origin is Union:
            names = [cls.type_name(arg) for arg in get_args(annotation) if arg is not type(None)]
            return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} or {names[-1]}"
        if origin is list:
            (item,) = get_args(annotation)
            return "list" if item is Any else f"list of {cls.type_name(item)}"
        if origin is dict:
            return "mapping"
        if annotation in cls.SCALARS:
            return cls.SCALARS[annotation]
        if hasattr(annotation, "model_fields"):
            return annotation.__name__.removesuffix("Model").lower()
        raise TypeError(f"no documented type name for {annotation!r}")

    @staticmethod
    def default_text(field: Any) -> str:
        if field.is_required() or field.default is None:
            return "-"
        if isinstance(field.default, bool):
            return f"`{str(field.default).lower()}`"
        return f"`{field.default}`"

    @classmethod
    def row(cls, name: str, field: Any) -> str:
        key = field.alias or name
        description = field.description.replace("|", "\\|")
        if key in cls.DEPRECATED:
            description = f"**Deprecated**, use `{cls.DEPRECATED[key]}`. {description}"
        required = "Yes" if field.is_required() else "No"
        cells = [f"`{key}`", cls.type_name(field.annotation), required, cls.default_text(field), description]
        return f"| {' | '.join(cells)} |"

    def table(self, model: Any) -> str:
        rows: List[str] = [self.row(name, field) for name, field in model.model_fields.items()]
        return "\n".join([self.HEADER, *rows])

    def render(self) -> str:
        return (
            f"### Channel Fields\n\n{self.table(PodcastChannelModel)}\n\n"
            f"### Episode Fields\n\n{self.table(EpisodeModel)}"
        )

    def splice(self, text: str) -> str:
        if text.count(self.BEGIN) != 1 or text.count(self.END) != 1 or text.index(self.BEGIN) > text.index(self.END):
            raise MarkersError(f"{self.page} must contain '{self.BEGIN}' then '{self.END}', each exactly once")
        head, rest = text.split(self.BEGIN)
        tail = rest.split(self.END)[1]
        return f"{head}{self.BEGIN}\n\n{self.render()}\n\n{self.END}{tail}"

    def _current_and_expected(self) -> Tuple[str, str]:
        current = self.page.read_text(encoding="utf-8")
        return current, self.splice(current)

    def is_current(self) -> bool:
        current, expected = self._current_and_expected()
        return current == expected

    def diff(self) -> str:
        current, expected = self._current_and_expected()
        lines = difflib.unified_diff(
            current.splitlines(), expected.splitlines(), str(self.page), "generated", lineterm=""
        )
        return "\n".join(lines)

    def write(self) -> bool:
        current, expected = self._current_and_expected()
        if current == expected:
            return False
        self.page.write_text(expected, encoding="utf-8")
        return True


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Render the configuration reference from the models.")
    parser.add_argument("--page", type=Path, default=DEFAULT_PAGE, help="Markdown page holding the generated region")
    parser.add_argument("--check", action="store_true", help="change nothing; exit 1 when the region is stale")
    args = parser.parse_args(argv)
    reference = ConfigReference(args.page)
    try:
        if args.check:
            if reference.is_current():
                return 0
            print(f"{args.page} is stale; run `task docs:reference`.\n{reference.diff()}", file=sys.stderr)
            return 1
        print(f"{'Updated' if reference.write() else 'Already current:'} {args.page}")
        return 0
    except (MarkersError, OSError) as e:
        print(f"config_reference: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
