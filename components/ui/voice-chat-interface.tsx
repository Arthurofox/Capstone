import React, { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";

export function VoiceChatInterface() {
  const [connected, setConnected] = useState(false);
  const [debugMessages, setDebugMessages] = useState<string[]>([]);
  const [timer, setTimer] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const audioElementRef = useRef<HTMLAudioElement | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Utility function to update debug messages (no console logs)
  const logDebug = (msg: string) => {
    setDebugMessages((prev) => [
      ...prev,
      new Date().toISOString().slice(11, 19) + ": " + msg,
    ]);
  };

  // Format time for the timer display (MM:SS format)
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Timer management
  useEffect(() => {
    if (connected) {
      timerIntervalRef.current = setInterval(() => {
        setTimer(prev => prev + 1);
      }, 1000);
    } else {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
        timerIntervalRef.current = null;
      }
      setTimer(0);
    }

    return () => {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
    };
  }, [connected]);

  const startVoiceChat = async () => {
    setIsAnimating(true);
    
    try {
      const tokenResponse = await fetch("http://localhost:8000/session");
      if (!tokenResponse.ok) {
        throw new Error("Failed to fetch ephemeral token");
      }
      const tokenData = await tokenResponse.json();
      const ephemeralKey = tokenData.client_secret.value;

      const pc = new RTCPeerConnection();
      pcRef.current = pc;

      pc.ontrack = (event) => {
        const [remoteStream] = event.streams;
        if (!audioElementRef.current) {
          const audioEl = document.createElement("audio");
          audioEl.autoplay = true;
          document.body.appendChild(audioEl);
          audioElementRef.current = audioEl;
        }
        audioElementRef.current.srcObject = remoteStream;
      };

      pc.createDataChannel("oai-events");

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      localStreamRef.current = stream;

      // Local muted playback (for testing mic)
      const localAudio = document.createElement("audio");
      localAudio.srcObject = stream;
      localAudio.autoplay = true;
      localAudio.muted = true;
      document.body.appendChild(localAudio);

      stream.getTracks().forEach((track) => pc.addTrack(track, stream));

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      const baseUrl = "https://api.openai.com/v1/realtime";
      const model = "gpt-4o-realtime-preview-2024-12-17";
      const sdpResponse = await fetch(`${baseUrl}?model=${model}`, {
        method: "POST",
        body: offer.sdp,
        headers: {
          Authorization: `Bearer ${ephemeralKey}`,
          "Content-Type": "application/sdp",
        },
      });
      const sdpAnswer = await sdpResponse.text();
      await pc.setRemoteDescription({ type: "answer", sdp: sdpAnswer });

      setConnected(true);
    } catch (error) {
      logDebug(
        `Error starting voice chat: ${
          error instanceof Error ? error.message : String(error)
        }`
      );
    } finally {
      setIsAnimating(false);
    }
  };

  const stopVoiceChat = () => {
    if (pcRef.current) {
      pcRef.current.close();
      pcRef.current = null;
    }
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach((track) => track.stop());
      localStreamRef.current = null;
    }
    setConnected(false);
  };

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        // No background - will use the parent container's background
      }}
    >
      <div
        style={{
          backgroundColor: "rgba(255, 255, 255, 0.15)",
          backdropFilter: "blur(8px)",
          padding: "2rem",
          borderRadius: "1.5rem",
          border: "1px solid rgba(255, 255, 255, 0.2)",
          boxShadow: "0 8px 32px rgba(0, 0, 0, 0.08)",
          textAlign: "center",
          width: "280px",
          maxWidth: "90%",
          transition: "all 0.3s ease",
        }}
      >
        {connected ? (
          <h2 
            style={{ 
              marginBottom: "1.5rem",
              fontSize: "1.5rem",
              fontWeight: "500",
              transition: "color 0.3s ease",
              color: "#4CAF50"
            }}
          >
            Voice Chat Active
          </h2>
        ) : (
          <motion.h2 
            style={{ 
              marginBottom: "1.5rem",
              fontSize: "1.5rem",
              fontWeight: "700", // Changed to bold
              color: "#FFF8DC"   // Same yellow-cream color
            }}
            animate={{
              textShadow: [
                '0 2px 8px rgba(255, 253, 208, 0.3)', 
                '0 2px 15px rgba(255, 253, 208, 0.7)', 
                '0 2px 8px rgba(255, 253, 208, 0.3)'
              ],
            }}
            transition={{
              duration: 4,
              ease: "easeInOut",
              repeat: Infinity,
            }}
          >
            Prepare your interview
          </motion.h2>
        )}
        
        {connected && (
          <div 
            style={{
              marginBottom: "1.5rem",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              gap: "0.5rem"
            }}
          >
            <div 
              style={{
                width: "12px",
                height: "12px",
                borderRadius: "50%",
                backgroundColor: "#4CAF50",
                animation: "pulse 1.5s infinite",
              }}
            />
            <span 
              style={{
                fontSize: "1.3rem",
                fontWeight: "300",
                fontFamily: "monospace",
                color: "#fff"
              }}
            >
              {formatTime(timer)}
            </span>
          </div>
        )}

        <button
          onClick={connected ? stopVoiceChat : startVoiceChat}
          disabled={isAnimating}
          style={{
            backgroundColor: connected ? "rgba(244, 67, 54, 0.1)" : "rgba(255, 255, 255, 0.15)",
            color: connected ? "#F44336" : "#fff",
            border: `1px solid ${connected ? "#F44336" : "rgba(255, 255, 255, 0.4)"}`,
            padding: "0.75rem 1.5rem",
            fontSize: "0.95rem",
            fontWeight: "400",
            borderRadius: "9999px",
            cursor: "pointer",
            transition: "all 0.3s ease",
            outline: "none",
            position: "relative",
            overflow: "hidden",
            boxShadow: connected ? "0 0 0 rgba(244, 67, 54, 0)" : "0 4px 15px rgba(0, 0, 0, 0.1)",
            transform: isAnimating ? "scale(0.98)" : "scale(1)",
            backdropFilter: "blur(4px)",
          }}
        >
          {isAnimating ? (
            <span>Connecting...</span>
          ) : (
            <span>{connected ? "End Voice Chat" : "Start Voice Chat"}</span>
          )}
          
          {/* The subtle ripple animation container (hidden by overflow:hidden in the button) */}
          {isAnimating && (
            <span
              style={{
                position: "absolute",
                top: "50%",
                left: "50%",
                transform: "translate(-50%, -50%)",
                width: "150%",
                height: "150%",
                backgroundColor: "rgba(255, 255, 255, 0.4)",
                borderRadius: "50%",
                animation: "ripple 1.5s infinite",
              }}
            />
          )}
        </button>

        {debugMessages.length > 0 && (
          <div
            style={{
              marginTop: "1.5rem",
              maxHeight: "120px",
              overflowY: "auto",
              color: "rgba(255, 255, 255, 0.7)",
              fontSize: "0.8rem",
              textAlign: "left",
              backgroundColor: "rgba(0, 0, 0, 0.2)",
              borderRadius: "0.5rem",
              padding: "0.5rem",
            }}
          >
            {debugMessages.map((msg, idx) => (
              <p key={idx} style={{ margin: "0.25rem 0", fontFamily: "monospace" }}>
                {msg}
              </p>
            ))}
          </div>
        )}
      </div>

      {/* CSS Animations */}
      <style>
        {`
          @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
          }
          
          @keyframes ripple {
            0% {
              transform: translate(-50%, -50%) scale(0);
              opacity: 1;
            }
            100% {
              transform: translate(-50%, -50%) scale(1);
              opacity: 0;
            }
          }
        `}
      </style>
    </div>
  );
}