"""Deploy Ledgerline into a Daytona sandbox and snapshot the green build.

Plan 0001 items 14 and 15. Daytona is where the app runs, not just where its
generated code runs — the sandbox clones this repo, installs it, serves it, and
exposes a preview URL that loads for someone outside the sandbox.

    uv run python scripts/deploy.py            # deploy, verify, snapshot
    uv run python scripts/deploy.py --no-snapshot

Prints the hosted URL on the last line so it can be captured by a caller.
"""

from __future__ import annotations

import pathlib
import sys
import time

import httpx
from daytona import CreateSandboxFromSnapshotParams, Daytona, DaytonaConfig, SessionExecuteRequest

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO = "https://github.com/qte77/2026-08-14-SF-AWS_EnterpriseHack.git"
WORKDIR = "ledgerline"
PORT = 8000
SESSION = "ledgerline-server"


def env_from_dotenv() -> dict[str, str]:
    env = {}
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


RESULTS = ROOT / "daytona_results"


def write_results(record: dict) -> None:
    """Record what was deployed, where, and from which commit.

    The hosted URL is the submission artifact, so it is written to a file rather
    than left in a terminal scrollback.
    """
    import json

    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = record["deployed_at"].replace(":", "").replace("-", "")
    (RESULTS / f"deploy-{stamp}.json").write_text(json.dumps(record, indent=2) + "\n")
    (RESULTS / "latest.json").write_text(json.dumps(record, indent=2) + "\n")

    (RESULTS / "README.md").write_text(
        "# Daytona deploy results\n\n"
        "Written by `scripts/deploy.py`. `latest.json` is the current deploy;\n"
        "`deploy-*.json` are the history.\n\n"
        f"| | |\n|---|---|\n"
        f"| **Hosted URL** | {record['hosted_url']} |\n"
        f"| **Sandbox** | `{record['sandbox_id']}` |\n"
        f"| **Snapshot** | `{record['snapshot'] or '—'}` |\n"
        f"| **Commit** | `{record['commit'][:12]}` on `{record['branch']}` |\n"
        f"| **Target / org** | {record['target']} · `{record['organization_id']}` |\n"
        f"| **Runtime** | {record['python']} |\n"
        f"| **Deployed** | {record['deployed_at']} |\n\n"
        "The sandbox is public, so the URL loads without a token — that is the\n"
        "done-when for plan 0001 item 15. The snapshot is item 14: it restores\n"
        "to this exact build.\n\n"
        "Note: Daytona's `GET /sandbox` list endpoint returns an empty set for\n"
        "this key even while a sandbox is running (`GET /sandbox/{id}` returns\n"
        "the full record). Verify by id, not by list.\n"
    )
    print("  results -> daytona_results/latest.json")


def run(sandbox, cmd: str, cwd: str | None = None, timeout: int = 300) -> str:
    res = sandbox.process.exec(cmd, cwd=cwd, timeout=timeout)
    if res.exit_code != 0:
        raise SystemExit(f"FAILED ({res.exit_code}): {cmd}\n{res.result}")
    return (res.result or "").strip()


def main() -> None:
    env = env_from_dotenv()
    branch = sys.argv[sys.argv.index("--branch") + 1] if "--branch" in sys.argv else "main"
    snapshot = "--no-snapshot" not in sys.argv

    daytona = Daytona(DaytonaConfig(api_key=env["DAYTONA_API_KEY"],
                                    api_url=env.get("DAYTONA_API_URL")))

    print("Creating the deploy sandbox…")
    sandbox = daytona.create(CreateSandboxFromSnapshotParams(
        public=True,
        labels={"app": "ledgerline", "role": "deploy"},
        env_vars={
            # The app creates its own nested sandbox per authorised work order,
            # so it needs the key. It is injected at runtime, never committed.
            "DAYTONA_API_KEY": env["DAYTONA_API_KEY"],
            "DAYTONA_API_URL": env.get("DAYTONA_API_URL", ""),
            "WEBHOOK_SECRET": env.get("WEBHOOK_SECRET", ""),
        },
        auto_stop_interval=0,   # do not stop under us during judging
    ))
    print(f"  sandbox {sandbox.id}")

    try:
        print(f"Cloning {branch}…")
        sandbox.git.clone(REPO, WORKDIR, branch=branch)
        print("  " + run(sandbox, "git log --oneline -1", cwd=WORKDIR))

        print("Installing…")
        python = run(sandbox, "command -v python3 || command -v python")
        run(sandbox, f"{python} -m pip install --quiet -e .", cwd=WORKDIR, timeout=600)
        print(f"  {run(sandbox, f'{python} --version')}")

        # The sandbox gets its own .env; secrets arrive as env vars, not in git.
        run(sandbox, "printf '%s\\n' "
                     "\"DAYTONA_API_KEY=$DAYTONA_API_KEY\" "
                     "\"DAYTONA_API_URL=$DAYTONA_API_URL\" "
                     "\"WEBHOOK_SECRET=$WEBHOOK_SECRET\" > .env", cwd=WORKDIR)

        print("Starting the server…")
        sandbox.process.create_session(SESSION)
        sandbox.process.execute_session_command(SESSION, SessionExecuteRequest(
            command=f"cd {WORKDIR} && PYTHONPATH=src {python} -m uvicorn ledgerline.app:app "
                    f"--host 0.0.0.0 --port {PORT} > server.log 2>&1",
            run_async=True,
        ))

        link = sandbox.get_preview_link(PORT)
        url = getattr(link, "url", str(link))
        print(f"  preview {url}")

        print("Waiting for it to answer…")
        deadline = time.time() + 120
        last = ""
        while time.time() < deadline:
            try:
                r = httpx.get(f"{url}/api/v1/dashboard", timeout=15, follow_redirects=True)
                if r.status_code == 200:
                    print(f"  HTTP 200 · counts {r.json().get('counts')}")
                    break
                last = f"HTTP {r.status_code}"
            except Exception as exc:  # noqa: BLE001 - the server is still booting
                last = f"{type(exc).__name__}"
            time.sleep(3)
        else:
            print(run(sandbox, "cat server.log", cwd=WORKDIR))
            raise SystemExit(f"the deployed app never answered ({last})")

        # Done-when for item 15: it loads for someone outside the sandbox.
        # This process is outside it, so these calls are the proof.
        checks = {
            "/": "Ledgerline",
            "/ui/audit-trail.html": "SHA-256 hash chain",
            "/api/v1/workorders": "[",
        }
        for path, needle in checks.items():
            r = httpx.get(url + path, timeout=20, follow_redirects=True)
            ok = r.status_code == 200 and needle in r.text
            print(f"  {'PASS' if ok else 'FAIL'}  GET {path} -> {r.status_code}")
            if not ok:
                raise SystemExit(f"{path} did not serve as expected")

        snapshot_name = None
        if snapshot:
            sha = run(sandbox, "git rev-parse --short HEAD", cwd=WORKDIR)
            # Snapshot names are unique per organisation, so stamp them —
            # deploying the same commit twice must not fail on the second run.
            snapshot_name = f"ledgerline-{sha}-{time.strftime('%H%M%S', time.gmtime())}"
            print(f"Snapshotting the green build as {snapshot_name}…")
            try:
                sandbox.create_snapshot(snapshot_name, timeout=600)
                print(f"  snapshot {snapshot_name}")
            except Exception as exc:  # noqa: BLE001 - a deploy is still a deploy without one
                snapshot_name = f"FAILED: {type(exc).__name__}"
                print(f"  snapshot failed, deploy stands: {exc}")

        record = {
            "deployed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "hosted_url": url,
            "sandbox_id": sandbox.id,
            "organization_id": getattr(sandbox, "organization_id", None),
            "target": getattr(sandbox, "target", None),
            "snapshot": snapshot_name,
            "commit": run(sandbox, "git rev-parse HEAD", cwd=WORKDIR),
            "branch": branch,
            "python": run(sandbox, f"{python} --version"),
            "port": PORT,
            "public": True,
            "smoke_checks": {p: "200" for p in checks},
        }
        write_results(record)

        print("\n" + "=" * 62)
        print(f"sandbox   {sandbox.id}")
        print(f"HOSTED URL {url}")
    except Exception:
        print(f"\nsandbox {sandbox.id} left running for inspection; "
              f"delete it with: daytona sandbox delete {sandbox.id}")
        raise


if __name__ == "__main__":
    main()
