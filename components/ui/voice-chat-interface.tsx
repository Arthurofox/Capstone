"use client";

import React, { useState, useEffect, useRef } from "react";

export function VoiceChatInterface() {
  const [connected, setConnected] = useState<boolean>(false);
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [debugMessages, setDebugMessages] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const activeRef = useRef<boolean>(false);
  const audioElementRef = useRef<HTMLAudioElement | null>(null);

  // Log debug messages
  const logDebug = (msg: string) => {
    console.log(msg);
    setDebugMessages((prev) => [...prev, `${new Date().toISOString().slice(11, 19)}: ${msg}`]);
  };

  // Calculate RMS of audio buffer
  const calculateRMS = (buffer: Float32Array): number => {
    let sum = 0;
    for (let i = 0; i < buffer.length; i++) {
      sum += buffer[i] * buffer[i];
    }
    return Math.sqrt(sum / buffer.length);
  };

  // Downsample audio to 16kHz for OpenAI
  const downsampleTo16kHz = (buffer: Float32Array, originalSampleRate: number): Float32Array => {
    const ratio = originalSampleRate / 16000;
    const newLength = Math.round(buffer.length / ratio);
    const result = new Float32Array(newLength);
    
    for (let i = 0; i < newLength; i++) {
      const oldIndex = Math.floor(i * ratio);
      result[i] = buffer[oldIndex];
    }
    
    return result;
  };

  // Convert Float32Array to Int16Array
  const float32ToInt16 = (buffer: Float32Array): Int16Array => {
    const l = buffer.length;
    const int16Buffer = new Int16Array(l);
    for (let i = 0; i < l; i++) {
      let s = Math.max(-1, Math.min(1, buffer[i]));
      int16Buffer[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return int16Buffer;
  };

  // Play a test sound
  const testAudio = () => {
    try {
      // Create a simple beep sound
      const audioContext = new AudioContext();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(440, audioContext.currentTime);
      gainNode.gain.setValueAtTime(0.5, audioContext.currentTime);
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      oscillator.start();
      logDebug("Playing test tone...");
      
      setTimeout(() => {
        oscillator.stop();
        audioContext.close();
        logDebug("Test tone stopped");
      }, 1000);
    } catch (error) {
      if (error instanceof Error) {
        logDebug(`Error playing test audio: ${error.message}`);
      }
    }
  };

  // Create a WAV file from PCM data
  const createWavFile = (audioData: Int16Array): Blob => {
    // WAV file header
    const numChannels = 1; // mono
    const sampleRate = 16000; // 16kHz
    const bitsPerSample = 16; // 16-bit
    const blockAlign = numChannels * bitsPerSample / 8;
    const byteRate = sampleRate * blockAlign;
    const dataSize = audioData.length * (bitsPerSample / 8);
    const buffer = new ArrayBuffer(44 + dataSize);
    const view = new DataView(buffer);
    
    // RIFF identifier
    writeString(view, 0, 'RIFF');
    // File length
    view.setUint32(4, 36 + dataSize, true);
    // RIFF type
    writeString(view, 8, 'WAVE');
    // Format chunk identifier
    writeString(view, 12, 'fmt ');
    // Format chunk length
    view.setUint32(16, 16, true);
    // Sample format (raw)
    view.setUint16(20, 1, true);
    // Channel count
    view.setUint16(22, numChannels, true);
    // Sample rate
    view.setUint32(24, sampleRate, true);
    // Byte rate (sample rate * block align)
    view.setUint32(28, byteRate, true);
    // Block align (channel count * bytes per sample)
    view.setUint16(32, blockAlign, true);
    // Bits per sample
    view.setUint16(34, bitsPerSample, true);
    // Data chunk identifier
    writeString(view, 36, 'data');
    // Data chunk length
    view.setUint32(40, dataSize, true);
    
    // Write the PCM samples
    const offset = 44;
    for (let i = 0; i < audioData.length; i++) {
      view.setInt16(offset + i * 2, audioData[i], true);
    }
    
    return new Blob([buffer], { type: 'audio/wav' });
  };
  
  // Helper function to write a string to a DataView
  const writeString = (view: DataView, offset: number, string: string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  };

  // Handle audio data from backend
  const handleAudioData = (audioBuffer: ArrayBuffer) => {
    try {
      // Convert the received PCM16 data to a WAV file
      const int16Data = new Int16Array(audioBuffer);
      logDebug(`Received audio chunk: ${int16Data.length} samples`);
      
      // Create a WAV blob from the PCM data
      const wavBlob = createWavFile(int16Data);
      
      // Create an object URL for the blob
      const objectUrl = URL.createObjectURL(wavBlob);
      
      // Create an audio element if it doesn't exist
      if (!audioElementRef.current) {
        const audioElement = document.createElement('audio');
        audioElement.setAttribute('controls', 'none');
        audioElement.style.display = 'none';
        document.body.appendChild(audioElement);
        
        audioElement.onplay = () => {
          setIsSpeaking(true);
          logDebug("Audio playback started");
        };
        
        audioElement.onended = () => {
          setIsSpeaking(false);
          logDebug("Audio playback ended");
          
          // Clean up the object URL
          URL.revokeObjectURL(audioElement.src);
        };
        
        audioElementRef.current = audioElement;
      }
      
      // Set the source and play
      const audioElement = audioElementRef.current;
      audioElement.src = objectUrl;
      audioElement.volume = 1.0; // Full volume
      
      // Autoplay with user gesture requirement workaround
      const playPromise = audioElement.play();
      if (playPromise !== undefined) {
        playPromise.catch(error => {
          logDebug(`Audio play error: ${error}`);
          // Show a play button if autoplay is blocked
        });
      }
    } catch (error) {
      if (error instanceof Error) {
        logDebug(`Error handling audio data: ${error.message}`);
        console.error(error);
      }
    }
  };

  // Send a test message
  const sendTestMessage = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const testMessage = {
        type: "text",
        content: "Hello Sophia, can you hear me? Please respond with a greeting."
      };
      wsRef.current.send(JSON.stringify(testMessage));
      logDebug("Sent test message to trigger a response");
    } else {
      logDebug("WebSocket not connected");
    }
  };

  // Start voice chat
  const startVoiceChat = async () => {
    try {
      activeRef.current = true;
      logDebug("Starting voice chat...");
      
      // Connect to backend WebSocket
      const wsUrl = "ws://localhost:8000/ws/voice";
      logDebug(`Connecting to WebSocket at ${wsUrl}`);
      
      const ws = new WebSocket(wsUrl);
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        logDebug("Connected to voice agent backend");
      };

      ws.onmessage = (event: MessageEvent) => {
        try {
          if (event.data instanceof ArrayBuffer) {
            logDebug(`Received audio data: ${event.data.byteLength} bytes`);
            handleAudioData(event.data);
          } else if (typeof event.data === 'string') {
            // Log JSON messages
            try {
              const parsed = JSON.parse(event.data);
              const jsonString = JSON.stringify(parsed);
              
              // Log transcripts
              if (parsed.type === 'response.audio_transcript.done') {
                logDebug(`Transcript: ${parsed.transcript}`);
              }
              
              // Log brief preview of JSON responses
              logDebug("Received: " + (jsonString.length > 150 ? jsonString.substring(0, 150) + "..." : jsonString));
            } catch (e) {
              logDebug(`Error parsing JSON: ${e instanceof Error ? e.message : 'Unknown error'}`);
            }
          }
        } catch (e) {
          logDebug(`Error processing message: ${e instanceof Error ? e.message : 'Unknown error'}`);
        }
      };

      ws.onerror = (error: Event) => {
        logDebug("WebSocket error occurred");
        console.error("WebSocket error:", error);
      };

      ws.onclose = (event: CloseEvent) => {
        setConnected(false);
        logDebug(`WebSocket closed. Code: ${event.code}, Reason: ${event.reason || "none provided"}`);
      };

      // Create audio context and request microphone access
      const audioCtx = new AudioContext();
      audioContextRef.current = audioCtx;
      logDebug(`AudioContext created. Sample rate: ${audioCtx.sampleRate}Hz`);
      
      // Resume AudioContext if needed (required by some browsers)
      if (audioCtx.state === 'suspended') {
        await audioCtx.resume();
        logDebug("AudioContext resumed");
      }
      
      // Request microphone access
      logDebug("Requesting microphone access...");
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      mediaStreamRef.current = stream;
      logDebug("Microphone access granted");
      
      // Setup audio processing
      const source = audioCtx.createMediaStreamSource(stream);
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      
      processor.onaudioprocess = (e: AudioProcessingEvent) => {
        if (!activeRef.current) return;
        
        const inputData = e.inputBuffer.getChannelData(0);
        
        // Calculate volume for debugging
        const volume = calculateRMS(inputData);
        const now = Date.now();
        if (!window.lastVolumeLog || now - window.lastVolumeLog > 2000) {
          logDebug(`Mic volume: ${volume.toFixed(4)}`);
          window.lastVolumeLog = now;
        }
        
        // Log when voice is detected
        if (volume > 0.01) {
          logDebug(`Voice detected at volume ${volume.toFixed(3)}`);
        }
        
        // Downsample to 16kHz for OpenAI
        let processedData: Float32Array;
        if (audioCtx.sampleRate !== 16000) {
          processedData = downsampleTo16kHz(inputData, audioCtx.sampleRate);
        } else {
          processedData = inputData;
        }
        
        // Convert to PCM16 and send
        const int16Data = float32ToInt16(processedData);
        
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(int16Data.buffer);
          
          // Log sends periodically
          if (!window.lastSendLog || now - window.lastSendLog > 2000) {
            logDebug(`Sent audio data: ${int16Data.buffer.byteLength} bytes`);
            window.lastSendLog = now;
          }
        } else {
          logDebug("WebSocket not ready");
        }
      };
      
      source.connect(processor);
      processorRef.current = processor;
      
      logDebug("Audio processing set up");
      
      // Send a test message after 3 seconds
      setTimeout(() => {
        sendTestMessage();
      }, 3000);
      
    } catch (err) {
      logDebug(`Error in startVoiceChat: ${err instanceof Error ? err.message : 'Unknown error'}`);
      stopVoiceChat();
    }
  };

  // Stop voice chat
  const stopVoiceChat = () => {
    logDebug("Stopping voice chat...");
    activeRef.current = false;
    
    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    // Clean up audio processing
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    
    // Stop microphone
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
    
    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    
    // Clean up audio element
    if (audioElementRef.current) {
      if (audioElementRef.current.src) {
        URL.revokeObjectURL(audioElementRef.current.src);
      }
      if (audioElementRef.current.parentNode) {
        audioElementRef.current.parentNode.removeChild(audioElementRef.current);
      }
      audioElementRef.current = null;
    }
    
    setConnected(false);
    setIsSpeaking(false);
    logDebug("Voice chat stopped");
  };

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (connected) {
        stopVoiceChat();
      }
    };
  }, [connected]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen relative z-10">
      <div className="mb-4 text-center">
        <div className={`px-3 py-1 rounded-full inline-block ${
          isSpeaking ? "bg-green-500" : connected ? "bg-blue-500" : "bg-gray-500"
        }`}>
          {isSpeaking ? "AI Speaking" : connected ? "Connected" : "Disconnected"}
        </div>
      </div>
      
      <button
        onClick={connected ? stopVoiceChat : startVoiceChat}
        className="px-6 py-3 bg-blue-500 text-white rounded-lg shadow-lg hover:bg-blue-600 transition-colors"
      >
        {connected ? "Stop Voice Chat" : "Start Voice Chat"}
      </button>
      
      {connected && (
        <button
          onClick={sendTestMessage}
          className="mt-2 px-6 py-3 bg-green-500 text-white rounded-lg shadow-lg hover:bg-green-600 transition-colors"
        >
          Test Response
        </button>
      )}
      
      <button
        onClick={testAudio}
        className="mt-2 px-6 py-3 bg-yellow-500 text-white rounded-lg shadow-lg hover:bg-yellow-600 transition-colors"
      >
        Test Audio
      </button>
      
      <div className="mt-4 w-full max-w-md bg-white/10 p-4 rounded-lg text-white overflow-y-auto max-h-96">
        {debugMessages.map((msg, idx) => (
          <p key={idx} className="text-sm mb-1">
            {msg}
          </p>
        ))}
      </div>
    </div>
  );
}

// Add these to fix TypeScript errors
declare global {
  interface Window {
    lastVolumeLog?: number;
    lastSendLog?: number;
    AudioContext: typeof AudioContext;
  }
}