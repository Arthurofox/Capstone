"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import { ArrowLeft } from "lucide-react";
import { VoiceChatInterface } from "@/components/ui/voice-chat-interface";
import Link from "next/link";

export default function VoiceChatPage() {
  const [theme, setTheme] = useState("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const savedTheme = localStorage.getItem("theme") || "light";
    setTheme(savedTheme);
    if (savedTheme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    setMounted(true);
  }, []);

  return (
    <>
      {/* Static Background for Voice Chat Page */}
      <div className="fixed inset-0 z-0">
        <Image
          src="/background-p2.png"
          alt="Voice Chat Background"
          fill
          priority
          className="object-cover"
        />
      </div>

      {/* Voice Chat Page Content */}
      <div className="min-h-screen flex flex-col relative z-10">
        <nav className="w-full py-4 px-6 flex items-center bg-black/10 backdrop-blur-sm">
          <Link
            href="/"
            className="flex items-center text-white hover:text-white/80 transition-colors"
          >
            <ArrowLeft className="h-5 w-5 mr-2" />
            <span>Back</span>
          </Link>
          <div className="flex-grow text-center">
            <h1 className="text-2xl font-bold text-white">Voice Chat</h1>
          </div>
          <div className="w-20">
            {/* Empty div to balance the layout */}
          </div>
        </nav>

        <main className="flex-grow flex items-center justify-center px-4 py-8">
          <div className="w-full max-w-md mx-auto">
            <VoiceChatInterface />
          </div>
        </main>
      </div>
    </>
  );
}