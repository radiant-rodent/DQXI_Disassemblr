import os
import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TABLES_DIR = PROJECT_ROOT / "game_tables"
READABLE_DIR = TABLES_DIR / "by_category"

CATEGORY_MAP = {
    # Monsters & Enemies
    "enemy_base": ("Monsters_Bestiary", "Monster_Stats_and_Attributes", "Core monster stats, EXP, Gold, HP, and drop rates"),
    "enemySpecialAttack": ("Monsters_Bestiary", "Monster_Special_Attacks", "Special enemy skill parameters and animations"),
    "enemy_book": ("Monsters_Bestiary", "Defeated_Monster_List", "In-game bestiary catalog and defeat counts"),
    
    # Items, Equipment & Forge
    "item": ("Items_and_Equipment", "Items_Weapons_Armor_Catalog", "All weapons, armor, accessories, and usable items"),
    "item_add_effect_text": ("Items_and_Equipment", "Equipment_Bonus_Effects", "Special passive bonuses for equipment (e.g. +crit, resistances)"),
    "smith_art_param": ("Items_and_Equipment", "FunSize_Forge_Recipes", "Crafting difficulty, base materials, and target perfection levels"),
    
    # Party, Characters & Skills
    "player_spell": ("Characters_and_Skills", "Player_Spells_and_Abilities", "Spells, MP costs, base damage, and healing values"),
    "passive_skill": ("Characters_and_Skills", "Passive_Skill_Trees", "Character builder hexagon grid passive nodes"),
    "panel": ("Characters_and_Skills", "Skill_Panel_Layout", "Positioning coordinates for character skill panels"),
    "player_param_hero": ("Characters_and_Skills", "Hero_Growth_Stats", "Luminary level-up stat progressions (HP, MP, Str, Resilience)"),
    "player_param_camu": ("Characters_and_Skills", "Erik_Growth_Stats", "Erik level-up stat progressions"),
    "player_param_veronica": ("Characters_and_Skills", "Veronica_Growth_Stats", "Veronica level-up stat progressions"),
    "player_param_sena": ("Characters_and_Skills", "Serena_Growth_Stats", "Serena level-up stat progressions"),
    "player_param_sylvia": ("Characters_and_Skills", "Sylvando_Growth_Stats", "Sylvando level-up stat progressions"),
    "player_param_rou": ("Characters_and_Skills", "Rab_Growth_Stats", "Rab level-up stat progressions"),
    "player_param_martina": ("Characters_and_Skills", "Jade_Growth_Stats", "Jade level-up stat progressions"),
    "player_param_graig": ("Characters_and_Skills", "Hendrik_Growth_Stats", "Hendrik level-up stat progressions"),

    # Places, Maps & Travel
    "level_area": ("Places_and_Maps", "World_Regions_and_Areas", "World geographic zones, environmental flags, and level streaming"),
    "level_map": ("Places_and_Maps", "Map_Boundaries_and_Layers", "Map bounds, sub-layers, and camera heights"),
    "rura_point": ("Places_and_Maps", "Zoom_Travel_Locations", "All Zoom (Rula) teleport waypoints and landing coordinates"),
    "revival_point_param": ("Places_and_Maps", "Church_Respawn_Points", "Church confession respawn coordinates upon party defeat"),
    "world2d_area_name": ("Places_and_Maps", "2D_Mode_Map_Labels", "Classic 2D retro mode map and town names"),

    # Quests & Achievements
    "quest_param": ("Quests_and_Achievements", "Side_Quests_List", "All side quests, quest givers, objectives, and rewards"),
    "quest_ui_param": ("Quests_and_Achievements", "Quest_Journal_UI", "Quest log descriptions, completion flags, and icons"),
    "achievement": ("Quests_and_Achievements", "Hero_Accolades_and_Trophies", "All in-game accolades, requirements, and trophy ranks"),
    "scenario_guide": ("Quests_and_Achievements", "Story_Objectives_Guide", "Chronological story chapter objectives and Luminary compass hints"),
    "tutorial": ("Quests_and_Achievements", "Gameplay_Tutorials", "Battle, forging, horse racing, and camp tutorial instructions"),

    # Casino & Minigames
    "horserace_rank_param": ("Casino_and_Minigames", "Gallopolis_Horse_Races", "Race tracks, stamina consumption, and cup prizes"),
    "fukubiki": ("Casino_and_Minigames", "Tombola_Lottery", "Prize tiers and ball probabilities for the Tombola lottery"),
    "training_trial_param": ("Casino_and_Minigames", "AngriLa_Wheel_of_Harma", "Angri-La trials, round limits, and secret technique rewards"),

    # Sound & Audio
    "sound_bgm": ("Audio_Soundtrack", "BGM_Music_Tracks", "Sugiyama orchestral BGM cues, loop points, and volume balances"),
    "sound_se": ("Audio_Soundtrack", "Sound_Effects_Registry", "Combat, UI, environmental, and magic sound effect triggers"),
    "sound_me": ("Audio_Soundtrack", "Music_Jingles_and_Stings", "Level up, quest cleared, victory fanfare, and cursed jingles")
}


def main():
    READABLE_DIR.mkdir(parents=True, exist_ok=True)
    catalog = []

    print(f"Organizing game parameter tables in {TABLES_DIR} into human-readable directory structure...")
    
    # Iterate through all json files across all subdirectories in game_tables (except by_category)
    for p in TABLES_DIR.glob("*/*.json"):
        if "by_category" in p.parts:
            continue
        
        base_stem = p.stem
        subpkg = p.parent.name
        
        if base_stem in CATEGORY_MAP:
            cat, clean_name, desc = CATEGORY_MAP[base_stem]
        else:
            cat = "General_Tables"
            clean_name = f"{subpkg.capitalize()}_{base_stem}"
            desc = f"Internal parameter table: {base_stem} in {subpkg}"

        target_dir = READABLE_DIR / cat
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / f"{clean_name}.json"
        
        shutil.copy2(p, target_file)
        
        catalog.append({
            "original_file": f"{subpkg}/{p.name}",
            "category": cat,
            "readable_name": clean_name,
            "description": desc,
            "path": f"game_tables/by_category/{cat}/{clean_name}.json"
        })

    catalog.sort(key=lambda x: (x["category"], x["readable_name"]))

    # Write TABLES_CATALOG.md
    catalog_md = TABLES_DIR / "TABLES_CATALOG.md"
    with open(catalog_md, "w", encoding="utf-8") as f:
        f.write("# Dragon Quest XI (3DS) - Master Human-Readable Game Tables Catalog\n\n")
        f.write("This catalog maps all binary parameter tables (.bxon) to human-readable names and organized game domains.\n\n")
        f.write("| Internal Table | Category | Human-Readable Name | Description | Path |\n")
        f.write("|---|---|---|---|---|\n")
        for item in catalog:
            f.write(f"| `{item['original_file']}` | **{item['category']}** | `{item['readable_name']}` | {item['description']} | [`{item['readable_name']}.json`]({item['path']}) |\n")

    print(f"Organization complete! Created human-readable tables in {READABLE_DIR}")
    print(f"Generated comprehensive catalog: {catalog_md}")


if __name__ == "__main__":
    main()
