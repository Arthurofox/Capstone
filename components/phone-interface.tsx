"use client"

import React, { useState, useRef, useEffect } from "react"
import { motion } from "framer-motion"
import { Send, Upload, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { v4 as uuidv4 } from 'uuid'

// Define types
interface Message {
  role: "user" | "assistant";
  content: string;
}

interface JobMatch {
  content?: string;
  metadata?: {
    title?: string;
    company?: string;
    location?: string;
    [key: string]: any;
  };
  score?: number;
}

interface ResumeAnalysis {
  summary: string;
  skills: string[];
  recommendations: string[];
  job_matches?: JobMatch[];
  resume_id?: string;
}

// Increased phone dimensions
const PHONE_WIDTH = 480  // Increased from typical 375
const PHONE_HEIGHT = 800 // Increased from typical 667

export default function PhoneInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState<string>("")
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [sessionId, setSessionId] = useState<string>("")
  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [resumeAnalysis, setResumeAnalysis] = useState<ResumeAnalysis | null>(null)
  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  
  // Generate a session ID on component mount
  useEffect(() => {
    setSessionId(uuidv4())
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return

    const userMessage = input
    setInput("")
    setIsLoading(true)

    // Add user message to chat
    setMessages((prev) => [...prev, { role: "user", content: userMessage }])

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          content: userMessage,
          session_id: sessionId,
        }),
      })

      if (!response.ok) throw new Error("Failed to send message")

      const data = await response.json()
      
      // Add assistant response to chat
      setMessages((prev) => [...prev, { role: "assistant", content: data.content }])
      
      // Update session ID if provided
      if (data.session_id) {
        setSessionId(data.session_id)
      }
    } catch (error) {
      console.error("Error sending message:", error)
      setMessages((prev) => [
        ...prev, 
        { role: "assistant", content: "Sorry, I encountered an error. Please try again." }
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setResumeFile(file)
      uploadResume(file)
    }
  }

  const uploadResume = async (file: File) => {
    setIsLoading(true)
    
    // Add message about uploading resume
    setMessages((prev) => [
      ...prev, 
      { role: "user", content: `I've uploaded my CV for review\n${file.name}` }
    ])

    const formData = new FormData()
    formData.append("file", file)

    try {
      const response = await fetch("/api/resume/upload", {
        method: "POST",
        body: formData,
      })

      if (!response.ok) throw new Error("Failed to upload resume")

      const analysis: ResumeAnalysis = await response.json()
      setResumeAnalysis(analysis)
      
      // Format the response to include skills, recommendations, and job matches
      let responseContent = `Here's my analysis: ${analysis.summary}\n\n`
      
      if (analysis.skills && analysis.skills.length > 0) {
        responseContent += `Key skills: ${analysis.skills.join(', ')}\n\n`
      }
      
      if (analysis.recommendations && analysis.recommendations.length > 0) {
        responseContent += `Recommendations: ${analysis.recommendations.join('\n')}\n\n`
      }
      
      // Add job matches section with larger formatting
      if (analysis.job_matches && analysis.job_matches.length > 0) {
        responseContent += `Job Matches:\n\n`
        analysis.job_matches.forEach((job, index) => {
          const title = extractField(job.content || "", "Title") || job.metadata?.title || "Unknown Position"
          const company = extractField(job.content || "", "Company") || job.metadata?.company || "Unknown Company"
          const location = extractField(job.content || "", "Location") || job.metadata?.location || ""
          
          responseContent += `${index + 1}. ${title}\n`
          responseContent += `   Company: ${company}\n`
          if (location) responseContent += `   Location: ${location}\n`
          
          // Extract and add description snippet
          const description = extractDescription(job.content || "")
          if (description) {
            const snippet = description.length > 100 ? `${description.substring(0, 100)}...` : description
            responseContent += `   Description: ${snippet}\n`
          }
          
          responseContent += "\n"
        })
      }
      
      // Add response to chat
      setMessages((prev) => [...prev, { role: "assistant", content: responseContent }])
      
    } catch (error) {
      console.error("Error uploading resume:", error)
      setMessages((prev) => [
        ...prev, 
        { role: "assistant", content: "Sorry, I encountered an error processing your resume. Please try again." }
      ])
    } finally {
      setIsLoading(false)
    }
  }
  
  // Helper function to extract fields from job content
  const extractField = (content: string, fieldName: string): string => {
    if (!content) return ""
    const regex = new RegExp(`${fieldName}:\\s*(.+?)(?:\\n|$)`, "i")
    const match = content.match(regex)
    return match ? match[1].trim() : ""
  }
  
  // Helper function to extract description from job content
  const extractDescription = (content: string): string => {
    if (!content) return ""
    const descIndex = content.indexOf("Description:")
    if (descIndex === -1) return ""
    
    const descContent = content.substring(descIndex + "Description:".length).trim()
    const nextFieldIndex = descContent.search(/\n\s*[A-Za-z]+:/)
    
    return nextFieldIndex !== -1 
      ? descContent.substring(0, nextFieldIndex).trim() 
      : descContent.trim()
  }

  const triggerFileUpload = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click()
    }
  }

  // Simple loading spinner component
  const Spinner = ({ size = "sm" }: { size?: "sm" | "md" | "lg" }) => {
    const sizeClasses = {
      sm: "w-4 h-4",
      md: "w-6 h-6",
      lg: "w-8 h-8",
    };
    
    return (
      <div className={`animate-spin rounded-full border-2 border-t-transparent ${sizeClasses[size]}`}></div>
    );
  };

  return (
    <div className="relative">
      {/* Phone Frame - Increased size */}
      <motion.div
        className="relative mx-auto rounded-[40px] overflow-hidden shadow-2xl border-8 border-gray-800 bg-gray-800"
        style={{ width: `${PHONE_WIDTH}px`, height: `${PHONE_HEIGHT}px` }}
        initial={{ y: 100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ type: "spring", damping: 20, stiffness: 100 }}
      >
        {/* Phone Notch */}
        <div className="absolute top-0 inset-x-0 h-6 bg-gray-800 rounded-b-lg z-10 flex justify-center">
          <div className="w-40 h-4 bg-black rounded-b-xl" />
        </div>

        {/* Phone Content */}
        <div className="h-full bg-gray-900 pt-8 pb-4 flex flex-col">
          {/* Chat Header */}
          <div className="px-4 py-2 flex items-center justify-between border-b border-gray-800">
            <div className="flex items-center space-x-2">
              <Sparkles className="text-purple-400 w-5 h-5" />
              <h2 className="font-medium text-white">AI Career Buddy</h2>
            </div>
          </div>

          {/* Chat Messages - Taller container */}
          <div className="flex-1 overflow-y-auto px-4 py-2 space-y-4" style={{ maxHeight: "calc(100% - 130px)" }}>
            {/* Welcome Message */}
            {messages.length === 0 && (
              <div className="bg-gray-800 rounded-lg p-3 text-gray-300 text-sm">
                <p>👋 Hi there! I'm your AI Career Buddy.</p>
                <p className="mt-2">How can I help with your career today? You can:</p>
                <ul className="list-disc list-inside mt-1 space-y-1">
                  <li>Upload your resume for analysis</li>
                  <li>Ask for career advice</li>
                  <li>Get job recommendations</li>
                  <li>Improve your interview skills</li>
                </ul>
              </div>
            )}

            {/* Message Bubbles */}
            {messages.map((message, index) => (
              <motion.div
                key={index}
                className={cn("flex", message.role === "user" ? "justify-end" : "justify-start")}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 * (index % 3) }}
              >
                <div
                  className={cn(
                    "max-w-[90%] rounded-lg px-4 py-2 text-sm whitespace-pre-wrap",
                    message.role === "user"
                      ? "bg-purple-600 text-white rounded-br-none"
                      : "bg-gray-800 text-gray-100 rounded-bl-none"
                  )}
                >
                  {message.content}
                </div>
              </motion.div>
            ))}

            {/* Loading Indicator */}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-800 rounded-lg px-4 py-2 text-gray-100 rounded-bl-none">
                  <Spinner size="sm" />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input */}
          <div className="px-4 pt-2">
            <form onSubmit={handleSendMessage} className="flex items-center space-x-2">
              <Button
                type="button"
                size="icon"
                variant="ghost"
                className="text-gray-400 hover:text-purple-400"
                onClick={triggerFileUpload}
              >
                <Upload className="w-5 h-5" />
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  className="hidden"
                  accept=".pdf,.doc,.docx"
                />
              </Button>
              <Input
                type="text"
                placeholder="Type a message..."
                className="flex-1 bg-gray-800 border-gray-700 text-white focus:ring-purple-500"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={isLoading}
              />
              <Button type="submit" size="icon" disabled={isLoading || !input.trim()}>
                <Send className="w-4 h-4" />
              </Button>
            </form>
          </div>
        </div>
      </motion.div>
    </div>
  )
}