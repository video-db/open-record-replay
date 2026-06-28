"""Re-compile youtube-video-upload with correct June 27 video."""
import asyncio, sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from compiler.compiler import compile_skill
from state import state
import videodb
from config import API_KEY, BASE_URL, COLLECTION_NAME


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

    skill_name = "youtube-video-upload-v3"
    new_video_id = "m-z-019f092a-5964-71e2-85d2-1a260609e519"

    # Fix session metadata to point to correct video
    session_dir = Path.home() / ".mcp-videodb/sessions/1782590657_youtube-video-upload"
    meta_path = session_dir / "metadata.json"
    meta = json.loads(meta_path.read_text())
    print(f"Old video_id in metadata: {meta['video_id']}")
    meta["video_id"] = new_video_id
    meta_path.write_text(json.dumps(meta, indent=2))
    print(f"Updated to: {meta['video_id']}")

    print("\nStarting compilation...")
    skill = await compile_skill(new_video_id, skill_name)

    print(f"\n=== RESULTS ===")
    print(f"Name: {skill['name']}")
    print(f"Scene index: {skill.get('scene_index_id', '?')}")
    print(f"Steps: {len(skill.get('steps', []))}")
    print(f"Inputs: {list(skill.get('inputs', {}).keys())}")
    print(f"Execution strategy: {json.dumps(skill.get('execution_strategy', {}), indent=2)}")
    print(f"Recorded surface: {skill.get('recorded_surface', {})}")

    dark = 0
    for s in skill.get("steps", []):
        esc = s.get("expected_scene", "")
        if any(w in esc.lower() for w in ("can't determine", "blank", "too dark")):
            dark += 1
    print(f"Dark scenes: {dark}/{len(skill.get('steps', []))}")

    for i, s in enumerate(skill.get("steps", [])):
        esc = s.get("expected_scene", "")[:150]
        print(f"  Step {i+1}: {esc}")

    # Restore old metadata
    meta["video_id"] = "m-z-019f0ab1-86dd-7f31-a198-ca43fcf4b380"
    meta_path.write_text(json.dumps(meta, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
