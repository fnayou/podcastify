# CICD audit: Podcastify

Scope: `.github/workflows/{ci,commits,release}.yml`, `Taskfile.yml`, `tasks/*.yml`, `.pre-commit-config.yaml`, `requirements*.txt`, `CHANGELOG.md`, `docs/contributing.md`. Supporting reads: `docker/podcastify/Dockerfile`, `docker-compose.yml`, git tags.

Branch protection settings on GitHub were not checked: that needs network access. The claims below about protection come from the documentation only.

### CICD-01 Actions pinned by mutable tags, including a recently hijacked one
- severity: high
- evidence: `ci.yml:141` `uses: aquasecurity/trivy-action@v0.36.0`; `release.yml:119`, `release.yml:130` same; every other step uses a major tag, for example `ci.yml:21` `actions/checkout@v4`, `release.yml:187` `softprops/action-gh-release@v2`, `ci.yml:64` `driver-opts: image=moby/buildkit:buildx-stable-1`
- problem: Tags are mutable. On 2026-03-19, an attacker force-pushed 76 of 77 `aquasecurity/trivy-action` tags to malicious commits (GHSA-69fq-xp46-6x23, CVE-2026-33634). The release `docker` job holds `DOCKERHUB_TOKEN`, `id-token: write` and `attestations: write`. A hijacked tag in that job can push a backdoored `latest` to Docker Hub. Several majors are also stale: `docker/build-push-action` is at v7, `actions/attest-build-provenance` is at v4, and Node 20 deprecation warnings hit the old docker/* majors.
- fix: Pin every third-party action to a full commit SHA with a `# vX.Y.Z` comment. Let Dependabot bump them (CICD-06). Bump to current majors in the same pass. Drop the `driver-opts` line, because the buildx default is fine.
- effort: S
- depends-on: none

### CICD-02 Token permissions are not least privilege
- severity: medium
- evidence: no top-level `permissions:` in `ci.yml`, `release.yml`, or `commits.yml` (its job-level block exists at `commits.yml:11-12`). The `test` jobs (`ci.yml:13`, `release.yml:12`) have no block at all. `ci.yml:47-52` grants `id-token: write` and `attestations: write`, but `ci.yml` has no attestation or OIDC step.
- problem: Jobs without a block inherit the repository default token permissions, which may be read/write. The CI `docker` job requests OIDC and attestation write rights it never uses. These rights widen the blast radius of CICD-01.
- fix: Add a top-level `permissions: {}` to each workflow, or `contents: read`. In the CI `docker` job, keep only `contents: read`, plus `security-events: write` and `pull-requests: write` if CICD-04 still needs them. Fork PRs are already safe: the workflows use `pull_request`, not `pull_request_target`.
- effort: S
- depends-on: none

### CICD-03 Release vulnerability gate runs after the image is pushed
- severity: high
- evidence: `release.yml:106` `push: true` and `release.yml:89` `type=raw,value=latest,...` in step "Build & Push"; then `release.yml:118-126` "Trivy scan (push, fail on CRITICAL)" with `exit-code: "1"`
- problem: When Trivy finds a CRITICAL, the job fails, but `vX.Y.Z`, `X.Y` and `latest` are already on Docker Hub. Only the GitHub Release step is skipped. The gate only reports; it protects no user.
- fix: Build `linux/amd64` with `load: true`, scan it, then run the multi-arch build and push. The second build is a cache hit. Another option: push only the version tag, scan, then move `latest` (for example with `docker buildx imagetools create`).
- effort: M
- depends-on: CICD-04

### CICD-04 Scanner stack is oversized for a two-dependency app
- severity: medium
- evidence: each PR runs Docker Scout (`ci.yml:111-138`, with Docker Hub login, PR comment, and SARIF), Trivy as a table (`ci.yml:140-149`), and Trivy as SARIF (`ci.yml:151-167`). Each release runs Trivy twice (`release.yml:118-145`). Three SARIF upload sites exist (`ci.yml:134`, `ci.yml:163`, `release.yml:141`).
- problem: The PR scans are non-blocking: `continue-on-error: true` and `exit-code: "0"`. Two scanners report the same Alpine and pip CVEs twice. Scout pulls Docker Hub secrets into PR runs and needs `pull-requests: write`. The SARIF at `LOW` severity floods code scanning with base-image noise. Each extra scanner action is one more supply-chain surface (see CICD-01).
- fix: Keep one scanner. Trivy CLI, pinned by SHA or as a checksummed binary, is enough. `anchore/scan-action` (Grype) is an equal lighter swap if trust in Trivy is gone. Run it once per workflow with `severity: CRITICAL,HIGH` and `ignore-unfixed`. Make it blocking on release (CICD-03) and non-blocking or blocking on PRs, by choice. Drop Docker Scout, its login, and its PR comment. Upload SARIF only if the owner reads the code-scanning tab; otherwise drop it and `security-events: write`. pip-audit or osv-scanner would duplicate the Python-library part that Trivy already covers, so skip them.
- effort: M
- depends-on: CICD-01

### CICD-05 Scout SARIF upload fails the job when Scout fails
- severity: medium
- evidence: `ci.yml:122` `continue-on-error: true` on Scout; `ci.yml:134-138` "Upload SARIF (Scout, PR)" has only the fork condition, with no `steps.docker-scout.outcome == 'success'` guard (compare the Trivy guard at `ci.yml:164`)
- problem: If Scout errors (quota, Docker Hub outage, auth), `docker-scout.sarif` is missing. The upload step then fails the required `docker` check, which defeats the `continue-on-error`.
- fix: CICD-04 removes this step. Until then, add `if: steps.docker-scout.outcome == 'success'`.
- effort: S
- depends-on: CICD-04

### CICD-06 No dependency update automation; transitive deps unpinned
- severity: medium
- evidence: `.github/` holds only `workflows/` (no `dependabot.yml` and no Renovate config). `requirements.txt:1-2` pins only `PyYAML==6.0.2` and `pydantic==2.11.5`, so `pydantic-core`, `annotated-types` and `typing-extensions` float. `requirements-dev.txt:1-4` is on older pins (`pytest==8.3.5`, `pre-commit==4.0.1`). The base images `caddy:2.11.4-alpine` and `python:3.12-alpine3.22` (`Dockerfile:4,6`) are updated by hand (see `CHANGELOG.md` v1.1.1 and commit `c445816`).
- problem: CVE fixes depend on someone remembering. Image builds are not reproducible, because `pydantic-core` resolves fresh on each build.
- fix: Add `.github/dependabot.yml` with ecosystems `pip`, `github-actions`, `docker` (directory `/docker/podcastify`) and `pre-commit` (native since 2026-03). Use weekly updates and one group per ecosystem. Dependabot is the lighter choice over Renovate here. For full pins, compile a lock with `pip-compile` or `uv pip compile` into `requirements.txt`, or add a `constraints.txt`.
- effort: S
- depends-on: none

### CICD-07 No scheduled rescan of the published image
- severity: medium
- evidence: `release.yml:2-5` triggers only on `push: tags`; `ci.yml:2-6` triggers only on `pull_request` and `workflow_dispatch`; no `schedule:` exists in any workflow
- problem: Most image CVEs appear after release, in Alpine, ffmpeg, Caddy or Python. Today nobody learns that `latest` went vulnerable until the next PR happens to scan.
- fix: Add a weekly `schedule:` job that scans `fnayou/podcastify:latest` with the single scanner from CICD-04 and opens an issue or fails visibly. Use the same pinned scanner.
- effort: S
- depends-on: CICD-04

### CICD-08 Test job and image metadata duplicated across workflows and tasks
- severity: medium
- evidence: `ci.yml:13-38` and `release.yml:12-37` are identical `test` jobs. The labels block `ci.yml:80-87` equals `release.yml:90-97`. The pytest command line exists three times: `ci.yml:38`, `release.yml:37`, and `tasks/dev.yml:26` (`dev:test:ci`, which no workflow calls).
- problem: The copies drift. Changing the coverage gate or Python version needs three edits. `dev:test:ci` is dead code.
- fix: Move pytest and coverage options into a `pyproject.toml` (`[tool.pytest.ini_options] addopts`, `[tool.coverage.report] fail_under = 90`) so every caller runs plain `pytest`. Make `test` a reusable workflow (`on: workflow_call`) called by `ci.yml` and `release.yml`. Delete `dev:test:ci`. Put shared labels in the Dockerfile as `LABEL`s, or accept the one duplicated block.
- effort: M
- depends-on: none

### CICD-09 Dead config in CI build
- severity: low
- evidence: `ci.yml:58-59` "Set up QEMU", but `ci.yml:95` `platforms: linux/amd64`. `ci.yml:79` `type=raw,value=pr-...` tags are never used, because the build uses `tags: local/podcastify:${{ github.sha }}` (`ci.yml:98`). `ci.yml:9` `REGISTRY` is unused. `build-args: VERSION/BUILD_DATE/VCS_REF` (`ci.yml:102-105`, `release.yml:113-116`) are passed, but `Dockerfile` declares no `ARG`. `release.yml:188-189` passes `GITHUB_TOKEN` env, which the action already defaults to.
- problem: The noise slows reading and hides what matters. QEMU setup costs a few seconds per PR for nothing.
- fix: Remove the QEMU step, the `tags:` input of metadata in CI, `REGISTRY` in CI, the `build-args` blocks, and the `GITHUB_TOKEN` env.
- effort: S
- depends-on: none

### CICD-10 CI never runs on `main`
- severity: low
- evidence: `ci.yml:2-6` `on: pull_request: branches: [main]` plus `workflow_dispatch` only
- problem: Rebase merges create new SHAs on `main` that are never tested. GHA build cache entries made on PR refs are not visible to other PRs or to tag builds, so every PR and every release builds cold despite `cache-to: type=gha,mode=max` (`ci.yml:101`, `release.yml:112`).
- fix: Add `push: branches: [main]` to `ci.yml`, with scans non-blocking there. This also seeds the default-branch cache that PRs and tags can read.
- effort: S
- depends-on: none

### CICD-11 Concurrency settings inverted
- severity: low
- evidence: `ci.yml:44-46` `ci-docker-${{ github.ref }}` with `cancel-in-progress: false`; `release.yml:15-17` `release-test-${{ github.ref }}` with `cancel-in-progress: true`
- problem: On PRs, a superseded push keeps a 20-minute Docker job running. On releases, cancel is meaningless, because one tag means one run.
- fix: Set one workflow-level `concurrency: { group: ci-${{ github.ref }}, cancel-in-progress: true }` in `ci.yml`. In `release.yml`, use a single group with `cancel-in-progress: false`.
- effort: S
- depends-on: none

### CICD-12 Release notes extraction from CHANGELOG is fragile
- severity: medium
- evidence: `release.yml:169-176` builds the awk regex from the tag: `START_MARKER="## ${GITHUB_REF_NAME}"` and `/^${START_MARKER}/`. `release.yml:178-180` falls back silently to `"See CHANGELOG.md for details."`. `release.yml:182-184` uses a fixed `EOF` delimiter. `CHANGELOG.md` has sections `## v1.1.1` (line 5) and `## v1.0.1 (Maintenance)` (line 34), but no `## v1.1.0`, although tag `v1.1.0` exists.
- problem: The dots in the tag are regex wildcards, and the match is a prefix match, so `## v1.1.1` also matches `## v1.1.10`. A missing section, as for v1.1.0, publishes an empty release with no error. A changelog line `EOF` truncates the output. The tag text is spliced into the awk program, which is safe only because only the owner can push tags.
- fix: Fail the job when the section is missing (`exit 1` instead of the fallback). Use exact matching such as `index($0, "## " tag) == 1` with `-v tag=...`, and a random heredoc delimiter. Better: let git-cliff produce the notes (CICD-13), which removes the awk step.
- effort: S
- depends-on: none

### CICD-13 CalVer plus git-cliff plan: constraints to settle first
- severity: medium
- evidence: `release.yml:5` trigger `"v*.*.*"`; `release.yml:87-88` `type=semver,pattern={{version}}` and `{{major}}.{{minor}}`; prerelease is detected by `-` (`release.yml:76,89,206`). History before `963a220` is not conventional (for example `17b83a4 Merge pull request #4 from fnayou/delete-supervisord`).
- problem: CalVer tags still match `v*.*.*`. However, `metadata-action`'s `semver` type needs valid SemVer, and a zero-padded month (`v2026.03.0`) is not valid, so the tag type would yield no tag. `{{major}}.{{minor}}` turns into a month channel (`2026.10`), which users cannot pin to meaningfully. git-cliff over the old history would emit merge-commit noise.
- fix: Choose `vYYYY.M.PATCH` without zero padding (for example `v2026.10.0`), which stays valid SemVer, so the trigger and the `semver` patterns keep working. Drop the `{{major}}.{{minor}}` tag, and keep `{{version}}` plus `latest`. Add `cliff.toml` with `conventional_commits = true`, `filter_unconventional = true`, and no merge commits. Keep the existing `CHANGELOG.md` text below a marker and generate only new sections. In `release.yml`, replace the awk step with `orhun/git-cliff-action` (SHA-pinned) using `--latest --strip header`. Add a `task release:changelog` that runs `git cliff --unreleased` locally. Write an ADR for the version-scheme change, because it alters the tags users pull.
- effort: M
- depends-on: CICD-12, CICD-14

### CICD-14 Docker Hub tag policy: duplicate and stray tags
- severity: low
- evidence: `release.yml:86` `type=ref,event=tag` (pushes `v1.1.1`) plus `release.yml:87` `type=semver,pattern={{version}}` (pushes `1.1.1`), the same image under two names. `release.yml:196` advertises the `v`-prefixed one. Git has a stray tag `1.0.1` next to `v1.0.1` (`git tag -l`), both on the same merge.
- problem: Users see two spellings per version. The stray git tag does not match the release trigger and confuses tooling such as git-cliff.
- fix: Publish only `X.Y.Z` and `latest`; drop `type=ref`. Change the release body to `docker pull fnayou/podcastify:${VERSION}`. Delete git tag `1.0.1` locally and on origin, by explicit owner action. Docker Hub retention needs no action: PR images are never pushed (`ci.yml:97`).
- effort: S
- depends-on: none

### CICD-15 Provenance produced twice
- severity: low
- evidence: `release.yml:107-108` `sbom: true` and `provenance: true` (BuildKit attestations); `release.yml:147-152` `actions/attest-build-provenance@v1` with `push-to-registry: true`
- problem: There are two provenance records per image, and only the GitHub one is signed and verifiable (`gh attestation verify`). `@v1` is three majors behind. As of v4 it is a wrapper over `actions/attest`.
- fix: Keep `sbom: true` and `actions/attest` (SHA-pinned, CICD-01). Set `provenance: false`, or keep `mode=max` and drop the GitHub step. One is enough for this project.
- effort: S
- depends-on: CICD-01

### CICD-16 Docker Hub description not synced
- severity: low
- evidence: no workflow step updates the Docker Hub repository overview. The description exists only as an OCI label (`release.yml:92`).
- problem: The Docker Hub page drifts from `README.md` and `docs/deployment.md`. This matters most when the env var contract or user model changes (v1.1.1 changed to PUID/PGID).
- fix: On release, add one SHA-pinned `peter-evans/dockerhub-description` step (`readme-filepath: README.md`, `short-description`). It needs a Docker Hub token with rights to edit the repository. Or edit the page by hand on each release and note that in the release checklist.
- effort: S
- depends-on: CICD-01

### CICD-17 Multi-arch build through QEMU: fine as is
- severity: info
- evidence: `release.yml:56-57` QEMU and `release.yml:105` `platforms: linux/amd64,linux/arm64`, release only
- problem: None of real size. The arm64 layer is `apk add` plus pip wheels, which all exist for musllinux aarch64, so emulation costs minutes per release, not per PR. Native `ubuntu-24.04-arm` runners plus a manifest merge would add a matrix and a merge job for little gain.
- fix: No ticket. Revisit only if release builds exceed about 10 minutes.
- effort: S
- depends-on: none

### CICD-18 No linting despite documented rules
- severity: medium
- evidence: `AGENTS.md` "No unused imports or dead code"; `docs/contributing.md:64` same. `.pre-commit-config.yaml:4-21` has only the commit-msg hook. No linter runs in `ci.yml`.
- problem: The documented rules are enforced only by review. The Dockerfile has no lint either.
- fix: Add `ruff` (one tool for lint and format) and `hadolint` as pre-commit hooks at the `pre-commit` stage. Add one CI step, `pre-commit run --all-files`, or the `ruff` and `hadolint` actions, to the `test` job. Both tools are light and standard. Configure ruff in the `pyproject.toml` from CICD-08.
- effort: S
- depends-on: CICD-08

### CICD-19 Built image is never started in CI; smoke task is brittle
- severity: medium
- evidence: `ci.yml:89-105` builds and `load: true`, but only scans. `tasks/dev.yml:42-75` `dev:smoke` exists but no workflow calls it. It hardcodes `IMAGE="podcastify-podcastify:latest"` (`tasks/dev.yml:50`), a Compose project name derived from the checkout directory name, and waits with `sleep 3` (`tasks/dev.yml:64`).
- problem: Entrypoint, `su-exec`, Caddy and PUID/PGID regressions (the whole v1.1.1 change set) pass CI unseen. The smoke task breaks in any clone not named `podcastify` and flakes on slow hosts.
- fix: In `ci.yml`, after the build, run `docker run -d` on `local/podcastify:${{ github.sha }}` with a tmp podcasts/public dir. Poll `curl` until 200, with a 30 s cap, and fail otherwise. Make `dev:smoke` build with an explicit tag (`docker build -t podcastify:smoke -f docker/podcastify/Dockerfile .`) and use the same poll loop.
- effort: M
- depends-on: none

### CICD-20 `docker:clean` prunes the whole host
- severity: medium
- evidence: `tasks/docker.yml:150` `- docker system prune -f`
- problem: The task says it cleans the project, but the prune deletes every stopped container, unused network, dangling image and build cache on the developer's machine, from all projects. `docs/contributing.md:55` tells contributors to run it.
- fix: Keep `{{.COMPOSE}} down --volumes --remove-orphans` only. Remove the `docker system prune` line.
- effort: S
- depends-on: none

### CICD-21 `docker:pull` pulls nothing
- severity: low
- evidence: `tasks/docker.yml:109-115` desc "Pull latest base images", cmd `{{.COMPOSE}} pull`. `docker-compose.yml:3-5` defines only `build:`, with no `image:`.
- problem: Compose skips pull for build-only services, so base images are never refreshed. The task gives a false sense of being patched.
- fix: Change the command to `{{.COMPOSE}} build --pull {{.SERVICE_NAME}}`, or fold `--pull` into `docker:build`.
- effort: S
- depends-on: none

### CICD-22 Taskfile has duplicate and near-dead tasks
- severity: low
- evidence: `Taskfile.yml:57-65` `health` only runs `task info`. `Taskfile.yml:38-55` `info`, `tasks/docker.yml:129-141` `env` and `Taskfile.yml:67-80` `version` overlap. `tasks/docker.yml:59-77` `shell` and `shell:root` both open a root shell, because the image sets no `USER` (`Dockerfile`), so `compose exec` defaults to root. `tasks/dev.yml:4-26` has three pytest variants. `tasks/dev.yml:32` `- task docker:build:quick` shells out, while line 31 uses `task:`. `tasks/docker.yml:170` `|| true` hides a failed `sudo chown`. `Taskfile.yml:20-22` includes `Taskfile.dev.yml`, which is not in the repo.
- problem: `task --list` is long and redundant, and contributors cannot tell which task is canonical.
- fix: Merge `info`, `health`, `version` and `docker:env` into `doctor`, plus at most one `info`. Drop `shell:root`, or give `shell` `--user {{.PUID}}`. Keep `dev:test` and `dev:test:coverage` (CICD-08 removes `test:ci`). Use `task: docker:build:quick` in `validate`. Remove `|| true` from `fix:perms`. Document or drop the optional `devlocal` include.
- effort: S
- depends-on: CICD-08

### CICD-23 Contributing setup misses runtime deps and venv
- severity: low
- evidence: `docs/contributing.md:20-25` runs `pip install -r requirements-dev.txt` only, into whatever Python is active. The tasks prefer `.venv/bin/python` (`tasks/dev.yml:9`).
- problem: `task dev:validate` (`docs/contributing.md:86`) then fails on `import yaml` and `import pydantic`. On Homebrew or Debian Python, a global `pip install` is refused (PEP 668).
- fix: Add a `dev:setup` task: `python3 -m venv .venv`, then `.venv/bin/pip install -r requirements.txt -r requirements-dev.txt`, then `dev:hooks`. Point the docs at it.
- effort: S
- depends-on: none

### CICD-24 PR-title check and merge policy: consistent, one note
- severity: info
- evidence: `commits.yml:21-28` checks the PR title; `AGENTS.md` "PRs merge by rebase only"; `commits.yml:41` checks every non-merge commit subject
- problem: The commit-subject check matches rebase-only merging, and the job names `test`, `docker` and `commits` match the documented required checks. The PR-title check never affects `main` under rebase merge. It is harmless and keeps titles tidy. Whether GitHub branch protection really enforces these settings was not verified (no network).
- fix: No ticket. Optionally confirm the protection settings with `gh api repos/fnayou/podcastify/branches/main/protection`.
- effort: S
- depends-on: none

## Summary

| id | severity | effort |
|---|---|---|
| CICD-01 | high | S |
| CICD-02 | medium | S |
| CICD-03 | high | M |
| CICD-04 | medium | M |
| CICD-05 | medium | S |
| CICD-06 | medium | S |
| CICD-07 | medium | S |
| CICD-08 | medium | M |
| CICD-09 | low | S |
| CICD-10 | low | S |
| CICD-11 | low | S |
| CICD-12 | medium | S |
| CICD-13 | medium | M |
| CICD-14 | low | S |
| CICD-15 | low | S |
| CICD-16 | low | S |
| CICD-17 | info | S |
| CICD-18 | medium | S |
| CICD-19 | medium | M |
| CICD-20 | medium | S |
| CICD-21 | low | S |
| CICD-22 | low | S |
| CICD-23 | low | S |
| CICD-24 | info | S |

## Already good

- Every job has `timeout-minutes`.
- PR workflows use `pull_request`, not `pull_request_target`. Docker Hub login is gated to same-repo PRs (`ci.yml:112`), so forks never see secrets.
- `commits.yml` is a dependency-free shell check with job-scoped `contents: read`, a tag-free regex, and title and subject values passed through `env:` (no script injection).
- The release flow is ordered as test, then docker, then release. `latest` moves only on non-prerelease tags (`release.yml:89`). Prerelease detection is consistent across tags and the GitHub Release.
- The SBOM is attached, and the attestation is bound to the pushed digest.
- Runtime deps are pinned to exact versions. The `pip` cache in `setup-python` is keyed on the requirements files.
- Python 3.12 is the same in CI (`ci.yml:26`) and in the image base (`Dockerfile:6`).
- PR images are built locally and never pushed, so Docker Hub has no PR tag clutter.
- The Conventional Commits rule is enforced three times (hook, CI and review), and the type lists match in `.pre-commit-config.yaml:10-21`, `commits.yml:14`, and `docs/contributing.md:70`.

Sources: GHSA-69fq-xp46-6x23 (https://github.com/aquasecurity/trivy/security/advisories/GHSA-69fq-xp46-6x23); Aqua incident post (https://www.aquasec.com/blog/trivy-supply-chain-attack-what-you-need-to-know); GitHub changelog 2026-03-10, Dependabot pre-commit support (https://github.blog/changelog/2026-03-10-dependabot-now-supports-pre-commit-hooks/); actions/attest-build-provenance releases (https://github.com/actions/attest-build-provenance/releases).
