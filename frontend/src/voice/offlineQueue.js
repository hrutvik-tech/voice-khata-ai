import { get, set, keys, del } from 'idb-keyval';

const DB_STORE_NAME = 'bk-offline';
const MAX_QUEUE_SIZE = 20;

export async function enqueueOfflineTurn(turnData) {
  try {
    const allKeys = await keys();
    const offlineKeys = allKeys.filter((k) => typeof k === 'string' && k.startsWith(`${DB_STORE_NAME}:`));

    if (offlineKeys.length >= MAX_QUEUE_SIZE) {
      console.warn('Offline queue is full (max 20 turns). Oldest turn dropped.');
      const oldestKey = offlineKeys[0];
      await del(oldestKey);
    }

    const key = `${DB_STORE_NAME}:${turnData.turn_id || crypto.randomUUID()}`;
    await set(key, {
      ...turnData,
      recorded_at: turnData.recorded_at || new Date().toISOString(),
      idempotency_key: turnData.idempotency_key || crypto.randomUUID(),
    });
  } catch (err) {
    console.error('Failed to enqueue offline turn:', err);
  }
}

export async function getOfflineTurns() {
  try {
    const allKeys = await keys();
    const offlineKeys = allKeys.filter((k) => typeof k === 'string' && k.startsWith(`${DB_STORE_NAME}:`));
    const turns = [];
    for (const key of offlineKeys) {
      const turn = await get(key);
      if (turn) turns.push({ key, ...turn });
    }
    return turns;
  } catch (err) {
    console.error('Failed to get offline turns:', err);
    return [];
  }
}

export async function getOfflineQueueCount() {
  try {
    const allKeys = await keys();
    return allKeys.filter((k) => typeof k === 'string' && k.startsWith(`${DB_STORE_NAME}:`)).length;
  } catch (err) {
    return 0;
  }
}

export async function removeOfflineTurn(key) {
  try {
    await del(key);
  } catch (err) {
    console.error('Failed to remove offline turn:', err);
  }
}
