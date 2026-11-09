#ifndef DQXI_AUDIO_H
#define DQXI_AUDIO_H

#pragma once

#include "types.h"

#define MAX_AUDIO_CHANNELS      32
#define MAX_VOICE_TRACKS        8
#define MAX_SFX_CHANNELS        16
#define CTR_AUDIO_SAMPLE_RATE   32728

/* Stream Audio State (BGM / BCSTM) */
typedef struct StreamAudioContext {
    bool    is_playing;
    bool    is_looping;
    bool    is_paused;
    u16     stream_id;
    u32     sample_rate;
    u32     total_samples;
    u32     loop_start_sample;
    u32     loop_end_sample;
    u32     current_sample;
    f32     volume;
    f32     target_volume;
    f32     fade_step;
} StreamAudioContext;

/* Voice Track for Character Dialogue */
typedef struct VoiceTrack {
    u16     voice_id;
    u8      character_id;
    bool    is_active;
    f32     volume;
    f32     pan;
    u32     priority;
    u32     elapsed_samples;
    u32     total_samples;
} VoiceTrack;

/* Sound Effect Channel */
typedef struct SoundEffectChannel {
    u16     sfx_id;
    bool    is_playing;
    f32     volume;
    f32     pan;
    f32     pitch;
    u32     channel_index;
} SoundEffectChannel;

/* Audio Subsystem Master State */
typedef struct AudioContext {
    bool                is_initialized;
    f32                 master_volume;
    f32                 bgm_volume;
    f32                 se_volume;
    f32                 voice_volume;
    StreamAudioContext  bgm_stream;
    VoiceTrack          voices[MAX_VOICE_TRACKS];
    SoundEffectChannel  sfx[MAX_SFX_CHANNELS];
    u32                 active_sfx_count;
} AudioContext;

/* Core Audio Subsystem Functions */
void Audio_Init(AudioContext *ctx);
bool Audio_PlayBGM(AudioContext *ctx, u16 bgm_id, bool loop, f32 fade_in_sec);
void Audio_StopBGM(AudioContext *ctx, f32 fade_out_sec);
void Audio_UpdateStreams(AudioContext *ctx, f32 delta_time);
bool Audio_PlayVoice(AudioContext *ctx, u16 voice_id, u8 character_id, f32 volume, f32 pan);
void Audio_StopVoice(AudioContext *ctx, u8 character_id);
bool Audio_PlaySFX(AudioContext *ctx, u16 sfx_id, f32 volume, f32 pan, f32 pitch);
void Audio_StopAllSFX(AudioContext *ctx);
void Audio_SetMasterVolume(AudioContext *ctx, f32 volume);

#endif /* DQXI_AUDIO_H */
