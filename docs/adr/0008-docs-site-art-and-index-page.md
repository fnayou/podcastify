# 0008 - Documentation site, generated art and the index page

## Status

Accepted and implemented. Decided by the owner on 2026-10-24 in the design
sessions of issues #49 and #50, recorded by issue #115. The child tickets are
under References.

## Context

Podcastify has no public documentation site. The user documentation is in
`docs/` next to the internal documents, and the README is the only
presentation. The container has no page at `/`: Caddy directory browsing was
removed, so a visitor sees a 404.

A site generator has to be chosen now. Material for MkDocs entered maintenance
mode on 2025-11-05 and its promise of critical fixes ends on 2026-11-05, so a
new site should not start on it. The owner's `fnayou/dotfiles` repository has a
working layout for a site and for generated art; this repository follows it
where it fits.

## Decision

### Generator: Zensical on GitHub Pages

The site is built with Zensical and published on GitHub Pages. Facts, as
checked when deciding:

- Zensical is MIT licensed and installed with pip.
- It reads `mkdocs.yml` or its own `zensical.toml`.
- Its support for mkdocstrings is preliminary, and this project does not use it.
- Its website advertises paid editions (Studio) while the generator itself stays
  MIT.
- It has no built-in documentation versioning. The site tracks `main` only
  ("latest") and links to the GitHub Releases for older versions.

Rejected:

- Material for MkDocs: maintenance mode since 2025-11-05, critical fixes only
  until 2026-11-05.
- Sphinx with MyST and Furo: mature but heavier; the owner rejected it.
- Astro Starlight and similar tools: a second toolchain.
- Documentation inside the image.
- No site.

### One site, one place

There is one site, at `https://fnayou.github.io/podcastify/`, with no custom
domain for now. Its home page is the presentation page, so the separate
one-page site of issue #51 is folded into the documentation epic (#49). A
second repository or the user site `fnayou.github.io` is not used. The Pages
source is "GitHub Actions", a one-time repository setting made by the owner.

### Public folder apart from internal documents

As in the dotfiles repository, `website/` is the published site (`docs_dir`).
`docs/` stays internal and is never published: ADRs, agent documents, the audit,
architecture notes, worktree documents and `contributing.md`.

The public pages are six: Home (the presentation), Getting Started, Deployment,
Configuration, How it works and Troubleshooting. There is no Screenshots page
until the index page gives something to show.

### Configuration reference generated from the models

The configuration reference is generated from the pydantic models, between
markers in the Configuration page, and committed. A freshness test compares the
committed text with the generated text (the same pattern as the golden XML
test). Descriptions live in `Field(description=...)`. Rules that a schema cannot
express stay as reviewed prose with focused tests.

### Build and deployment

Zensical is pinned and runs in strict mode. A documentation build runs on pull
requests only when `website/**`, the models, the Zensical configuration or the
workflow change. Deployment happens only from `main`, through the official Pages
actions, and the Pages environment is restricted to `main`.

### Generated art

The art is the logo, the favicon, the README banner, the social preview and the
architecture diagram. It is produced by a stdlib-only Python program in
`tools/art/`, following `scripts/art/` of the dotfiles repository adapted to
this repository's `tools/` folder.

- The palette is Catppuccin (https://catppuccin.com/palette/), variant
  Macchiato, with the accent yellow `#eed49f`: the dotfiles identity (banner layout
  and palette) with a yellow accent in place of blue. The same palette styles
  the generated index page (Latte in light mode) and the documentation site.
- The committed images are SVG with a PNG sidecar of the same base name. The
  tasks write them (`task art:build`, `task art:logo` and so on); the PNG needs
  `rsvg-convert`, which is optional tooling.
- The architecture diagram is generated automatically in the documentation build
  and is not committed.
- Output is deterministic: no timestamp, commit hash or branch.
- CI regenerates the committed SVGs in memory and compares them byte for byte,
  without committing anything. There are no bot commits: every commit is authored
  by the owner.

### Index page at `/` of the container

The container can serve an index of the feeds. It is opt-in and off by default:

- The setting is `PUBLISH_INDEX`, with the same true/false parsing as
  `PUBLISH_XML`, and it takes effect only when XML publishing is on.
- Every feed is listed unless its configuration has `listed: false`. The page
  lists feeds only (title, feed URL, episode count, last build date, optional
  cover), never media files.
- The generator writes `public/index.html` next to the feeds, with the same
  atomic write. The first line is a generator marker. The page is semantic HTML
  with plain CSS and dark-mode support, no JavaScript and no external fonts.
- The page is rewritten only when its content changes, and the build dates come
  from real feed publishes, so the watcher does not churn it.
- Disabling the index removes `public/index.html` only when it carries the
  marker, never a hand-made file.
- Caddy keeps browsing off and dotfiles hidden. `/` answers 200 when the file
  exists and 404 otherwise.

## Consequences

- Two new tools arrive: Zensical for the site (pinned) and the art program in
  `tools/` (stdlib only).
- The site shows `main`, not the release the user runs; older states are on the
  GitHub Releases.
- Descriptions of configuration keys live in the models, so a model change
  without a regenerated page fails the freshness test.
- The owner approves the colours and the wordmark before the art is merged, and
  uploads the social preview PNG in the repository settings.
- Enabling the index on a public reverse proxy makes feed names discoverable,
  and `listed: false` only hides a feed from the page; it does not protect a
  known feed URL. The documentation says so.
- Until the child tickets are merged, nothing described here exists.

## References

- Issues #49 (documentation epic), #50 (index page epic), #51 (one-page site,
  folded into #49)
- Child tickets: #115 (this ADR), #116 (configuration reference generator),
  #117 (public site content in `website/`), #118 (Zensical build and Pages
  deploy), #119 (generated brand art and diagram), #120 (opt-in index page)
- The owner's `fnayou/dotfiles` repository: `website/`, `scripts/art/`,
  `docs/guides/art-setup.md` and its ADR 0082
- [ADR 0002](0002-env-var-contract.md), the environment variable contract that
  `PUBLISH_INDEX` joins
