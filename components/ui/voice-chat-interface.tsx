"use client";

import React, { useState, useEffect, useRef } from "react";

export function VoiceChatInterface() {
  const [connected, setConnected] = useState(false);
  const [debugMessages, setDebugMessages] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);

  const logDebug = (msg: string) => {
    console.log(msg);
    setDebugMessages((prev) => [...prev, msg]);
  };

  // Converts a Float32Array to an Int16Array (PCM16)
  const float32ToInt16 = (buffer: Float32Array): Int16Array => {
    const l = buffer.length;
    const int16Buffer = new Int16Array(l);
    for (let i = 0; i < l; i++) {
      let s = Math.max(-1, Math.min(1, buffer[i]));
      int16Buffer[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return int16Buffer;
  };

  // Converts an Int16Array to a Float32Array (for playback)
  const int16ToFloat32 = (int16Buffer: Int16Array): Float32Array => {
    const float32Buffer = new Float32Array(int16Buffer.length);
    for (let i = 0; i < int16Buffer.length; i++) {
      float32Buffer[i] = int16Buffer[i] / 32767;
    }
    return float32Buffer;
  };

  // Plays a received binary audio chunk using the AudioContext.
  const playAudioChunk = (arrayBuffer: ArrayBuffer) => {
    const audioCtx = audioContextRef.current;
    if (!audioCtx) {
      logDebug("AudioContext not initialized.");
      return;
    }
    const int16Data = new Int16Array(arrayBuffer);
    const float32Data = int16ToFloat32(int16Data);
    const audioBuffer = audioCtx.createBuffer(1, float32Data.length, audioCtx.sampleRate);
    audioBuffer.copyToChannel(float32Data, 0);
    const source = audioCtx.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioCtx.destination);
    source.start();
  };

  const startVoiceChat = async () => {
    try {
      logDebug("Starting voice chat...");
      // Use the correct backend URL explicitly during development
      const wsUrl = process.env.NODE_ENV === 'production' 
        ? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/ws/voice`
        : `ws://localhost:8000/ws/voice`;
      
      logDebug(`Connecting to WebSocket at ${wsUrl}`);
      const ws = new WebSocket(wsUrl);
      ws.binaryType = "arraybuffer"; // Expect binary audio data.
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        logDebug("Connected to voice agent backend.");
      };

      ws.onmessage = (event) => {
        // Try to parse as JSON; if fails, assume it's binary audio.
        try {
          const parsed = JSON.parse(event.data);
          logDebug("Received text: " + JSON.stringify(parsed));
        } catch (e) {
          logDebug("Received audio chunk.");
          if (event.data instanceof ArrayBuffer) {
            playAudioChunk(event.data);
          }
        }
      };

      ws.onerror = (error) => {
        logDebug("WebSocket error: " + JSON.stringify(error));
      };

      ws.onclose = () => {
        setConnected(false);
        logDebug("Voice chat connection closed.");
      };

      // Set up AudioContext for recording and playback.
      if (!audioContextRef.current) {
        audioContextRef.current = new AudioContext();
        logDebug("AudioContext created.");
      }
      const audioCtx = audioContextRef.current;

      logDebug("Requesting microphone access...");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      logDebug("Microphone access granted.");
      const source = audioCtx.createMediaStreamSource(stream);
      // Create a ScriptProcessorNode to capture audio samples.
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        const int16Data = float32ToInt16(inputData);
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(int16Data.buffer);
        }
      };
      source.connect(processor);
      // Uncomment the next line if you want to hear your own voice.
      // processor.connect(audioCtx.destination);
      processorRef.current = processor;
      logDebug("Audio processing set up.");
    } catch (err) {
      logDebug("Error in startVoiceChat: " + err);
    }
  };

  const stopVoiceChat = () => {
    logDebug("Stopping voice chat...");
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    setConnected(false);
    logDebug("Voice chat stopped.");
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen relative z-10">
      <button
        onClick={connected ? stopVoiceChat : startVoiceChat}
        className="px-6 py-3 bg-blue-500 text-white rounded-lg shadow-lg hover:bg-blue-600 transition-colors"
      >
        {connected ? "Stop Voice Chat" : "Start Voice Chat"}
      </button>
      <div className="mt-4 w-full max-w-md bg-white/10 p-4 rounded-lg text-white overflow-y-auto max-h-60">
        {debugMessages.map((msg, idx) => (
          <p key={idx} className="text-sm">
            {msg}
          </p>
        ))}
      </div>
    </div>
  );
}
