"""Smoke-test the macOS AX hook over the production JSONL IPC path."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from capture.ax_client import AxClient  # noqa: E402


async def _run(args):
    hook = ROOT / "capture" / "native" / "ax_hook_darwin.py"
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(hook),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    client = AxClient(proc)
    await client.start(event_handler=lambda event: print(json.dumps({"event": event}, indent=2)))
    try:
        permission = await client.send("check_permissions", {"prompt": args.prompt_permissions})
        print(json.dumps({"check_permissions": permission}, indent=2))

        if args.find:
            result = await client.send(
                "find_element",
                {"type": args.find_type, "label": args.find},
            )
            print(json.dumps({"find_element": result}, indent=2))

        if args.list_type:
            result = await client.send("find_all_elements", {"type": args.list_type})
            print(json.dumps({"find_all_elements": result}, indent=2))

        if args.click_at:
            x, y = args.click_at
            result = await client.send("execute_action", {"action": "click_at", "x": x, "y": y})
            print(json.dumps({"click_at": result}, indent=2))
    finally:
        await client.shutdown()


def main():
    parser = argparse.ArgumentParser(description="Smoke-test the macOS record/replay native hook.")
    parser.add_argument(
        "--prompt-permissions",
        action="store_true",
        help="Ask macOS to show the Accessibility permission prompt when needed.",
    )
    parser.add_argument("--find", help="Find one visible element by label.")
    parser.add_argument("--find-type", default="AXButton", help="Element type for --find.")
    parser.add_argument("--list-type", help="List visible elements of this AX type.")
    parser.add_argument(
        "--click-at",
        nargs=2,
        type=int,
        metavar=("X", "Y"),
        help="Perform a coordinate click through the hook.",
    )
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
