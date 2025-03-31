"use client";

import Link from "next/link";
import Image from "next/image";
import { Heart, Sun, Moon } from "lucide-react";
import { useState, useEffect } from "react";
import { ChatbotInterface } from "@/components/ui/chatbot-interface";

export default function HomePage() {
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

  const pillStyle =
    theme === "dark"
      ? "rounded-full bg-indigo-900 bg-opacity-70 text-indigo-100 hover:bg-indigo-800 border border-indigo-700 transition-all"
      : "rounded-full bg-yellow-100 bg-opacity-90 text-slate-800 hover:bg-yellow-200 border border-yellow-300 transition-all";

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
                aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
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
          </div>
        </nav>

        {/* Main Landing Content */}
        <main className="flex-1 flex flex-col items-center justify-center px-4 pt-6 pb-16">
          <div className="text-center mb-8">
            <h1 className="text-5xl md:text-7xl font-bold text-white drop-shadow-lg mb-4">
              Career advice in seconds.
            </h1>
            <p className="text-xl md:text-2xl text-white drop-shadow-md max-w-2xl mx-auto">
              PathFinder is your AI career advisor for every step of your journey.
            </p>
          </div>

          {/* ChatbotInterface rendered inline so it scrolls with the page */}
          <div className="w-full flex items-center justify-center my-8">
            <ChatbotInterface />
          </div>

          {/* Additional landing page elements can be placed here */}
        </main>
      </div>
    </>
  );
}
