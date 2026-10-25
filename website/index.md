# fnayou/podcastify

Tiny self-hosted podcast RSS generator: private feeds from your own audio files.

Drop audio files into a folder, add a small YAML file, and Podcastify writes an iTunes-compatible RSS feed. One
container (Caddy and Python) serves the feeds and the media.

!!! note "This site tracks `main`"
    These pages describe the `latest` image and the `main` branch. For an older version, use the
    [GitHub Releases](https://github.com/fnayou/podcastify/releases) and pin that image tag.

## Quick start

```bash
docker run -d --name podcastify \
  -p 8080:8080 \
  -e PUBLIC_BASE_URL=http://localhost:8080 \
  -v "$(pwd)/podcasts:/app/podcasts" \
  -v "$(pwd)/public:/app/public" \
  -v "$(pwd)/cache:/app/.cache" \
  fnayou/podcastify:latest
```

Then add a podcast: follow [Getting Started](getting-started.md).

## Features

- Simple layout: `podcasts/*.yaml` for configs, `public/<name>/` for media and images.
- Episodes are discovered from the folder when you omit the `episodes:` list.
- Durations for MP3, M4A, MP4, OGG and Opus, read with `tinytag`; a file that cannot be read gets no duration tag.
- iTunes fields: author, owner, subtitle, summary, explicit, categories, episode types, seasons.
- Clean XML: stable GUIDs, a self link, and a feed file rewritten only when its content changes.
- Optional index page at `/` that lists your feeds.
- Regenerates by itself when configs or media change, if you set `GENERATE_INTERVAL`.
- One image, no database, no account.

## Example feed

??? example "A generated feed (from the test fixtures, not a live sample)"
    This is the output of the generator for the `basic` fixture of the test suite. Podcastify does not run a public
    demo feed.

    ```xml
    <?xml version='1.0' encoding='utf-8'?>
    <rss xmlns:atom="http://www.w3.org/2005/Atom" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
      <channel>
        <title>Basic Show</title>
        <link>http://localhost:8080</link>
        <atom:link href="http://localhost:8080/basic.xml" rel="self" type="application/rss+xml" />
        <description>A basic show</description>
        <language>en</language>
        <generator>podcastify</generator>
        <lastBuildDate>Wed, 02 Jan 2030 03:04:05 +0000</lastBuildDate>
        <itunes:explicit>false</itunes:explicit>
        <itunes:author>Test Author</itunes:author>
        <itunes:subtitle>Short line</itunes:subtitle>
        <itunes:summary>A basic show</itunes:summary>
        <itunes:owner>
          <itunes:name>Test Author</itunes:name>
          <itunes:email>test@example.com</itunes:email>
        </itunes:owner>
        <itunes:category text="Technology" />
        <itunes:type>episodic</itunes:type>
        <item>
          <guid isPermaLink="false">a59514daa931c150fe2e464fefbc14026372ded3</guid>
          <title>Episode 2</title>
          <pubDate>Thu, 07 Jun 2029 00:00:00 +0000</pubDate>
          <enclosure url="http://localhost:8080/basic/episode2.mp3" length="2000" type="audio/mpeg" />
          <itunes:explicit>false</itunes:explicit>
          <itunes:author>Test Author</itunes:author>
          <itunes:duration>0:42</itunes:duration>
        </item>
        <item>
          <guid isPermaLink="false">basic-guid-1</guid>
          <title>Episode 1</title>
          <description>First episode</description>
          <pubDate>Sun, 06 May 2029 07:08:09 +0000</pubDate>
          <enclosure url="http://localhost:8080/basic/episode1.mp3" length="1000" type="audio/mpeg" />
          <itunes:explicit>false</itunes:explicit>
          <itunes:author>Test Author</itunes:author>
          <itunes:duration>00:10:00</itunes:duration>
          <itunes:summary>First episode</itunes:summary>
          <itunes:season>1</itunes:season>
          <itunes:episode>1</itunes:episode>
          <itunes:episodeType>full</itunes:episodeType>
        </item>
      </channel>
    </rss>
    ```

## Links

- [Getting Started](getting-started.md), [Deployment](deployment.md), [Configuration](configuration.md),
  [How it works](how-it-works.md), [Troubleshooting](troubleshooting.md)
- [GitHub](https://github.com/fnayou/podcastify)
- [Docker Hub](https://hub.docker.com/r/fnayou/podcastify)
- [Releases](https://github.com/fnayou/podcastify/releases)
