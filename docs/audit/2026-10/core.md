# Podcastify audit: CORE

Scope: `podcastify/*.py`, `app.py`, `tests/`, `requirements*.txt`, `GLOSSARY.md`, `docs/architecture-notes.md`.
Branch `main` at `963a220`. Read-only review. No tests were run. Every finding was checked by reading the code.
Spec sources: RSS 2.0 (rssboard.org/rss-specification), Apple "Podcast requirements" (podcasters.apple.com/support/823-podcast-requirements), PyPI JSON for versions. The Apple tag reference page (help.apple.com/itc/podcasts_connect) needs JavaScript and could not be fetched; the claims that rely on it are marked.

---

### CORE-01 CDATA sections are not escaped, so `]]>` in any description breaks the feed
- severity: high
- evidence: `podcastify/rss.py:108` `f"    <description><![CDATA[{description}]]></description>"`; same pattern at `rss.py:122` (channel `itunes:summary`), `rss.py:217` (item `description`), `rss.py:231` (item `itunes:summary`).
- problem: user text goes into CDATA verbatim. A description that contains `]]>` (pasted code, Markdown, some HTML) ends the CDATA early and the whole feed becomes malformed XML. Podcast apps then reject the whole feed, not just one episode. Characters that XML 1.0 does not allow (for example `\x00`–`\x08`, `\x0b`, `\x0c`, `\x0e`–`\x1f`, often pasted from Word) are not removed in CDATA or in `xml_escape` (`rss.py:23`), so they break the feed too.
- fix: put the text through one helper, for example `cdata(text)`, that replaces `]]>` with `]]]]><![CDATA[>` and removes characters XML does not allow. Use it in all four places. Better still, build the document with `xml.etree.ElementTree` (stdlib) so escaping is always right (see CORE-15). Add a test that parses the output with `ElementTree.fromstring`.
- effort: S
- depends-on: none

### CORE-02 Enclosure and image URLs are not percent-encoded
- severity: high
- evidence: `podcastify/rss.py:168` `media_url = f"{Config.BASE_URL}/{podcast_name}/{fname}"`; `podcastify/parser.py:199` `return f"{Config.BASE_URL}/{podcast_name}/{img_path.name}"`. Only XML escaping is applied (`rss.py:221` `esc(media_url)`).
- problem: auto-discovered files keep their real names (`parser.py:183` `"file": mp3.name`). A file like `Épisode 1 #2.mp3` gives `url=".../Épisode 1 #2.mp3"`. The URL has a space, characters outside ASCII and a `#` that starts a fragment, so clients fetch `.../Épisode 1 ` or fail. Apple's requirements page says URLs and filenames should use only `a-z, A-Z, 0-9`. The podcast name has the same problem, because `_sanitize_name` keeps spaces and other special characters (see CORE-11).
- fix: build path segments with `urllib.parse.quote(segment, safe="")` for `podcast_name` and the filename, in one shared `media_url(podcast, filename)` helper that both the enclosure and the image use. Add tests for a space, a unicode name, `#` and `?`.
- effort: S
- depends-on: CORE-03

### CORE-03 A trailing slash in `PUBLIC_BASE_URL` produces `//` in every link
- severity: medium
- evidence: `podcastify/config.py:23` `BASE_URL = _EnvVar("PUBLIC_BASE_URL", "http://localhost:8080")` (no normalisation); joined with `/` at `rss.py:168` and `parser.py:199`.
- problem: `PUBLIC_BASE_URL=https://pod.example.com/` is a natural value, and it gives `https://pod.example.com//myshow/ep.mp3`. Caddy may serve that, but the enclosure URL is now different from what a correct config gives. Apple ignores duplicate enclosure URLs, and some clients treat a changed URL as a new file. Whitespace and a missing scheme are not checked either.
- fix: in `Config`, cast `PUBLIC_BASE_URL` with `lambda v: v.strip().rstrip("/")` and check that it starts with `http://` or `https://` when processing starts, logging an error otherwise.
- effort: S
- depends-on: none

### CORE-04 Episodes whose file is missing are still published, with `length="0"` and a 1970 pubDate
- severity: high
- evidence: `podcastify/cli.py:115-121` only logs `Missing episode files for ...` and goes on; `podcastify/rss.py:172-175` `except (OSError, FileNotFoundError): stat_result = None` then `length = stat_result.st_size if stat_result else 0`; `rss.py:188-190` `datetime.fromtimestamp(stat_result.st_mtime if stat_result else 0, tz=timezone.utc)`.
- problem: a typo in `file:` in an explicit `episodes:` list publishes an item that points at a 404, with `length="0"`, no duration, and (when `pub_date` is not set) `pubDate` of `Thu, 01 Jan 1970`. Subscribers get a broken episode that cannot be played, and its GUID stays in their history.
- fix: leave out items whose file does not exist, log one warning for each, and count them in the summary. Optionally add a strict mode, or let `PUBLISH_XML=false` (dry run) report them as errors.
- effort: S
- depends-on: none

### CORE-05 A missing `ffprobe` binary makes every podcast fail
- severity: medium
- evidence: `podcastify/media.py:115` `subprocess.run(["ffprobe", ...])`; the handlers at `media.py:172-181` catch only `CalledProcessError`, `TimeoutExpired` and `ValueError`. `media.py:235` `future.result()` raises again in the caller, and `cli.py:147-149` turns that into `Failed to process <name>: [Errno 2] No such file or directory: 'ffprobe'`.
- problem: duration is an optional tag (the docs say "omitted entirely if ffprobe fails", `docs/architecture-notes.md:41-43`), but a missing binary raises `FileNotFoundError` and stops every feed instead. Running `python app.py generate` outside the image without ffmpeg installed publishes nothing. The test suite has the same hidden dependency: `test_podcast_processor.py`, `test_integration.py` and `test_golden_xml.py` call the real `ffprobe` with no mock, and only pass because CI installs ffmpeg (`.github/workflows/ci.yml:34-35`).
- fix: check once with `shutil.which("ffprobe")`. If it is missing, log one warning and skip duration probing. Also catch `OSError` in `get_duration_seconds`. Mock `_run_ffprobe` in the processor and integration tests so the suite does not need ffmpeg.
- effort: S
- depends-on: none

### CORE-06 Unquoted YAML dates fail validation, and dates without a timezone use the host's local time
- severity: medium
- evidence: `podcastify/parser.py:43` `pub_date: Optional[str] = None`; `rss.py:180` `datetime.fromisoformat(pub_str.replace("Z", "+00:00"))`; `parser.py:16` `eut.format_datetime(dt.astimezone(timezone.utc))`.
- problem: (a) YAML reads `pub_date: 2025-01-01T08:00:00Z` or `pub_date: 2025-01-01` without quotes as a `datetime` or `date`. Pydantic v2 does not convert those to `str`, so validation fails and the **whole podcast** is rejected with a long pydantic message. Only the template's quotes (`templates/podcast-config-template.yaml:16`) avoid this. (b) A date with no offset, such as `"2025-01-01T08:00:00"`, gives a naive datetime. `astimezone()` and `.timestamp()` (`cli.py:94-96`) then read it as the container's local time, so the same config produces different pubDates on different hosts.
- fix: declare `pub_date: Optional[datetime]` with a `field_validator(mode="before")` that accepts `date`, `datetime` and ISO strings, and sets UTC on naive values. Parse it once, in the model (see CORE-07). Python 3.11+ `fromisoformat` already accepts `Z`, so `.replace("Z", "+00:00")` can go.
- effort: S
- depends-on: none

### CORE-07 pub_date is parsed in two places, and the mtime fallback is unstable
- severity: low
- evidence: `podcastify/cli.py:90-99` `_ep_ts` parses `pub_date` with `except Exception: pass`; `podcastify/rss.py:177-190` parses it again with its own fallback. `cli.py:101-108` stats every file again with `except Exception`.
- problem: sorting and rendering can disagree if one parser changes. The mtime fallback for files with no `pub_date` (the default for auto-scanned episodes) changes when files are copied, restored from backup or moved to another host without `-p`. Episodes then move in the list and get new pubDates, so some apps show them as new. That is the documented behaviour (`docs/architecture-notes.md:50-51`), but users are not warned about it.
- fix: add one `Episode` value object (or the validated `EpisodeModel`) with `published: datetime` worked out once: `pub_date`, else mtime. Sort and render from that field. Mention in `docs/configuration.md` that `pub_date` should be set for a stable feed.
- effort: S
- depends-on: CORE-06

### CORE-08 Enclosure MIME type is always `audio/mpeg`, and auto-scan finds only lowercase `*.mp3`
- severity: medium
- evidence: `podcastify/rss.py:221` `... type="audio/mpeg"/>`; `podcastify/parser.py:181` `pub_dir.glob("*.mp3")`.
- problem: an explicit `episodes:` list can name `.m4a`, `.mp4`, `.ogg` or `.opus` files. They are published as `audio/mpeg`, and Apple and other clients use the type to choose a player. The RSS 2.0 spec says `type` is the file's real MIME type. Auto-scan on a case-sensitive filesystem misses `EP01.MP3`, with no warning.
- fix: use a small extension-to-MIME map (`.mp3` audio/mpeg, `.m4a` audio/x-m4a, `.mp4` video/mp4, `.ogg` audio/ogg, `.opus` audio/opus), or `mimetypes.guess_type`. Scan with a case-insensitive suffix check against that map. If the project means to support MP3 only, reject other extensions during validation instead.
- effort: S
- depends-on: none

### CORE-09 Feed is missing the namespaces and self link that Apple and validators expect
- severity: medium
- evidence: `podcastify/rss.py:83` `<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">`; there is no `atom:link rel="self"` anywhere. `rss.py:114` and `rss.py:222` write `itunes:explicit` as `yes`/`no`.
- problem: Apple's requirements page says the feed must "include the XML declaration with the itunes and content namespaces". `xmlns:content` is missing. The W3C/Cast Feed Validator warns when `atom:link rel="self"` is missing, and Podcasting 2.0 tools use it. *Not verified (Apple's tag page could not be loaded):* Apple's current tag reference lists `true`/`false` for `itunes:explicit`; `yes`/`no` is the older form, still accepted. `itunes:summary` and `itunes:subtitle` are legacy tags that Apple no longer shows, and both are written on every channel and item, including empty `<itunes:summary></itunes:summary>` (`rss.py:124`, `rss.py:233`). Empty `<itunes:author></itunes:author>` is written when no author is set (`rss.py:115`).
- fix: declare `xmlns:content` and `xmlns:atom`. Add `<atom:link href="{BASE_URL}/{name}.xml" rel="self" type="application/rss+xml"/>`. Write `itunes:explicit` as `true`/`false` after checking Apple's tag page. Leave out empty optional tags. Optional Podcasting 2.0 tags (`podcast:guid`, `podcast:locked`) can be a later feature ticket, not part of this fix.
- effort: S
- depends-on: none

### CORE-10 No check for duplicate GUIDs, duplicate episode files or duplicate feed names
- severity: medium
- evidence: `podcastify/parser.py:170-174` adds every listed episode with no check; `rss.py:192-194` takes `guid` from YAML or the SHA-1 of the filename; `parser.py:145-151` accepts both `<name>-podcast.yaml` and `<name>-podcast.yml`.
- problem: listing the same `file` twice, or copying an episode entry and keeping its `guid`, publishes two items with the same GUID. Clients then merge the items or drop one. `myshow-podcast.yaml` and `myshow-podcast.yml` both map to `myshow`, so both run and the second one silently overwrites `myshow.xml`. Sanitisation can also make two names collide (`my..show` and `myshow`, see CORE-11).
- fix: after discovery, reject (or at least log an error for) duplicate GUIDs and duplicate resolved paths for each podcast. In `discover_podcast_configs`, reject a second config that maps to an existing name and log both filenames.
- effort: S
- depends-on: CORE-11

### CORE-11 Name and filename sanitising changes the input instead of rejecting it
- severity: low
- evidence: `podcastify/parser.py:31-32` `return name.replace("..", "").replace("/", "").replace("\\", "").strip()`; `parser.py:171` `fname = Path(e.get("file", "")).name`.
- problem: path traversal is blocked, which is good. But the rule is a deny-list that rewrites input: `my..show` quietly becomes `myshow`, and spaces, unicode, `#`, `?` and `%` stay in the name, then appear in URLs (CORE-02) and in the feed path. `file: ""` resolves to the podcast directory itself, and `file: ".."` resolves to `PUBLIC_ROOT` (`Path("..").name == ".."`). Neither is a traversal, but both are accepted without an error and fed to `stat` and `ffprobe`.
- fix: validate with an allow-list, for example `re.fullmatch(r"[a-z0-9][a-z0-9_-]*", name)`, and reject with a clear log line instead of rewriting. Add a pydantic validator on `EpisodeModel.file` that requires a plain filename with an allowed extension.
- effort: S
- depends-on: none

### CORE-12 Exit codes hide partial failure and treat "no configs" as an error
- severity: medium
- evidence: `podcastify/cli.py:173-175` `count = processor.process_all_podcasts()` then `return count > 0`; `app.py:32` `sys.exit(0 if main() else 1)`; `tests/test_integration.py:52-57` asserts `main()` is `False` with no configs.
- problem: if 1 of 3 feeds fails validation, the exit code is 0, so a cron job, `task podcastify:generate` or a CI dry run reports success. A fresh install with an empty `podcasts/` exits 1, and the entrypoint prints `Generator exited non-zero` (`docker/podcastify/entrypoint.sh:31`) on a valid first boot. The `generate` argument is parsed by hand (`cli.py:171`), and any other argument is ignored without a message.
- fix: return 0 when every config succeeded (including when there are none), 1 when any failed, and 2 for usage errors. Use `argparse` (stdlib) with one `generate` subcommand plus `--dry-run`, which can replace `PUBLISH_XML`. Update the integration test.
- effort: S
- depends-on: none

### CORE-13 Catch-all exception handlers drop the traceback
- severity: low
- evidence: `podcastify/cli.py:147-149` `except Exception as e: logger.error(f"Failed to process {podcast_name}: {e}")`; `cli.py:97` and `cli.py:107` `except Exception:`.
- problem: a real bug, such as a `TypeError` in rendering, shows up as one line with no stack trace, even at `LOG_LEVEL=DEBUG`. The two inner `except Exception` handlers hide every error.
- fix: use `logger.exception(...)` in the outer handler. Narrow the inner ones to `(ValueError, TypeError)` and `OSError`, or remove them as part of CORE-07.
- effort: S
- depends-on: none

### CORE-14 Dead code from the old "dual metadata path", and the architecture notes are out of date
- severity: low
- evidence: `podcastify/parser.py:126-132` `extract_podcast_metadata` is called only from `tests/test_configuration_manager.py:44-65` (checked with `git grep`). `podcastify/config.py:34-38` `EPISODE_FIELDS` is never read outside `tests/test_config.py:31-33`. `parser.py:166-167` `eps = config.get("episodes")` cannot run, because `cli.py:53-56` returns early whenever `validated` is `None`. `app.py:8-29` re-exports eight names, including private `_coerce_bool` and `_sanitize_name`, that nothing imports from `app`. `podcastify/__init__.py:23-24` lists private names in `__all__`.
- problem: the dual metadata path that `docs/architecture-notes.md:29-34` warns about is already gone in production. `cli.py:58` builds metadata from the validated model, so the note and its "keep both in sync" rule (`architecture-notes.md:26-28`) send readers to dead code. The notes are also wrong on two facts: the cache is described as `<PUBLIC_ROOT>/.podcastify-cache.json` (`architecture-notes.md:39`), but it is `CACHE_ROOT` (`media.py:23`, ADR 0003, `GLOSSARY.md:8`). They say deleted-file entries are "never pruned" (`architecture-notes.md:40`), but `_save_disk_cache` prunes them (`media.py:86-88`). The module map has no line numbers (`architecture-notes.md:10-16`, "config.py, config.py"). `GLOSSARY.md:16` describes whitelisted fields "copied into feed metadata", which no longer happens for episodes.
- fix: delete `extract_podcast_metadata`, `EPISODE_FIELDS`, the raw-dict fallback in `discover_episodes`, and the `app.py` re-export block (keep `from podcastify.cli import main`). Drop the private names from `__all__`. Rewrite the "Legacy author", "Dual metadata path" and "Duration cache" bullets, and either fix the module map or drop the location column. Update `GLOSSARY.md:16`.
- effort: S
- depends-on: none

### CORE-15 The renderer works on untyped dicts and builds XML by string concatenation
- severity: low
- evidence: `podcastify/cli.py:27-42` converts the validated `PodcastChannelModel` back into a `Dict[str, Any]`; `rss.py:72-73` takes `metadata: Dict[str, Any], episodes: List[Dict[str, Any]]` and sets defaults again (`rss.py:94-103`, for example `language = metadata.get("language") or "en"`, which the model already sets at `parser.py:65`). Episodes carry private keys `__resolved_path` and `__mtime` in the same dict (`parser.py:173`, `cli.py:106`). Typing details: `config.py:7` `cast: Optional[Any]`, `cli.py:22` `__init__` has no return type, `cli.py:27` `model: Any`. No type checker or linter is set up (`requirements-dev.txt`, `.pre-commit-config.yaml`).
- problem: the generator does not get the benefit of the validated model. A typo in a key such as `"author-name"` or `"new_feed_url"` is silent. Defaults live in two places, and escaping is manual, which is what led to CORE-01. `EpisodeModel` uses `extra="allow"` (`parser.py:36`), so misspelled keys such as `pubdate:` are accepted and ignored with no warning.
- fix: pass `PodcastChannelModel` and a typed episode object (model plus resolved path, size, published datetime, MIME type) straight to `RSSGenerator`. Build the tree with `xml.etree.ElementTree` and `register_namespace`, which is stdlib and needs no new dependency. Change to `extra="forbid"` (or log a warning for unknown keys) so typos show up. For tooling, add `ruff` as the single lightweight linter and formatter. Leave out mypy unless the owner wants it; pydantic plus ruff's annotation rules cover most of this.
- effort: M
- depends-on: CORE-14

### CORE-16 The duration cache keeps temporary failures forever, and old mtime entries are never removed
- severity: low
- evidence: `podcastify/media.py:176-178` `except subprocess.TimeoutExpired ... return cls._cache_failure(key, persist=persist)`; `media.py:106-110` stores `None` and saves it to disk; pruning `media.py:86-88` only checks `file_path.exists()`.
- problem: one ffprobe timeout on a busy NAS (30 s, `media.py:114`) stores `None` on disk, and that episode has no duration until its mtime changes. Every time a file is edited, a new `(path, mtime)` key is added and the old key is kept while the file exists, so the cache keeps growing slowly. The keys are absolute paths, so changing `PUBLIC_ROOT` or a bind-mount path makes every entry stale. This is small at podcast scale.
- fix: do not save `TimeoutExpired` failures to disk (keep them in memory only). On save, keep only the newest mtime for each path. Optionally key the cache by the path relative to `PUBLIC_ROOT`.
- effort: S
- depends-on: none

### CORE-17 The atomic-write temp file is public and can be left behind
- severity: low
- evidence: `podcastify/cli.py:127` `tempfile.mkstemp(dir=str(Config.PUBLIC_ROOT), suffix=".xml")`; `cli.py:133-134` `os.chmod(...)` then `os.replace(...)`, with no `fsync`.
- problem: the temp-plus-replace approach is correct, and readers never see a partial feed. But if the process is killed between `mkstemp` and `replace`, a `tmpXXXXXX.xml` file stays in the directory Caddy serves and `task podcastify:clean:feeds` matches it. Without `fsync`, a power cut can leave an empty feed after the rename on some filesystems. This rarely matters for this project.
- fix: use `prefix=f".{podcast_name}."` so the temp file is hidden (check that the Caddyfile hides dotfiles), call `f.flush(); os.fsync(f.fileno())` before `replace`, and remove stale `.*.xml` temp files at startup.
- effort: S
- depends-on: none

### CORE-18 Logging is set up for each module, and the env booleans are stricter than the YAML ones
- severity: low
- evidence: `podcastify/logging_config.py:26-58` adds two handlers to **each** module logger (`podcastify.cli`, `podcastify.parser`, ...) and sets `logger.propagate = True`; `LOG_LEVEL` is read at import time (`logging_config.py:34`) through module-level `logger = get_logger(__name__)`. `config.py:24-25` `lambda v: v.lower() == "true"` while YAML uses `_coerce_bool` (`parser.py:19-26`).
- problem: if anything configures the root logger (a library, or `logging.basicConfig` in a future CLI), every line prints twice. Changing `LOG_LEVEL` after import has no effect. `reset_logger_cache()` in `tests/conftest.py:23-24` removes the handlers from module loggers that are never set up again, so tests run with different logging than production. `PUBLISH_XML=1` or `RUN_ON_START=yes` is read as **false** with no warning, unlike YAML booleans.
- fix: replace `logging_config.py` with one `configure_logging(level)` call in `main()` that sets handlers on the `podcastify` logger. Modules use plain `logging.getLogger(__name__)`. Use one shared bool parser for env vars and YAML, and log a warning for values it does not recognise.
- effort: S
- depends-on: none

### CORE-19 The "golden XML" test is not a golden test
- severity: medium
- evidence: `tests/test_golden_xml.py:66-74` checks only substrings, for example `assert '<item>' in xml_content`. There is no snapshot file in `tests/`, and the XML is never parsed.
- problem: the file says it guards against "unintended changes to feed output" (`test_golden_xml.py:4-5`), but tag order, escaping, enclosure attributes, pubDate, GUID, duration and well-formedness are not checked. CORE-01 (malformed XML) and CORE-02 (unencoded URLs) would both pass this test. The output is also not deterministic: `lastBuildDate` uses `datetime.now()` (`rss.py:76`), and pubDate and duration depend on file mtime and real ffprobe.
- fix: add `tests/golden/<case>.xml` files. Fix `datetime.now` (inject a `now` argument), set `pub_date` and `duration_hms` in the fixture config, then compare the output exactly and parse it with `ElementTree.fromstring`. Cover a nasty case: `&`, `]]>`, unicode, spaces in filenames, nested categories. Keep it to stdlib and pytest, with no snapshot plugin.
- effort: S
- depends-on: CORE-01, CORE-02

### CORE-20 Tests touch real `/app` paths, and the class-level cache leaks between tests
- severity: medium
- evidence: `tests/conftest.py:18` `monkeypatch.setenv("CACHE_ROOT", "/app/.cache")` is the default for every test; `podcastify/media.py:98-103` `clear_cache()` calls `path.unlink(...)` on `CACHE_ROOT/.podcastify-cache.json`; it is called without a `CACHE_ROOT` override in `tests/test_media_processor.py:84, 99, 116, 195, 210, 256, 291`. `MediaProcessor._duration_cache` (`media.py:15`) is class state and is never reset by an autouse fixture. The processor and integration tests write to `/app/.cache` through `_save_disk_cache`.
- problem: running `pytest` inside the container (which has `/app/.cache`) **deletes the production duration cache** and fills it with temp paths. On a dev machine, the writes fail and the `OSError` is silently swallowed (`media.py:94-95`), so the cache-saving code is never really exercised there. Tests depend on each other's cache state and on test order. Coverage passes 90% while these paths go untested.
- fix: in `conftest.py`, point `PODCASTS_ROOT`, `PUBLIC_ROOT` and `CACHE_ROOT` at `tmp_path` subdirectories by default, and add an autouse fixture that clears `MediaProcessor._duration_cache` and `_disk_loaded`. Also mock `ffprobe` by default (CORE-05).
- effort: S
- depends-on: CORE-05

### CORE-21 The 90% coverage gate leaves the edge cases that matter untested
- severity: low
- evidence: `tests/` has no tests for: `]]>` or control characters in text, unicode, space or `#` in filenames or podcast names, a trailing-slash base URL, a listed episode whose file is missing, an unquoted YAML date, a naive `pub_date`, sort order across mixed `pub_date` and mtime episodes, duplicate GUIDs, an invalid `pub_date` fallback (`rss.py:182-186`), a YAML file whose top level is a list or a string (`parser.py:98-99` passes it through to pydantic), or `.yaml` and `.yml` for the same name. Some tests check only that some log line exists, for example `test_podcast_processor.py:72` `any(record.levelname == "WARNING" ...)`, which passes on any warning.
- problem: line coverage is high because the happy paths run through most lines, but the bugs listed above sit in branches and inputs that are never tested. Tests that only check for "any warning" pass even when the wrong code path runs.
- fix: add a parametrised edge-case test for each fix as it lands (CORE-01 to CORE-12). Check specific log messages. Consider `--cov-branch` in the coverage task so the gate measures branches.
- effort: M
- depends-on: CORE-01, CORE-02, CORE-03, CORE-04, CORE-06, CORE-10

### CORE-22 Dependencies are behind, and pre-commit is a heavy tool for one hook
- severity: low
- evidence: `requirements.txt:1-2` `PyYAML==6.0.2`, `pydantic==2.11.5`; `requirements-dev.txt:1-4` `pytest==8.3.5`, `pytest-cov==6.0.0`, `pytest-mock==3.14.0`, `pre-commit==4.0.1`. PyPI today: PyYAML 6.0.3, pydantic 2.14.1 (changelog dated 2026-10-11), pytest 9.1.1. I did not check pytest-cov, pytest-mock or pre-commit.
- problem: the pins are exact, which is good, but they are three minor pydantic releases and one major pytest release behind, with no hashes and no automated update flow. PyYAML 6.0.3 adds Python 3.14 wheels, which matters if the base image moves forward. `pre-commit` brings in `virtualenv`, `nodeenv`, `identify` and `cfgv`, and clones a remote repository (`.pre-commit-config.yaml:5`), only to run one `commit-msg` regex that the `commits` CI check already runs. All runtime dependencies are used: PyYAML (`parser.py:121`) and pydantic (`parser.py:7`). Pydantic is a reasonable choice here and should stay. All dev dependencies are used.
- fix: update to the current versions and run the suite. Turn on Dependabot for `pip` (a GitHub-native config file, no new tool) to keep them current. Optionally replace pre-commit with a small `commit-msg` script under `.githooks/` and `git config core.hooksPath .githooks` in `task dev:hooks`.
- effort: S
- depends-on: none

---

## Summary

| id | severity | effort |
|---|---|---|
| CORE-01 | high | S |
| CORE-02 | high | S |
| CORE-04 | high | S |
| CORE-03 | medium | S |
| CORE-05 | medium | S |
| CORE-06 | medium | S |
| CORE-08 | medium | S |
| CORE-09 | medium | S |
| CORE-10 | medium | S |
| CORE-12 | medium | S |
| CORE-19 | medium | S |
| CORE-20 | medium | S |
| CORE-07 | low | S |
| CORE-11 | low | S |
| CORE-13 | low | S |
| CORE-14 | low | S |
| CORE-15 | low | M |
| CORE-16 | low | S |
| CORE-17 | low | S |
| CORE-18 | low | S |
| CORE-21 | low | M |
| CORE-22 | low | S |

## Already good (no ticket)

- Path traversal is blocked: episode files and images resolve with `Path(x).name` under `PUBLIC_ROOT/<name>` (`parser.py:171`, `parser.py:196`), and the podcast name has `..`, `/` and `\` removed (`parser.py:32`).
- `yaml.safe_load` is used (`parser.py:121`). Errors in YAML loading and file reads are caught and logged per podcast, so one bad config does not stop the others.
- Feeds are written with temp file plus `os.replace` and `0644` permissions (`cli.py:127-134`). The duration cache is written atomically too (`media.py:90-92`).
- The duration cache is thread-safe: it uses double-checked loading, snapshots under the lock, and saves once after the parallel warm-up instead of N times (`media.py:31-37`, `media.py:80-81`, `media.py:226-236`).
- `pubDate` and `lastBuildDate` use `email.utils.format_datetime` in UTC, which is valid RFC 2822 (`parser.py:16`).
- Attribute values are escaped with quotes (`rss.py:23`, `rss.py:31`). The category structure supports a string, a list, `[parent, sub]` pairs and dicts (`rss.py:47-68`).
- `format_itunes_duration` is correct and well tested, including rounding and negative values (`media.py:239-245`, `test_media_processor.py:12-39`).
- `isPermaLink="false"` on the hash GUID is correct, and the GUID rule is documented as a compatibility constraint.
- Pydantic validation of the required `title` and `description` fields and of the `type` enum gives clear failures. Pydantic is a reasonable, standard choice at this size.
- Dependencies are pinned exactly, and there are only two runtime dependencies.
