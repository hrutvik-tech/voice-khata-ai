/**
 * Manages audio playback for TTS streaming responses.
 *
 * Rules:
 * - Collect binary chunks between audio_start and audio_end into one Blob (audio/mpeg).
 * - Play through one HTMLAudioElement unlocked in start().
 * - Keep the last Blob for replay().
 * - While playing and for 300 ms after, ignore wake detections and send no frames.
 */

export class AudioPlayer {
  constructor() {
    this.audioElement = typeof Audio !== 'undefined' ? new Audio() : null;
    this.chunks = [];
    this.isReceiving = false;
    this.lastAudioBlob = null;
    this.isPlaying = false;
    this.cooldownTimer = null;

    if (this.audioElement) {
      this.audioElement.onplay = () => {
        this.isPlaying = true;
        if (this.cooldownTimer) {
          clearTimeout(this.cooldownTimer);
          this.cooldownTimer = null;
        }
      };

      this.audioElement.onended = () => {
        // Keep isPlaying = true for 300 ms cooldown after audio finishes
        this.cooldownTimer = setTimeout(() => {
          this.isPlaying = false;
          this.cooldownTimer = null;
        }, 300);
      };

      this.audioElement.onerror = () => {
        this.isPlaying = false;
      };
    }
  }

  /**
   * Unlock the audio element within a user tap gesture.
   */
  async unlock() {
    if (!this.audioElement) return;
    try {
      this.audioElement.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=';
      await this.audioElement.play();
      this.audioElement.pause();
      this.audioElement.currentTime = 0;
    } catch (e) {
      // Audio unlock attempted
    }
  }

  startAudio() {
    this.chunks = [];
    this.isReceiving = true;
  }

  addChunk(chunk) {
    if (this.isReceiving) {
      this.chunks.push(chunk);
    }
  }

  async endAudio() {
    this.isReceiving = false;
    if (this.chunks.length === 0) return null;

    const blob = new Blob(this.chunks, { type: 'audio/mpeg' });
    this.lastAudioBlob = blob;
    this.chunks = [];
    await this.playBlob(blob);
    return blob;
  }

  async playBlob(blob) {
    if (!this.audioElement || !blob) return;
    this.isPlaying = true;
    try {
      const url = URL.createObjectURL(blob);
      this.audioElement.src = url;
      await this.audioElement.play();
    } catch (err) {
      console.warn('Playback error:', err);
      this.isPlaying = false;
    }
  }

  async replay() {
    if (this.lastAudioBlob) {
      await this.playBlob(this.lastAudioBlob);
    }
  }

  /**
   * Returns true while audio is actively playing or in the 300 ms cooldown window.
   */
  shouldIgnoreVoice() {
    return this.isPlaying;
  }

  stop() {
    if (this.audioElement) {
      this.audioElement.pause();
      this.audioElement.currentTime = 0;
    }
    this.isPlaying = false;
    if (this.cooldownTimer) {
      clearTimeout(this.cooldownTimer);
      this.cooldownTimer = null;
    }
  }
}

export const defaultPlayer = new AudioPlayer();
