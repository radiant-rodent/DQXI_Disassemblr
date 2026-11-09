# NPC dialogue: how the game picks what a character says

Decoded from `Text_ResolveMessageEntry` (0x15698C, `decomp/readable/functions`), `IEMessageSetup` /
`IEMessageSetupEx` and the area scripts. Exported by `python tools/npc_talk.py` to
`game_assets/maps/npc_talks.json`; shown in the Level Editor's **Dialogue** group (actor Inspector).

## Who talks

`RCommand_talk` (script/common) calls `IEMessageSetup(GetActorRegionCharacterID(target))`; the region
character id is the actor's **entity id** (= row of the region `npc_list`, the same id that picks its model).
Books use `ActorGetRegionBookID` and `book_ie` instead. The text lives in `param/region/r<region+1>/npc_ie.bxon`
(`CharacterIEData`, text bank key `param/region/rNNN/npc_ie`).

## Layout of `npc_ie`

```
root[]  24-byte rows, one per region character id   (+8 talks_n, +12 -> talks)
  talk  16 bytes   = one conditional conversation
    +0  variants_n, +4 -> variants
    +8  u32  byte0 flag group, byte1 minimum value of that group, byte2 time-of-day mask
             (1 morning, 2 day, 4 evening, 8 night; 15 = any), byte3 first-time page
    +12 u32  byte0 redirect group (0xFF = none), byte1 redirect index, byte2 redirect mask
  variant 12 bytes  lines_n, -> 28-byte line records (speaker string +0x10, text string +0x14), +8 offset
```

Selection (mode 0): every talk is tested against the current story flag of its group (the byte-0 group is read
with `func_0066B17C`; group 0 means "always") being at least the minimum, and the time-of-day mask against
the current time zone; the last talk that matches wins. A talk with no variants and a redirect uses the text of
the talk with that group / minimum. `IEMessageSetupEx(rc, 0, serifu_flag, time_flag, exec_count)` is the quest
form used by `SetupQuestMessage` (serifu_flag 3..14 by quest stage).
Variants inside a talk are played one after another on repeat conversations (`GetEventExecCount`).

**Not proven in the emulator**: the exact tie-breaking of the selection and the meaning of the first-time byte
(read from the decompilation only). The text edit itself uses the proven text-bank path (docs/EDITING.md).

## Events

An area script can take over a character: `TrgRCommand(10)` compares `rg_id` (= region character id) and calls
`StartEvent(IE_...)`. Those events show up in the Dialogue group as "Triggers an event" with an **Open script**
button. Events usually still call `IEMessageSetup(rc_id)` and then `IEChangeBlock("...")` to choose a text block,
so editing the character's conversations changes those too.

## Emulator attempts (not proven yet)

A test bank with every `npc_ie` text of region 21 (Heliodor) replaced by `ZZ` was staged and the Player save started
(`talk_test.py` pattern: `build_mod_members`, B presses to skip the welcome, then A). Findings:

* The **church priest does not use `npc_ie`**: pressing A in front of him shows the church bank's lines
  (`Church messages`), unchanged by the edit. Church, shop and inn staff are separate banks.
* Walking left in the nave towards Actor 006 (entity id 182, region 21) and pressing A did not open a dialogue
  in two attempts (position/facing not right). A reliable test needs a street NPC with a known spot in the open
  Heliodor street (`b002_001a`) and a path to it.

### PROVEN: an edited npc_ie line shows in the game

Test event (`script/b002`, love-letter branch, body replaced by `WaitFrame(200); IEMessageSetup(182); MessageLoop(-1);
MessageEnd(); return;`) with every text of `param/region/r021/npc_ie` replaced by `ZZ`: the message window showed
`Z`, `ZZ` (typed out) at frames 3184-3258 of the probe log (`out/emu/probe/tev_99549`). So `IEMessageSetup(character id)`
reads exactly the bank the editor's Dialogue group edits, and a bank rebuilt by `text_tool.rebuild_bank` loads.
Re-run with `StartFadeInDefault(); WaitAllFade();` before the message (`out/emu/probe/tev_99704`): ZZ again at frame 3473 and the scene is visible
(an event that returns without the fade-in leaves the screen black; that was the first test script, not the edit). Not yet proven: that pressing A on the NPC in the street picks the same talk.
