/**
 * src/audio/sound_effects.c - Sound Effects Dispatcher
 *
 * Implements SFX channel allocation, pitch modulation, and 3D stereo panning
 * for battle and field audio cues.
 */

#include "dqxi.h"
#include "audio.h"

bool Audio_PlaySFX(AudioContext *ctx, u16 sfx_id, f32 volume, f32 pan, f32 pitch) {
    if (!ctx || sfx_id == 0) return false;

    /* Find inactive SFX channel */
    int slot = -1;
    for (int i = 0; i < MAX_SFX_CHANNELS; i++) {
        if (!ctx->sfx[i].is_playing) {
            slot = i;
            break;
        }
    }

    /* Fallback: reuse slot 0 */
    if (slot < 0) {
        slot = 0;
    }

    SoundEffectChannel *ch = &ctx->sfx[slot];
    ch->sfx_id = sfx_id;
    ch->is_playing = true;
    ch->volume = volume * ctx->se_volume * ctx->master_volume;
    ch->pan = pan;
    ch->pitch = pitch;

    if (slot >= (int)ctx->active_sfx_count) {
        ctx->active_sfx_count = slot + 1;
    }

    return true;
}

void Audio_StopAllSFX(AudioContext *ctx) {
    if (!ctx) return;

    for (int i = 0; i < MAX_SFX_CHANNELS; i++) {
        ctx->sfx[i].is_playing = false;
        ctx->sfx[i].sfx_id = 0;
    }
    ctx->active_sfx_count = 0;
}

void Audio_SetMasterVolume(AudioContext *ctx, f32 volume) {
    if (!ctx) return;
    if (volume < 0.0f) volume = 0.0f;
    if (volume > 1.0f) volume = 1.0f;
    ctx->master_volume = volume;
}
