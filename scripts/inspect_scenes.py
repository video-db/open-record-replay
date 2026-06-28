import json
data = json.load(open(r"C:\Users\ASUS\.mcp-videodb\skills\youtube-video-upload-v2\SKILL.json", encoding="utf-8"))
steps = data.get("steps", [])
print(f"Steps: {len(steps)}")
print(f"Inputs: {list(data.get('inputs', {}).keys())}")
print(f"Execution strategy: {data.get('execution_strategy', {})}")
print(f"Recorded surface: {data.get('recorded_surface', {})}")
print()
dark = 0
for i, s in enumerate(steps):
    esc = s.get("expected_scene", "")
    if any(w in esc.lower() for w in ("can't determine", "blank", "too dark")):
        dark += 1
    act = s.get("action", "")
    lbl = s.get("target", {}).get("label", "")
    val = s.get("value", "")
    print(f"Step {i+1} [{act}] label={lbl!r} value={val!r}")
    print(f"  scene: {esc[:200]}...")
    print()
print(f"Dark scenes: {dark}/{len(steps)}")
