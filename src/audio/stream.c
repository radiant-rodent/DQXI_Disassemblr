/**
 * src/audio/stream.c - Stream Audio Controller (BGM / BCSTM)
 *
 * Implements continuous streaming background music playback, sample loop points,
 * and smooth volume fading.
 */

#include "dqxi.h"
#include "audio.h"

void Audio_Init(AudioContext *ctx) {
    if (!ctx) return;

    ctx->is_initialized = true;
    ctx->master_volume = 1.0f;
    ctx->bgm_volume = 0.8f;
    ctx->se_volume = 0.9f;
    ctx->voice_volume = 1.0f;
    ctx->active_sfx_count = 0;

    /* Initialize BGM stream */
    ctx->bgm_stream.is_playing = false;
    ctx->bgm_stream.is_looping = true;
    ctx->bgm_stream.is_paused = false;
    ctx->bgm_stream.stream_id = 0;
    ctx->bgm_stream.sample_rate = CTR_AUDIO_SAMPLE_RATE;
    ctx->bgm_stream.total_samples = 0;
    ctx->bgm_stream.loop_start_sample = 0;
    ctx->bgm_stream.loop_end_sample = 0;
    ctx->bgm_stream.current_sample = 0;
    ctx->bgm_stream.volume = 0.0f;
    ctx->bgm_stream.target_volume = ctx->bgm_volume;
    ctx->bgm_stream.fade_step = 0.0f;

    /* Initialize voice tracks */
    for (int i = 0; i < MAX_VOICE_TRACKS; i++) {
        ctx->voices[i].voice_id = 0;
        ctx->voices[i].character_id = 0;
        ctx->voices[i].is_active = false;
        ctx->voices[i].volume = 1.0f;
        ctx->voices[i].pan = 0.0f;
        ctx->voices[i].priority = 0;
    }

    /* Initialize sound effects channels */
    for (int i = 0; i < MAX_SFX_CHANNELS; i++) {
        ctx->sfx[i].sfx_id = 0;
        ctx->sfx[i].is_playing = false;
        ctx->sfx[i].channel_index = (u32)i;
    }
}

bool Audio_PlayBGM(AudioContext *ctx, u16 bgm_id, bool loop, f32 fade_in_sec) {
    if (!ctx || bgm_id == 0) return false;

    StreamAudioContext *bgm = &ctx->bgm_stream;
    bgm->stream_id = bgm_id;
    bgm->is_playing = true;
    bgm->is_looping = loop;
    bgm->is_paused = false;
    bgm->current_sample = 0;

    if (fade_in_sec > 0.0f) {
        bgm->volume = 0.0f;
        bgm->target_volume = ctx->bgm_volume;
        bgm->fade_step = ctx->bgm_volume / (fade_in_sec * 60.0f);
    } else {
        bgm->volume = ctx->bgm_volume;
        bgm->target_volume = ctx->bgm_volume;
        bgm->fade_step = 0.0f;
    }

    return true;
}

void Audio_StopBGM(AudioContext *ctx, f32 fade_out_sec) {
    if (!ctx) return;

    StreamAudioContext *bgm = &ctx->bgm_stream;
    if (!bgm->is_playing) return;

    if (fade_out_sec > 0.0f) {
        bgm->target_volume = 0.0f;
        bgm->fade_step = -bgm->volume / (fade_out_sec * 60.0f);
    } else {
        bgm->volume = 0.0f;
        bgm->is_playing = false;
    }
}

void Audio_UpdateStreams(AudioContext *ctx, f32 delta_time) {
    if (!ctx) return;

    StreamAudioContext *bgm = &ctx->bgm_stream;
    if (bgm->is_playing && !bgm->is_paused) {
        /* Advance stream samples */
        u32 samples_to_advance = (u32)(bgm->sample_rate * delta_time);
        bgm->current_sample += samples_to_advance;

        /* Handle loop points */
        if (bgm->is_looping && bgm->loop_end_sample > 0 && bgm->current_sample >= bgm->loop_end_sample) {
            bgm->current_sample = bgm->loop_start_sample + (bgm->current_sample - bgm->loop_end_sample);
        }

        /* Apply volume fade */
        if (bgm->fade_step != 0.0f) {
            bgm->volume += bgm->fade_step;
            if ((bgm->fade_step > 0.0f && bgm->volume >= bgm->target_volume) ||
                (bgm->fade_step < 0.0f && bgm->volume <= bgm->target_volume)) {
                bgm->volume = bgm->target_volume;
                bgm->fade_step = 0.0f;

                if (bgm->volume <= 0.0f) {
                    bgm->is_playing = false;
                }
            }
        }
    }
}
