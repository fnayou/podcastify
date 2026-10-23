#!/usr/bin/env python3
"""Tests for the release tag helper in tools/release_tag.py."""

import json
import re
import runpy
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

from tools import release_tag
from tools.release_tag import CalVerTag, CommandRunner, ReleaseHelper, TagPlanner

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 10, 23)
SHA = "a" * 40


def _planner(names, today=TODAY):
    return TagPlanner(names, today)


class TestCalVerTag:
    @pytest.mark.parametrize("name", ["v2026.10.0", "v2026.1.12", "v2026.12.3-rc.1", "v2030.5.0-beta.10"])
    def test_round_trip(self, name):
        assert str(CalVerTag.parse(name)) == name

    @pytest.mark.parametrize(
        "name",
        [
            "v1.1.1",
            "1.0.1",
            "v2026.01.0",
            "v2026.13.0",
            "2026.10.0",
            "v2026.10",
            "v2026.10.01",
            "v2026.10.0-rc",
            "v2026.10.0-rc.0",
            "v2026.10.0-1",
            "v2026.10.0+meta",
            "latest",
            "",
        ],
    )
    def test_rejects_other_shapes(self, name):
        assert CalVerTag.parse(name) is None

    def test_fields(self):
        tag = CalVerTag.parse("v2026.10.4-rc.2")
        assert (tag.year, tag.month, tag.patch, tag.label, tag.number) == (2026, 10, 4, "rc", 2)
        assert tag.base == (2026, 10, 4)


class TestNextStable:
    def test_first_tag_of_all(self):
        assert str(_planner([]).next_stable()) == "v2026.10.0"

    def test_same_month_adds_one(self):
        assert str(_planner(["v2026.10.0", "v2026.10.1"]).next_stable()) == "v2026.10.2"

    def test_highest_patch_wins_regardless_of_order(self):
        assert str(_planner(["v2026.10.2", "v2026.10.0", "v2026.10.1"]).next_stable()) == "v2026.10.3"

    def test_new_month_restarts_at_zero(self):
        assert str(_planner(["v2026.9.3", "v2026.9.4"]).next_stable()) == "v2026.10.0"

    def test_same_month_of_another_year_does_not_count(self):
        assert str(_planner(["v2025.10.7"]).next_stable()) == "v2026.10.0"

    def test_year_change_december_to_january(self):
        assert str(_planner(["v2026.12.4"], date(2027, 1, 5)).next_stable()) == "v2027.1.0"

    def test_december_continues_in_december(self):
        assert str(_planner(["v2026.12.0"], date(2026, 12, 31)).next_stable()) == "v2026.12.1"

    def test_month_has_no_zero_padding(self):
        assert str(_planner([], date(2026, 3, 1)).next_stable()) == "v2026.3.0"

    def test_legacy_and_foreign_tags_are_ignored(self):
        names = ["v1.0.1", "1.0.1", "v1.1.0", "v1.1.1", "v2026.01.0", "v2026.10", "latest", "v2026.13.0"]
        assert str(_planner(names).next_stable()) == "v2026.10.0"

    def test_patch_is_ordered_numerically_not_lexically(self):
        names = [f"v2026.10.{n}" for n in range(10)]
        assert str(_planner(names).next_stable()) == "v2026.10.10"
        assert str(_planner(names + ["v2026.10.10"]).next_stable()) == "v2026.10.11"
        assert str(_planner(["v2026.10.9", "v2026.10.10"]).next_stable()) == "v2026.10.11"

    def test_rc_alone_does_not_hold_a_patch(self):
        assert str(_planner(["v2026.10.0-rc.1"]).next_stable()) == "v2026.10.0"

    def test_rc_above_the_last_stable_does_not_move_the_patch(self):
        assert str(_planner(["v2026.10.0", "v2026.10.1-rc.1", "v2026.10.1-rc.2"]).next_stable()) == "v2026.10.1"

    def test_rc_of_the_same_base_does_not_make_it_the_next_stable_patch(self):
        assert str(_planner(["v2026.10.0-rc.1"]).next_stable()) != "v2026.10.1"


class TestNextPrerelease:
    def test_first_candidate_of_the_next_stable(self):
        assert str(_planner([]).next_prerelease("rc")) == "v2026.10.0-rc.1"

    def test_candidates_are_counted_for_the_same_base(self):
        names = ["v2026.10.0-rc.1", "v2026.10.0-rc.2"]
        assert str(_planner(names).next_prerelease("rc")) == "v2026.10.0-rc.3"

    def test_candidate_number_is_numeric(self):
        names = [f"v2026.10.0-rc.{n}" for n in range(1, 10)]
        assert str(_planner(names).next_prerelease("rc")) == "v2026.10.0-rc.10"
        assert str(_planner(names + ["v2026.10.0-rc.10"]).next_prerelease("rc")) == "v2026.10.0-rc.11"

    def test_base_follows_the_last_stable(self):
        names = ["v2026.10.0", "v2026.10.0-rc.1"]
        assert str(_planner(names).next_prerelease("rc")) == "v2026.10.1-rc.1"

    def test_candidates_of_other_bases_do_not_count(self):
        names = ["v2026.9.0-rc.4", "v2026.10.1-rc.3", "v2026.10.0"]
        assert str(_planner(names).next_prerelease("rc")) == "v2026.10.1-rc.4"

    def test_labels_are_counted_separately(self):
        names = ["v2026.10.0-rc.2", "v2026.10.0-beta.5"]
        assert str(_planner(names).next_prerelease("beta")) == "v2026.10.0-beta.6"

    @pytest.mark.parametrize("label", ["", "rc.1", "1rc", "r c", "-rc"])
    def test_invalid_label_is_rejected(self, label):
        with pytest.raises(ValueError):
            _planner([]).next_prerelease(label)


class FakeRunner:
    def __init__(self, overrides=None):
        self.calls = []
        self.overrides = overrides or {}

    def __call__(self, args):
        args = list(args)
        self.calls.append(args)
        for prefix, result in self.overrides.items():
            if tuple(args[: len(prefix)]) == prefix:
                return result
        return self.default(args)

    def default(self, args):
        if args[:2] == ["git", "fetch"]:
            return _done()
        if args[:3] == ["git", "rev-parse", "--abbrev-ref"]:
            return _done("main\n")
        if args[:2] == ["git", "status"]:
            return _done("")
        if args[:2] == ["git", "rev-parse"]:
            return _done(SHA + "\n")
        if args[:2] == ["gh", "run"]:
            return _done(json.dumps([{"status": "completed", "conclusion": "success"}]))
        if args[:3] == ["git", "tag", "--list"]:
            return _done("v1.1.1\n1.0.1\nv2026.9.0\n")
        if args[:2] == ["task", "release:changelog"]:
            return _done("### Features\n- **media:** Read durations (abc1234)\n")
        if args[:3] == ["git", "tag", "-a"]:
            return _done()
        raise AssertionError(f"unexpected command: {args}")

    def ran(self, *prefix):
        return any(tuple(call[: len(prefix)]) == prefix for call in self.calls)


def _done(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


class Session:
    def __init__(self, overrides=None, answer="y", has_gh=True, dry_run=False, prerelease=None):
        self.runner = FakeRunner(overrides)
        self.lines = []
        self.prompts = []

        def confirm(prompt):
            self.prompts.append(prompt)
            return answer

        self.helper = ReleaseHelper(
            runner=self.runner,
            today=TODAY,
            has_gh=has_gh,
            confirm=confirm,
            out=self.lines.append,
            dry_run=dry_run,
            prerelease=prerelease,
        )

    @property
    def text(self):
        return "\n".join(self.lines)


class TestCreatesTheTag:
    def test_happy_path_creates_an_annotated_tag_and_prints_the_push_command(self):
        session = Session()
        assert session.helper.run() == 0
        assert ["git", "tag", "-a", "v2026.10.0", "-m", "Release v2026.10.0"] in session.runner.calls
        assert "Proposed tag: v2026.10.0" in session.text
        assert "git push origin v2026.10.0" in session.lines
        assert "### Features" in session.text

    def test_never_pushes(self):
        session = Session()
        session.helper.run()
        assert not session.runner.ran("git", "push")

    def test_fetches_main_and_tags_first(self):
        session = Session()
        session.helper.run()
        assert session.runner.calls[0] == ["git", "fetch", "--tags", "origin", "main"]

    def test_preview_uses_the_existing_task_with_the_proposed_tag(self):
        session = Session()
        session.helper.run()
        assert ["task", "release:changelog", "TAG=v2026.10.0"] in session.runner.calls

    def test_prompt_names_the_tag_and_the_commit(self):
        session = Session()
        session.helper.run()
        assert "v2026.10.0" in session.prompts[0]
        assert SHA[:7] in session.prompts[0]

    def test_confirmation_is_trimmed(self):
        session = Session(answer=" y ")
        assert session.helper.run() == 0

    @pytest.mark.parametrize("answer", ["", "n", "yes", "Y", "no"])
    def test_anything_but_y_aborts(self, answer):
        session = Session(answer=answer)
        assert session.helper.run() == 1
        assert not session.runner.ran("git", "tag", "-a")
        assert "Aborted" in session.text

    def test_prerelease_proposes_the_next_candidate(self):
        session = Session(
            {("git", "tag", "--list"): _done("v2026.10.0-rc.1\nv2026.9.0\n")},
            prerelease="rc",
        )
        assert session.helper.run() == 0
        assert ["git", "tag", "-a", "v2026.10.0-rc.2", "-m", "Release v2026.10.0-rc.2"] in session.runner.calls
        assert ["task", "release:changelog", "TAG=v2026.10.0-rc.2"] in session.runner.calls

    def test_invalid_prerelease_label_is_refused(self):
        session = Session(prerelease="rc.1")
        assert session.helper.run() == 1
        assert "invalid prerelease label" in session.text
        assert not session.runner.ran("git", "tag", "-a")

    def test_git_tag_failure_is_reported(self):
        session = Session({("git", "tag", "-a"): _done(returncode=128, stderr="tag exists")})
        assert session.helper.run() == 1
        assert "git tag failed: tag exists" in session.text
        assert "git push origin" not in session.text


class TestRefusals:
    def _refused(self, session, expected):
        assert session.helper.run() == 1
        assert expected in session.text
        assert not session.runner.ran("git", "tag", "-a")
        assert not session.runner.ran("task")
        assert not session.prompts

    def test_not_on_main(self):
        self._refused(Session({("git", "rev-parse", "--abbrev-ref"): _done("feat/x\n")}), "not on main (on feat/x)")

    def test_detached_head(self):
        self._refused(Session({("git", "rev-parse", "--abbrev-ref"): _done("")}), "(on unknown)")

    def test_dirty_tree(self):
        self._refused(Session({("git", "status"): _done(" M README.md\n")}), "working tree is not clean")

    def test_head_differs_from_origin_main(self):
        self._refused(Session({("git", "rev-parse", "origin/main"): _done("b" * 40 + "\n")}), "HEAD is not origin/main")

    def test_fetch_failure(self):
        self._refused(
            Session({("git", "fetch"): _done(returncode=1, stderr="no network")}), "git fetch failed: no network"
        )

    def test_ci_red(self):
        runs = json.dumps([{"status": "completed", "conclusion": "failure"}])
        self._refused(Session({("gh", "run"): _done(runs)}), "CI is not green")

    def test_ci_running(self):
        runs = json.dumps([{"status": "in_progress", "conclusion": ""}])
        self._refused(Session({("gh", "run"): _done(runs)}), "CI is still running")

    def test_no_ci_run(self):
        self._refused(Session({("gh", "run"): _done("[]")}), "no CI run found")

    def test_gh_failure(self):
        self._refused(Session({("gh", "run"): _done(returncode=1, stderr="not logged in")}), "not logged in")

    def test_gh_unreadable_output(self):
        self._refused(Session({("gh", "run"): _done("nope")}), "unreadable CI run data")

    def test_preview_failure(self):
        session = Session({("task", "release:changelog"): _done(returncode=1, stderr="docker missing")})
        assert session.helper.run() == 1
        assert "preview failed: docker missing" in session.text
        assert not session.runner.ran("git", "tag", "-a")

    def test_every_problem_is_listed(self):
        session = Session(
            {
                ("git", "rev-parse", "--abbrev-ref"): _done("feat/x\n"),
                ("git", "status"): _done(" M a\n"),
            }
        )
        assert session.helper.run() == 1
        assert "not on main" in session.text
        assert "not clean" in session.text

    def test_without_gh_the_ci_check_is_skipped_with_a_note(self):
        session = Session(has_gh=False)
        assert session.helper.run() == 0
        assert not session.runner.ran("gh")
        assert "gh not found: CI status not checked" in session.lines


class TestDryRun:
    def test_prints_the_plan_and_creates_nothing(self):
        session = Session(dry_run=True)
        assert session.helper.run() == 0
        assert "Proposed tag: v2026.10.0" in session.text
        assert "Dry run: no tag created." in session.lines
        assert not session.runner.ran("git", "tag", "-a")
        assert not session.prompts

    def test_reports_refusals_without_enforcing_them(self):
        session = Session({("git", "rev-parse", "--abbrev-ref"): _done("feat/x\n")}, dry_run=True)
        assert session.helper.run() == 0
        assert "Would refuse: not on main (on feat/x)" in session.text
        assert "Proposed tag: v2026.10.0" in session.text

    def test_invalid_label_still_fails(self):
        session = Session(dry_run=True, prerelease="1x")
        assert session.helper.run() == 1


class TestCommandRunner:
    def test_captures_output(self):
        result = CommandRunner()([sys.executable, "-c", "print('hi')"])
        assert (result.returncode, result.stdout) == (0, "hi\n")

    def test_missing_program_is_a_failed_result(self):
        result = CommandRunner()(["definitely-not-a-program-xyz"])
        assert result.returncode == 127
        assert result.stderr


class TestMain:
    @pytest.fixture
    def wired(self, monkeypatch):
        runner = FakeRunner()
        monkeypatch.setattr(release_tag, "CommandRunner", lambda: runner)
        monkeypatch.setattr(release_tag.shutil, "which", lambda name: "/usr/bin/gh")
        monkeypatch.setattr("builtins.input", lambda prompt: "y")

        class FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 10, 23, 12, 0, tzinfo=tz)

        monkeypatch.setattr(release_tag, "datetime", FixedDatetime)
        return runner

    def test_creates_the_tag(self, wired, capsys):
        assert release_tag.main([]) == 0
        assert "Proposed tag: v2026.10.0" in capsys.readouterr().out
        assert ["git", "tag", "-a", "v2026.10.0", "-m", "Release v2026.10.0"] in wired.calls

    def test_dry_run_and_prerelease_flags(self, wired, capsys):
        assert release_tag.main(["--dry-run", "--prerelease", "rc"]) == 0
        out = capsys.readouterr().out
        assert "-rc.1" in out
        assert not wired.ran("git", "tag", "-a")

    def test_running_the_file_as_a_script_parses_arguments(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["release_tag.py", "--help"])
        with pytest.raises(SystemExit) as exit_info:
            runpy.run_path(str(ROOT / "tools" / "release_tag.py"), run_name="__main__")
        assert exit_info.value.code == 0


def _workflow_pattern():
    text = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    match = re.search(r"PATTERN='(\^v20[^']*\$)'", text)
    assert match, "validate-tag pattern not found in release.yml"
    return re.compile(match.group(1))


class TestWorkflowAgreement:
    def test_the_workflow_pattern_was_found(self):
        pattern = _workflow_pattern()
        assert pattern.match("v2026.10.0")
        assert not pattern.match("v1.1.1")

    def test_every_tag_the_tool_can_make_passes_validate_tag(self):
        pattern = _workflow_pattern()
        for year in (2026, 2027, 2030):
            for month in range(1, 13):
                for names in ([], [f"v{year}.{month}.9"], [f"v{year}.{month}.9", f"v{year}.{month}.10"]):
                    planner = TagPlanner(names, date(year, month, 15))
                    assert pattern.match(str(planner.next_stable()))
                    assert pattern.match(str(planner.next_prerelease("rc")))
                    assert pattern.match(str(planner.next_prerelease("beta")))

    @pytest.mark.parametrize(
        "name",
        ["v2026.10.0", "v2026.10.1", "v2026.11.0", "v2026.10.0-rc.1", "v2026.1.0", "v2026.12.10-rc.12"],
    )
    def test_accepted_by_both(self, name):
        assert CalVerTag.parse(name) is not None
        assert _workflow_pattern().match(name)

    @pytest.mark.parametrize("name", ["v1.1.1", "v2026.01.0", "2026.10.0", "v2026.13.0", "v2026.10.00"])
    def test_rejected_by_both(self, name):
        assert CalVerTag.parse(name) is None
        assert not _workflow_pattern().match(name)

    def test_the_tool_never_accepts_what_the_workflow_rejects(self):
        pattern = _workflow_pattern()
        candidates = [
            f"v{y}.{m}.{p}{s}"
            for y in (1999, 2026, 2100)
            for m in (0, 1, 9, 12, 13)
            for p in ("0", "7", "07", "10")
            for s in ("", "-rc.1", "-rc.0", "-rc", "-x_y.1", "-1.1")
        ]
        for name in candidates:
            if CalVerTag.parse(name):
                assert pattern.match(name), name
