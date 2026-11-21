import { PorcupineWorker } from '@picovoice/porcupine-web';
import { WebVoiceProcessor } from '@picovoice/web-voice-processor';

export const WAKE_WORD_SENSITIVITY = 0.65;

let porcupineWorker = null;

export async function initWakeWord(onDetected) {
  const accessKey = import.meta.env.VITE_PICOVOICE_ACCESS_KEY || '';
  if (!accessKey) {
    console.warn('VITE_PICOVOICE_ACCESS_KEY is not set');
    return null;
  }

  const keyword = {
    publicPath: '/porcupine/suno_munshi.ppn',
    label: 'Suno Munshi',
    sensitivity: WAKE_WORD_SENSITIVITY,
  };

  const porcupineModel = {
    publicPath: '/porcupine/porcupine_params.pv',
  };

  const detectionCallback = (detection) => {
    if (detection && detection.label === 'Suno Munshi') {
      if (onDetected) {
        onDetected(detection);
      }
    }
  };

  try {
    porcupineWorker = await PorcupineWorker.create(
      accessKey,
      keyword,
      detectionCallback,
      porcupineModel,
      { sensitivities: [WAKE_WORD_SENSITIVITY] }
    );
    await WebVoiceProcessor.subscribe(porcupineWorker);
    return porcupineWorker;
  } catch (err) {
    console.error('Failed to initialize Porcupine wake word:', err);
    throw err;
  }
}

export async function stopWakeWord() {
  if (porcupineWorker) {
    try {
      await WebVoiceProcessor.unsubscribe(porcupineWorker);
      await porcupineWorker.terminate();
    } catch (e) {
      // Ignore cleanup error
    }
    porcupineWorker = null;
  }
}
