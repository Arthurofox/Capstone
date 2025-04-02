"use client";

import React, { useState, useEffect, useRef } from "react";

export function VoiceChatInterface() {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  const startVoiceChat = () => {
    // Build the WebSocket URL using the current protocol and host.
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const host = window.location.host;
    const wsUrl = `${protocol}://${host}/ws/voice`;
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setMessages((prev) => [...prev, "Connected to voice agent backend."]);
    };

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        setMessages((prev) => [...prev, "Received: " + JSON.stringify(parsed)]);
      } catch (e) {
        setMessages((prev) => [...prev, "Received: " + event.data]);
      }
    };

    ws.onerror = (error) => {
      setMessages((prev) => [
        ...prev,
        "WebSocket error: " + JSON.stringify(error),
      ]);
    };

    ws.onclose = () => {
      setConnected(false);
      setMessages((prev) => [...prev, "Voice chat connection closed."]);
    };
  };

  const stopVoiceChat = () => {
    if (wsRef.current) {
      wsRef.current.close();
    }
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
        {messages.map((msg, idx) => (
          <p key={idx} className="text-sm">
            {msg}
          </p>
        ))}
      </div>
    </div>
  );
}
