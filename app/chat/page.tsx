"use client"
import { ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ChatbotInterface } from "@/components/chatbot-interface"
import Link from "next/link"

export default function ChatPage() {
  return (
    <div className="min-h-screen bg-gray-950 overflow-hidden relative">
      {/* Background Gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-purple-900/5 via-pink-900/5 to-black" />

      {/* Back Button */}
      <Link href="/" className="absolute top-4 left-4 z-50">
        <Button variant="ghost" className="text-white hover:bg-white/10">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Home
        </Button>
      </Link>

      {/* Centered Phone Interface */}
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="relative w-[380px] h-[820px] bg-gray-900 rounded-[60px] overflow-hidden shadow-xl border-8 border-gray-800">
          {/* Notch */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[160px] h-[34px] bg-black rounded-b-[20px] z-50" />

          {/* Phone Screen */}
          <div className="h-full">
            <ChatbotInterface fullScreen />
          </div>

          {/* Home Indicator */}
          <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-32 h-1 bg-black rounded-full opacity-10" />
        </div>
      </div>
    </div>
  )
}


