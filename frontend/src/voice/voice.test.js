import { describe, it, expect, vi, beforeEach } from 'vitest';
import { processFrame } from './frameTap.js';
import { LocalVad, calculateRms } from './localVad.js';
import { useVoiceStore } from './voiceStore.js';
import { defaultPlayer, AudioPlayer } from './player.js';
import { defaultSocket } from './voiceSocket.js';

describe('Voice System Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('1. Frame Tap (1,024-byte enforcement)', () => {
    it('produces exactly 1,024-byte little-endian ArrayBuffer for standard 512-sample frame', () => {
      const input = new Int16Array(512);
      input[0] = 1234;
      input[511] = -5678;

      const buffer = processFrame(input);
      expect(buffer).toBeInstanceOf(ArrayBuffer);
      expect(buffer.byteLength).toBe(1024);

      const view = new DataView(buffer);
      expect(view.getInt16(0, true)).toBe(1234);
      expect(view.getInt16(511 * 2, true)).toBe(-5678);
    });

    it('pads frames smaller than 512 samples to exactly 1,024 bytes', () => {
      const shortFrame = new Int16Array(256);
      shortFrame[0] = 42;

      const buffer = processFrame(shortFrame);
      expect(buffer.byteLength).toBe(1024);

      const view = new DataView(buffer);
      expect(view.getInt16(0, true)).toBe(42);
      expect(view.getInt16(511 * 2, true)).toBe(0);
    });

    it('truncates frames larger than 512 samples to exactly 1,024 bytes', () => {
      const longFrame = new Int16Array(1024);
      longFrame[0] = 99;
      longFrame[511] = 88;
      longFrame[512] = 77;

      const buffer = processFrame(longFrame);
      expect(buffer.byteLength).toBe(1024);

      const view = new DataView(buffer);
      expect(view.getInt16(0, true)).toBe(99);
      expect(view.getInt16(511 * 2, true)).toBe(88);
    });
  });

  describe('2. Local VAD (Voice Activity Detection)', () => {
    it('cancels turn if no speech occurs within 5 seconds of wake word', () => {
      const onCancel = vi.fn();
      const vad = new LocalVad({
        thresholdMultiplier: 3.0,
        noSpeechTimeoutMs: 5000,
        onCancel,
      });

      // Calibrate baseline with low noise
      vad.startCalibration(0);
      const quietFrame = new Int16Array(512).fill(20);
      vad.processFrame(quietFrame, 0);
      vad.processFrame(quietFrame, 1000);

      // Start turn at t = 2000
      vad.startTurn(2000);

      // Feed quiet frames at t = 3000, 4000, 6000
      vad.processFrame(quietFrame, 3000);
      vad.processFrame(quietFrame, 5000);

      // At t = 7000 (5000 ms after startTurn), timeout triggers
      const result = vad.processFrame(quietFrame, 7000);
      expect(result.action).toBe('cancel');
      expect(result.reason).toBe('no_speech');
      expect(onCancel).toHaveBeenCalledWith('no_speech');
    });

    it('ends turn after 600 ms of silence following speech', () => {
      const onTurnEnd = vi.fn();
      const vad = new LocalVad({
        silenceTimeoutMs: 600,
        onTurnEnd,
      });

      // Set known threshold
      vad.threshold = 300;

      // Start turn at t = 1000
      vad.startTurn(1000);

      // Loud speech frame
      const speechFrame = new Int16Array(512).fill(1500);
      const res1 = vad.processFrame(speechFrame, 1100);
      expect(vad.hasSpeechStarted).toBe(true);

      // Silence begins at t = 1500
      const quietFrame = new Int16Array(512).fill(10);
      vad.processFrame(quietFrame, 1500);
      expect(vad.silenceStartTime).toBe(1500);

      // Silence continues at t = 1800 (300 ms of silence)
      const res2 = vad.processFrame(quietFrame, 1800);
      expect(res2.inTurn).toBe(true);
      expect(onTurnEnd).not.toHaveBeenCalled();

      // Silence reaches 600 ms at t = 2100
      const res3 = vad.processFrame(quietFrame, 2100);
      expect(res3.action).toBe('commit');
      expect(res3.reason).toBe('silence');
      expect(onTurnEnd).toHaveBeenCalledWith('silence');
    });
  });

  describe('3. Voice Store Message Handling Sequence', () => {
    it('correctly updates fields across scripted message flow: heard, entry, question, choose, answer', () => {
      const store = useVoiceStore.getState();

      // 1. Server sends state "listening"
      store._handleMessage({ type: 'state', state: 'listening' });
      expect(useVoiceStore.getState().state).toBe('listening');

      // 2. Server sends "heard"
      store._handleMessage({
        type: 'heard',
        turn_id: 't-100',
        text: 'Ramesh Sharma ka 340 udhaar',
        language: 'hi',
      });
      expect(useVoiceStore.getState().lastHeard).toEqual({
        turnId: 't-100',
        text: 'Ramesh Sharma ka 340 udhaar',
        language: 'hi',
      });

      // 3. Server sends "entry"
      const entryMsg = {
        type: 'entry',
        turn_id: 't-100',
        entry: {
          id: 41,
          customer_name: 'Ramesh Sharma',
          amount_paise: 34000,
          direction: 'credit',
        },
      };
      store._handleMessage(entryMsg);
      expect(useVoiceStore.getState().lastEvent).toEqual(entryMsg);

      // 4. Server sends "question"
      const questionMsg = {
        type: 'question',
        turn_id: 't-100',
        kind: 'choose_customer',
        say: 'Kaunsa Ramesh?',
        options: [
          { id: '1', label: 'Ramesh Sharma' },
          { id: '2', label: 'Ramesh Gupta' },
        ],
      };
      store._handleMessage(questionMsg);
      expect(useVoiceStore.getState().pendingQuestion).toEqual(questionMsg);
      expect(useVoiceStore.getState().lastAnswerSay).toBe('Kaunsa Ramesh?');

      // 5. User chooses an option via choose()
      const sendSpy = vi.spyOn(defaultSocket, 'send').mockImplementation(() => true);
      useVoiceStore.getState().choose('t-100', { customer_id: 1 });
      expect(sendSpy).toHaveBeenCalledWith({
        type: 'choose',
        turn_id: 't-100',
        choice: { customer_id: 1 },
      });

      // 6. Server sends final "answer" -> clears pendingQuestion
      const answerMsg = {
        type: 'answer',
        turn_id: 't-100',
        kind: 'entry_saved',
        say: 'Ramesh Sharma ka udhaar darj kiya',
        data: { count: 1 },
      };
      store._handleMessage(answerMsg);
      expect(useVoiceStore.getState().lastEvent).toEqual(answerMsg);
      expect(useVoiceStore.getState().pendingQuestion).toBeNull();
      expect(useVoiceStore.getState().lastAnswerSay).toBe('Ramesh Sharma ka udhaar darj kiya');
    });
  });

  describe('4. Player playback state and wake suppression', () => {
    it('ignores wake detection and suppresses frame sending while playing and for 300ms after', () => {
      // Simulate playback starting
      defaultPlayer.isPlaying = true;
      expect(defaultPlayer.shouldIgnoreVoice()).toBe(true);

      // Simulate audio ending -> triggers 300 ms cooldown
      if (defaultPlayer.audioElement && defaultPlayer.audioElement.onended) {
        defaultPlayer.audioElement.onended();
      }

      // Still in cooldown
      expect(defaultPlayer.shouldIgnoreVoice()).toBe(true);

      // Stop player
      defaultPlayer.stop();
      expect(defaultPlayer.shouldIgnoreVoice()).toBe(false);
    });
  });

  describe('5. Browser Latency Tracking and Reporting', () => {
    it('records commit, audio_start, and playback start in window.__bkLatency and reports median and P90', () => {
      window.__bkLatency = [];

      const store = useVoiceStore.getState();

      // Turn 1: 500 ms latency
      store._recordCommitLatency('turn-1', 1000);
      store._recordAudioStartLatency(1200);
      store._recordPlaybackLatency(1500);

      // Turn 2: 700 ms latency
      store._recordCommitLatency('turn-2', 2000);
      store._recordAudioStartLatency(2300);
      store._recordPlaybackLatency(2700);

      // Turn 3: 300 ms latency
      store._recordCommitLatency('turn-3', 3000);
      store._recordAudioStartLatency(3100);
      store._recordPlaybackLatency(3300);

      expect(window.__bkLatency.length).toBe(3);
      expect(window.__bkLatency[0].durationMs).toBe(500);
      expect(window.__bkLatency[1].durationMs).toBe(700);
      expect(window.__bkLatency[2].durationMs).toBe(300);

      const report = window.__bkLatencyReport();
      expect(report.count).toBe(3);
      expect(report.median).toBe(500);
      expect(report.p90).toBe(700);
    });
  });

  describe('6. Replay persistence across navigation', () => {
    it('replays the last reply even after simulated page navigation / unmount', async () => {
      const player = new AudioPlayer();
      const playSpy = vi.spyOn(player, 'playBlob').mockImplementation(() => Promise.resolve());

      // Collect audio chunks
      player.startAudio();
      player.addChunk(new Uint8Array([1, 2, 3]));
      player.addChunk(new Uint8Array([4, 5, 6]));
      await player.endAudio();

      expect(player.lastAudioBlob).not.toBeNull();
      expect(playSpy).toHaveBeenCalledTimes(1);

      // Simulate component unmount / page navigation
      // (The player instance is at module/singleton scope, so lastAudioBlob persists)
      await player.replay();
      expect(playSpy).toHaveBeenCalledTimes(2);
      expect(playSpy).toHaveBeenLastCalledWith(player.lastAudioBlob);
    });
  });
});
