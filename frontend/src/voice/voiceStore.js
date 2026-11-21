import { create } from 'zustand';
import { WebVoiceProcessor } from '@picovoice/web-voice-processor';
import { defaultSocket } from './voiceSocket.js';
import { defaultPlayer } from './player.js';
import { LocalVad } from './localVad.js';
import { startFrameTap } from './frameTap.js';
import { initWakeWord } from './wakeWord.js';
import { getOfflineQueueCount } from './offlineQueue.js';

export const useVoiceStore = create((set, get) => {
  let activeTurnId = null;
  let isSendingFrames = false;
  let demoTime = null;

  const vad = new LocalVad({
    onSpeechStart: () => {
      // Speech started
    },
    onTurnEnd: (reason) => {
      if (isSendingFrames && activeTurnId) {
        isSendingFrames = false;
        defaultSocket.send({ type: 'commit', turn_id: activeTurnId });
      }
    },
    onCancel: (reason) => {
      if (isSendingFrames && activeTurnId) {
        isSendingFrames = false;
        defaultSocket.send({ type: 'cancel', turn_id: activeTurnId });
        set({ state: 'resting' });
        activeTurnId = null;
      }
    },
  });

  const onWakeWordDetected = () => {
    const { state, connection } = get();

    // Only trigger if resting, online, and player is not active or in 300ms cooldown
    if (state !== 'resting' || connection !== 'online' || defaultPlayer.shouldIgnoreVoice()) {
      return;
    }

    const turnId = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `turn-${Date.now()}`;
    activeTurnId = turnId;
    isSendingFrames = true;

    set({ state: 'listening' });

    // Send turn_start message
    defaultSocket.send({
      type: 'turn_start',
      turn_id: turnId,
      now_override: demoTime || null,
    });

    // Start local VAD
    vad.startTurn();
  };

  const onFrameReceived = (buffer, inputFrame) => {
    // Calibrate VAD if calibrating
    vad.processFrame(inputFrame);

    // If currently in a turn and sending frames
    if (isSendingFrames && activeTurnId) {
      if (!defaultPlayer.shouldIgnoreVoice()) {
        defaultSocket.sendBinary(buffer);
      }
    }
  };

  // Connect socket listeners
  defaultSocket.onConnectionChange((conn) => {
    set({ connection: conn });
    if (conn === 'online') {
      vad.startCalibration();
    }
  });

  defaultSocket.onMessage((data) => {
    // Handle binary audio chunks
    if (data instanceof ArrayBuffer) {
      defaultPlayer.addChunk(data);
      return;
    }

    let msg;
    try {
      msg = typeof data === 'string' ? JSON.parse(data) : data;
    } catch (e) {
      return;
    }

    const { type } = msg;

    if (type === 'audio_start') {
      defaultPlayer.startAudio();
      return;
    }

    if (type === 'audio_end') {
      defaultPlayer.endAudio();
      return;
    }

    // State transition message
    if (type === 'state') {
      set({ state: msg.state });
      // Stop sending frames as soon as server transitions to understanding
      if (msg.state === 'understanding') {
        isSendingFrames = false;
        vad.stopTurn();
      }
      return;
    }

    // Heard message
    if (type === 'heard') {
      set({
        lastHeard: {
          turnId: msg.turn_id,
          text: msg.text,
          language: msg.language,
        },
      });
      return;
    }

    // Final answer / question / event messages
    if (type === 'entry' || type === 'answer' || type === 'question' || type === 'not_understood' || type === 'error') {
      set({ lastEvent: msg });

      if (type === 'question') {
        set({ pendingQuestion: msg });
      } else {
        // Any other final message clears pendingQuestion
        set({ pendingQuestion: null });
      }

      if (msg.say) {
        set({ lastAnswerSay: msg.say });
      }
      return;
    }

    if (type === 'not_saved') {
      const current = get().notSaved || [];
      set({ notSaved: [...current, msg] });
      return;
    }
  });

  return {
    started: false,
    state: 'resting',
    connection: 'offline',
    micPermission: 'unknown',
    lastHeard: null,
    lastEvent: null,
    pendingQuestion: null,
    lastAnswerSay: '',
    queuedCount: 0,
    notSaved: [],

    setDemoTime: (timeIso) => {
      demoTime = timeIso;
    },

    choose: (turnId, choice) => {
      defaultSocket.send({
        type: 'choose',
        turn_id: turnId,
        choice: choice,
      });
    },

    replay: async () => {
      await defaultPlayer.replay();
    },

    start: async () => {
      try {
        // 1. Unlock HTMLAudioElement within tap
        await defaultPlayer.unlock();

        // 2. Request mic permission through WebVoiceProcessor
        let micGranted = false;
        try {
          // Request mic access
          await navigator.mediaDevices.getUserMedia({ audio: true });
          micGranted = true;
          set({ micPermission: 'granted' });
        } catch (err) {
          console.warn('Microphone permission denied:', err);
          set({ micPermission: 'denied' });
          return;
        }

        // 3. Start frame tap engine
        await startFrameTap(onFrameReceived);

        // 4. Initialize Porcupine wake word engine
        try {
          await initWakeWord(onWakeWordDetected);
        } catch (e) {
          console.warn('Wake word initialization failed or not configured, frame tap remains active.');
        }

        // 5. Connect WebSocket
        defaultSocket.connect();

        // 6. Update queuedCount from IndexedDB
        const qCount = await getOfflineQueueCount();
        set({ queuedCount: qCount });

        set({ started: true });
      } catch (err) {
        console.error('Failed to start voice system:', err);
      }
    },

    // Testing helpers for dispatching synthetic events
    _handleMessage: (msg) => {
      const parsed = typeof msg === 'string' ? JSON.parse(msg) : msg;
      const { type } = parsed;

      if (type === 'state') {
        set({ state: parsed.state });
        if (parsed.state === 'understanding') {
          isSendingFrames = false;
          vad.stopTurn();
        }
      } else if (type === 'heard') {
        set({
          lastHeard: {
            turnId: parsed.turn_id,
            text: parsed.text,
            language: parsed.language,
          },
        });
      } else if (['entry', 'answer', 'question', 'not_understood', 'error'].includes(type)) {
        set({ lastEvent: parsed });
        if (type === 'question') {
          set({ pendingQuestion: parsed });
        } else {
          set({ pendingQuestion: null });
        }
        if (parsed.say) {
          set({ lastAnswerSay: parsed.say });
        }
      }
    },
  };
});
