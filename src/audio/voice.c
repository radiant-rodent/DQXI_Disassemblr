/**
 * src/audio/voice.c - Character Voice Manager
 *
 * Implements dialogue voice clip allocation, priority preemption, and playback
 * across dedicated voice channels.
 */

#include "dqxi.h"
#include "audio.h"

bool Audio_PlayVoice(AudioContext *ctx, u16 voice_id, u8 character_id, f32 volume, f32 pan) {
    if (!ctx || voice_id == 0) return false;

    /* Find available voice track or preempt lower priority track */
    int target_slot = -1;
    u32 lowest_priority = 0xFFFFFFFF;

    for (int i = 0; i < MAX_VOICE_TRACKS; i++) {
        if (!ctx->voices[i].is_active) {
            target_slot = i;
            break;
        }
        if (ctx->voices[i].priority < lowest_priority) {
            lowest_priority = ctx->voices[i].priority;
            target_slot = i;
        }
    }

    if (target_slot < 0) return false;

    VoiceTrack *track = &ctx->voices[target_slot];
    track->voice_id = voice_id;
    track->character_id = character_id;
    track->is_active = true;
    track->volume = volume * ctx->voice_volume * ctx->master_volume;
    track->pan = pan;
    track->priority = 10;
    track->elapsed_samples = 0;
    track->total_samples = CTR_AUDIO_SAMPLE_RATE * 3; /* Typical 3 second clip */

    return true;
}

void Audio_StopVoice(AudioContext *ctx, u8 character_id) {
    if (!ctx) return;

    for (int i = 0; i < MAX_VOICE_TRACKS; i++) {
        if (ctx->voices[i].is_active && ctx->voices[i].character_id == character_id) {
            ctx->voices[i].is_active = false;
        }
    }
}
