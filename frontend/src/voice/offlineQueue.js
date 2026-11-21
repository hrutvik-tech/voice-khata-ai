import { createStore, get, set, del, entries } from 'idb-keyval';

const DB_NAME = 'bk-offline';
const STORE_NAME = 'bk-offline';
export const MAX_OFFLINE_RECORDINGS = 20;

// Memory fallback store for environments without IndexedDB (e.g. testing)
const memoryStore = new Map();

let customStoreInstance = null;

export function getOfflineStore() {
  if (typeof indexedDB !== 'undefined') {
    if (!customStoreInstance) {
      customStoreInstance = createStore(DB_NAME, STORE_NAME);
    }
    return customStoreInstance;
  }
  return null;
}

export function resetOfflineStore() {
  customStoreInstance = null;
}

export const offlineStore = {
  getStore: getOfflineStore,
  resetStore: resetOfflineStore,
};

let isSyncing = false;

export function getSyncingState() {
  return isSyncing;
}

export function encodeWav(pcmFrames) {
  // Calculate total PCM bytes
  let totalBytes = 0;
  for (const frame of pcmFrames) {
    totalBytes += frame.byteLength || frame.length * 2;
  }

  // 44-byte RIFF/WAVE header
  const buffer = new ArrayBuffer(44 + totalBytes);
  const view = new DataView(buffer);

  // 'RIFF' chunk descriptor
  view.setUint8(0, 0x52); // 'R'
  view.setUint8(1, 0x49); // 'I'
  view.setUint8(2, 0x46); // 'F'
  view.setUint8(3, 0x46); // 'F'
  view.setUint32(4, 36 + totalBytes, true);
  view.setUint8(8, 0x57);  // 'W'
  view.setUint8(9, 0x41);  // 'A'
  view.setUint8(10, 0x56); // 'V'
  view.setUint8(11, 0x45); // 'E'

  // 'fmt ' sub-chunk
  view.setUint8(12, 0x66); // 'f'
  view.setUint8(13, 0x6d); // 'm'
  view.setUint8(14, 0x74); // 't'
  view.setUint8(15, 0x20); // ' '
  view.setUint32(16, 16, true);       // Subchunk1Size = 16 for PCM
  view.setUint16(20, 1, true);        // AudioFormat = 1 (linear PCM)
  view.setUint16(22, 1, true);        // NumChannels = 1 (mono)
  view.setUint32(24, 16000, true);    // SampleRate = 16000
  view.setUint32(28, 32000, true);    // ByteRate = 16000 * 1 * 2 = 32000
  view.setUint16(32, 2, true);        // BlockAlign = 1 * 2 = 2
  view.setUint16(34, 16, true);       // BitsPerSample = 16

  // 'data' sub-chunk
  view.setUint8(36, 0x64); // 'd'
  view.setUint8(37, 0x61); // 'a'
  view.setUint8(38, 0x74); // 't'
  view.setUint8(39, 0x61); // 'a'
  view.setUint32(40, totalBytes, true);

  // Copy audio frame data
  const uint8View = new Uint8Array(buffer, 44);
  let offset = 0;
  for (const frame of pcmFrames) {
    let frameBytes;
    if (frame instanceof ArrayBuffer) {
      frameBytes = new Uint8Array(frame);
    } else if (frame instanceof Int16Array) {
      frameBytes = new Uint8Array(frame.buffer, frame.byteOffset, frame.byteLength);
    } else {
      frameBytes = new Uint8Array(frame);
    }
    uint8View.set(frameBytes, offset);
    offset += frameBytes.length;
  }

  return new Blob([buffer], { type: 'audio/wav' });
}

export function playConfirmationBeep() {
  if (typeof window === 'undefined') return;
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) return;
  try {
    const ctx = new AudioContextClass();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(800, ctx.currentTime);

    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.15);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start();
    osc.stop(ctx.currentTime + 0.15);
  } catch (e) {
    // AudioContext blocked or not supported
  }
}

export async function getOfflineQueueCount() {
  const store = getOfflineStore();
  if (!store) {
    return memoryStore.size;
  }
  try {
    const allEntries = await entries(store);
    return allEntries.length;
  } catch (err) {
    return memoryStore.size;
  }
}

export async function getOfflineQueueItems() {
  const store = getOfflineStore();
  if (!store) {
    return Array.from(memoryStore.entries()).map(([k, v]) => ({ key: k, ...v }));
  }
  try {
    const allEntries = await entries(store);
    return allEntries.map(([key, val]) => ({ key, ...val }));
  } catch (err) {
    return Array.from(memoryStore.entries()).map(([k, v]) => ({ key: k, ...v }));
  }
}

export async function enqueueOfflineTurn(turnData) {
  const currentCount = await getOfflineQueueCount();
  if (currentCount >= MAX_OFFLINE_RECORDINGS) {
    console.warn(`Offline recording refused: queue limit reached (${MAX_OFFLINE_RECORDINGS} turns).`);
    return false;
  }

  const idempotency_key = turnData.idempotency_key || (typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `idemp-${Date.now()}`);
  const record = {
    idempotency_key,
    recorded_at: turnData.recorded_at || new Date().toISOString(),
    wav: turnData.wav,
  };

  const store = getOfflineStore();
  if (!store) {
    memoryStore.set(idempotency_key, record);
    playConfirmationBeep();
    return true;
  }

  try {
    await set(idempotency_key, record, store);
    playConfirmationBeep();
    return true;
  } catch (err) {
    memoryStore.set(idempotency_key, record);
    playConfirmationBeep();
    return true;
  }
}

export async function removeOfflineItem(key) {
  const store = getOfflineStore();
  if (!store) {
    memoryStore.delete(key);
    return;
  }
  try {
    await del(key, store);
  } catch (err) {
    memoryStore.delete(key);
  }
}

export async function clearOfflineQueue() {
  memoryStore.clear();
  const store = getOfflineStore();
  if (store) {
    try {
      const items = await entries(store);
      for (const [k] of items) {
        await del(k, store);
      }
    } catch (e) {}
  }
}

export async function syncOfflineQueue(callbacks = {}) {
  const { onEntryEvent, onNotSaved, onQueuedCountChange, onSyncStateChange } = callbacks;

  if (isSyncing) return;

  const items = await getOfflineQueueItems();
  if (items.length === 0) {
    if (onQueuedCountChange) onQueuedCountChange(0);
    return;
  }

  isSyncing = true;
  if (onSyncStateChange) onSyncStateChange(true);

  const token = typeof localStorage !== 'undefined' ? (localStorage.getItem('bk_token') || '') : '';
  const apiUrl = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL) || 'http://localhost:8000';

  try {
    for (const item of items) {
      const formData = new FormData();
      const wavBlob = item.wav instanceof Blob ? item.wav : new Blob([item.wav], { type: 'audio/wav' });

      formData.append('audio', wavBlob, 'recording.wav');
      formData.append('idempotency_key', item.idempotency_key);
      formData.append('recorded_at', item.recorded_at);

      let response;
      try {
        response = await fetch(`${apiUrl}/sync/audio`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        });
      } catch (networkErr) {
        // Network error -> stop and retry on next reconnect
        console.warn('Network error during offline sync:', networkErr);
        break;
      }

      if (!response.ok) {
        console.warn(`Sync request failed with status ${response.status}. Retrying on next reconnect.`);
        break;
      }

      const data = await response.json();

      // On success, remove item from IndexedDB
      await removeOfflineItem(item.key || item.idempotency_key);

      const count = await getOfflineQueueCount();
      if (onQueuedCountChange) onQueuedCountChange(count);

      // Process events
      const events = data.events || [];
      for (const event of events) {
        if (event.type === 'entry') {
          if (onEntryEvent) onEntryEvent(event);
        } else if (event.type === 'not_saved') {
          if (onNotSaved) onNotSaved(event);
        }
      }
    }
  } finally {
    isSyncing = false;
    if (onSyncStateChange) onSyncStateChange(false);
  }
}
