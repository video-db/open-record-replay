"""Load recommended tool guidance for generated skills."""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MANIFEST_PATH = Path(__file__).with_name("recommended_tools.json")

FALLBACK_MANIFEST = {
    "version": 1,
    "tools": {
        "browser-use": {
            "display_name": "browser-use",
            "recommended_setup": True,
            "use_when": "Browser workflows where the agent can use the same browser app, account, profile, and page state described by the skill.",
        },
        "chrome-use": {
            "display_name": "chrome-use",
            "recommended_setup": True,
            "use_when": "Codex browser-control plugin for connecting to the user's existing Chromium-family browser session/profile when available.",
        },
        "native_accessibility": {
            "display_name": "Native accessibility controls",
            "recommended_setup": True,
            "use_when": "Visible app replay across desktop apps, browser windows, OS UI, file pickers, and browser chrome.",
            "platforms": {
                "macos": "Accessibility API / AX, System Events, osascript, Finder clipboard, and screencapture",
                "windows": "UI Automation / UIA",
                "linux": "AT-SPI/accessibility APIs",
            },
        },
        "visual_computer_use": {
            "display_name": "Visual computer-use",
            "recommended_setup": True,
            "use_when": "Fallback visible-desktop interaction when structured controls are unavailable.",
        },
    },
    "surfaces": {
        "web_browser": {
            "preferred_tools": ["browser-use", "chrome-use"],
            "fallback_tools": [],
            "guidance": [
                "For browser workflows, first look for browser-use or chrome-use and connect it to the existing browser app/profile/session.",
                "If browser-use/chrome-use is unavailable or cannot connect to the existing browser session, stop and ask the user to enable/connect it. Do not substitute Playwright, a fresh browser profile, or an isolated automation browser.",
            ],
        },
        "desktop_app": {
            "preferred_tools": ["native_accessibility"],
            "fallback_tools": ["visual_computer_use"],
            "guidance": ["Prefer platform-native accessibility controls for desktop app windows and OS UI."],
        },
        "hybrid": {
            "preferred_tools": ["native_accessibility"],
            "fallback_tools": ["visual_computer_use"],
            "guidance": ["Replay the recorded visible app/browser directly with native desktop automation."],
        },
        "terminal": {
            "preferred_tools": ["terminal"],
            "fallback_tools": ["native_accessibility"],
            "guidance": ["Use shell commands for terminal workflows."],
        },
        "file_system": {
            "preferred_tools": ["file_system"],
            "fallback_tools": ["native_accessibility", "visual_computer_use"],
            "guidance": ["Use file-system operations for direct file changes."],
        },
        "unknown": {
            "preferred_tools": ["native_accessibility"],
            "fallback_tools": ["visual_computer_use"],
            "guidance": ["Start with structured native accessibility when available."],
        },
    },
}


def load_tool_manifest(path: Path | None = None) -> dict:
    manifest_path = path or MANIFEST_PATH
    try:
        data = json.loads(manifest_path.read_text())
    except Exception as exc:
        logger.warning("Failed to load recommended tool manifest, using fallback: %s", exc)
        return FALLBACK_MANIFEST.copy()

    if not _is_valid_manifest(data):
        logger.warning("Invalid recommended tool manifest, using fallback")
        return FALLBACK_MANIFEST.copy()
    return data


def surface_tool_guidance(surface: str, manifest: dict | None = None) -> dict:
    data = manifest or load_tool_manifest()
    surfaces = data.get("surfaces", {})
    surface_key = surface if surface in surfaces else "unknown"
    selected = surfaces.get(surface_key, FALLBACK_MANIFEST["surfaces"]["unknown"])
    return {
        "surface": surface_key,
        "preferred_tools": _string_list(selected.get("preferred_tools")),
        "fallback_tools": _string_list(selected.get("fallback_tools")),
        "guidance": _string_list(selected.get("guidance")),
    }


def tool_details(tool_names: list[str], manifest: dict | None = None) -> list[dict]:
    data = manifest or load_tool_manifest()
    tools = data.get("tools", {})
    details = []
    for name in tool_names:
        item = tools.get(name)
        if isinstance(item, dict):
            details.append({"name": name, **item})
        else:
            details.append({"name": name, "display_name": name.replace("_", " "), "recommended_setup": True})
    return details


def _is_valid_manifest(data: object) -> bool:
    if not isinstance(data, dict):
        return False
    if not isinstance(data.get("tools"), dict):
        return False
    surfaces = data.get("surfaces")
    if not isinstance(surfaces, dict):
        return False
    for required_surface in ("web_browser", "desktop_app", "hybrid", "terminal", "file_system", "unknown"):
        if required_surface not in surfaces:
            return False
    return True


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
