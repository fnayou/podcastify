# Security policy

## Supported versions

Only the latest release receives security fixes: the `latest` image tag on Docker Hub (`fnayou/podcastify`) and the newest `v*.*.*` git tag.

## Reporting a vulnerability

Do not open a public issue for a vulnerability.

Report it privately through GitHub: open the repository's **Security** tab, choose **Report a vulnerability**, and describe:

- the affected image tag or commit
- what an attacker can do and how
- a minimal way to reproduce it

You will get an acknowledgement as soon as the maintainer sees the report. A fix ships in a new release and is credited in the release notes unless you ask otherwise.

## Scope

In scope: the `podcastify` Python package, the container image and its entrypoint, the shipped Caddy configuration, and the GitHub Actions workflows.

Out of scope: vulnerabilities in upstream base images or packages with no fix available yet. Those are tracked by the image scans and updated through dependency updates.
