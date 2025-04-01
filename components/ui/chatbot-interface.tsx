"use client";

import { useState, useRef, useEffect, ChangeEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Heart, SendHorizontal, Paperclip } from "lucide-react";
import { Button } from "./button";
import { cn } from "@/lib/utils";

type MessageType = "user" | "bot";

interface Message {
  id: string;
  content: string;
  type: MessageType;
  timestamp: Date;
}

/**
 * Minimal shape of the server's /api/chat response
 */
interface ChatAPIResponse {
  content: string;     // The bot's response text
  session_id: string;  // The session ID
}

/**
 * Minimal shape of the server's /api/resume/upload response
 */
interface ResumeAnalysis {
  summary: string;
  skills: string[];
  recommendations: string[];
  job_matches?: any[];
  resume_id?: string;
}

export function ChatbotInterface({
  onExpandChange,
}: {
  onExpandChange?: (expanded: boolean) => void;
}) {
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
  const [sessionId, setSessionId] = useState<string | null>(null); // track session
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Suggestions (only 2, as requested)
  const suggestions = [
    "Advice for building a resume",
    "How do I negotiate my salary",
  ];

  // Notify parent about expansion state
  useEffect(() => {
    onExpandChange?.(expanded);
  }, [expanded, onExpandChange]);


  // Focus input if expanded
  useEffect(() => {
    if (expanded) {
      setTimeout(() => {
        inputRef.current?.focus();
      }, 300);
    }
  }, [expanded]);

  /**
   * Handle user submitting text
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    // 1. Add user's message to local state
    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      type: "user",
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // 2. Clear input, expand chat (if first time)
    setInputValue("");
    if (!expanded) setExpanded(true);

    // 3. Call the FastAPI /api/chat endpoint
    try {
      const res = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: userMessage.content,
          session_id: sessionId, // pass existing session if any
        }),
      });
      if (!res.ok) {
        throw new Error(`Chat API error: ${res.statusText}`);
      }
      const data: ChatAPIResponse = await res.json();

      // 4. Save or update the session ID
      if (!sessionId) {
        setSessionId(data.session_id);
      }

      // 5. Add bot's response to local state
      const botMessage: Message = {
        id: Date.now().toString() + "-bot",
        content: data.content,
        type: "bot",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error("Error in /api/chat:", error);
      // You could display an error message in the UI:
      const errorMessage: Message = {
        id: Date.now().toString() + "-bot",
        content: "Sorry, I ran into a problem reaching the server.",
        type: "bot",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  /**
   * Handle file uploads (resume)
   */
  const handleFileUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    const file = e.target.files[0];

    try {
      const formData = new FormData();
      formData.append("file", file);

      // POST to FastAPI /api/resume/upload
      const res = await fetch("http://localhost:8000/api/resume/upload", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        throw new Error(`Upload API error: ${res.statusText}`);
      }
      const data: ResumeAnalysis = await res.json();

      // Example: show summary in the chat
      const analysisMessage: Message = {
        id: Date.now().toString() + "-resume",
        content: `**Resume Analysis**\n\n**Summary:** ${data.summary}\n**Skills:** ${data.skills.join(", ")}\n**Recommendations:** ${data.recommendations.join(", ")}`,
        type: "bot",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, analysisMessage]);
    } catch (error) {
      console.error("Error in /api/resume/upload:", error);
      const errorMessage: Message = {
        id: Date.now().toString() + "-bot",
        content: "Resume upload failed. Please try again later.",
        type: "bot",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  return (
    <div className="relative w-full max-w-[600px] mx-auto">
      {/* COLLAPSED (Page 1) */}
      <motion.div
        className="relative rounded-xl overflow-hidden"
        initial={{ opacity: 1 }}
        animate={{ opacity: expanded ? 0 : 1 }}
        transition={{ duration: 0.3 }}
        style={{ pointerEvents: expanded ? "none" : "auto" }}
      >
        <form onSubmit={handleSubmit} className="p-4">
          <div className="relative flex flex-col space-y-2">
            {/* Main input + ASK button */}
            <div className="flex items-center">
              <input
                type="text"
                placeholder="Ask PathFinder about your career path..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                className="flex-1 p-4 pl-6 pr-16 rounded-lg border border-gray-300 bg-white/30 text-slate-900 focus:outline-none focus:ring-2 focus:ring-yellow-300 backdrop-blur-sm"
              />
              <button
                type="submit"
                className="absolute right-2 px-4 py-2 rounded-md bg-yellow-400 hover:bg-yellow-500 text-yellow-900"
                style={{ top: "50%", transform: "translateY(-50%)" }}
              >
                Ask
              </button>
            </div>

            {/* Suggestions (2 only) */}
            <div className="flex gap-2 mt-1">
              {suggestions.map((suggestion, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setInputValue(suggestion)}
                  className="px-3 py-1 text-sm bg-white/50 hover:bg-white/60 text-slate-800 rounded-full border border-gray-200"
                >
                  {suggestion}
                </button>
              ))}
            </div>

            {/* Upload button with paperclip */}
            <div className="mt-2">
              <label
                className="
                  inline-flex items-center space-x-1 
                  cursor-pointer p-2 text-sm bg-white/70
                  border border-gray-300 rounded-md
                  hover:bg-white hover:text-gray-700
                  transition-colors text-gray-800
                "
              >
                <Paperclip className="w-4 h-4" />
                <span>Upload CV</span>
                <input
                  type="file"
                  hidden
                  onChange={handleFileUpload}
                  accept=".pdf,.doc,.docx"
                />
              </label>
            </div>
          </div>
        </form>
      </motion.div>

      {/* EXPANDED (Page 2) */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.4 }}
            className="overflow-hidden"
          >
            <div className="mt-2 bg-white/5 border border-white/10 rounded-xl p-2 backdrop-blur-none">
              <header className="p-4 border-b border-white/10 flex justify-between items-center">
                <div>
                  <h3 className="text-lg font-medium flex items-center text-white">
                    <Heart className="h-5 w-5 text-yellow-400 mr-2" />
                    Career Advisor
                  </h3>
                  <p className="text-sm text-slate-300">
                    Ask me anything about your career path
                  </p>
                </div>
                <Button
                  onClick={() => setExpanded(false)}
                  className="px-3 py-1 text-sm bg-yellow-200/70 hover:bg-yellow-300/70 text-slate-700 rounded-md"
                >
                  Minimize
                </Button>
              </header>

              <main className="overflow-y-auto p-4 space-y-4">
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
                  delay: index > messages.length - 2 ? 0.1 : 0,
                }}
              >
                <div
                  className={cn(
                    "max-w-[80%] rounded-lg px-4 py-2",
                    {
                      "bg-yellow-100/40 text-slate-800 border border-yellow-200/50":
                        message.type === "user",
                      "bg-sky-50/40 text-slate-800 border border-sky-100/50":
                        message.type === "bot",
                    }
                  )}
                >
                  <div
                    className="text-sm leading-relaxed"
                    dangerouslySetInnerHTML={{ __html: message.content }}
                  ></div>
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


              <footer className="p-4 border-t border-white/10 flex items-center space-x-2">
                {/* Upload button in expanded view */}
                <label
                  className="
                    inline-flex items-center space-x-1 
                    cursor-pointer p-2 text-sm bg-white/70
                    border border-gray-300 rounded-md
                    hover:bg-white hover:text-gray-700
                    transition-colors text-gray-800
                  "
                >
                  <Paperclip className="w-4 h-4" />
                  <span>Upload CV</span>
                  <input
                    type="file"
                    hidden
                    onChange={handleFileUpload}
                    accept=".pdf,.doc,.docx"
                  />
                </label>

                <form onSubmit={handleSubmit} className="flex flex-1 items-center space-x-2">
                  <input
                    ref={inputRef}
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    placeholder="Ask about your career path..."
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-300 bg-white/30"
                  />
                  <Button
                    type="submit"
                    className="p-2 bg-yellow-400/80 hover:bg-yellow-500/80 text-yellow-900"
                  >
                    <SendHorizontal className="h-5 w-5" />
                    <span className="sr-only">Send</span>
                  </Button>
                </form>
              </footer>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
