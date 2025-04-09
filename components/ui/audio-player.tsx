// components/ui/audio-player.tsx
"use client";

import { useState, useRef, useEffect } from "react";
import { Volume2, VolumeX, Play, Pause, Music } from "lucide-react";

export function AudioPlayer() {
  const [volume, setVolume] = useState(0.3);
  const [muted, setMuted] = useState(false);
  const [playing, setPlaying] = useState(true);
  const [showControls, setShowControls] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = muted ? 0 : volume;
    }
  }, [volume, muted]);

  const toggleMute = () => {
    setMuted(!muted);
    if (audioRef.current) {
      audioRef.current.volume = muted ? volume : 0;
    }
  };

  const togglePlay = () => {
    if (audioRef.current) {
      if (playing) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      setPlaying(!playing);
    }
  };

  return (
    <div 
      className="flex items-center gap-2"
      onMouseEnter={() => setShowControls(true)}
      onMouseLeave={() => setShowControls(false)}
    >
      <div className="flex items-center">
        <Music size={14} className="text-yellow-400 mr-1" />
      </div>

      <button 
        onClick={togglePlay}
        className="p-2 rounded-full bg-yellow-400/80 hover:bg-yellow-500/80 transition-colors text-yellow-900"
      >
        {playing ? <Pause size={16} /> : <Play size={16} />}
      </button>

      <button 
        onClick={toggleMute}
        className="p-2 rounded-full bg-yellow-400/80 hover:bg-yellow-500/80 transition-colors text-yellow-900"
      >
        {muted ? <VolumeX size={16} /> : <Volume2 size={16} />}
      </button>
      
      <div 
        className={`transition-all duration-300 overflow-hidden ${
          showControls ? "w-24 opacity-100" : "w-0 opacity-0"
        }`}
      >
        <input
          type="range"
          min="0"
          max="1"
          step="0.01"
          value={volume}
          onChange={(e) => setVolume(parseFloat(e.target.value))}
          className="w-full h-1 bg-yellow-200 appearance-none rounded cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-yellow-400"
          style={{ accentColor: '#fcd34d' }}
        />
      </div>
      
      <audio 
        ref={audioRef} 
        src="/lofi-background.mp3" 
        loop 
        autoPlay 
      />
    </div>
  );
}
