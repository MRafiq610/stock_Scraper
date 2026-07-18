from __future__ import annotations

from datetime import datetime, timezone

import notifier


def main() -> None:
    sent_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    notifier.send_notification(
        "Stock pipeline notification test",
        f"Email notification is configured correctly.\nSent at: {sent_at}",
        strict=True,
    )
    print("notification test completed")


if __name__ == "__main__":
    main()
