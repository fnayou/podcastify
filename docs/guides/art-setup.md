# Generated Art Setup Guide

This guide explains how the repository's images are generated, how to rebuild them, and how the reminder
works. It is internal documentation for contributors; the decisions are in
[ADR 0008](../adr/0008-docs-site-art-and-index-page.md).

The README banner, the logo, the favicon, the GitHub social preview and the architecture diagram are
written by a small Python program in `tools/art/`, which uses the standard library only. They use the
Catppuccin Macchiato palette (https://catppuccin.com/palette/) with the blue accent `#8aadf4`. Names, the
one-line pitch, the media formats, the module list, the settings and the container facts are read from files
of the working tree (`.github/workflows/release.yml`, `podcastify/`, `AGENTS.md`, `.env.example`,
`docker/podcastify/Dockerfile`), never from git. The same inputs always give the same bytes: no timestamp, no
commit hash, no branch.

Run every command from the root of the repository.

## 1. What is generated

| Image | Files in `website/assets/images/` | Committed | Used by |
|---|---|---|---|
| Logo | `podcastify-logo.svg` + `.png` | yes | the documentation site |
| Favicon | `favicon.svg` + `.png` (64 px) | yes | the documentation site |
| README banner | `podcastify-readme-banner.svg` + `.png` | yes | `README.md` (the SVG) |
| Social preview | `podcastify-social-preview.svg` + `.png` | yes | GitHub repository settings (the PNG, uploaded by you) |
| Architecture diagram | `podcastify-architecture.svg` | **no**, git-ignored, SVG only | the "How it works" page of the site |

Every committed SVG has a PNG with the same base name beside it, rendered from it right after. The pair is
written together, so they cannot disagree. The PNGs need `rsvg-convert` (section 2); without it only the SVGs
are written and the tool says `PNG skipped: rsvg-convert not found`. The SVGs use a system monospace font
stack and no external font or CDN, so the PNG lettering depends on the fonts of the machine that renders it.

## 2. Prerequisites

Python 3.12 is the only requirement for the SVGs. `rsvg-convert` comes from librsvg and is optional:

```bash
# macOS
brew install librsvg
```

```bash
# Debian and Ubuntu
sudo apt install librsvg2-bin
```

## 3. Build, check and rebuild

```bash
task art:check          # read-only: are the committed SVGs current?
```

If it reports `stale: ...`, regenerate. This writes inside `website/assets/images/` only:

```bash
task art:build                       # every image (SVG, then its PNG)
task art:build ARGS='--only banner'  # one or more of: logo, favicon, banner, social, architecture
task art:build ARGS='--no-png'       # SVGs only
task art:logo                        # the logo and the favicon only
```

Then review `git diff --stat website/assets/images/` and commit the SVGs and PNGs. A change to something the
images are built from (the pitch or image name in `release.yml`, a module of `podcastify/`, its row in the
`AGENTS.md` architecture table, the media types in `podcastify/config.py`, `.env.example`, the Dockerfile) can
make the banner, the social preview or the diagram stale. Rebuild after the last such change.

`task art:build` also writes the architecture diagram, which is git-ignored, so it never shows up in a commit.

## 4. What CI does

The `test` job runs `tests/test_art.py` with the rest of the suite. The test regenerates the committed SVGs in
memory, compares them byte for byte with the files, and checks the palette constants against the Catppuccin
Macchiato values. It needs no `rsvg-convert` and no `task` binary, and it never compares PNGs, because PNG
output depends on fonts and the renderer. A stale SVG fails the pull request.

CI never commits images. Every commit in this repository is authored by the owner, so you rebuild and commit
the images yourself.

## 5. The architecture diagram

`podcastify-architecture.svg` shows the pipeline (sources, `parser`, `media`, `rss`, `cli`, the feeds and
Caddy), the support modules, the container (image, `tini`, `entrypoint.sh`, the generator, Caddy and the three
mounted folders) and the settings of `.env.example`. A module added to `podcastify/` appears in the support row
on the next run without a change to the generator.

The diagram is not committed. The documentation build and deployment workflow (ticket #118) generates it with
`python3 -m tools.art build --only architecture` just before building the site, so the "How it works" page is
always current. Until that workflow exists, run the command above to look at it locally.

## 6. The reminder

`task art:remind` prints a short message when the change in your working tree touches something the images are
built from and a committed SVG is stale. Otherwise it prints nothing.

```bash
task art:remind                         # changes against HEAD (default)
task art:remind ARGS='--staged'         # staged changes
task art:remind ARGS='--range main..HEAD'
```

It is read-only, never fails and is not wired to a git hook or a CI step: run it when you want it.

## 7. Uploading the social preview

GitHub does not read the social preview from the repository. After building, upload the PNG yourself under the
repository's Settings, General, Social preview, using `website/assets/images/podcastify-social-preview.png`.

## 8. Troubleshooting

### `stale: ...` from `task art:check` or a failing `tests/test_art.py`

The SVG no longer matches what the repository would generate. Run `task art:build`, review the diff and
commit the images.

### `PNG skipped: rsvg-convert not found`

Install librsvg (section 2). The SVG was still written. Until then the PNG sidecars are missing; the freshness
test only checks the SVGs.

### `release.yml: no match for ...` or another `art:` message

A file the generator reads changed shape (for example the `IMAGE_NAME` or `IMAGE_DESCRIPTION` line of
`release.yml`, the `ENTRYPOINT` or `EXPOSE` line of the Dockerfile). Restore the line or update
`tools/art/facts.py` together with its tests.

### The README banner looks different from the PNG

GitHub renders an SVG image with the viewer's fonts, so the lettering can differ slightly from the PNG. The
layout and the colours are the same. Docker Hub may not render the SVG banner; check the overview after the
first release and, if needed, point the README at the PNG instead.
