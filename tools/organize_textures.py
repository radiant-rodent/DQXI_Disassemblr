import os
import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEXTURES_DIR = PROJECT_ROOT / "game_textures"
READABLE_DIR = TEXTURES_DIR / "by_category"

def categorize_texture(tex_name: str, pkg_name: str) -> tuple[str, str, str]:
    """Returns (category, readable_name, description)."""
    tex_lower = tex_name.lower()
    pkg_lower = pkg_name.lower()
    
    # UI Icons & Cursors
    if "icon" in tex_lower:
        cat = "UI_Icons_and_Markers"
        desc = f"Map marker or interface icon ({tex_name})"
        return cat, f"UI_{tex_name}", desc
    if "cursor" in tex_lower or "arrow" in tex_lower:
        cat = "UI_Icons_and_Markers"
        desc = f"Navigation cursor or indicator ({tex_name})"
        return cat, f"UI_{tex_name}", desc
    if "font" in tex_lower or "txt" in tex_lower:
        cat = "UI_Fonts_and_Text"
        desc = f"Font glyph atlas or text banner ({tex_name})"
        return cat, f"Font_{tex_name}", desc
    
    # Boss / Battle backgrounds
    if pkg_lower.startswith("b"):
        cat = "Battle_Arenas_and_Backgrounds"
        desc = f"Battle combat stage background texture ({tex_name} from {pkg_name})"
        return cat, f"Battle_{pkg_name}_{tex_name}", desc
    
    # Overworld / Field Maps
    if pkg_lower.startswith("m"):
        cat = "Overworld_Field_Maps"
        desc = f"Overworld terrain map tile / texture ({tex_name} from {pkg_name})"
        return cat, f"Field_{pkg_name}_{tex_name}", desc
    
    # Dungeons
    if pkg_lower.startswith("d"):
        cat = "Dungeon_Maps_and_Textures"
        desc = f"Dungeon environment map texture ({tex_name} from {pkg_name})"
        return cat, f"Dungeon_{pkg_name}_{tex_name}", desc
    
    # Town / Scenario Maps
    if pkg_lower.startswith("a"):
        cat = "Town_and_Story_Maps"
        desc = f"Town / settlement layout map texture ({tex_name} from {pkg_name})"
        return cat, f"Town_{pkg_name}_{tex_name}", desc

    return "General_Textures", f"Texture_{pkg_name}_{tex_name}", f"Game texture asset ({tex_name} from {pkg_name})"


def main():
    READABLE_DIR.mkdir(parents=True, exist_ok=True)
    catalog = []

    print(f"Organizing textures in {TEXTURES_DIR} into human-readable directory structure...")
    
    # Iterate through all PNGs in game_textures (skipping by_category)
    png_files = [p for p in TEXTURES_DIR.glob("**/*.png") if "by_category" not in p.parts]
    print(f"Found {len(png_files)} PNG textures to organize...")
    
    for p in png_files:
        tex_name = p.stem
        # pkg_name is grandparent if inside timg/
        pkg_name = p.parent.parent.name if p.parent.name == "timg" else p.parent.name
        
        cat, clean_name, desc = categorize_texture(tex_name, pkg_name)
        
        target_dir = READABLE_DIR / cat
        target_dir.mkdir(parents=True, exist_ok=True)
        
        target_file = target_dir / f"{clean_name}.png"
        shutil.copy2(p, target_file)
        
        # Also copy meta if present
        meta_file = p.with_name(f"{p.stem}.meta.json")
        if meta_file.exists():
            shutil.copy2(meta_file, target_dir / f"{clean_name}.meta.json")
            
        catalog.append({
            "original_file": f"{pkg_name}/{p.name}",
            "category": cat,
            "readable_name": clean_name,
            "description": desc,
            "path": f"game_textures/by_category/{cat}/{clean_name}.png"
        })

    catalog.sort(key=lambda x: (x["category"], x["readable_name"]))

    # Write TEXTURES_CATALOG.md
    catalog_md = TEXTURES_DIR / "TEXTURES_CATALOG.md"
    with open(catalog_md, "w", encoding="utf-8") as f:
        f.write("# Dragon Quest XI (3DS) - Master Human-Readable Textures Catalog\n\n")
        f.write("This catalog maps all extracted texture assets to human-readable categories, interface elements, and map backgrounds.\n\n")
        f.write("| Original Package & File | Category | Human-Readable Name | Description | Path |\n")
        f.write("|---|---|---|---|---|\n")
        for item in catalog[:200]:  # Top 200 catalog entries in summary table
            f.write(f"| `{item['original_file']}` | **{item['category']}** | `{item['readable_name']}` | {item['description']} | [`{item['readable_name']}.png`]({item['path']}) |\n")
        if len(catalog) > 200:
            f.write(f"\n*(And {len(catalog) - 200} more categorized textures in `{READABLE_DIR}`)*\n")

    print(f"Organization complete! Created {len(catalog)} human-readable textures in {READABLE_DIR}")
    print(f"Generated comprehensive catalog: {catalog_md}")


if __name__ == "__main__":
    main()
