"""Generate SKILL.md from latest youtube-video-upload compilation."""
import asyncio, sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from state import state
import videodb
from config import API_KEY, BASE_URL, COLLECTION_NAME
from compiler.md_generator import generate_skill_md
from registry import save_skill


async def main():
    connect_kwargs = {"api_key": API_KEY}
    if BASE_URL:
        connect_kwargs["base_url"] = BASE_URL
    state.conn = videodb.connect(**connect_kwargs)
    collections = state.conn.get_collections()
    existing = next((c for c in collections if c.name == COLLECTION_NAME), None)
    state.coll = state.conn.get_collection(existing.id)

    # Find latest youtube-video-upload SKILL.json
    registry = Path.home() / ".mcp-videodb/skills"
    skill_files = sorted(registry.glob("youtube-video-upload*/SKILL.json"), reverse=True)
    if not skill_files:
        print("No SKILL.json found")
        return

    skill_path = skill_files[0]
    print(f"Reading: {skill_path}")
    skill = json.loads(skill_path.read_text())
    print(f"Name: {skill['name']}")
    print(f"Steps: {len(skill.get('steps', []))}")
    print(f"Inputs: {list(skill.get('inputs', {}).keys())}")

    # Check step details
    for i, s in enumerate(skill.get("steps", [])[:5]):
        print(f"\n--- Step {i+1} ---")
        print(f"  action: {s.get('action')}")
        print(f"  description: {s.get('description', '')[:120]}")
        print(f"  target: {json.dumps(s.get('target', {}))}")
        print(f"  recording_ref: {s.get('recording_ref', {})}")
        print(f"  expected_scene: {s.get('expected_scene', '')[:150]}")

    # Generate MD
    print("\n\n=== GENERATING MD ===")
    try:
        md = await generate_skill_md(skill)
        md_path = skill_path.parent / "SKILL.md"
        md_path.write_text(md, encoding="utf-8")
        print(f"Written to {md_path}")
        print(f"MD length: {len(md)} chars")
        print("\n--- First 500 chars ---")
        print(md[:500])
        print("\n--- Last 500 chars ---")
        print(md[-500:])
    except Exception as e:
        print(f"MD generation error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
