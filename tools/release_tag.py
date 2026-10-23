#!/usr/bin/env python3
"""Compute and create the next CalVer release tag (vYYYY.M.PATCH). Never pushes."""

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Callable, List, Optional, Sequence

TAG_PATTERN = re.compile(r"^v(20[0-9]{2})\.([1-9]|1[0-2])\.(0|[1-9][0-9]*)(?:-([A-Za-z][0-9A-Za-z]*)\.([1-9][0-9]*))?$")
LABEL_PATTERN = re.compile(r"^[A-Za-z][0-9A-Za-z]*$")


@dataclass(frozen=True)
class CalVerTag:
    year: int
    month: int
    patch: int
    label: Optional[str] = None
    number: Optional[int] = None

    @classmethod
    def parse(cls, name: str) -> Optional["CalVerTag"]:
        match = TAG_PATTERN.match(name)
        if not match:
            return None
        year, month, patch, label, number = match.groups()
        return cls(int(year), int(month), int(patch), label, int(number) if number else None)

    @property
    def base(self) -> tuple:
        return (self.year, self.month, self.patch)

    def __str__(self) -> str:
        text = f"v{self.year}.{self.month}.{self.patch}"
        return f"{text}-{self.label}.{self.number}" if self.label else text


class TagPlanner:
    def __init__(self, names: Sequence[str], today: date):
        self.today = today
        self.tags = [tag for tag in (CalVerTag.parse(name) for name in names) if tag]

    def next_stable(self) -> CalVerTag:
        patches = [
            tag.patch
            for tag in self.tags
            if tag.label is None and (tag.year, tag.month) == (self.today.year, self.today.month)
        ]
        patch = max(patches) + 1 if patches else 0
        return CalVerTag(self.today.year, self.today.month, patch)

    def next_prerelease(self, label: str) -> CalVerTag:
        if not LABEL_PATTERN.match(label):
            raise ValueError(f"invalid prerelease label: {label!r}")
        base = self.next_stable()
        numbers = [tag.number for tag in self.tags if tag.base == base.base and tag.label == label]
        return CalVerTag(base.year, base.month, base.patch, label, max(numbers) + 1 if numbers else 1)


class CommandRunner:
    def __call__(self, args: Sequence[str]) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(list(args), capture_output=True, text=True, check=False)
        except FileNotFoundError as e:
            return subprocess.CompletedProcess(list(args), 127, "", str(e))


class ReleaseHelper:
    BRANCH = "main"
    WORKFLOW = "ci.yml"

    def __init__(
        self,
        runner: Callable[[Sequence[str]], subprocess.CompletedProcess],
        today: date,
        has_gh: bool,
        confirm: Callable[[str], str],
        out: Callable[[str], None],
        dry_run: bool = False,
        prerelease: Optional[str] = None,
    ):
        self.runner = runner
        self.today = today
        self.has_gh = has_gh
        self.confirm = confirm
        self.out = out
        self.dry_run = dry_run
        self.prerelease = prerelease

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return self.runner(["git", *args])

    def _head(self, ref: str) -> str:
        return self._git("rev-parse", ref).stdout.strip()

    def _ci_problem(self, sha: str) -> Optional[str]:
        result = self.runner(
            [
                "gh",
                "run",
                "list",
                "--workflow",
                self.WORKFLOW,
                "--commit",
                sha,
                "--limit",
                "1",
                "--json",
                "status,conclusion",
            ]
        )
        if result.returncode != 0:
            return f"gh could not read the CI runs: {result.stderr.strip()}"
        try:
            runs = json.loads(result.stdout)
        except json.JSONDecodeError:
            return "gh returned unreadable CI run data"
        if not runs:
            return f"no CI run found for {sha[:7]}"
        if runs[0].get("status") != "completed":
            return f"CI is still running for {sha[:7]}"
        if runs[0].get("conclusion") != "success":
            return f"CI is not green for {sha[:7]} ({runs[0].get('conclusion')})"
        return None

    def problems(self) -> List[str]:
        found: List[str] = []
        fetch = self._git("fetch", "--tags", "origin", self.BRANCH)
        if fetch.returncode != 0:
            found.append(f"git fetch failed: {fetch.stderr.strip()}")
        branch = self._git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        if branch != self.BRANCH:
            found.append(f"not on {self.BRANCH} (on {branch or 'unknown'})")
        if self._git("status", "--porcelain").stdout.strip():
            found.append("the working tree is not clean")
        head = self._head("HEAD")
        if head != self._head(f"origin/{self.BRANCH}"):
            found.append(f"HEAD is not origin/{self.BRANCH}")
        if self.has_gh:
            problem = self._ci_problem(head)
            if problem:
                found.append(problem)
        else:
            self.out("gh not found: CI status not checked")
        return found

    def next_tag(self) -> CalVerTag:
        names = self._git("tag", "--list").stdout.split()
        planner = TagPlanner(names, self.today)
        return planner.next_prerelease(self.prerelease) if self.prerelease else planner.next_stable()

    def run(self) -> int:
        found = self.problems()
        for line in found:
            self.out(f"{'Would refuse' if self.dry_run else 'Refusing'}: {line}")
        if found and not self.dry_run:
            return 1
        try:
            tag = str(self.next_tag())
        except ValueError as e:
            self.out(f"Refusing: {e}")
            return 1
        self.out(f"Proposed tag: {tag}")
        preview = self.runner(["task", "release:changelog", f"TAG={tag}"])
        if preview.returncode != 0:
            self.out(f"Refusing: the release notes preview failed: {preview.stderr.strip()}")
            return 1
        self.out(preview.stdout.rstrip())
        if self.dry_run:
            self.out("Dry run: no tag created.")
            return 0
        if self.confirm(f"Create annotated tag {tag} on {self._head('HEAD')[:7]}? [y/N] ").strip() != "y":
            self.out("Aborted: no tag created.")
            return 1
        created = self._git("tag", "-a", tag, "-m", f"Release {tag}")
        if created.returncode != 0:
            self.out(f"Refusing: git tag failed: {created.stderr.strip()}")
            return 1
        self.out(f"Created tag {tag} locally. Nothing was pushed. To release, run:")
        self.out(f"git push origin {tag}")
        return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Propose and create the next CalVer release tag.")
    parser.add_argument(
        "--prerelease", metavar="LABEL", help="create a prerelease tag, for example rc (rc.N is counted)"
    )
    parser.add_argument("--dry-run", action="store_true", help="print the plan and create nothing")
    args = parser.parse_args(argv)
    helper = ReleaseHelper(
        runner=CommandRunner(),
        today=datetime.now(timezone.utc).date(),
        has_gh=shutil.which("gh") is not None,
        confirm=input,
        out=print,
        dry_run=args.dry_run,
        prerelease=args.prerelease or None,
    )
    return helper.run()


if __name__ == "__main__":
    sys.exit(main())
