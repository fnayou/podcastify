# 0006 - tinytag for episode durations, ffmpeg removed

## Status

Accepted on 2026-10-23, after a spike that compared the two readers (issue #46)
and the decision in issue #99. Implemented: `MediaProcessor` reads durations
with `tinytag` only, and the image no longer contains ffmpeg.

## Context

`MediaProcessor` ran `ffprobe` as a subprocess for every episode, with a stream
fallback, timeouts and a warning for a missing binary. ffmpeg was the largest
package in the image and the only reason the Python code started child
processes.

The spike measured `tinytag` 2.3.2 (pure Python, MIT, no dependencies) against
`ffprobe` on 47 real files and 25 generated files (MP3 CBR and VBR, M4A, MP4,
OGG, Opus, ID3 tags with covers, truncated, zero-byte and garbage files).
Because both readers estimate the length, a full decode with ffmpeg served as
the reference.

- Formats: `tinytag` reads `.mp3`, `.m4a`, `.mp4`, `.ogg` and `.opus` with no
  flags.
- Accuracy against a full decode: on the first set of 17 real files `tinytag`
  was within 1.0 s on every file (worst case 0.92 s); on a second set of 30 real
  MP3 files (3 VBR with a Xing header) it was within 0.11 s on every file and
  matched `ffprobe` to the millisecond. On generated files with a known length
  it was within 0.07 s, except VBR without a header (0.46 s).
- `ffprobe` was the less accurate reader in all 3 disagreements: 3.2 s and
  3.4 s short on two 192 kbps files without a Xing header and with a large ID3
  tag, 7.4 s short on a generated VBR file without a header.
- Image: 345 MB to 190 MB (155 MB, 45% smaller), 107 fewer OS packages. Trivy
  HIGH findings with a fix: 5 before and after, all in the Caddy binary.
- Speed: 2000 files in 10.2 s with `ffprobe` (4 parallel jobs) against 0.33 s
  with `tinytag` in one thread (about 31 times faster). Four threads gave no
  gain for `tinytag`.
- Failure cases: a zero-byte file gives no duration. A garbage file with an
  `.mp3` name gives 0.048 s, because random bytes can parse as one short MPEG
  frame. A truncated MP3 whose first frame carries a Xing frame count reports
  the full original length, and `ffprobe` gives the same wrong value.

## Decision

Use `tinytag==2.3.2` as the only duration source and remove ffmpeg from the
image and from CI. The owner accepted these conditions:

1. **Yardstick.** Accuracy is judged against a full decode, not against
   `ffprobe`. Measured against `ffprobe` alone the strict 1 s rule fails on
   three files, and in all three `ffprobe` is the inaccurate side.
2. **Guard.** `get_duration_seconds` returns `None` for a `tinytag` exception,
   for no duration, for a non-finite or non-positive duration, and for a
   duration under 1 s on a file of at least 100 KB. The exception message is
   logged once per file. A guard that compares file size with bitrate to catch
   truncated files is deferred until it has been tested on VBR files and large
   tags.
3. **Cache.** The cache file carries a format version
   (`MediaProcessor.CACHE_VERSION`, now 2). A file in another version, including
   the flat format written before, is ignored, so every file is read once with
   `tinytag`. The migration from `PUBLIC_ROOT` still moves the old file; the
   next save replaces it with the versioned format.
4. **One change.** The reader swap, tests, cache change, Docker and CI cleanup,
   and removal of the `ffprobe` code and its warning land together.
   `warm_durations` replaces `warm_durations_parallel`: it reads the files one
   after the other and saves the cache once, because threads gave no gain and
   the subprocess timeouts no longer exist.
5. **Dependabot.** `tinytag` has its own group in `.github/dependabot.yml`, and
   the general `python` group excludes it. A `tinytag` update is a separate pull
   request. Before merging it, compare durations on a sample of episodes, and
   bump `CACHE_VERSION` if the new release reads any file differently.

Tests use small generated fixtures under `tests/fixtures/audio/`, built by
`tests/fixtures/make_audio.sh` in a throwaway container. No test mocks a
subprocess and no real audio is committed.

## Consequences

- The image is 155 MB smaller and the generator starts no child process.
- On the first run after the upgrade some episode durations change. Up to about
  3.3 s longer for files where `ffprobe` under-read (192 kbps, no Xing header, a
  large ID3 tag), and 0.4 s to 0.9 s longer for some 64 kbps and 128 kbps files
  without a header, where `tinytag` reads slightly high. Feeds are rewritten
  with the new values and subscribers may see a different length.
- Known limit: a truncated MP3 with a valid Xing header reports its full
  original length, as `ffprobe` did. The guard does not catch it.
- Known limit: `tinytag` runs up to 0.92 s above the decoded length on
  header-less constant-bitrate files. A larger ID3 tag or a longer file could
  cross 1 s. This is a rounding error for `itunes:duration`.
- Real VBR coverage: three real VBR files with a Xing header were exact. Real
  VBR without a Xing or VBRI header was tested only on one generated file
  (0.46 s short). If such a file turns up more than 1 s off, add a fallback that
  returns `None` or computes from file size and bitrate with a warning.
- Only the five extensions in `Config.MEDIA_TYPES` were tested.
- Trivy shows no CVE gain today; the benefit is size, speed and a smaller
  attack surface.

## References

- `MediaProcessor` in `podcastify/media.py`
- `tests/fixtures/make_audio.sh` and `tests/test_media_processor.py`
- `.github/dependabot.yml`
- [ADR 0003](0003-duration-cache-location.md)
- Issues #46 (spike) and #99 (decision)
