"""Recompile using existing scene index — no video re-indexing."""
import asyncio, sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from compiler.compiler import compile_skill
from state import state
import videodb
from config import API_KEY, BASE_URL, COLLECTION_NAME

VIDEO_ID = "m-z-019f0dd1-b4b1-7b83-89fb-6a8167d9b58a"
SCENE_INDEX_ID = "8cf2dc650538ae21"
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

    print(f"Compiling {SKILL_NAME} using scene index {SCENE_INDEX_ID}...")
    skill = await compile_skill(VIDEO_ID, SKILL_NAME, scene_index_id=SCENE_INDEX_ID)

    print(f"\n=== RESULTS ===")
    print(f"Steps: {len(skill.get('steps', []))}")
    print(f"Inputs: {list(skill.get('inputs', {}).keys())}")

    dark = 0
    dup = 0
    seen_refs = set()
    for i, s in enumerate(skill.get("steps", [])):
        esc = s.get("expected_scene", "")
        fg = (s.get("target") or {}).get("foreground_window", "")
        ref_key = json.dumps(s.get("recording_ref", {}), sort_keys=True)
        if ref_key in seen_refs:
            dup += 1
        seen_refs.add(ref_key)
        dark_kw = ("can't determine", "blank", "too dark", "can't actually see", "no visible")
        if any(w in esc.lower() for w in dark_kw):
            dark += 1
        rf = s.get("recording_ref", {})
        ref = f"[{rf.get('start', 0):.0f}-{rf.get('end', 0):.0f}s]"
        act = s.get("action", "?")
        lbl = (s.get("target") or {}).get("label", "")[:30]
        has_esc = "Y" if s.get("expected_scene") else "N"
        print(f"  {i+1}: {ref} {act} fg={fg[:30]} esc={has_esc} {lbl}")

    print(f"\nDark: {dark}/{len(skill.get('steps', []))}  Dup refs: {dup}")

    md_path = Path.home() / ".mcp-videodb/skills" / SKILL_NAME / "SKILL.md"
    if md_path.exists():
        print(f"\nSKILL.md written to {md_path}")


if __name__ == "__main__":
    asyncio.run(main())
