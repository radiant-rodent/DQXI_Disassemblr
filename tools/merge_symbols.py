import json
from pathlib import Path

SYMBOLS_FILE = Path("symbols.json")
RECOVERED_FILE = Path("symbols_recovered.json")

with open(SYMBOLS_FILE, "r", encoding="utf-8") as f:
    master = json.load(f)

with open(RECOVERED_FILE, "r", encoding="utf-8") as f:
    recovered = json.load(f)

existing_addrs = {s["address"].lower(): s for s in master.get("symbols", [])}

added_count = 0
for hex_addr, name in recovered.items():
    key = hex_addr.lower()
    if key not in existing_addrs:
        # Infer category / description from name
        desc = "Native gameplay engine function"
        if "BGM" in name or "SE" in name or "Sound" in name:
            desc = f"Audio engine: {name}"
        elif "Actor" in name or "NPC" in name or "Player" in name:
            desc = f"Actor/Entity system: {name}"
        elif "Camera" in name:
            desc = f"Camera controller: {name}"
        elif "Fade" in name:
            desc = f"Screen transition / fade: {name}"
        elif "Battle" in name:
            desc = f"Battle engine: {name}"
        elif "Item" in name or "Equip" in name:
            desc = f"Inventory & equipment: {name}"
        elif "Map" in name or "Zone" in name or "Weather" in name:
            desc = f"World & field environment: {name}"
        elif "Message" in name or "Talk" in name or "Dialog" in name:
            desc = f"Dialogue & message window: {name}"

        master["symbols"].append({
            "address": hex_addr,
            "name": name,
            "type": "function",
            "mode": "arm",
            "description": desc,
            "source": "native_engine_table"
        })
        added_count += 1
    else:
        # Update existing name if it was a generic name
        existing = existing_addrs[key]
        if existing["name"].startswith("func_"):
            existing["name"] = name

master["symbols"].sort(key=lambda s: int(s["address"], 16))

with open(SYMBOLS_FILE, "w", encoding="utf-8") as f:
    json.dump(master, f, indent=2)

print(f"Successfully integrated {added_count} newly recovered symbols into symbols.json (Total: {len(master['symbols'])})")
