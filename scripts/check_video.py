import asyncio, sys
sys.path.insert(0, ".")
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

    video = state.coll.get_video("m-z-019f092a-5964-71e2-85d2-1a260609e519")
    scenes = video.get_scene_index("104f301a36aaf718")
    print(f"Scene index 104f301a36aaf718: {len(scenes)} scenes")
    for i, s in enumerate(scenes):
        desc = s.get("description", "")[:100]
        print(f"  [{s.get('start',0):.1f}-{s.get('end',0):.1f}s] {desc}")

asyncio.run(main())
