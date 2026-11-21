import { useVoiceStore } from './voiceStore.js';
import { useMockVoiceStore } from './mockVoice.js';

export function useVoice() {
  const useMock = import.meta.env?.VITE_USE_MOCK_VOICE === 'true' || import.meta.env?.VITE_USE_MOCK_VOICE === true;
  if (useMock) {
    return useMockVoiceStore();
  }
  return useVoiceStore();
}

export default useVoice;
