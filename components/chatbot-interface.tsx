"use client"

import { useState, useEffect, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Send, Paperclip, FileText, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { toast } from "sonner"

interface ChatbotInterfaceProps {
  fullScreen?: boolean
}

type Message = {
  id: string
  text: string
  isUser: boolean
  attachment?: {
    name: string
    type: string
  }
}

export function ChatbotInterface({ fullScreen = false }: ChatbotInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isUploading, setIsUploading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      setMessages([
        {
          id: "1",
          text: "Hey there! 👋 I'm your AI career buddy.",
          isUser: false,
        },
        {
          id: "2",
          text: "You can upload your CV, and I'll help you improve it or find matching job roles!",
          isUser: false,
        },
        {
          id: "3",
          text: "Or you can ask me about:",
          isUser: false,
        },
        {
          id: "4",
          text: "1️⃣ Resume improvement tips\n2️⃣ Job role recommendations\n3️⃣ Career path evaluation",
          isUser: false,
        },
      ])
    }, 500)

    return () => clearTimeout(timer)
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim()) return

    const newMessage: Message = {
      id: Date.now().toString(),
      text: input,
      isUser: true,
    }

    setMessages(prev => [...prev, newMessage])
    setInput("")

    try {
      console.log('Sending message:', input)
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content: input }),
      })

      console.log('Response:', response)
      const data = await response.json()
      console.log('Data:', data)

      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        text: data.content,
        isUser: false,
      }])
    } catch (error) {
      console.error('Error:', error)
      toast.error("Failed to get response")
    }
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    console.log("File selected:", file.name)
    setIsUploading(true)

    try {
      const formData = new FormData()
      formData.append('file', file)
      console.log("Sending file to backend...")

      const response = await fetch('http://localhost:8000/api/resume/upload', {
        method: 'POST',
        body: formData,
      })

      console.log("Response status:", response.status)
      const data = await response.text()
      console.log("Response data:", data)

      if (!response.ok) {
        throw new Error('Upload failed')
      }

      const analysis = JSON.parse(data)

      setMessages(prev => [...prev,
        {
          id: Date.now().toString(),
          text: "I've uploaded my CV for review",
          isUser: true,
          attachment: {
            name: file.name,
            type: file.type,
          }
        },
        {
          id: (Date.now() + 1).toString(),
          text: `Here's my analysis:\n\n${analysis.summary}\n\nKey skills:\n${analysis.skills.join(', ')}\n\nRecommendations:\n${analysis.recommendations.join('\n')}`,
          isUser: false,
        }
      ])
    } catch (error) {
      console.error('Error:', error)
      toast.error("Failed to upload file")
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="relative h-full flex flex-col">
      <div className="p-6 bg-gradient-to-r from-purple-900 to-purple-800">
        <h3 className="text-white font-bold text-2xl text-center tracking-tight">AI Career Buddy</h3>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3 bg-gray-900">
        <AnimatePresence mode="popLayout">
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, x: message.isUser ? 20 : -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.3 }}
              className={`flex ${message.isUser ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-3 py-1.5 text-sm ${
                  message.isUser
                    ? "bg-gradient-to-r from-purple-600 to-pink-600 text-white"
                    : "bg-gray-800 text-gray-100"
                }`}
              >
                {message.text}
                {message.attachment && (
                  <div className="mt-2 flex items-center gap-2 p-2 rounded bg-black/20">
                    <FileText className="w-4 h-4" />
                    <span className="text-sm truncate">{message.attachment.name}</span>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      <div className="p-3 border-t border-gray-800 bg-gray-900">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Type your message..."
            className="flex-1 bg-gray-800 border-gray-700 text-white placeholder-gray-400 text-sm h-9"
          />
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".pdf,.doc,.docx"
            className="hidden"
          />
          <Button
            onClick={() => fileInputRef.current?.click()}
            variant="ghost"
            size="sm"
            className="shrink-0 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 h-9 w-9 p-0"
            disabled={isUploading}
          >
            {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Paperclip className="w-4 h-4" />}
          </Button>
          <Button
            onClick={handleSend}
            size="sm"
            className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 h-9 w-9 p-0"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
