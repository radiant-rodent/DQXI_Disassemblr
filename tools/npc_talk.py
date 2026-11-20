#!/usr/bin/env python3
"""Export what an NPC says: `game_assets/maps/npc_talks.json`.

Talk text of a region lives in `param/region/rNNN/npc_ie.bxon` (CharacterIEData). Layout (decoded from
`Text_ResolveMessageEntry`, docs/DIALOGUE_FORMAT.md):

    root[ ] 24-byte rows          one per *region character id* (the npc_list row, = the actor's entity id)
      +8  talks_n, +12 -> talks
    talk 16 bytes                 one conditional conversation of that character
      +0 variants_n, +4 -> variants   (played in turn when the NPC is talked to again)
      +8  u32: byte0 flag group, byte1 minimum value of that group, byte2 time-of-day mask
                (1 morning, 2 day, 4 evening, 8 night), byte3 first-time page
      +12 u32: byte0 redirect group (0xFF = none), byte1 redirect index, byte2 redirect mask
    variant 12 bytes              lines_n, -> 28-byte line records, +8 -> block label (UTF-8, e.g. "【はいの場合】"), or 0
    line 28 bytes                 +0x09 u8 (0xFF, or a small number: unknown, probably a gesture), +0x0A u8 what follows the
                                  line: 0 end of the block, 1 next line, 3 a Yes / No question, 2 / 8 / 9 / 128 not decoded,
                                  +0x0C u32 line number inside the conversation, +0x10 speaker string, +0x14 text string

A variant with a label is a *block*: the script switches to it by name with `IEChangeBlock("【はいの場合】")`, usually
after `MessageLoop` returned the answer of a Yes / No question (0 = Yes). r021 character 16, conversation 3: the
question line (+0x0A = 3), then the blocks 【いいえの場合】, 【はいの場合】, 【ラベルＡ】. 365 lines have +0x0A = 3 and the
scripts have 323 `result == 0` branches after a MessageLoop. Unlabelled variants play in turn on repeat talks.
What an answer *does* besides showing a block (flags, fades, quests) is code of the event; `event_info` lists it.

Alongside it records which events the area script starts when that character is addressed
(`TrgRCommand` -> `rg_id == N` -> `StartEvent(...)`), since those replace the default talk.

    python tools/npc_talk.py            writes game_assets/maps/npc_talks.json
    python tools/npc_talk.py set-cond --region 21 --json edits.json   stage edited conversation conditions
"""
from __future__ import annotations

import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "game_assets" / "maps" / "npc_talks.json"


def u32(d: bytes, o: int) -> int:
    return struct.unpack_from("<I", d, o)[0]


def rel(d: bytes, o: int):
    v = u32(d, o)
    return None if v == 0 else o + v


def parse_region(region: int):
    key = f"param/region/r{region:03d}/npc_ie"
    bank_json = ROOT / "game_assets" / "text" / "banks" / f"{key}.json"
    bxon = ROOT / "game_data" / "packs" / "param" / "region" / f"r{region:03d}" / "npc_ie.bxon"
    if not bank_json.exists() or not bxon.exists():
        return None
    doc = json.loads(bank_json.read_text(encoding="utf8"))
    by_offset: dict[tuple[int, str], int] = {}
    for e in doc["entries"]:
        by_offset[(e["offset"], e["role"])] = e["id"]
    d = bxon.read_bytes()
    count, relptr = u32(d, 0x20), u32(d, 0x24)
    root = 0x24 + relptr
    characters: dict[str, dict] = {}
    for i in range(min(count, 0x1000)):
        entry = root + 24 * i
        if entry + 16 > len(d):
            break
        talks_n = u32(d, entry + 8)
        talks_at = rel(d, entry + 12)
        if not talks_n or talks_at is None:
            continue
        talks = []
        for t in range(min(talks_n, 0x1000)):
            tk = talks_at + 16 * t
            variants_n = u32(d, tk)
            variants_at = rel(d, tk + 4)
            cond = u32(d, tk + 8)
            redir = u32(d, tk + 12)
            variants = []
            labels = []
            if variants_n and variants_at is not None:
                for v in range(min(variants_n, 0x1000)):
                    vr = variants_at + 12 * v
                    lines_n = u32(d, vr)
                    lines_at = rel(d, vr + 4)
                    label_at = rel(d, vr + 8)
                    label = None
                    if label_at is not None and label_at < len(d):
                        end = d.find(b"\0", label_at)
                        label = d[label_at:end if end >= 0 else label_at].decode("utf8", "replace") or None
                    labels.append(label)
                    lines = []
                    if lines_n and lines_at is not None:
                        for k in range(min(lines_n, 0x10000)):
                            rec = lines_at + 28 * k
                            sp = rel(d, rec + 0x10)
                            tx = rel(d, rec + 0x14)
                            lines.append({
                                "s": by_offset.get((sp, "speaker")) if sp is not None else None,
                                "e": by_offset.get((tx, "text")) if tx is not None else None,
                                "k": d[rec + 0x0A],  # 0 end, 1 next line, 3 Yes / No question
                            })
                    variants.append(lines)
            talk = {
                "t": t,
                "group": cond & 0xFF,
                "min": (cond >> 8) & 0xFF,
                "time": (cond >> 16) & 0xFF,
                "first": (cond >> 24) & 0xFF,
                "variants": variants,
                "labels": labels,
            }
            if (redir & 0xFF) != 0xFF:
                talk["redirect"] = {"group": redir & 0xFF, "index": (redir >> 8) & 0xFF, "mask": (redir >> 16) & 0xFF}
            talks.append(talk)
        characters[str(i)] = {"talks": talks}
    return {"bank": key, "characters": characters}


RG = re.compile(r"rg_id == (\d+)")
REGION = re.compile(r"IsRegion\((\d+)\)")
START = re.compile(r"StartEvent\((\w+)\)")


def script_events(area: str):
    path = ROOT / "game_assets" / "scripts" / "packs" / "script" / area / "script.decompiled.nut"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf8", errors="replace").splitlines()
    start = next((i for i, l in enumerate(lines) if "function TrgRCommand" in l), None)
    if start is None:
        return []
    out = []
    i = start + 1
    while i < len(lines) and not re.match(r"    function ", lines[i]):
        m = RG.search(lines[i])
        if m:
            rg = int(m.group(1))
            region = REGION.search(lines[i])
            for j in range(i + 1, min(i + 14, len(lines))):
                if RG.search(lines[j]):
                    break
                s = START.search(lines[j])
                if s:
                    out.append({"rg_id": rg, "region": int(region.group(1)) if region else None, "event": s.group(1)})
                    break
        i += 1
    return out


# What a statement of an event does, in plain words (first match wins). Message plumbing is left out.
PLUMBING = re.compile(r"^(IEChangeBlock|MessageLoop|MessageEnd|Message|IEMessageSetup\w*|WaitMessage\w*|WaitAllFade|WaitFrame|TalkAnim\w+|"
                      r"local \w+ = (GetActorID|GetTargetActorID|GetActorRegionCharacterID|MessageLoop)\b|return\b|\}|\{|else\b)")
ACTIONS = [
    (re.compile(r"SetGlobalGameFlag\((\d+), (\d+)\)"), "set game flag {0} to {1}"),
    (re.compile(r"SetQuestFlag\((\d+), (\d+)\)"), "set quest {0} to stage {1}"),
    (re.compile(r"QuestCompletedMessage\((\d+)\)"), "complete quest {0}"),
    (re.compile(r"QuestAcceptMessage\((\d+)\)"), "accept quest {0}"),
    (re.compile(r"SetLevelGroupEnable\((\d+), true\)"), "show level group {0}"),
    (re.compile(r"SetLevelGroupEnable\((\d+), false\)"), "hide level group {0}"),
    (re.compile(r"StartFadeOut\w*\("), "fade the screen out"),
    (re.compile(r"StartFadeIn\w*\("), "fade the screen in"),
    (re.compile(r"(?:AutoAddItemInParty|AddItem\w*)\(([^)]*)\)"), "give item ({0})"),
    (re.compile(r"AddGold\(([^)]*)\)"), "give gold ({0})"),
    (re.compile(r"SubGold\(([^)]*)\)"), "take gold ({0})"),
    (re.compile(r"StartEvent\((\w+)\)"), "start event {0}"),
    (re.compile(r"ChangeMap\w*\(([^)]*)\)"), "go to another map ({0})"),
    (re.compile(r"PlaySE\w*\(([^)]*)\)"), "play sound {0}"),
]


def _describe(stmt: str) -> str | None:
    stmt = stmt.strip().rstrip(";")
    if not stmt or PLUMBING.match(stmt):
        return None
    for rx, text in ACTIONS:
        m = rx.search(stmt)
        if m:
            return text.format(*m.groups())
    return stmt  # unknown call: shown as written


def event_info(area: str, names: set[str]) -> dict:
    """What each event function does around a Yes / No question: {event: {line, asks, yes, no, always, blocks}}.

    The decompiled functions are regular: `local result = MessageLoop(target_id); if (result == 0) { yes } else { no }`.
    `yes` / `no` list the block shown and the other things the branch does; `always` what the event does outside it.
    """
    path = ROOT / "game_assets" / "scripts" / "packs" / "script" / area / "script.decompiled.nut"
    if not path.exists() or not names:
        return {}
    lines = path.read_text(encoding="utf8", errors="replace").splitlines()
    out = {}
    head = re.compile(r"^    function (\w+)\(")
    i = 0
    while i < len(lines):
        m = head.match(lines[i])
        if not m or m.group(1) not in names:
            i += 1
            continue
        name, start = m.group(1), i
        i += 1
        body = []
        while i < len(lines) and not head.match(lines[i]) and lines[i].rstrip() != "}":
            body.append(lines[i])
            i += 1
        info = {"line": start + 1, "asks": False, "yes": [], "no": [], "always": [], "blocks": []}
        branch, depth = None, None
        for raw in body:
            indent = len(raw) - len(raw.lstrip())
            text = raw.strip()
            block = re.search(r'IEChangeBlock\("([^"]*)"\)', text)
            if block and block.group(1) not in info["blocks"]:
                info["blocks"].append(block.group(1))
            if branch is None and re.match(r"if \(result == 0\) \{", text):
                info["asks"], branch, depth = True, "yes", indent
                continue
            if branch and indent == depth and text.startswith("} else"):
                branch = "no"
                continue
            if branch and indent == depth and text == "}":
                branch, depth = None, None
                continue
            target = info[branch] if branch else info["always"]
            if block:
                target.append(f"say block {block.group(1)}")
                continue
            said = _describe(text)
            if said and (not target or target[-1] != said):
                target.append(said)
        out[name] = info
    return out


# English for the chapter titles of syscmn/scenario_id_list (my translation; the game is Japanese only).
CHAPTER_EN = [
    "The Hero Sets Out", "Meeting the Mysterious Young Man", "Setting Out with Erik (Camus)", "The Hero's Homecoming",
    "Meeting Veronica and Serena", "Meeting Sylvando", "Escape from the Port Town", "The Masked Tournament of Octagonia (Grotta)",
    "The Truth of 16 Years Ago", "The Riddle of the Ancient Mural", "The Royal Medal Girls' Academy", "The Mermaid and the Promise",
    "The Kingdom Locked in Ice", "To the Tree of Life (Yggdrasil)", "The Hero at the Bottom of the Sea", "The Last Bastion",
    "Angri-La (Drustan's Homeland)", "Sylvando's Parade", "The Ruined Ocean", "The Giant Star over the Desert", "The Dream of Grief",
    "Octagonia, Paradise on Earth", "The Fate of the Fire Dragon", "Erik Loses His Memory", "A New Journey",
    "The Power to Drive Away the Dark", "The Final Battle with Mordegon (Urnoga)", "A World at Peace", "Third act (after turning back time)",
    "The Crossroads of Fate", "The Last Battle", "Rebuilding Cobblestone (Ishi)", "Jade (Martina) and the King of Heliodor",
    "Rescuing Derk", "Reviving Harima", "The Top-Class Horse Race", "The Defence of Gondolia", "Arachtagon Returns",
    "Irwin and Eleanor Again", "Hendrik and Sylvando's Training", "Kainui in Danger", "The Village Made to Dance",
    "Slaying the Dark Dragon", "The Soul of the Dark Dragon", "Reviving Munbaba", "Reviving Mia (Maya)", "The Rusty Staff",
    "The Training Ground Challenge", "The Demon of the Sea", "The Sword of Kings", "The Legendary Forge Again",
    "Drustan's Hidden Labyrinth", "Ending", "Events in Tickington (Yocchi Village)",
]


def _plain(text: str) -> str:
    """Tagged text -> what the player reads, on one line."""
    text = re.sub(r"\{ruby:([^|}]*)\|[^}]*\}", r"\1", text)
    text = text.replace("{PLAYER}", "\u4e3b\u4eba\u516c")  # 主人公 (the hero)
    text = re.sub(r"\{[^}]*\}", "", text)
    return re.sub(r"\s*\n\s*", " ", text).strip()


def scenarios() -> list[dict]:
    """What a conversation's "story flag" is: the scenario flag of a story chapter.

    The condition group of a talk record is the id a script passes to `SetScenarioFlag(id, stage)` / `GetScenarioFlag`
    (the area scripts set the stages in `OnCutSceneEnd`, i.e. when a cutscene of the chapter has played), and a row of
    `syscmn/scenario_id_list` (54 rows of 12 bytes: -> script area such as "a_010", -> UTF-16 title with ruby codes
    U+0001 base U+0002 reading U+0003, u16). `gamecmn/story_<id>` (UIStoryFlagRelation, the menu's "story so far")
    has one row per stage: 12 bytes with the stage number at +8 and the summary texts; the last text of a row is
    what just happened. Stage 0 = the chapter has begun, 34 = the chapter is over. A flag that was never set reads
    0xFF and matches nothing (Text_ResolveMessageEntry skips it), so "chapter N >= 0" means "chapter N has begun".
    Row 28 has no name or script area: `ScenarioToCPart` in script/common sets it to 34, and 989 conversations ask
    for "28 >= 0", so it marks the third act (the name used here is mine).
    """
    raw = (ROOT / "game_data" / "packs" / "syscmn" / "scenario_id_list.bxon").read_bytes()
    count, base = u32(raw, 0x20), 0x24 + u32(raw, 0x24)
    # where the scripts set each stage
    where: dict[tuple[int, int], dict] = {}
    head = re.compile(r"^    function (\w+)\(")
    scripts = ROOT / "game_assets" / "scripts" / "packs" / "script"
    for path in sorted(scripts.glob("*/script.decompiled.nut")):
        area, fn = path.parent.name, ""
        if area == "common":
            continue
        for n, line in enumerate(path.read_text(encoding="utf8", errors="replace").splitlines(), 1):
            m = head.match(line)
            if m:
                fn = m.group(1)
            for g, v in re.findall(r"SetScenarioFlag\((\d+), (\d+)\)", line):
                where.setdefault((int(g), int(v)), {"area": area, "function": fn, "line": n})
    out = []
    for i in range(count):
        row = base + 12 * i
        a, b = row + u32(raw, row), row + 4 + u32(raw, row + 4)
        ident = raw[a:raw.index(b"\0", a)].decode("ascii", "replace")
        end = b
        while raw[end:end + 2] != b"\0\0":
            end += 2
        title = raw[b:end].decode("utf-16-le", "replace")
        title = re.sub("\x01([^\x02]*)\x02[^\x03]*\x03", r"\1", title)
        stages: dict[str, dict] = {}
        bank = ROOT / "game_assets" / "text" / "banks" / "gamecmn" / f"story_{ident.replace('_', '')}.json"
        table = ROOT / "game_data" / "packs" / "gamecmn" / f"story_{ident.replace('_', '')}.bxon"
        if ident and bank.exists() and table.exists():
            t = table.read_bytes()
            rows, tbase = u32(t, 0x20), 0x24 + u32(t, 0x24)
            last: dict[int, str] = {}
            for e in json.loads(bank.read_text(encoding="utf8"))["entries"]:
                m = re.match(r"row\[(\d+)\]", e.get("location", ""))
                if m and e.get("text"):
                    last[int(m.group(1))] = e["text"]
            for r in range(rows):
                stage = t[tbase + 12 * r + 8]
                if r in last:
                    stages[str(stage)] = {"text": _plain(last[r])}
        for (g, v), w in where.items():
            if g == i:
                stages.setdefault(str(v), {}).update(set_by=w)
        out.append({"id": ident, "title": title, "title_en": CHAPTER_EN[i] if i < len(CHAPTER_EN) else "", "stages": stages})
    return out


def set_conditions(region: int, edits_file: Path) -> int:
    """Stage conversation condition edits of `region`: remember them (build/npc_conditions) and rebuild the bank
    through text_tool.save-mod, which applies them after the text edits."""
    import subprocess
    sys.path.insert(0, str(ROOT))
    from tools import text_tool as T

    key = f"param/region/r{region:03d}/npc_ie"
    edits = json.loads(edits_file.read_text(encoding="utf8"))
    T.CONDITION_DIR.mkdir(parents=True, exist_ok=True)
    (T.CONDITION_DIR / (key.replace("/", "_") + ".json")).write_text(json.dumps(edits), encoding="utf8")
    text_json = T.BUILD_DIR / f"{key}.json"
    if not text_json.exists():
        text_json = ROOT / "game_assets" / "text" / "banks" / f"{key}.json"
    proc = subprocess.run([sys.executable, str(ROOT / "tools" / "text_tool.py"), "save-mod", "--bank", key, "--json", str(text_json)],
                          cwd=ROOT, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    return proc.returncode


def set_structure(region: int, edits_file: Path) -> int:
    """Stage restructured characters of `region` ({"<character id>": model}, tools/npc_ie_edit.py; an empty model
    list entry `null` drops the character's custom structure) and rebuild the bank through text_tool.save-mod."""
    import subprocess
    sys.path.insert(0, str(ROOT))
    from tools import npc_ie_edit
    from tools import text_tool as T

    key = f"param/region/r{region:03d}/npc_ie"
    doc = {k: v for k, v in json.loads(edits_file.read_text(encoding="utf8")).items() if v}
    raw = npc_ie_edit.bank_path(region).read_bytes()
    npc_ie_edit.apply(raw, doc)  # refuse a bad model before anything is staged
    npc_ie_edit.STRUCTURE_DIR.mkdir(parents=True, exist_ok=True)
    (npc_ie_edit.STRUCTURE_DIR / (key.replace("/", "_") + ".json")).write_text(json.dumps(doc, ensure_ascii=False), encoding="utf8")
    text_json = T.BUILD_DIR / f"{key}.json"
    if not text_json.exists():
        text_json = ROOT / "game_assets" / "text" / "banks" / f"{key}.json"
    proc = subprocess.run([sys.executable, str(ROOT / "tools" / "text_tool.py"), "save-mod", "--bank", key, "--json", str(text_json)],
                          cwd=ROOT, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    return proc.returncode


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "set-structure":
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--region", type=int, required=True)
        ap.add_argument("--json", type=Path, required=True)
        a = ap.parse_args()
        return set_structure(a.region, a.json)
    if len(sys.argv) > 1 and sys.argv[1] == "set-cond":
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--region", type=int, required=True)
        ap.add_argument("--json", type=Path, required=True)
        a = ap.parse_args()
        return set_conditions(a.region, a.json)
    regions = {}
    for r in range(1, 26):
        got = parse_region(r)
        if got:
            regions[str(r)] = got
    areas = {}
    events = {}
    base = ROOT / "game_assets" / "scripts" / "packs" / "script"
    for p in sorted(base.iterdir()):
        ev = script_events(p.name)
        if ev:
            areas[p.name] = ev
            info = event_info(p.name, {e["event"] for e in ev})
            if info:
                events[p.name] = info
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"regions": regions, "area_events": areas, "event_info": events, "scenarios": scenarios()}, separators=(",", ":")), encoding="utf8")
    chars = sum(len(r["characters"]) for r in regions.values())
    print(f"{len(regions)} regions, {chars} characters with talk, {sum(len(v) for v in areas.values())} area event hooks -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
