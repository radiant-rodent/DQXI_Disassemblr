#!/usr/bin/env python3
"""Readable titles for every parameter table: writes ``game_assets/tables/table_titles.json``.

The Data > Tables list used to show raw file stems (``cs_text``, ``level2d``, ``sp000``) - thousands of them, many
sharing one name. This tool gives each table

* ``title``  - a human name ("Cutscene text - a_010_cs_010", "Monster King Slime - animation sp000");
* ``group``  - a friendly category ("Characters", "Levels - layout", ...);
* ``kind``   - the game's own type name read from the JSON header ("QuestIDParam"), shown as a hint.

Tables with a hand-written schema keep the schema's own title (``tools/table_schemas.json``).

    python tools/table_titles.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKS = ROOT / "game_assets" / "tables" / "packs"
OUT = ROOT / "game_assets" / "tables" / "table_titles.json"
SCHEMAS = ROOT / "tools" / "table_schemas.json"
MAPS = ROOT / "game_assets" / "maps"
MONSTERS = ROOT / "tools" / "monster_names.json"

CHARS = {
    "hero": "Luminary", "camu": "Erik", "sena": "Sylvando", "martina": "Veronica", "veronica": "Veronica",
    "sylvia": "Serena", "rou": "Jade", "graig": "Hendrik", "ex_sena": "Sylvando (alt)",
    "bahatora": "Bahatora", "cheron": "Cheron", "dog": "Dog", "ekkeharuto": "Eckhart", "ema": "Ema",
    "erwin": "Erwin", "hanfuri": "Humphrey", "kinai": "In-game NPC", "kuruchi": "Kuruchi", "ruki": "Luk",
    "ruko": "Lukoo", "sanpo": "Walk partner", "teba": "Teba",
}

# stem -> (title, group). Hand written from what each table holds (the type names and rows confirm these).
NAMES: dict[str, tuple[str, str]] = {
    "achievement": ("Achievements", "Progress"),
    "battle_act_text": ("Battle action messages", "Battle"),
    "battle_zoneparam": ("Battle zones", "Battle"),
    "chara_facial_param": ("Facial expression parameters", "Characters"),
    "chara_mouseorder_param": ("Mouth / lip-sync order", "Characters"),
    "chara_skeletal_param": ("Character skeleton parameters", "Characters"),
    "combination_param": ("Combination (pep power) attacks", "Battle"),
    "cs_chapter_player_visual": ("Cutscene party appearance per chapter", "Cutscenes"),
    "cutscene_chapter_param": ("Cutscene chapters", "Cutscenes"),
    "cutscene_param": ("Cutscene list", "Cutscenes"),
    "dive_progression_cap": ("Dive (Tockle) progress caps", "Minigames"),
    "effect2d_playlist": ("2D effect playlists", "Effects"),
    "effect_playlist": ("Effect playlists", "Effects"),
    "encount_table": ("Random encounters (monster groups per area)", "Monsters"),
    "enemy_AI": ("Monster AI behaviours", "Monsters"),
    "enemy_base": ("Monsters - base stats", "Monsters"),
    "enemy_battle": ("Monsters - battle data", "Monsters"),
    "enemy_category": ("Monster families", "Monsters"),
    "enemy_ecoAct": ("Monster field behaviour (eco actions)", "Monsters"),
    "enemy_pop": ("Monster spawn points", "Monsters"),
    "field_material": ("Field terrain materials (footsteps, etc.)", "World"),
    "gameBGM": ("Background music list", "Audio"),
    "irregular_party_param": ("Irregular party setups", "Characters"),
    "item_add_effect_text": ("Item bonus-effect descriptions", "Items"),
    "jackpot_param": ("Slot jackpot parameters", "Minigames"),
    "layer_item": ("Dungeon layer items", "Items"),
    "level_2dmapEffectVisual": ("2D map weather/effect visuals", "World"),
    "level_2druinEffectVisual": ("2D ruins effect visuals", "World"),
    "level_2dtimeVisual": ("2D map time-of-day visuals", "World"),
    "level_3dBGFog": ("3D background fog", "World"),
    "level_3dBGTime": ("3D background time-of-day", "World"),
    "level_3dCharaTime": ("3D character lighting by time of day", "World"),
    "level_BGM_group_ref": ("Level music groups", "Audio"),
    "level_BGM_param": ("Level music assignments", "Audio"),
    "level_mapType": ("Level map types", "World"),
    "level_weatherVisual": ("Weather visuals", "World"),
    "old_password_bonus": ("Old password bonuses", "Progress"),
    "passive_skill": ("Passive skills (skill-panel bonuses)", "Skills & spells"),
    "password_exp_table": ("Password experience table", "Progress"),
    "past_altar_param": ("Past - altar parameters", "Progress"),
    "past_world_param": ("Past - world parameters", "Progress"),
    "picture_card": ("Picture cards (Tockle cards)", "Items"),
    "player_special_learning": ("Special skills learned by party members", "Skills & spells"),
    "player_visual_param": ("Party member appearance", "Characters"),
    "profile_progress_param": ("Profile progress", "Progress"),
    "present": ("Presents / rewards", "Items"),
    "quest_param": ("Side quests", "Progress"),
    "quest_ui_param": ("Side quest UI", "Progress"),
    "recipe": ("Crafting recipes", "Items"),
    "recipebook": ("Recipe books", "Items"),
    "res_model2d": ("2D model resources", "Resources"),
    "res_model3d": ("3D model resources", "Resources"),
    "res_model3d_sub": ("3D model sub-resources", "Resources"),
    "res_motion_equip": ("Equipment motion resources", "Resources"),
    "res_skelton_param": ("Skeleton resources", "Resources"),
    "respawn_point": ("Respawn points", "World"),
    "revival_point_param": ("Revival points", "World"),
    "riremito_point": ("Return (Zoom) points", "World"),
    "rura_point": ("Fast-travel (Zoom) points", "World"),
    "scenario_battle": ("Scripted (story) battles", "Battle"),
    "scenario_guide": ("Story guide hints", "Progress"),
    "scenario_progress_param": ("Story progress", "Progress"),
    "scenario_restore_param": ("Story restore points", "Progress"),
    "script_message": ("Script messages", "Text"),
    "ship_anchorage_point": ("Ship anchorage points", "World"),
    "skill_param": ("Skills (skill-panel entries)", "Skills & spells"),
    "slot_machine": ("Slot machine", "Minigames"),
    "smith_art_param": ("Forging (smithing) techniques", "Items"),
    "smith_player_param": ("Forging - player parameters", "Items"),
    "special_revival_spell": ("Special revival spells", "Skills & spells"),
    "spell": ("Spells and abilities", "Skills & spells"),
    "spirit_except_atk_weapon": ("Spirit - non-attack weapons", "Minigames"),
    "spirit_hp_range": ("Spirit - HP ranges", "Minigames"),
    "spirit_name_table": ("Spirit names", "Minigames"),
    "spirit_pass_count_bns_upg": ("Spirit - pass-count bonus upgrades", "Minigames"),
    "spirit_weapon_coeff": ("Spirit - weapon coefficients", "Minigames"),
    "tutorial": ("Tutorials", "Text"),
    "ui_profile_text": ("Profile screen text", "Text"),
    "ui_text": ("Interface text", "Text"),
    # battlecmn
    "Player_AI": ("Party AI (tactics)", "Battle"),
    "battleExtraState": ("Extra battle states", "Battle"),
    "battle_2d_bg_param": ("2D battle backgrounds", "Battle"),
    "battle_2d_bossanim_param": ("2D battle boss animations", "Battle"),
    "battle_2d_param": ("2D battle parameters", "Battle"),
    "battle_2ds_appendparam": ("2D battle - appended effects", "Battle"),
    "battle_2ds_appendreaction": ("2D battle - appended reactions", "Battle"),
    "battle_2ds_param": ("2D battle sprite parameters", "Battle"),
    "battle_Message": ("Battle messages", "Battle"),
    "battle_Text": ("Battle text", "Battle"),
    "battle_common": ("Battle - common settings", "Battle"),
    "battle_hitstop_param": ("Battle hit-stop timings", "Battle"),
    "battle_item": ("Battle item use", "Battle"),
    "battle_item_addtional": ("Battle item use - extras", "Battle"),
    "battle_model_load": ("Battle model loading", "Battle"),
    "battle_zone": ("Battle zones (areas)", "Battle"),
    "enemyBattleSound": ("Monster battle sounds", "Monsters"),
    "enemySpecialAttack": ("Monster special attacks", "Monsters"),
    "enemy_action_array": ("Monster action lists", "Monsters"),
    "enemy_battleAction": ("Monster battle actions", "Monsters"),
    "player_battle": ("Party battle parameters", "Battle"),
    "second_check": ("Second-check conditions", "Battle"),
    "supportNPC_AI": ("Support NPC AI", "Battle"),
    # divecmn
    "accessory_table_param": ("Dive - accessory table", "Minigames"),
    "item_box_param": ("Dive - item boxes", "Minigames"),
    "item_table_param": ("Dive - item table", "Minigames"),
    "layer_param": ("Dive - layer parameters", "Minigames"),
    "monster_model_param_2d": ("Dive - 2D monster models", "Minigames"),
    "monster_param": ("Dive - monsters", "Minigames"),
    "monster_table": ("Dive - monster table", "Minigames"),
    # fieldcmn
    "area_drop_param": ("Area item drops", "World"),
    "area_drop_table": ("Area drop table", "World"),
    "bank": ("Bank (Gold Bank) settings", "Shops & services"),
    "battle_location_lottery": ("Battle location lottery", "Battle"),
    "blend_spirit_color_percent": ("Spirit blend - colour chance", "Minigames"),
    "blend_spirit_rarity_up_per": ("Spirit blend - rarity-up chance", "Minigames"),
    "casino_prize": ("Casino prizes", "Minigames"),
    "coinshop": ("Casino coin shop", "Shops & services"),
    "dive_layer_map": ("Dive - layer map", "Minigames"),
    "dummy_player_message": ("Dummy-player messages", "Minigames"),
    "dummy_player_name": ("Dummy-player names", "Minigames"),
    "dummy_player_profile": ("Dummy-player profiles", "Minigames"),
    "dummy_spirit_lottery_table": ("Dummy spirit lottery", "Minigames"),
    "enemy_detection": ("Monster detection ranges", "Monsters"),
    "enemy_field": ("Field monsters", "Monsters"),
    "enemy_field_common": ("Field monsters - common", "Monsters"),
    "field_3d_sea_encount": ("Sea encounters", "Monsters"),
    "field_camera_param": ("Field camera", "World"),
    "field_geography2d_param": ("2D world geography", "World"),
    "field_level_param": ("Field level parameters", "World"),
    "field_time_zone": ("Time-of-day zones", "World"),
    "fixed_drop_param": ("Fixed drops", "Items"),
    "fukubiki": ("Raffle (fukubiki)", "Minigames"),
    "glitter_drop_param": ("Sparkle spot drops", "Items"),
    "glitter_material_table": ("Sparkle spot materials", "Items"),
    "horserace_calc_param": ("Horse racing - calculations", "Minigames"),
    "horserace_rank_param": ("Horse racing - ranks", "Minigames"),
    "inn": ("Inns", "Shops & services"),
    "jack_area_convert": ("Jack area conversion", "World"),
    "jack_map_convert": ("Jack map conversion", "World"),
    "location_cs_ui": ("Location cutscene banners", "Cutscenes"),
    "medal_prize": ("Mini medal prizes", "Shops & services"),
    "metal_party_param": ("Metal slime party parameters", "Monsters"),
    "minigame_category_param": ("Minigame categories", "Minigames"),
    "nelsen_boss": ("Nelsen's boss list", "Minigames"),
    "npc_jockey_visual_param": ("Jockey appearance", "Minigames"),
    "quest_enemy_convert": ("Quest monster conversion", "Progress"),
    "res_gimmick3d_bounds": ("3D gimmick bounds", "World"),
    "shop": ("Shops (stock lists)", "Shops & services"),
    "sp_party_param": ("Special party parameters", "Characters"),
    "spirit_exclusion_weapon": ("Spirit - excluded weapons", "Minigames"),
    "spirit_generator_table": ("Spirit generator", "Minigames"),
    "spirit_lottery_table": ("Spirit lottery", "Minigames"),
    "spirit_passcount_bonus": ("Spirit - pass-count bonus", "Minigames"),
    "spirit_present_param": ("Spirit presents", "Minigames"),
    "spirit_talk_param": ("Spirit talk", "Minigames"),
    "talk_content": ("Party chat contents", "Characters"),
    "talk_emotion_param": ("Chat emotion parameters", "Characters"),
    "talk_flag_end_convert": ("Chat end-flag conversion", "Characters"),
    "talk_party": ("Party chat", "Characters"),
    "talk_party_2d_overwrite": ("Party chat - 2D overrides", "Characters"),
    "training_trial_param": ("Training trials", "Progress"),
    "vehicle_param": ("Vehicles (horse, ship, ...)", "World"),
    "weather_section_param": ("Weather sections", "World"),
    "world2d_area_name": ("2D world area names", "World"),
    # syscmn
    "global_game_flag": ("Global game flags", "Progress"),
    "item": ("Items and equipment", "Items"),
    "item_kana_order": ("Item sort order (kana)", "Items"),
    "level_area": ("Level areas (place names)", "World"),
    "level_map": ("Levels (map list)", "World"),
    "movie_list": ("Movies", "Audio"),
    "ngname": ("Banned name list", "Text"),
    "ngword": ("Banned word list", "Text"),
    "panel": ("Skill panels", "Skills & spells"),
    "panel_line": ("Skill-panel lines", "Skills & spells"),
    "player_initialize": ("New-game party setup", "Characters"),
    "player_rate_param": ("Level-up growth rates", "Characters"),
    "player_spell": ("Spells learned per level", "Skills & spells"),
    "program_param": ("Program parameters", "Resources"),
    "region_param": ("Regions", "World"),
    "save_point": ("Save points", "World"),
    "scenario_id_list": ("Story chapter IDs", "Progress"),
    "scenario_jump": ("Story jump points", "Progress"),
    "sound_arc": ("Sound archives", "Audio"),
    "sound_arc_file": ("Sound archive files", "Audio"),
    "sound_bgm": ("Music tracks", "Audio"),
    "sound_group": ("Sound groups", "Audio"),
    "sound_group_file": ("Sound group files", "Audio"),
    "sound_me": ("Jingles (ME)", "Audio"),
    "sound_se": ("Sound effects", "Audio"),
    "sound_step": ("Footstep sounds", "Audio"),
}

MSG = {
    "bank_msg": "Bank messages", "boushi_msg": "Hat shop messages", "boushi_text": "Hat shop text",
    "casino_prize_msg": "Casino prize messages", "church_msg": "Church messages", "church_text": "Church text",
    "coinshop_msg": "Coin shop messages", "horserace_recept_msg": "Horse race reception messages",
    "horserace_recept_text": "Horse race reception text", "inn_msg": "Inn messages",
    "item_failure_msg": "Item failure messages", "item_msg": "Item messages",
    "jewel_shop_msg": "Jewel shop messages", "mainmenu_msg": "Main menu messages",
    "mainmenu_text": "Main menu text", "medal_prize_msg": "Mini medal prize messages",
    "nelsen_hope_text": "Nelsen hope text", "past_altar_msg": "Past altar messages",
    "post_train_msg": "Post-training messages", "pre_dive_msg": "Pre-dive messages",
}

REGION_LEAF = {"book_ie": "Books", "npc_ie": "NPC dialogue", "npc_list": "NPC list"}
MOTION_LEAF = {
    "battle": "battle motions", "field": "field motions", "cs": "cutscene motions", "cs_ptn": "cutscene patterns",
    "fd_move": "field movement", "fd_ptn": "field patterns", "cs_move": "cutscene movement",
    "battle_hnd": "battle hand motions",
}


def humanize(stem: str) -> str:
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", stem).replace("_", " ").strip()
    return text[:1].upper() + text[1:] if text else stem


def type_of(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            head = fh.read(400)
    except OSError:
        return ""
    m = re.search(r'"type":\s*"([^"]*)"', head)
    return m.group(1) if m else ""


def load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def main() -> None:
    schemas = load(SCHEMAS, {}).get("tables", {})
    labels = load(MAPS / "level_labels.json", {}).get("levels", {})
    areas = load(MAPS / "area_names.json", {})
    monsters = load(MONSTERS, {})

    def place(code: str) -> str:
        info = labels.get(code)
        if info and info.get("place"):
            return f"{info['place']} ({code})"
        return f"{areas[code[:4]]} ({code})" if code[:4] in areas else code

    def monster(code: str) -> str:
        entry = monsters.get(code)
        name = entry[0].replace("_", " ") if entry else ""
        return f"{name} ({code})" if name else code

    out: dict[str, dict[str, str]] = {}
    for path in sorted(PACKS.rglob("*.json")):
        rel = path.relative_to(PACKS).as_posix()
        parts = rel[:-5].split("/")
        stem = parts[-1]
        top = parts[0]
        title, group = None, None
        schema = schemas.get(rel)
        if schema:
            title, group = schema.get("title"), schema.get("category")
        elif top in ("syscmn", "gamecmn", "fieldcmn", "battlecmn", "divecmn") and len(parts) == 2:
            if stem in NAMES:
                title, group = NAMES[stem]
            elif stem.startswith("player_param_"):
                who = CHARS.get(stem[13:].removeprefix("sp_"), stem[13:])
                title = f"{who} - {'special ' if 'sp_' in stem else ''}stats and growth"
                group = "Characters"
            elif stem.startswith("scenario_param_"):
                title, group = f"{CHARS.get(stem[15:], stem[15:])} - story parameters", "Characters"
            elif stem.startswith("another_name_"):
                title, group = f"{CHARS.get(stem[13:], stem[13:])} - alternate names", "Characters"
            elif stem.startswith("story_"):
                title, group = f"Story text - chapter {stem[6:]}", "Text"
        elif top == "level2d" and len(parts) == 3:
            code = parts[1]
            kind = {"level2d": "2D layout", "leveldmap": "dungeon map"}.get(stem, stem)
            title, group = f"{place(code)} - {kind}", "Levels"
        elif top == "level3d" and len(parts) == 3:
            title, group = f"{place(parts[1])} - 3D objects", "Levels"
        elif top == "3d" and len(parts) == 4 and parts[1] == "motion":
            title, group = f"Motions {parts[2]} - {MOTION_LEAF.get(stem, stem)}", "Animation"
        elif top == "3d" and len(parts) == 4 and parts[1] == "model":
            title, group = f"Model {parts[2]} - {stem} set", "Models"
        elif top == "2d":
            mon = next((p for p in parts if re.fullmatch(r"m\d{3}[a-z]?", p)), None)
            if mon:
                title, group = f"Monster {monster(mon)} - animation {stem}", "Monsters"
        elif top == "param" and len(parts) >= 4 and parts[1] == "region":
            title, group = f"Region {parts[2]} - {REGION_LEAF.get(stem, humanize(stem))}", "Regions"
        elif top == "param" and len(parts) >= 4 and parts[1] == "scenario":
            title, group = f"Cutscene text - {parts[3]}", "Text"
        elif top == "param" and len(parts) >= 4 and parts[1] == "talk_party":
            title = f"Party chat {parts[2].removeprefix('talk_party_')} - {'contents' if stem == 'talk_content' else 'lines'}"
            group = "Characters"
        elif top == "script":
            title, group = f"Event script data - {parts[1]}", "Scripts"
        elif top == "ui":
            leaf = MSG.get(stem)
            title = leaf or f"{humanize(stem)} ({parts[1]})"
            group = "Interface"
        if not title:
            title = humanize(stem) + (f" ({'/'.join(parts[:-1])})" if len(parts) > 1 else "")
            group = group or humanize(top)
        out[rel] = {"title": title, "group": group or humanize(top), "kind": type_of(path)}
    OUT.write_text(json.dumps({"format": 1, "tables": out}, indent=1, ensure_ascii=False), encoding="utf-8")
    groups: dict[str, int] = {}
    for v in out.values():
        groups[v["group"]] = groups.get(v["group"], 0) + 1
    print(len(out), "tables;", dict(sorted(groups.items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    main()
