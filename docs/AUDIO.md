# Audio / OST

The complete audio tree is `game_assets/audio/`:

- **155 BGM tracks** in `romfs/sound/str/BGM_*.wav`
- **37 ME jingles** in `romfs/sound/str/ME*.wav`
- 5,877 total WAV files (includes cutscene/voice streams)
- 8 unpacked BCSAR projects in `audio/archives/`

## Viewer

Open **Audio**. The default filter is **OST (155)**. The other filters are:

- **Jingles (37)** — short ME cues
- **Voices/SFX (5,685)** — cutscene/voice streams
- **All (5,877)**

The list is sortable by **Name**, **Length** or **Size** (ascending/descending) and shows exact WAV lengths from the RIFF header. The previous duration bug was a missing
`/8` when converting bits-per-sample to bytes-per-sample; a 59.9-second track was being reported
as 14.9 seconds. `read_wav_info` now computes:

```
frames = data_len / ((bits_per_sample / 8) * channels)
```

A regression test reads `BGM_B01.dspadpcm.wav` and asserts the known 59.87-second duration.

## Catalog

`game_assets/audio/AUDIO_CATALOG.md` lists all 155 BGM and 37 jingle tracks with duration, rate,
channels and path. Regenerate it with:

```powershell
python tools/audio_catalog.py
```

The machine-readable version is `game_assets/audio/ost.json`.

## Playback

The built-in player uses Windows `PlaySoundW`. Use **Open externally** for seeking or for a
player that displays its own timeline.

## Replacing a stream

`tools/bcstm_encode.py` rebuilds a BCSTM around an existing stream template. It keeps the
template INFO/channel tables, switches the stream to linear PCM16, updates sample counts and the
DATA section size, and resamples the replacement WAV if the rate differs.

```powershell
python tools/bcstm_encode.py --template game_data/romfs/sound/str/BGM_B01.dspadpcm.bcstm \
  --wav my_replace.wav --out build/BGM_B01.bcstm
```

The replacement WAV must have the same channel count as the template. The tool refuses templates
whose DATA section is not last (all DQXI streams checked so far are). A round-trip test encodes a
1-second stereo tone and verifies `decode_bcstm` returns the exact PCM.
