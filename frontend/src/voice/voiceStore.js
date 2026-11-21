import { create } from 'zustand';
import { WebVoiceProcessor } from '@picovoice/web-voice-processor';
import { defaultSocket } from './voiceSocket.js';
import { defaultPlayer } from './player.js';
import { LocalVad } from './localVad.js';
import { startFrameTap } from './frameTap.js';
import { initWakeWord } from './wakeWord.js';
import { getOfflineQueueCount } from './offlineQueue.js';

// Setup window.__bkLatency and window.__bkLatencyReport
if (typeof window !== 'undefined') {
  window.__bkLatency = window.__bkLatency || [];
  window.__bkLatencyReport = function () {
    const records = window.__bkLatency || [];
    if (records.length === 0) {
      console.log('No latency records found.');
      return { median: 0, p90: 0, count: 0 };
    }
    const durations = records
      .map((r) => r.durationMs)
      .filter((d) => typeof d === 'number' && !isNaN(d))
      .sort((a, b) => a - b);

    if (durations.length === 0) {
      return { median: 0, p90: 0, count: 0 };
    }

    const mid = Math.floor(durations.length / 2);
    const median = durations.length % 2 !== 0 ? durations[mid] : (durations[mid - 1] + durations[mid]) / 2;

    const p90Index = Math.ceil(0.9 * durations.length) - 1;
    const p90 = durations[Math.max(0, p90Index)];

    console.log(`Commit-to-Playback Latency (N=${durations.length}):`);
    console.log(`  Median: ${median.toFixed(2)} ms`);
    console.log(`  90th percentile: ${p90.toFixed(2)} ms`);

    return { median, p90, count: durations.length };
  };
}

export const useVoiceStore = create((set, get) => {
  let activeTurnId = null;
  let isSendingFrames = false;
  let demoTime = null;
  let currentTurnLatency = null;

  defaultPlayer.onPlaybackStart = () => {
    if (currentTurnLatency && currentTurnLatency.playbackStartTime === null) {
      const now = typeof performance !== 'undefined' ? performance.now() : Date.now();
      currentTurnLatency.playbackStartTime = now;
      currentTurnLatency.durationMs = now - currentTurnLatency.commitTime;

      if (typeof window !== 'undefined') {
        window.__bkLatency = window.__bkLatency || [];
        window.__bkLatency.push({ ...currentTurnLatency });
      }
    }
  };

  const vad = new LocalVad({
    onSpeechStart: () => {
      // Speech started
    },
    onTurnEnd: (reason) => {
      if (isSendingFrames && activeTurnId) {
        isSendingFrames = false;
        const now = typeof performance !== 'undefined' ? performance.now() : Date.now();
        currentTurnLatency = {
          turnId: activeTurnId,
          commitTime: now,
          audioStartTime: null,
          playbackStartTime: null,
          durationMs: null,
        };
        defaultSocket.send({ type: 'commit', turn_id: activeTurnId });
      }
    },
    onCancel: (reason) => {
      if (isSendingFrames && activeTurnId) {
        isSendingFrames = false;
        currentTurnLatency = null;
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
      if (currentTurnLatency) {
        currentTurnLatency.audioStartTime = typeof performance !== 'undefined' ? performance.now() : Date.now();
      }
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

    _recordCommitLatency: (turnId, commitTime = performance.now()) => {
      currentTurnLatency = {
        turnId,
        commitTime,
        audioStartTime: null,
        playbackStartTime: null,
        durationMs: null,
      };
    },

    _recordAudioStartLatency: (audioStartTime = performance.now()) => {
      if (currentTurnLatency) {
        currentTurnLatency.audioStartTime = audioStartTime;
      }
    },

    _recordPlaybackLatency: (playbackStartTime = performance.now()) => {
      if (currentTurnLatency) {
        currentTurnLatency.playbackStartTime = playbackStartTime;
        currentTurnLatency.durationMs = playbackStartTime - currentTurnLatency.commitTime;
        if (typeof window !== 'undefined') {
          window.__bkLatency = window.__bkLatency || [];
          window.__bkLatency.push({ ...currentTurnLatency });
        }
      }
    },
  };
});
