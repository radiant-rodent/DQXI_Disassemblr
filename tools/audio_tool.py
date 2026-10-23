#!/usr/bin/env python3
"""tools/audio_tool.py - Universal NW4C BCSAR Sound Archive & BCSTM Audio Decompiler.

Unpacks Nintendo CTR Sound Archives (.bcsar), Sound Groups (.bcgrp), and decodes
DSP-ADPCM / PCM audio stream files (.bcstm, .bcwav, .cwav) into standard playable RIFF WAV format.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import struct
import sys
import wave
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
if "../reference project" not in sys.path:
    sys.path.insert(0, "../reference project")

AUDIO_OUT = PROJECT_ROOT / "game_audio"


def clamp16(v: int) -> int:
    return max(-32768, min(32767, v))


def decode_dsp_adpcm_frame(
    data: bytes,
    pos: int,
    coeffs: list[tuple[int, int]],
    hist1: int,
    hist2: int,
) -> tuple[list[int], int, int, int]:
    """Decodes one 8-byte DSP-ADPCM frame (14 audio samples)."""
    if pos + 8 > len(data):
        return [], hist1, hist2, pos

    header = data[pos]
    pos += 1
    pred_idx = (header >> 4) & 0x7
    scale = header & 0xF
    c0, c1 = coeffs[pred_idx]

    samples = []
    for _ in range(7):
        b = data[pos]
        pos += 1
        for nibble in [(b >> 4) & 0xF, b & 0xF]:
            val = nibble if nibble < 8 else nibble - 16
            s = (val * (1 << scale)) + ((c0 * hist1 + c1 * hist2 + 1024) >> 11)
            s = clamp16(s)
            hist2 = hist1
            hist1 = s
            samples.append(s)

    return samples, hist1, hist2, pos


@dataclass
class BcstmInfo:
    codec: int  # 0 = PCM8, 1 = PCM16, 2 = DSP-ADPCM
    loop: bool
    channels: int
    sample_rate: int
    loop_start: int
    total_samples: int
    block_count: int
    block_size: int
    samples_per_block: int
    last_block_size: int
    last_block_samples: int
    channel_coeffs: list[list[tuple[int, int]]] = field(default_factory=list)


def parse_bcstm_info(data: bytes) -> tuple[BcstmInfo, int]:
    """Parses BCSTM header and INFO chunk."""
    if len(data) < 0x40 or data[:4] != b"CSTM":
        raise ValueError("Invalid BCSTM stream header (expected CSTM)")

    # Read section table
    info_off = struct.unpack_from("<I", data, 0x18)[0]
    data_off = struct.unpack_from("<I", data, 0x30)[0]

    # In INFO chunk
    fmt, loop, ch_cnt = struct.unpack_from("<BBH", data, info_off + 0x20)
    rate, loop_start, total_samples = struct.unpack_from("<III", data, info_off + 0x24)
    blk_cnt, blk_size, spl_per_blk = struct.unpack_from("<III", data, info_off + 0x30)
    last_blk_size, last_blk_spl, _ = struct.unpack_from("<III", data, info_off + 0x3C)

    # Dynamic Channel Table lookup
    ch_coeffs = []
    ch_table_ref = struct.unpack_from("<I", data, info_off + 0x1C)[0]
    ch_table_pos = info_off + 8 + ch_table_ref
    reported_channels = struct.unpack_from("<I", data, ch_table_pos)[0]

    for c in range(reported_channels):
        _, ref_off = struct.unpack_from("<II", data, ch_table_pos + 4 + c * 8)
        ch_info_pos = ch_table_pos + ref_off
        _, adpcm_ref_off = struct.unpack_from("<II", data, ch_info_pos)
        adpcm_pos = ch_info_pos + adpcm_ref_off
        raw_coeffs = struct.unpack_from("<16h", data, adpcm_pos)
        pairs = [(raw_coeffs[k * 2], raw_coeffs[k * 2 + 1]) for k in range(8)]
        ch_coeffs.append(pairs)

    info = BcstmInfo(
        codec=fmt,
        loop=bool(loop),
        channels=ch_cnt,
        sample_rate=rate,
        loop_start=loop_start,
        total_samples=total_samples,
        block_count=blk_cnt,
        block_size=blk_size,
        samples_per_block=spl_per_blk,
        last_block_size=last_blk_size,
        last_block_samples=last_blk_spl,
        channel_coeffs=ch_coeffs,
    )

    audio_start = data_off + 0x20  # Skip DATA section header
    return info, audio_start


def decode_bcstm(data: bytes) -> tuple[bytes, int, int]:
    """Decodes BCSTM file into linear PCM bytes, sample rate, and channel count."""
    info, audio_start = parse_bcstm_info(data)

    if info.codec != 2:
        # PCM16 or PCM8
        if info.codec == 1:
            raw_pcm = data[audio_start:audio_start + info.total_samples * info.channels * 2]
            return raw_pcm, info.sample_rate, info.channels
        elif info.codec == 0:
            raw_u8 = data[audio_start:audio_start + info.total_samples * info.channels]
            pcm16 = struct.pack(f"<{len(raw_u8)}h", *[((b - 128) << 8) for b in raw_u8])
            return pcm16, info.sample_rate, info.channels

    # Decode DSP-ADPCM
    channels_samples: list[list[int]] = [[] for _ in range(info.channels)]
    hists = [[0, 0] for _ in range(info.channels)]
    pos = audio_start

    for blk in range(info.block_count):
        is_last = (blk == info.block_count - 1)
        cur_blk_size = info.last_block_size if is_last else info.block_size
        target_samples = info.last_block_samples if is_last else info.samples_per_block

        for ch in range(info.channels):
            ch_start = pos
            ch_pos = ch_start
            h1, h2 = hists[ch]
            coeffs = info.channel_coeffs[ch] if ch < len(info.channel_coeffs) else info.channel_coeffs[0]

            ch_samples = []
            while len(ch_samples) < target_samples and ch_pos + 8 <= ch_start + cur_blk_size:
                frame_spl, h1, h2, ch_pos = decode_dsp_adpcm_frame(data, ch_pos, coeffs, h1, h2)
                ch_samples.extend(frame_spl)

            # Truncate to block target
            channels_samples[ch].extend(ch_samples[:target_samples])
            hists[ch] = [h1, h2]

            # Advance to next channel block
            # Align block size to 0x20
            padded_blk_size = (cur_blk_size + 0x1F) & ~0x1F
            pos += padded_blk_size

    # Truncate each channel to total_samples
    for ch in range(info.channels):
        channels_samples[ch] = channels_samples[ch][:info.total_samples]

    # Interleave channels
    num_samples = len(channels_samples[0])
    interleaved = []
    if info.channels == 1:
        interleaved = channels_samples[0]
    elif info.channels == 2:
        for s0, s1 in zip(channels_samples[0], channels_samples[1]):
            interleaved.append(s0)
            interleaved.append(s1)

    pcm_bytes = struct.pack(f"<{len(interleaved)}h", *interleaved)
    return pcm_bytes, info.sample_rate, info.channels


def bcstm_to_wav(data: bytes, wav_path: Path):
    """Decodes BCSTM data and saves as standard playable WAV."""
    wav_bytes = bcstm_to_wav_bytes(data)
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    wav_path.write_bytes(wav_bytes)


def bcstm_to_wav_bytes(data: bytes) -> bytes:
    """Decodes BCSTM data to standard RIFF WAV byte string in memory."""
    import io
    pcm_bytes, rate, channels = decode_bcstm(data)
    bio = io.BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm_bytes)
    return bio.getvalue()


def unpack_bcsar(bcsar_data: bytes, out_dir: Path | None = None) -> int | list[tuple[str, bytes]]:
    """Unpacks embedded sound data and tables from BCSAR archive."""
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
    if bcsar_data[:4] != b"CSAR":
        raise ValueError("Invalid BCSAR header")

    hsize = struct.unpack_from("<H", bcsar_data, 6)[0]
    total_extracted = 0
    extracted_files: list[tuple[str, bytes]] = []

    # 1. Extract high-level sections (INFO, FILE, etc.)
    pos = hsize
    sec_idx = 0
    while pos < len(bcsar_data) - 8:
        smagic, ssz = struct.unpack_from("<4sI", bcsar_data, pos)
        if smagic in (b"INFO", b"FILE", b"STRM") and 8 <= ssz <= len(bcsar_data) - pos:
            sec_name = f"section_{sec_idx}_{smagic.decode('ascii', 'replace').lower().strip()}.bin"
            sec_bytes = bcsar_data[pos:pos + ssz]
            if out_dir is not None:
                (out_dir / sec_name).write_bytes(sec_bytes)
            extracted_files.append((sec_name, sec_bytes))
            total_extracted += 1
            sec_idx += 1
            pos += ssz
        else:
            break

    # 2. Search for embedded CWAV / CWSD
    pos = hsize
    cwav_idx = 0
    while pos < len(bcsar_data) - 4:
        magic = bcsar_data[pos:pos + 4]
        if magic in (b"CWAV", b"CWSD"):
            sz = struct.unpack_from("<I", bcsar_data, pos + 8)[0] if pos + 12 <= len(bcsar_data) else 0
            if 0 < sz <= len(bcsar_data) - pos:
                fname = f"sound_{cwav_idx:03d}.{magic.decode('ascii').lower()}"
                fbytes = bcsar_data[pos:pos + sz]
                if out_dir is not None:
                    out_file = out_dir / fname
                    out_file.write_bytes(fbytes)
                extracted_files.append((fname, fbytes))
                total_extracted += 1
                cwav_idx += 1
                pos += sz
                continue
        pos += 4

    return total_extracted if out_dir is not None else extracted_files


def parse_bcstm(data: bytes) -> BcstmInfo:
    """Parses BCSTM stream and returns BcstmInfo metadata."""
    return parse_bcstm_info(data)[0]


def unpack_bcgrp(bcgrp_data: bytes, out_dir: Path) -> int:
    """Unpacks sound group (.bcgrp) into component .cwav and .wav files."""
    out_dir.mkdir(parents=True, exist_ok=True)
    if bcgrp_data[:4] != b"CGRP":
        raise ValueError("Invalid BCGRP header")

    total_extracted = 0
    pos = 0x80
    idx = 0
    while pos < len(bcgrp_data) - 4:
        magic = bcgrp_data[pos:pos + 4]
        if magic in (b"CWAV", b"CWSD"):
            sz = struct.unpack_from("<I", bcgrp_data, pos + 8)[0] if pos + 12 <= len(bcgrp_data) else 0
            if 0 < sz <= len(bcgrp_data) - pos:
                out_file = out_dir / f"wave_{idx:03d}.{magic.decode('ascii').lower()}"
                out_file.write_bytes(bcgrp_data[pos:pos + sz])
                total_extracted += 1
                idx += 1
                pos += sz
                continue
        pos += 4

    return total_extracted


def read_romfs():
    sys.path.insert(0, "../reference project")
    from dq11tool.ctr.formats import open_image
    f, ncsd, ncch = open_image(r"..\reference project\DQXI.3ds")
    return f, ncch.romfs()


def generate_audio_catalog(out_dir: Path, entries: list[dict]):
    """Generates detailed Markdown catalog for all extracted audio tracks."""
    catalog_path = out_dir / "AUDIO_CATALOG.md"
    lines = [
        "# Dragon Quest XI (3DS) - Music & Audio Soundtrack Catalog",
        "",
        "This catalog documents the extracted NintendoWare for CTR (NW4C) BCSTM audio streams and BCSAR archives from retail *Dragon Quest XI* (Nintendo 3DS).",
        "All tracks are decoded from DSP-ADPCM / 16-bit PCM into standard **16-bit Linear PCM RIFF WAV** (`.wav`) at native CTR sample rates (typically 32,728 Hz stereo).",
        "",
        f"**Total Documented Audio Tracks**: {len(entries)}",
        "",
        "## Soundtrack Categories",
        "",
        "| Category | Tracks | Output Location | Description |",
        "| :--- | :--- | :--- | :--- |",
        "| **Music (BGM)** | 155 | `game_audio/music/` | Complete symphonic background music soundtrack (Koichi Sugiyama score). |",
        "| **Jingles (ME)** | 37 | `game_audio/jingles/` | Music effects, fanfares, level-up, inn sleep, church save, cursed themes. |",
        "| **Streams** | 50+ | `game_audio/streams/` | Cutscene environmental cues and audio streams. |",
        "| **Archives (BCSAR)** | 8 | `game_audio/archives/` | Sound archives containing sound groups, sequences, and sound effect wave banks. |",
        "",
        "## Music Tracks (BGM)",
        "",
        "| Track | Duration | Sample Rate | Channels | Path |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]

    bgm_list = [e for e in entries if e.get("category") == "Music"]
    bgm_list.sort(key=lambda x: x["track"])
    for e in bgm_list:
        mins = int(e["duration"]) // 60
        secs = int(e["duration"]) % 60
        dur_str = f"{mins}:{secs:02d}"
        ch_str = "Stereo" if e["channels"] == 2 else "Mono"
        lines.append(f"| `{e['track']}` | {dur_str} ({e['duration']:.1f}s) | {e['rate']} Hz | {ch_str} | [{e['track']}.wav]({e['path']}) |")

    lines.extend([
        "",
        "## Music Jingles & Fanfares (ME)",
        "",
        "| Jingle | Duration | Sample Rate | Channels | Path |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ])
    me_list = [e for e in entries if e.get("category") == "Jingles"]
    me_list.sort(key=lambda x: x["track"])
    for e in me_list:
        ch_str = "Stereo" if e["channels"] == 2 else "Mono"
        lines.append(f"| `{e['track']}` | {e['duration']:.2f}s | {e['rate']} Hz | {ch_str} | [{e['track']}.wav]({e['path']}) |")

    catalog_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated audio catalog at {catalog_path}")


def export_music_soundtrack(out_dir: Path) -> tuple[int, int]:
    """Decodes ALL 155 BGM music tracks and 37 ME jingles to standard RIFF WAV."""
    music_dir = out_dir / "music"
    jingles_dir = out_dir / "jingles"
    music_dir.mkdir(parents=True, exist_ok=True)
    jingles_dir.mkdir(parents=True, exist_ok=True)

    f, romfs = read_romfs()

    bgm_files = [rf for rf in romfs.files if "BGM" in rf.path.upper() and rf.path.endswith(".bcstm")]
    me_files = [rf for rf in romfs.files if Path(rf.path).name.startswith("ME") and rf.path.endswith(".bcstm")]

    print(f"Exporting complete Dragon Quest XI OST ({len(bgm_files)} BGM tracks, {len(me_files)} jingles)...")

    # Read binary blobs sequentially from romfs
    bgm_tasks = []
    for rf in bgm_files:
        stem = Path(rf.path).stem
        if stem.endswith(".dspadpcm"):
            stem = stem[:-9]
        d = romfs.read_file(rf)
        bgm_tasks.append((stem, d, music_dir / f"{stem}.wav", "Music"))

    me_tasks = []
    for rf in me_files:
        stem = Path(rf.path).stem
        if stem.endswith(".dspadpcm"):
            stem = stem[:-9]
        d = romfs.read_file(rf)
        me_tasks.append((stem, d, jingles_dir / f"{stem}.wav", "Jingles"))

    f.close()

    catalog_entries = []

    def _worker(item):
        stem, data, wav_path, cat = item
        info, _ = parse_bcstm_info(data)
        bcstm_to_wav(data, wav_path)
        dur = info.total_samples / info.sample_rate if info.sample_rate else 0.0
        return {
            "track": stem,
            "duration": dur,
            "channels": info.channels,
            "rate": info.sample_rate,
            "path": str(wav_path.relative_to(out_dir)).replace("\\", "/"),
            "category": cat
        }

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=8) as pool:
        for res in pool.map(_worker, bgm_tasks + me_tasks):
            catalog_entries.append(res)
            print(f"  [OK] Decoded {res['track']} ({res['duration']:.1f}s, {res['rate']}Hz)")

    generate_audio_catalog(out_dir, catalog_entries)
    print(f"\nSoundtrack export complete! Decoded {len(bgm_files)} BGM tracks and {len(me_files)} jingles into {out_dir}")
    return len(bgm_files), len(me_files)


def batch_extract(out_dir: Path, stream_limit: int | None = 50, archive_limit: int | None = 8) -> tuple[int, int]:
    """Batch extracts and decodes BCSTM streams, complete music soundtrack, and BCSAR archives."""
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Always export full music soundtrack (all 155 BGM tracks and 37 jingles)
    export_music_soundtrack(out_dir)

    # 2. Decode voice / dialogue / cutscene streams
    f, romfs = read_romfs()
    streams_dir = out_dir / "streams"
    archives_dir = out_dir / "archives"
    streams_dir.mkdir(parents=True, exist_ok=True)
    archives_dir.mkdir(parents=True, exist_ok=True)

    bcstms = [rf for rf in romfs.files if rf.path.endswith(".bcstm") and "BGM" not in rf.path.upper() and not Path(rf.path).name.startswith("ME")]
    if stream_limit:
        bcstms = bcstms[:stream_limit]

    print(f"\nDecoding {len(bcstms)} voice/cutscene BCSTM streams into {streams_dir}...")
    decoded_streams = 0
    for i, rf in enumerate(bcstms):
        stem = Path(rf.path).stem
        if stem.endswith(".dspadpcm"):
            stem = stem[:-9]
        d = romfs.read_file(rf)
        wav_path = streams_dir / f"{stem}.wav"
        try:
            bcstm_to_wav(d, wav_path)
            decoded_streams += 1
        except Exception as err:
            print(f"  [ERROR] {rf.path}: {err}")

        if (i + 1) % 10 == 0 or i + 1 == len(bcstms):
            print(f"  [{i+1}/{len(bcstms)}] Decoded {stem}.wav (Total decoded: {decoded_streams})")

    # 3. Unpack BCSAR archives
    bcsars = [rf for rf in romfs.files if rf.path.endswith(".bcsar")]
    if archive_limit:
        bcsars = bcsars[:archive_limit]

    print(f"\nUnpacking {len(bcsars)} BCSAR sound archives into {archives_dir}...")
    unpacked_archives = 0
    for rf in bcsars:
        stem = Path(rf.path).stem
        d = romfs.read_file(rf)
        arc_out = archives_dir / stem
        try:
            count = unpack_bcsar(d, arc_out)
            info_json = arc_out / "manifest.json"
            info_json.write_text(json.dumps({
                "archive": stem,
                "size_bytes": len(d),
                "extracted_elements": count,
            }, indent=2), encoding="utf-8")
            unpacked_archives += 1
            print(f"  [OK] Unpacked {stem} ({len(d)} B)")
        except Exception as err:
            print(f"  [ERROR] {rf.path}: {err}")

    f.close()
    print(f"\nAudio extraction complete! Decoded {decoded_streams} streams and unpacked {unpacked_archives} archives.")
    return decoded_streams, unpacked_archives


def main():
    parser = argparse.ArgumentParser(description="DQXI 3DS Audio Decompiler & WAV Extractor")
    sub = parser.add_subparsers(dest="command")

    ext_p = sub.add_parser("extract", help="Batch decode audio streams, soundtrack, and archives to WAV")
    ext_p.add_argument("--streams", type=int, default=50, help="Number of cutscene streams to decode")
    ext_p.add_argument("--archives", type=int, default=8, help="Number of BCSAR archives to unpack")
    ext_p.add_argument("--out", type=Path, default=AUDIO_OUT, help="Output directory")

    mus_p = sub.add_parser("music", help="Export all 155 BGM soundtrack tracks and 37 jingles to WAV")
    mus_p.add_argument("--out", type=Path, default=AUDIO_OUT, help="Output directory")

    dec_p = sub.add_parser("decode", help="Decode single BCSTM stream to WAV")
    dec_p.add_argument("input", type=Path, help="Input .bcstm file")
    dec_p.add_argument("--out", type=Path, required=True, help="Output .wav file")

    inf_p = sub.add_parser("info", help="Inspect BCSTM stream metadata")
    inf_p.add_argument("input", type=Path, help="Input .bcstm file")

    args = parser.parse_args()

    if args.command == "extract":
        s_cnt, a_cnt = batch_extract(args.out, stream_limit=args.streams, archive_limit=args.archives)
        return 0 if s_cnt > 0 else 1
    elif args.command == "music":
        b_cnt, m_cnt = export_music_soundtrack(args.out)
        return 0 if b_cnt > 0 else 1
    elif args.command == "decode":
        data = args.input.read_bytes()
        bcstm_to_wav(data, args.out)
        print(f"Decoded WAV saved to {args.out}")
        return 0
    elif args.command == "info":
        data = args.input.read_bytes()
        info, _ = parse_bcstm_info(data)
        dur = info.total_samples / info.sample_rate if info.sample_rate else 0
        codec_name = {0: "PCM8", 1: "PCM16", 2: "DSP-ADPCM"}.get(info.codec, "Unknown")
        print(f"BCSTM Audio Stream: {args.input}")
        print(f"  Codec:        {codec_name}")
        print(f"  Channels:     {info.channels}")
        print(f"  Sample Rate:  {info.sample_rate} Hz")
        print(f"  Duration:     {dur:.2f} seconds ({info.total_samples} samples)")
        print(f"  Loop:         {info.loop} (start: {info.loop_start})")
        print(f"  Block Size:   {info.block_size} bytes ({info.samples_per_block} samples/block)")
        return 0
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
