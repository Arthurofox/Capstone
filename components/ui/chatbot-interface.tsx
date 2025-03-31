"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Heart, SendHorizontal, X } from "lucide-react";
import { Button } from "./button";
import { cn } from "@/lib/utils";

type MessageType = "user" | "bot";

interface Message {
  id: string;
  content: string;
  type: MessageType;
  timestamp: Date;
}

export function ChatbotInterface({ onExpandChange }: { onExpandChange?: (expanded: boolean) => void }) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      content: "Hi there! I'm your career advisor. How can I help you today?",
      type: "bot",
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [expanded, setExpanded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Notify parent component when expanded state changes
  useEffect(() => {
    onExpandChange?.(expanded);
  }, [expanded, onExpandChange]);

  // Scroll to bottom whenever messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus the input field when expanded
  useEffect(() => {
    if (expanded) {
      setTimeout(() => {
        inputRef.current?.focus();
      }, 500); // Delay focus until animation completes
    }
  }, [expanded]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      type: "user",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");

    // Expand the chat interface on first submission
    if (!expanded) setExpanded(true);

    // Simulate bot response
    setTimeout(() => {
      const botResponses = [
        "That's a great question about career development!",
        "Based on your interests, you might want to explore these fields...",
        "Have you considered internships in this area?",
        "I'd recommend focusing on developing these specific skills...",
        "Let me help you craft a plan for your career journey.",
      ];
      const randomResponse =
        botResponses[Math.floor(Math.random() * botResponses.length)];

      const botMessage: Message = {
        id: Date.now().toString(),
        content: randomResponse,
        type: "bot",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, botMessage]);
    }, 1000);
  };

  return (
    <div className="relative w-full max-w-[600px] mx-auto">
      {/* Collapsed input - always visible but opacity changes */}
      <motion.div
        className="relative rounded-xl overflow-hidden"
        initial={{ opacity: 1 }}
        animate={{ opacity: expanded ? 0 : 1 }}
        transition={{ duration: 0.3 }}
        style={{ pointerEvents: expanded ? "none" : "auto" }}
      >
        <form onSubmit={handleSubmit} className="p-4">
          <div className="relative">
            <input
              type="text"
              placeholder="Ask PathFinder about your career path..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              className="w-full p-4 pl-6 pr-16 rounded-lg border border-gray-300 bg-white/30 text-slate-900 focus:outline-none focus:ring-2 focus:ring-yellow-300 backdrop-blur-sm"
            />
            <button
              type="submit"
              className="absolute right-2 top-1/2 transform -translate-y-1/2 px-4 py-2 rounded-md bg-yellow-400 hover:bg-yellow-500 text-yellow-900"
            >
              Ask
            </button>
          </div>
        </form>
      </motion.div>

      {/* Expanded Chat Interface - Fixed position but with high transparency */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            className="fixed inset-0 z-40 flex items-center justify-center p-4 pointer-events-none"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          >
            {/* Semi-transparent overlay for background effect only - no darkening */}
            <motion.div 
              className="absolute inset-0 bg-transparent" 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            />

            {/* Chat Container */}
            <motion.div
              className="bg-white/20 shadow-lg border border-white/20 rounded-xl backdrop-blur-sm w-full max-w-3xl h-[80vh] overflow-hidden pointer-events-auto z-50"
              initial={{ scale: 0.9, y: 50, opacity: 0 }}
              animate={{ scale: 1, y: 0, opacity: 1 }}
              exit={{ scale: 0.9, y: 50, opacity: 0 }}
              transition={{ 
                type: "spring", 
                damping: 25, 
                stiffness: 300,
                duration: 0.4 
              }}
            >
              <div className="flex flex-col h-full">
                <header className="p-4 border-b border-yellow-200/30 bg-white/20 backdrop-blur-md flex justify-between items-center">
                  <div>
                    <h3 className="text-lg font-medium flex items-center">
                      <Heart className="h-5 w-5 text-yellow-500 mr-2" fill="#FFD700" />
                      Career Advisor
                    </h3>
                    <p className="text-sm text-slate-700">
                      Ask me anything about your career path
                    </p>
                  </div>
                  <Button
                    onClick={() => setExpanded(false)}
                    className="px-3 py-1 text-sm bg-yellow-200/70 hover:bg-yellow-300/70 text-slate-700 rounded-md backdrop-blur-sm"
                  >
                    Minimize
                  </Button>
                </header>

                <main className="flex-1 p-4 overflow-y-auto space-y-4 bg-transparent">
                  {messages.map((message, index) => (
                    <motion.div
                      key={message.id}
                      className={cn("flex", {
                        "justify-end": message.type === "user",
                        "justify-start": message.type === "bot",
                      })}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{
                        duration: 0.3,
                        delay: index > messages.length - 2 ? 0.1 : 0, // Only animate newest messages
                      }}
                    >
                      <div
                        className={cn("max-w-[80%] rounded-lg px-4 py-2 backdrop-blur-sm", {
                          "bg-yellow-100/40 text-slate-800 border border-yellow-200/50":
                            message.type === "user",
                          "bg-sky-50/40 text-slate-800 border border-sky-100/50":
                            message.type === "bot",
                        })}
                      >
                        <p>{message.content}</p>
                        <p className="text-xs opacity-70 mt-1">
                          {message.timestamp.toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </p>
                      </div>
                    </motion.div>
                  ))}
                  <div ref={messagesEndRef} />
                </main>

                <footer className="p-4 border-t border-yellow-200/30 bg-white/20 backdrop-blur-md">
                  <form onSubmit={handleSubmit} className="flex space-x-2">
                    <input
                      ref={inputRef}
                      type="text"
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      placeholder="Ask about your career path..."
                      className="flex-1 px-4 py-2 border border-yellow-200/40 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-300/50 bg-white/30 backdrop-blur-sm"
                    />
                    <Button type="submit" className="p-2 bg-yellow-400/80 hover:bg-yellow-500/80 text-yellow-900">
                      <SendHorizontal className="h-5 w-5" />
                      <span className="sr-only">Send message</span>
                    </Button>
                  </form>
                </footer>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Modified HomePage component with text fade animation
export function UpdatedHomePage() {
  const [chatExpanded, setChatExpanded] = useState(false);
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

  return (
    <>
      {/* Dynamic Background */}
      <div className="fixed inset-0 z-0">
        {/* Day background */}
        {/* Background elements as in your original code */}
      </div>

      {/* Landing Page Content */}
      <div className="min-h-screen flex flex-col theme-transition relative z-10">
        {/* Navigation */}
        <nav className="w-full py-4 px-6 flex justify-between items-center bg-black/10 backdrop-blur-soft">
          {/* Navigation elements as in your original code */}
        </nav>

        {/* Main Landing Content */}
        <main className="flex-1 flex flex-col items-center justify-center px-4 pt-6 pb-16">
          {/* Headline Text with Fade Animation */}
          <motion.div 
            className="text-center mb-8"
            initial={{ opacity: 1 }}
            animate={{ 
              opacity: chatExpanded ? 0 : 1,
              y: chatExpanded ? -20 : 0 
            }}
            transition={{ 
              opacity: { duration: 0.7, ease: "easeOut" },
              y: { duration: 0.5, ease: "easeOut" }
            }}
          >
            <h1 className="text-5xl md:text-7xl font-bold text-white drop-shadow-lg mb-4">
              Career advice in seconds.
            </h1>
            <p className="text-xl md:text-2xl text-white drop-shadow-md max-w-2xl mx-auto">
              PathFinder is your AI career advisor for every step of your journey.
            </p>
          </motion.div>

          {/* ChatbotInterface with expanded state callback */}
          <div className="w-full flex items-center justify-center my-8">
            <ChatbotInterface onExpandChange={setChatExpanded} />
          </div>

          {/* Additional landing page elements can be placed here */}
        </main>
      </div>
    </>
  );
}