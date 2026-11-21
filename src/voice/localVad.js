/**
 * Local VAD (Voice Activity Detection) based on RMS energy.
 *
 * Rules:
 * - Baseline: Average RMS of the first 1 second after start() (re-measured after reconnect).
 * - Threshold: 3 x baseline RMS.
 * - Speech start: RMS >= threshold.
 * - Turn end: 600 ms of silence below threshold.
 * - Cancel: No speech within 5 s of wake word.
 * - Max duration: 12 s maximum turn duration.
 */

export function calculateRms(samples) {
  if (!samples || samples.length === 0) return 0;
  let sumSquares = 0;
  for (let i = 0; i < samples.length; i++) {
    sumSquares += samples[i] * samples[i];
  }
  return Math.sqrt(sumSquares / samples.length);
}

export class LocalVad {
  constructor(options = {}) {
    this.thresholdMultiplier = options.thresholdMultiplier || 3.0;
    this.minThreshold = options.minThreshold || 50.0;
    this.silenceTimeoutMs = options.silenceTimeoutMs || 600;
    this.noSpeechTimeoutMs = options.noSpeechTimeoutMs || 5000;
    this.maxTurnDurationMs = options.maxTurnDurationMs || 12000;

    this.baselineRms = 100;
    this.threshold = this.baselineRms * this.thresholdMultiplier;

    this.isCalibrating = false;
    this.calibrationStartTime = 0;
    this.calibrationRmsSum = 0;
    this.calibrationFramesCount = 0;

    this.inTurn = false;
    this.hasSpeechStarted = false;
    this.turnStartTime = 0;
    this.silenceStartTime = null;

    this.onSpeechStart = options.onSpeechStart || null;
    this.onTurnEnd = options.onTurnEnd || null;
    this.onCancel = options.onCancel || null;
  }

  /**
   * Begins baseline RMS calibration for 1 second.
   */
  startCalibration(currentTime = Date.now()) {
    this.isCalibrating = true;
    this.calibrationStartTime = currentTime;
    this.calibrationRmsSum = 0;
    this.calibrationFramesCount = 0;
  }

  /**
   * Starts a turn triggered by wake word.
   */
  startTurn(currentTime = Date.now()) {
    this.inTurn = true;
    this.hasSpeechStarted = false;
    this.turnStartTime = currentTime;
    this.silenceStartTime = null;
  }

  stopTurn() {
    this.inTurn = false;
    this.hasSpeechStarted = false;
    this.silenceStartTime = null;
  }

  /**
   * Processes one audio frame (Int16Array or ArrayBuffer).
   */
  processFrame(frame, currentTime = Date.now()) {
    let samples;
    if (frame instanceof ArrayBuffer) {
      samples = new Int16Array(frame);
    } else if (frame instanceof Int16Array) {
      samples = frame;
    } else {
      samples = new Int16Array(frame);
    }

    const rms = calculateRms(samples);

    // Calibration phase (first 1000 ms)
    if (this.isCalibrating) {
      this.calibrationRmsSum += rms;
      this.calibrationFramesCount += 1;

      if (currentTime - this.calibrationStartTime >= 1000) {
        this.isCalibrating = false;
        if (this.calibrationFramesCount > 0) {
          const avgRms = this.calibrationRmsSum / this.calibrationFramesCount;
          this.baselineRms = Math.max(avgRms, 10);
          this.threshold = Math.max(this.baselineRms * this.thresholdMultiplier, this.minThreshold);
        }
      }
    }

    if (!this.inTurn) {
      return { inTurn: false, rms, threshold: this.threshold };
    }

    // Check maximum turn duration (12s)
    if (currentTime - this.turnStartTime >= this.maxTurnDurationMs) {
      this.inTurn = false;
      if (this.onTurnEnd) {
        this.onTurnEnd('max_duration');
      }
      return { inTurn: false, action: 'commit', reason: 'max_duration', rms };
    }

    // Speech hasn't started yet
    if (!this.hasSpeechStarted) {
      // Check 5-second no-speech timeout
      if (currentTime - this.turnStartTime >= this.noSpeechTimeoutMs) {
        this.inTurn = false;
        if (this.onCancel) {
          this.onCancel('no_speech');
        }
        return { inTurn: false, action: 'cancel', reason: 'no_speech', rms };
      }

      // Check if speech started
      if (rms >= this.threshold) {
        this.hasSpeechStarted = true;
        this.silenceStartTime = null;
        if (this.onSpeechStart) {
          this.onSpeechStart();
        }
      }
      return { inTurn: true, speech: this.hasSpeechStarted, rms };
    }

    // Speech has started - detect silence
    if (rms < this.threshold) {
      if (this.silenceStartTime === null) {
        this.silenceStartTime = currentTime;
      } else if (currentTime - this.silenceStartTime >= this.silenceTimeoutMs) {
        // 600 ms of silence reached -> turn ends
        this.inTurn = false;
        if (this.onTurnEnd) {
          this.onTurnEnd('silence');
        }
        return { inTurn: false, action: 'commit', reason: 'silence', rms };
      }
    } else {
      // Still speaking
      this.silenceStartTime = null;
    }

    return { inTurn: true, speech: true, rms };
  }
}
