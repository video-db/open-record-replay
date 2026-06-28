"""Test: improved scene prompt — tell VLM to describe every distinct state across the interval's frames."""
import asyncio, sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from state import state
import videodb
from videodb import SceneExtractionType
from config import API_KEY, BASE_URL, COLLECTION_NAME

CURRENT_PROMPT = (
    "For this single moment in time:\n"
    "1. What application, website, page, or screen is visible? Describe the UI layout.\n"
    "2. What text, labels, buttons, fields, data, dropdowns, radio buttons, checkboxes, "
    "or other UI elements are visible on screen? List everything you can read.\n"
    "3. If the user is mid-interaction (clicking, typing, selecting), what element "
    "is being used and what value is being entered or chosen?\n"
    "4. What has visibly changed from a typical idle state -- progress bars, toasts, "
    "modals, highlights, selections, checkmarks appearing, new content loading?\n\n"
    "Describe what IS visible, even when the scene appears static. Never say "
    "\"I can't determine what the user is doing\" or \"blank/too dark\" or "
    "\"upload a clearer screenshot.\" If you can see a window border, a button "
    "outline, or partial text, describe that.\n\n"
    "Use generic terms: say 'a file selection dialog' not 'Windows file picker', "
    "'the browser' not 'Chrome' or 'Brave'. Do not mention the operating system "
    "or browser name unless the UI text itself displays it."
)

IMPROVED_PROMPT = (
    "Multiple frames from this time interval are shown. Describe what you see "
    "in EACH distinct state. If the active browser tab changed across frames "
    "(check the title bar text for clues), or if a different application appeared, "
    "describe each state separately -- do not collapse them into a single summary.\n\n"
    "For each state:\n"
    "1. What application, website, page, or screen is visible? What browser tab "
    "is active? Check the title bar and address bar.\n"
    "2. What text, labels, buttons, fields, data, dropdowns, radio buttons, "
    "checkboxes, or other UI elements are visible? List everything you can read.\n"
    "3. If the user is mid-interaction (clicking, typing, selecting), what element "
    "is being used and what value is being entered or chosen?\n"
    "4. What has visibly changed from a typical idle state -- progress bars, toasts, "
    "modals, highlights, selections, checkmarks appearing, new content loading?\n\n"
    "For example, if one frame shows a video upload page and another frame shows "
    "a spreadsheet or document editor, describe both separately. Never say "
    "\"I can't determine what the user is doing\" or \"blank/too dark\" or "
    "\"upload a clearer screenshot.\" If you can see a window border, a button "
    "outline, or partial text, describe that.\n\n"
    "Use generic terms: say 'a file selection dialog' not 'Windows file picker', "
    "'the browser' not a specific browser name. Do not mention the operating system "
    "or browser name unless the UI text itself displays it."
)

VIDEO_ID = "m-z-019f0dd1-b4b1-7b83-89fb-6a8167d9b58a"
TIME_INTERVAL = 5
FRAME_COUNT = 5


async def index_and_show(label: str, prompt: str) -> list[dict]:
    print(f"\n{'='*60}")
    print(f"Indexing with {label} prompt...")
    print(f"{'='*60}")

    connect_kwargs = {"api_key": API_KEY}
    if BASE_URL:
        connect_kwargs["base_url"] = BASE_URL
    state.conn = videodb.connect(**connect_kwargs)
    all_collections = state.conn.get_collections()
    coll = next((c for c in all_collections if c.name == COLLECTION_NAME), None)
    if not coll:
        col_list = state.conn.get_collections()
        coll = state.conn.get_collection(col_list[0].id)
    state.coll = coll

    video = state.coll.get_video(VIDEO_ID)
    try:
        si_id = video.index_scenes(
            extraction_type=SceneExtractionType.time_based,
            extraction_config={"time": TIME_INTERVAL, "frame_count": FRAME_COUNT},
            prompt=prompt,
        )
    except Exception as e:
        import re
        msg = str(e)
        match = re.search(r"with id (\w+) already exists", msg)
        if match:
            old_id = match.group(1)
            video.delete_scene_index(old_id)
            si_id = video.index_scenes(
                extraction_type=SceneExtractionType.time_based,
                extraction_config={"time": TIME_INTERVAL, "frame_count": FRAME_COUNT},
                prompt=prompt,
            )
        else:
            raise

    for attempt in range(30):
        scenes = video.get_scene_index(si_id)
        if len(scenes) > 0:
            break
        await asyncio.sleep(3)

    print(f"{len(scenes)} scenes:\n")
    for s in scenes:
        desc = s.get("description", "")
        desc_safe = desc.encode("ascii", "replace").decode("ascii")
        start = s.get("start", 0)
        end = s.get("end", 0)
        kw = []
        for k in ("spreadsheet", "sheet", "excel", "document", "editor", "tab", "switch", "data", "cell", "grid", "rows", "columns", "copy"):
            if k in desc.lower():
                kw.append(k)
        tag = f" [{','.join(kw).upper()}]" if kw else ""
        print(f"  [{start:.1f}-{end:.1f}s]{tag}")
        print(f"  {desc_safe[:400]}")
        print()

    return scenes


async def main():
    await index_and_show("CURRENT", CURRENT_PROMPT)
    await index_and_show("IMPROVED", IMPROVED_PROMPT)

    print("\nDone. Compare the two outputs above.")
    print("Look for scenes that mention: spreadsheet, sheet, tab switch, document editor, ")


if __name__ == "__main__":
    asyncio.run(main())
