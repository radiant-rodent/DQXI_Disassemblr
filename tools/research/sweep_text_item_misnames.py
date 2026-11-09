"""Build orchestration/naming/refine/out/R_S01.json: renames of item/shop functions misnamed as Text_*."""
import json, re
from pathlib import Path
F = Path('decomp/functions')
# old name -> (new name, confidence, summary, evidence)
REN = {
 'Text_LineCanInsert': ('Shop_CanAffordItem', 0.55, 'Returns non-zero when the item exists and its price (record +0x18) does not exceed the party gold (bag work+0x24A98 +0x28); a negative count skips the check.', 'Item_LookupRecord, then compares bag+0x28 (gold) with the price; sibling of the 9,999,999 cap check.'),
 'Text_LineWouldOverflow': ('maybe_Shop_GoldWouldExceedCap', 0.45, 'Checks the party gold (bag +0x28) plus an amount against the cap 9,999,999 (0x98967F).', 'Constant 0x0098967F = 9,999,999, the gold cap; reads bag work+0x24A98 +0x28.'),
 'Text_LineGetMaxInsertCount': ('maybe_Shop_GetMaxAffordableCount', 0.45, 'Returns party gold (bag +0x28) divided by the item price (record +0x18) via func_0011CFAC, or 0 for an unknown item.', 'Price field +0x18 and gold field bag+0x28 passed to the divide helper.'),
 'Text_LineInsertChars': ('maybe_Shop_BuyItemForMember', 0.4, 'Buys an item: reads its price (+0x18), pays from the bag (func_00613FC0), then for a party member (< 0x1F) places or equips it (Text_LinePlaceCharAt, func_00629890) and refreshes the cells.', 'Price +0x18, bag work+0x24A98, member record func_0035EB98, member index bound 0x1F.'),
 'Text_LineInsertGlyph': ('maybe_Shop_BuyItemToBag', 0.35, 'Shorter buy path: pays the price from the bag (func_00613FC0) and adds the item for the member (func_006115BC / Text_InsertLineChar).', 'Same price/bag pattern as maybe_Shop_BuyItemForMember.'),
 'Text_CanInsertCellChar': ('maybe_Item_CanAddOneMore', 0.35, 'For the item in a member cell (+0xEC): reads the per-item stack limit (+0x45) and returns whether the held count (func_006138D4 on the bag, func_0051B1FC) plus one stays within it.', 'Item_LookupRecord on the cell id, bag work+0x24A98, limit byte +0x45.'),
 'Text_MoveCharBetweenBuffers': ('maybe_Party_MoveEquipmentBetweenMembers', 0.4, 'Moves an equipment item (ids 0xA4..0x9BF or 0xB19..0xB1C) from one active party member to another and refreshes both members cells.', 'Two func_0035EB98 member records, maybe_Party_IsMemberActive, equipment id ranges.'),
 'Text_LinePlaceCharAt': ('maybe_Party_PlaceItemInMemberSlot', 0.35, 'Places an item into a party member slot (func_006292A4/func_006297C8, func_0066C724 for the slot kind).', 'Member record func_0035EB98 plus equip-slot helpers.'),
 'Text_CharList_Sort': ('maybe_Item_SortIdList', 0.45, 'Sorts a u16 item-id list with the item-order comparators (std_introsort_u16_itemName / itemB, maybe_Item_CompareNameOrder).', 'Every callee is an item comparator or item lookup.'),
 'Text_GlyphSet_CollectFromTable': ('maybe_Item_CollectIdsFromBag', 0.35, 'Collects item ids from the bag (work+0x24A98) into a set (Container_GlyphSet_Insert).', 'Item_LookupRecord and the bag offset; the set holds item ids.'),
 'Text_InsertLineChar': ('maybe_Member_RemoveItemAtSlot', 0.45, 'Removes the item in slot `slot` of a party member inventory (24 u16 ids at member+0xEC): an equipped slot (func_006292A4) is unequipped first and the stats refreshed; otherwise the later slots shift down and the last becomes 0xFFFF.', 'Slot bound 0x18, base +0xEC/+0xEE shifted with func_00116A14, 0xFFFF fill at +0x11A.'),
 'Text_SetCellChar': ('maybe_Member_SetItemAtSlot', 0.42, 'Writes an item id into inventory slot `slot` of a party member (member+0xEC + slot*2), unequipping the old item first when the slot is equipped, then compacts the 24 slots.', 'Stores the id at +0xEC; 0x18-slot loop; same unequip path as maybe_Member_RemoveItemAtSlot.'),
 'Text_RefreshCell': ('maybe_Member_UnequipSlotAndRefresh', 0.3, 'Calls maybe_Text_ClearCell on the member slot and, on success, func_00191E3C and Text_ApplyFontRecord (likely a stat refresh); returns 1.', 'Same helper trio as the unequip path of maybe_Member_RemoveItemAtSlot.'),
 'Text_SwapCellChars': ('maybe_Member_SwapInventorySlots', 0.45, 'Swaps the item ids in two party-member inventory slots (member+0xEC + slot*2), unequipping either slot first when it is equipped, then refreshes both members.', 'Exchanges the u16 at +0xEC of the two slot addresses; func_006292A4 equipped checks and maybe_Text_ClearCell before the swap.'),
}
srcs = sorted(Path('orchestration/naming/out').glob('N_*.json')) + sorted(Path('orchestration/naming/refine/out').glob('R_0*.json'))
prev = {}
for p in srcs:
    try: data = json.loads(p.read_text(encoding='utf-8-sig'))
    except Exception: continue
    for e in data if isinstance(data, list) else []:
        if isinstance(e, dict) and 'name' in e: prev[e['name']] = e
out = []
for old, v in REN.items():
    if not v: continue
    new, conf, summ, ev = v
    head = (F / f'{old}.c').read_text(encoding='utf-8')
    addr = re.search(r'Address:\s*(0x[0-9A-Fa-f]+)', head).group(1)
    p = prev.get(old, {})
    sig = p.get('signature', f'u32 {old}(void)').replace(old + '(', new + '(', 1)
    out.append(dict(address='0x' + addr[2:].upper().zfill(8), name=new, signature=sig, params={}, summary=summ,
                    confidence=conf, evidence=ev, previous_name=old,
                    previous_confidence=float(p.get('confidence', 0)), change='corrected'))
    print(out[-1]['address'], old, '->', new, '(sig from', 'proposal)' if p else 'default)')
Path('orchestration/naming/refine/out/R_S01.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
