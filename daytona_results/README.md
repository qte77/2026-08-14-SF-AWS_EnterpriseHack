# Daytona deploy results

Written by `scripts/deploy.py`. `latest.json` is the current deploy;
`deploy-*.json` are the history.

| | |
|---|---|
| **Hosted URL** | https://8000-8cff584c-c83c-45cb-a1c8-8b8767705f72.daytonaproxy01.net |
| **Sandbox** | `8cff584c-c83c-45cb-a1c8-8b8767705f72` |
| **Snapshot** | `ledgerline-b312e26-230625` |
| **Commit** | `b312e261c639` on `main` |
| **Target / org** | us · `41484d9a-e2cc-45ab-bc05-8135e3e01d7f` |
| **Runtime** | Python 3.14.4 |
| **Deployed** | 2026-08-14T23:06:33Z |

The sandbox is public, so the URL loads without a token — that is the
done-when for plan 0001 item 15. The snapshot is item 14: it restores
to this exact build.

Note: Daytona's `GET /sandbox` list endpoint returns an empty set for
this key even while a sandbox is running (`GET /sandbox/{id}` returns
the full record). Verify by id, not by list.
