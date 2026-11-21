/**
 * Mock voice implementation for testing and demo mode without live WebSocket / Picovoice.
 */

import { create } from 'zustand';

export const useMockVoiceStore = create((set, get) => ({
  started: false,
  state: 'resting',
  connection: 'online',
  micPermission: 'granted',
  lastHeard: null,
  lastEvent: null,
  pendingQuestion: null,
  lastAnswerSay: '',
  queuedCount: 0,
  syncing: false,
  notSaved: [],

  dismissNotSaved: (turnId) => {
    set((s) => ({
      notSaved: (s.notSaved || []).filter((x) => (x.turn_id || x.turnId) !== turnId),
    }));
  },

  setDemoTime: (timeIso) => {},

  start: async () => {
    set({
      started: true,
      state: 'resting',
      connection: 'online',
      micPermission: 'granted',
    });
  },

  choose: (turnId, choice) => {
    // Simulates choosing an option
    set({
      pendingQuestion: null,
      lastEvent: {
        type: 'answer',
        turn_id: turnId,
        kind: 'entry_saved',
        say: 'Entry saved successfully',
        data: {},
      },
      lastAnswerSay: 'Entry saved successfully',
      state: 'resting',
    });
  },

  replay: async () => {
    // Mock replay
  },

  // Mock trigger to simulate a spoken utterance in demo mode
  simulateUtterance: (text = 'Ramesh Sharma ka 340 udhaar', language = 'hi') => {
    const turnId = `mock-turn-${Date.now()}`;
    set({ state: 'listening' });

    setTimeout(() => {
      set({
        state: 'understanding',
        lastHeard: { turnId, text, language },
      });

      setTimeout(() => {
        const event = {
          type: 'entry',
          turn_id: turnId,
          entry: {
            id: 41,
            customer_id: 1,
            customer_name: 'Ramesh Sharma',
            amount_paise: 34000,
            direction: 'credit',
            business_date: '2026-11-21',
            status: 'new',
            language,
          },
          balance_paise: 84000,
          new_customer: false,
        };

        set({
          state: 'speaking',
          lastEvent: event,
          lastAnswerSay: 'Ramesh Sharma ka teen sau chalees rupaye udhaar darj kiya',
        });

        setTimeout(() => {
          set({ state: 'resting' });
        }, 1500);
      }, 500);
    }, 500);
  },
}));

export const mockVoice = useMockVoiceStore;
