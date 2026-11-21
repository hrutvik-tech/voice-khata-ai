import { WebVoiceProcessor } from '@picovoice/web-voice-processor';

const subscribers = new Set();
let isSubscribed = false;

/**
 * Converts an incoming Int16Array of samples to exactly 512 samples at 16 kHz,
 * emitted as a 1,024-byte little-endian ArrayBuffer.
 */
export function processFrame(inputFrame) {
  let samples = inputFrame;
  if (!samples || samples.length !== 512) {
    const fixed = new Int16Array(512);
    if (samples) {
      fixed.set(samples.subarray(0, Math.min(samples.length, 512)));
    }
    samples = fixed;
  }

  // 512 16-bit samples = 1,024 bytes little-endian
  const buffer = new ArrayBuffer(1024);
  const view = new DataView(buffer);
  for (let i = 0; i < 512; i++) {
    view.setInt16(i * 2, samples[i], true); // true = little-endian
  }

  return buffer;
}

export const frameTapEngine = {
  onmessage(e) {
    if (e.data && e.data.command === 'process') {
      const inputFrame = e.data.inputFrame;
      const buffer = processFrame(inputFrame);
      for (const callback of subscribers) {
        try {
          callback(buffer, inputFrame);
        } catch (err) {
          console.error('Error in frame subscriber callback:', err);
        }
      }
    }
  },
};

export async function startFrameTap(onFrame) {
  if (onFrame) {
    subscribers.add(onFrame);
  }
  if (!isSubscribed) {
    try {
      WebVoiceProcessor.setOptions({
        frameLength: 512,
        outputSampleRate: 16000,
      });
      await WebVoiceProcessor.subscribe(frameTapEngine);
      isSubscribed = true;
    } catch (err) {
      console.error('Failed to subscribe frameTapEngine to WebVoiceProcessor:', err);
      throw err;
    }
  }
}

export async function stopFrameTap(onFrame) {
  if (onFrame) {
    subscribers.delete(onFrame);
  }
  if (subscribers.size === 0 && isSubscribed) {
    try {
      await WebVoiceProcessor.unsubscribe(frameTapEngine);
    } catch (e) {
      // Ignore cleanup error
    }
    isSubscribed = false;
  }
}

export function subscribeFrame(onFrame) {
  subscribers.add(onFrame);
  return () => {
    subscribers.delete(onFrame);
  };
}
