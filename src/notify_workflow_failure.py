from __future__ import annotations

import os

import notifier


def main() -> None:
    run_url = os.getenv("GITHUB_RUN_URL", "")
    workflow = os.getenv("GITHUB_WORKFLOW", "Daily Stock Pipeline")
    ref = os.getenv("GITHUB_REF_NAME", "")
    sha = os.getenv("GITHUB_SHA", "")

    message = "\n".join([
        f"Workflow: {workflow}",
        f"Branch: {ref}",
        f"Commit: {sha[:7]}",
        "Status: failed",
        f"Run: {run_url}",
    ])
    notifier.send_notification("Stock pipeline failed", message, strict=True)


if __name__ == "__main__":
    main()
