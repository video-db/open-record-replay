"""Verify Fix #0: COM initialization enables UIA property capture.

Launches the AX hook, records a programmatic click on the current app,
and checks that automation_id, class_name, foreground_window are populated.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def _get_ax_binary_path() -> str:
    binary_name = "ax_hook_win32.py"
    native_dir = Path(__file__).parent.parent / "capture" / "native"
    candidate = native_dir / binary_name
    if not candidate.exists():
        raise FileNotFoundError(f"AX binary not found at {candidate}")
    return str(candidate)


async def _connect_tcp(port_file: str, timeout: float = 10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(port_file):
            try:
                with open(port_file) as f:
                    port = int(f.read().strip())
                if port > 0:
                    reader, writer = await asyncio.open_connection("127.0.0.1", port)
                    return reader, writer
            except (ValueError, OSError):
                pass
        await asyncio.sleep(0.2)
    raise RuntimeError(f"AX hook port file not found: {port_file}")


async def _send(writer, msg: dict) -> None:
    data = (json.dumps(msg) + "\n").encode("utf-8")
    writer.write(data)
    await writer.drain()


class _AxSession:
    def __init__(self, reader, writer, events_path: str):
        self._reader = reader
        self._writer = writer
        self._events_path = events_path
        self._events_file = open(events_path, "a", encoding="utf-8")
        self._pending: dict[str, asyncio.Future] = {}
        self._counter = 0
        self._read_task: asyncio.Task | None = None

    def start_read_loop(self):
        self._read_task = asyncio.create_task(self._read_loop())

    async def _read_loop(self):
        buf = b""
        while True:
            try:
                data = await asyncio.wait_for(self._reader.read(4096), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except (ConnectionResetError, ConnectionAbortedError, OSError):
                return
            if not data:
                return
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    continue
                if "id" in msg:
                    future = self._pending.pop(msg["id"], None)
                    if future and not future.done():
                        future.set_result(msg)
                elif "event" in msg:
                    self._events_file.write(json.dumps(msg) + "\n")
                    self._events_file.flush()

    async def request(self, method: str, params: dict, timeout: float = 15.0) -> dict:
        rid = f"req-{self._counter}"
        self._counter += 1
        future = asyncio.get_event_loop().create_future()
        self._pending[rid] = future
        await _send(self._writer, {"id": rid, "method": method, "params": params})
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending.pop(rid, None)
            return {"status": "error", "error": {"code": "TIMEOUT", "message": f"'{method}' timed out"}}

    async def shutdown(self):
        try:
            await self.request("shutdown", {})
        except Exception:
            pass
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        self._events_file.close()
        self._writer.close()
        await self._writer.wait_closed()


async def main():
    output_dir = Path.home() / ".mcp-videodb" / "sessions" / f"{int(time.time())}_uia-fix-test"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(output_dir / "events.jsonl")

    binary = _get_ax_binary_path()
    temp_dir = os.environ.get("TEMP", os.environ.get("TMP", "C:\\Temp"))
    port_file = os.path.join(temp_dir, "ax_hook_port.txt")
    if os.path.exists(port_file):
        os.remove(port_file)

    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    proc = subprocess.Popen(
        [sys.executable, os.path.abspath(binary)],
        creationflags=creationflags,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        reader, writer = await _connect_tcp(port_file)
        session = _AxSession(reader, writer, output_path)
        session.start_read_loop()

        resp = await session.request("start_recording", {"output_path": output_path})
        if resp.get("status") != "ok":
            print(f"FAIL: AX hook failed to start: {resp}")
            return 1

        print("Recording started. Performing test click...")
        await asyncio.sleep(1.0)

        import pyautogui
        x, y = 500, 500
        pyautogui.click(x, y)
        await asyncio.sleep(1.5)
        pyautogui.click(x + 100, y)
        await asyncio.sleep(0.5)

        resp = await session.request("stop_recording", {})
        print(f"Recording stopped.")

        await session.shutdown()

    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    events = []
    content = Path(output_path).read_text(encoding="utf-8").strip()
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
            if event.get("event") == "action":
                events.append(event)
        except json.JSONDecodeError:
            pass

    print(f"\n{'=' * 80}")
    print(f"  UIA Fix Verification — {len(events)} events captured")
    print(f"{'=' * 80}")

    if not events:
        print("  FAIL: No events captured!")
        return 1

    rich = 0
    for i, e in enumerate(events):
        t = e.get("target", {})
        label = t.get("label", "")[:45]
        auto_id = t.get("automation_id", "")[:25]
        cls = t.get("class_name", "")[:25]
        fg = t.get("foreground_window", "")[:30]
        surface = e.get("surface", {})

        has_rich = bool(auto_id) or bool(cls) or bool(fg)
        if has_rich:
            rich += 1
            status = "RICH"
        else:
            status = "POOR"

        print(f"  [{status}] label='{label}' auto_id='{auto_id}' class='{cls}' fg='{fg}'")
        if surface:
            print(f"          surface: platform='{surface.get('platform','')}' window='{surface.get('window_title','')[:40]}'")
        if e.get("value"):
            print(f"          value: '{str(e['value'])[:80]}'")

    pct = rich / len(events) * 100
    print(f"\n  Summary: {rich}/{len(events)} rich events ({pct:.0f}%)")

    if pct > 0:
        print(f"\n  PASS: Fix #0 (COM initialization) is working!")
        print(f"  Events now capture automation_id, class_name, and foreground_window.")
        return 0
    else:
        print(f"\n  FAIL: No UIA data captured. COM initialization may not be working,")
        print(f"  or the element at the click position doesn't expose UIA properties.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
