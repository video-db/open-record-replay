"""Recompile from scratch with improved scene prompt and all fixes."""
import asyncio, sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from compiler.compiler import compile_skill
from compiler.md_generator import generate_skill_md
from state import state
import videodb
from config import API_KEY, BASE_URL, COLLECTION_NAME

VIDEO_ID = "m-z-019f0dd1-b4b1-7b83-89fb-6a8167d9b58a"
SKILL_NAME = "youtube-video-upload"
SESSION_DIR = "1782643154_youtube-video-upload"


async def main():
    connect_kwargs = {"api_key": API_KEY}
    if BASE_URL:
        connect_kwargs["base_url"] = BASE_URL
    state.conn = videodb.connect(**connect_kwargs)
    collections = state.conn.get_collections()
    existing = next((c for c in collections if c.name == COLLECTION_NAME), None)
    state.coll = state.conn.get_collection(existing.id)
    ws = state.conn.connect_websocket()
    ws_conn = await ws.connect()
    state.ws_connection_id = ws_conn.connection_id

    session_dir = Path.home() / ".mcp-videodb/sessions" / SESSION_DIR
    meta_path = session_dir / "metadata.json"
    meta = json.loads(meta_path.read_text())
    meta["video_id"] = VIDEO_ID
    meta_path.write_text(json.dumps(meta, indent=2))

    video = state.coll.get_video(VIDEO_ID)
    sis = video.list_scene_index()
    si_id = sis[-1]["scene_index_id"] if sis else None
    print(f"Compiling {SKILL_NAME} using scene index {si_id}...")
    skill = await compile_skill(VIDEO_ID, SKILL_NAME, scene_index_id=si_id)

    print(f"\n=== RESULTS ===")
    print(f"Steps: {len(skill.get('steps', []))}")
    print(f"Inputs: {list(skill.get('inputs', {}).keys())}")
    print(f"Scene index: {skill.get('scene_index_id')}")

    dark = 0
    for i, s in enumerate(skill.get("steps", [])):
        esc = s.get("expected_scene", "")
        fg = (s.get("target") or {}).get("foreground_window", "")
        rf = s.get("recording_ref", {})
        ref = f"[{rf.get('start', 0):.0f}-{rf.get('end', 0):.0f}s]"
        act = s.get("action", "?")
        lbl = (s.get("target") or {}).get("label", "")[:30]
        has_esc = "Y" if s.get("expected_scene") else "N"
        sheet = "SHEET" if "spreadsheet" in fg.lower() else ("YT" if "youtube" in fg.lower() or "studio" in fg.lower() else fg[:15])
        dark_kw = ("can't determine", "blank", "too dark", "can't actually see", "no visible")
        if any(w in esc.lower() for w in dark_kw):
            dark += 1
        print(f"  {i+1}: {ref} {act:>5} [{sheet}] esc={has_esc} {lbl}")

    print(f"\nDark: {dark}/{len(skill.get('steps', []))}")

    print(f"\nGenerating SKILL.md...")
    md_content = await generate_skill_md(skill)
    md_path = Path.home() / ".mcp-videodb/skills" / SKILL_NAME / "SKILL.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md_content, encoding="utf-8")
    print(f"\nSKILL.md written to {md_path}")


if __name__ == "__main__":
    asyncio.run(main())
