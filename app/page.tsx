"use client";

import Link from "next/link";
import Image from "next/image";
import { Heart, Sun, Moon } from "lucide-react";
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { ChatbotInterface } from "@/components/ui/chatbot-interface";

export default function HomePage() {
  const [theme, setTheme] = useState("light");
  const [mounted, setMounted] = useState(false);
  const [chatExpanded, setChatExpanded] = useState(false);

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

  const toggleTheme = () => {
    const newTheme = theme === "light" ? "dark" : "light";
    setTheme(newTheme);
    localStorage.setItem("theme", newTheme);
    if (newTheme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  };

  return (
    <>
      {/* Dynamic Background */}
      <div className="fixed inset-0 z-0">
        {/* Day background */}
        <Image
          src="/background.png"
          alt="Day background"
          fill
          priority
          className="object-cover"
          style={{
            objectPosition: "60% center",
            transition: "opacity 5s ease",
            opacity: theme === "dark" ? 0 : 1,
          }}
        />
        {/* Night background */}
        <Image
          src="/background_night.png"
          alt="Night background"
          fill
          priority
          className="object-cover absolute inset-0"
          style={{
            objectPosition: "60% center",
            transition: "opacity 5s ease",
            opacity: theme === "dark" ? 1 : 0,
          }}
        />
        {/* Optional subtle overlay */}
        <div
          className="absolute inset-0"
          style={{
            backgroundColor: "rgba(37, 55, 90, 0.3)",
            transition: "opacity 5s ease",
            opacity: theme === "dark" ? 1 : 0,
          }}
        />
      </div>

      {/* Landing Page Content */}
      <div className="min-h-screen flex flex-col theme-transition relative z-10">
        {/* Navigation */}
        <nav className="w-full py-4 px-6 flex justify-between items-center bg-black/10 backdrop-blur-soft">
          <Link href="/" className="flex items-center space-x-2">
            <Heart className="h-6 w-6 text-yellow-500" fill="#FFD700" />
            <span className="text-2xl font-semibold text-white drop-shadow-md">
              PathFinder
            </span>
          </Link>
          <div className="flex items-center space-x-3">
            {mounted && (
              <button
                onClick={toggleTheme}
                className="p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
                aria-label={
                  theme === "dark" ? "Switch to light mode" : "Switch to dark mode"
                }
              >
                {theme === "dark" ? (
                  <Sun className="h-5 w-5 text-yellow-200" />
                ) : (
                  <Moon className="h-5 w-5 text-slate-700" />
                )}
              </button>
            )}
            <a
              href="/signin"
              className="px-4 py-2 text-sm bg-transparent border border-white text-white rounded-full hover:bg-white/20 transition-colors"
            >
              Sign in
            </a>
            <a
              href="/signup"
              className="px-4 py-2 text-sm bg-white text-slate-800 rounded-full hover:bg-white/90 transition-colors"
            >
              Sign up
            </a>
            {/* New Voice Chat Link */}
            <Link
              href="/voice"
              className="px-4 py-2 text-sm bg-transparent border border-white text-white rounded-full hover:bg-white/20 transition-colors"
            >
              Voice Chat
            </Link>
          </div>
        </nav>

        {/* Main Landing Content */}
        {/*
          Removed the previous flex "justify-center" so content stays higher.
          Adjust padding as needed:
          - pt-6 controls top spacing
          - pb-8 controls bottom spacing
        */}
        <main className="pt-6 px-4 pb-8">
          {/* Headline Text that fades when chat expands */}
          <motion.div
            className="text-center mb-8"
            initial={{ opacity: 1 }}
            animate={{
              opacity: chatExpanded ? 0 : 1,
              y: chatExpanded ? -20 : 0,
            }}
            transition={{
              opacity: { duration: 0.7, ease: "easeOut" },
              y: { duration: 0.5, ease: "easeOut" },
            }}
          >
            <motion.h1 
              className="text-5xl md:text-7xl font-bold mb-4"
              style={{ color: '#FFF8DC' }}
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
              Define your path.
            </motion.h1>
            <p className="text-xl md:text-2xl drop-shadow-md max-w-2xl mx-auto" style={{ color: '#FFFACD' }}>
            Explore tailored opportunities, enhanced resumes, and empowering career guidance for a stress-free journey.
            </p>
          </motion.div>

          {/* ChatbotInterface */}
          <div className="flex items-center justify-center">
            <ChatbotInterface onExpandChange={setChatExpanded} />
          </div>
        </main>
      </div>
    </>
  );
}