/**
 * WebSocket manager for Voice Khata backend connection.
 * Handles authentication, ping heartbeats, online/offline detection, and exponential backoff reconnection.
 */

export class VoiceSocket {
  constructor(options = {}) {
    this.ws = null;
    this.messageHandlers = new Set();
    this.connectionHandlers = new Set();

    this.connection = typeof navigator !== 'undefined' && !navigator.onLine ? 'offline' : 'offline';
    this.reconnectAttempts = 0;
    this.reconnectTimer = null;
    this.pingTimer = null;
    this.isExplicitlyClosed = false;

    this.getWsUrl = options.getWsUrl || (() => {
      const base = import.meta.env?.VITE_WS_URL || 'ws://localhost:8000';
      const token = typeof localStorage !== 'undefined' ? (localStorage.getItem('bk_token') || '') : '';
      return `${base}/ws?token=${token}`;
    });

    if (typeof window !== 'undefined') {
      window.addEventListener('online', () => this.handleNetworkChange(true));
      window.addEventListener('offline', () => this.handleNetworkChange(false));
    }
  }

  setConnection(newStatus) {
    if (this.connection !== newStatus) {
      this.connection = newStatus;
      for (const handler of this.connectionHandlers) {
        try {
          handler(newStatus);
        } catch (e) {
          console.error('Error in connection handler:', e);
        }
      }
    }
  }

  handleNetworkChange(isOnline) {
    if (!isOnline) {
      this.setConnection('offline');
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
      if (this.ws) {
        this.ws.close();
      }
    } else {
      if (!this.isExplicitlyClosed) {
        this.reconnectAttempts = 0;
        this.connect();
      }
    }
  }

  connect() {
    this.isExplicitlyClosed = false;
    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      this.setConnection('offline');
      return;
    }

    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const url = this.getWsUrl();
    try {
      this.ws = new WebSocket(url);
      this.ws.binaryType = 'arraybuffer';
    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.setConnection('online');
      this.startPing();
    };

    this.ws.onmessage = (event) => {
      for (const handler of this.messageHandlers) {
        try {
          handler(event.data);
        } catch (err) {
          console.error('Error handling WebSocket message:', err);
        }
      }
    };

    this.ws.onclose = () => {
      this.stopPing();
      if (!this.isExplicitlyClosed) {
        if (typeof navigator !== 'undefined' && !navigator.onLine) {
          this.setConnection('offline');
        } else {
          this.setConnection('reconnecting');
          this.scheduleReconnect();
        }
      } else {
        this.setConnection('offline');
      }
    };

    this.ws.onerror = (err) => {
      console.warn('WebSocket error encountered:', err);
      // onclose handles reconnection
    };
  }

  scheduleReconnect() {
    if (this.reconnectTimer) return;
    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      this.setConnection('offline');
      return;
    }

    // Exponential backoff: 1, 2, 4, 8s (max 8)
    const backoffSeconds = Math.min(Math.pow(2, this.reconnectAttempts), 8);
    this.reconnectAttempts++;

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, backoffSeconds * 1000);
  }

  startPing() {
    this.stopPing();
    this.pingTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping' });
      }
    }, 20000); // 20s
  }

  stopPing() {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  send(msg) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(typeof msg === 'string' ? msg : JSON.stringify(msg));
      return true;
    }
    return false;
  }

  sendBinary(buffer) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(buffer);
      return true;
    }
    return false;
  }

  onMessage(handler) {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onConnectionChange(handler) {
    this.connectionHandlers.add(handler);
    handler(this.connection);
    return () => this.connectionHandlers.delete(handler);
  }

  disconnect() {
    this.isExplicitlyClosed = true;
    this.stopPing();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setConnection('offline');
  }
}

export const defaultSocket = new VoiceSocket();
