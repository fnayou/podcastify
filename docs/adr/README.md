# Architecture decision records

| ADR | Title | Status |
|---|---|---|
| [0001](0001-root-only-container-runtime.md) | Run container as root | Superseded by 0005 |
| [0002](0002-env-var-contract.md) | Environment variable contract (PORT -> SERVICE_PORT) | Accepted |
| [0003](0003-duration-cache-location.md) | Duration cache location and lifecycle | Accepted, implemented |
| [0004](0004-path-env-vars-are-internal.md) | Container path variables are image defaults, not settings | Accepted |
| [0005](0005-puid-pgid-runtime.md) | PUID/PGID drop with su-exec; pinned `user:` as hardened mode | Accepted |
| [0006](0006-tinytag-for-durations.md) | tinytag for episode durations, ffmpeg removed | Accepted |

## Writing an ADR

- File name: `NNNN-short-title.md`, numbered after the last row of the table.
- Sections: Status, Context, Decision, Consequences, References.
- Refer to code by file and symbol name, never by line number.
- Replace a decision with a new ADR: mark the old one `Superseded by NNNN` with a link, and say `Supersedes NNNN` in the new one.
- Add a row to the table above in the same commit.
