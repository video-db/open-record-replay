"""Re-compile the youtube-video-upload recording with new scene index prompt."""
import asyncio
import sys
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
    if existing:
        state.coll = state.conn.get_collection(existing.id)
    else:
        state.coll = state.conn.create_collection(
            name=COLLECTION_NAME,
            description="MCP Record & Replay recordings",
        )
    ws = state.conn.connect_websocket()
    ws_conn = await ws.connect()
    state.ws_connection_id = ws_conn.connection_id

    print("Connected. Starting compilation...")
    skill = await compile_skill(
        "m-z-019f0ab1-86dd-7f31-a198-ca43fcf4b380",
        "youtube-video-upload-v2",
    )
    print(f"Compiled: {skill['name']}")
    print(f"Scene index: {skill.get('scene_index_id', '?')}")
    print(f"Steps: {len(skill.get('steps', []))}")
    print(f"Inputs: {list(skill.get('inputs', {}).keys())}")
    print(f"Execution strategy: {skill.get('execution_strategy', {})}")
    print(f"Recorded surface: {skill.get('recorded_surface', {})}")

    dark = 0
    for s in skill.get("steps", []):
        esc = s.get("expected_scene", "")
        if any(w in esc.lower() for w in ("can't determine", "blank", "too dark")):
            dark += 1
    print(f"Dark scenes: {dark}/{len(skill.get('steps', []))}")

    # Show a few scene samples
    for i, s in enumerate(skill.get("steps", [])[:5]):
        esc = s.get("expected_scene", "")[:120]
        print(f"  Step {i+1}: {esc}...")


if __name__ == "__main__":
    asyncio.run(main())
