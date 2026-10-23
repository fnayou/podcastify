# 0007 - CalVer tags and release policy

## Status

Accepted on 2026-10-23, from the owner decisions of the design session in
issue #48 (recorded by issue #100). Implemented: the Docker tags and the
provenance (#101), the git-cliff release notes (#102), the tag helper
`task release:tag` (#103) and the Docker Hub overview sync (#105).

## Context

A release is a git tag that matches `v*.*.*`. The `Release` workflow
(`.github/workflows/release.yml`) then builds the image, scans it, pushes it to
Docker Hub and creates the GitHub Release. Today:

- Tags are `vX.Y.Z` (the last ones are `v1.0.1`, `v1.1.0` and `v1.1.1`), made by
  hand. A stray lightweight tag `1.0.1` sits beside `v1.0.1`.
- Docker Hub gets the same image under several names: the tag as written
  (`v1.1.1`), the version (`1.1.1`), a floating `X.Y` (`1.1`) and `latest`.
- The BuildKit SBOM and the BuildKit provenance are on, and a GitHub artifact
  attestation is created as well, so an image has two provenance records. Only
  the GitHub one is signed.
- The GitHub Release body is cut from `CHANGELOG.md` with an `awk` step that
  looks for the section titled with the tag. When the section is missing, as for
  `v1.1.0`, the body is a fixed fallback sentence.
- The Docker Hub overview text is not updated by any workflow.

The audit of 2026-10 (`docs/audit/2026-10/cicd.md`, CICD-12 to CICD-16) listed
these problems and asked for a version scheme that does not break the tag
trigger or the tag generation of the Docker metadata action, which needs valid
SemVer.

## Decision

### Git tag format

Git tags are `vYYYY.M.PATCH`: the year, the month without zero padding, and a
`PATCH` counter that starts at 0 and resets each month. Examples: `v2026.10.0`,
`v2026.10.1`, `v2026.11.0`. A prerelease is `vYYYY.M.PATCH-rc.N`. This is valid
SemVer, so the `v*.*.*` trigger and the `semver` patterns of the metadata action
keep working.

Rejected:

- A running counter per year (for example `v2026.7`): the tag does not say when
  the release was cut.
- `vYYYY.MM.DD`: allows one release per day.
- A zero-padded month (`v2026.03.0`): not valid SemVer, because a number may not
  start with 0, and the metadata action would produce no tag.

### Who creates the tag

A local helper, `task release:tag`, computes and proposes the next tag, and the
owner pushes it. A workflow does not create the tag, because a tag pushed with
`GITHUB_TOKEN` does not start other workflows, so the release workflow would
never run.

### Registry and Docker tags

Docker Hub stays the only registry. A GitHub Container Registry mirror is
possible later and is not part of this decision.

- A stable release gets the tags `YYYY.M.PATCH` and `latest`.
- A prerelease gets its exact tag only (`YYYY.M.PATCH-rc.N`) and never moves
  `latest`.
- No `v`-prefixed Docker tag. It names the same image a second time.
- No floating `YYYY.M` tag. With CalVer it would be a month channel that users
  cannot pin to in a meaningful way.

### Provenance

Keep the BuildKit SBOM and the signed GitHub artifact attestation. Turn the
BuildKit provenance off, so there is one provenance record per image and it can
be verified with `gh attestation verify`. Rejected: both records (two records,
one unsigned), and the BuildKit record alone (it is not signed).

### Release notes

The notes are the output of git-cliff, used as the body of the GitHub Release.
They replace the `awk` step over `CHANGELOG.md`. There is no release commit,
because `main` is protected and changes reach it only through pull requests.

- Commits are read as Conventional Commits. The hidden types are `ci`, `docs`,
  `chore`, `test`, `style` and `refactor`, except when the commit is breaking.
  The other types (`feat`, `fix`, `perf`, `build`, `revert`) are shown.
- Dependency bumps are folded into one "Dependencies" line.
- Breaking changes get their own prominent section.
- The range of the first release is `f1e964de..<first CalVer tag>`. Older
  history is not used.
- The generator configuration is a `cliff.toml` at the repository root.

Rejected: keeping the `awk` extraction (it fails silently on a missing section),
and a release commit that edits `CHANGELOG.md` (`main` is protected).

`CHANGELOG.md` is frozen history. It keeps its text up to `v1.1.1` with the
missing `v1.1.0` section backfilled (issue #104) and is not edited any more.

### Old tags

The tags `v1.0.1`, `v1.1.0`, `v1.1.1` and the stray `1.0.1` are not touched
until the first CalVer release is published. Then all of them are deleted (git
tags, locally and on origin). What happens to their GitHub Releases and Docker
Hub tags is decided at that moment.

### Docker Hub description

The Docker Hub overview is synced from `README.md` when a release is published.
The sync is non-blocking: if it fails, the release still succeeds. Relative
links in `README.md` are made absolute so they work on Docker Hub.

## Consequences

- A tag says when a release was cut, not whether it is breaking. The release
  notes show breaking changes in their own section.
- Users pin an exact version (`2026.10.0`) or follow `latest`. There is no
  floating minor tag any more. Tags already published on Docker Hub are not
  changed by this decision.
- The first release of a month has `PATCH` 0, even if the last release of the
  month before had a higher number. The helper does the counting.
- Tags are pushed from the owner's machine. A wrong tag is corrected by hand.
- Release notes depend on commit subjects, so the `commits` check on pull
  requests (Conventional Commits) now also protects the release notes.
- Until #101, #102, #103 and #105 are merged the old behaviour stays: `v`-prefixed
  Docker tags, the floating `X.Y` tag, two provenance records and notes read
  from `CHANGELOG.md`.

## References

- `.github/workflows/release.yml`
- `cliff.toml` (planned, issue #102)
- `Taskfile.yml` and `tasks/` for `release:tag` (planned, issue #103)
- `CHANGELOG.md` and `README.md`
- `docs/audit/2026-10/cicd.md` (CICD-12 to CICD-16)
- Issues #48 (design session), #100 (this ADR), #101 (Docker tags and
  provenance), #102 (git-cliff notes), #103 (`task release:tag`), #104
  (CHANGELOG freeze), #105 (Docker Hub description sync)
