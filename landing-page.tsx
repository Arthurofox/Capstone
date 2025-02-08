"use client"

import { useRef } from "react"
import { Button } from "@/components/ui/button"
import { motion } from "framer-motion"
import { MessageSquare, Sparkles } from "lucide-react"
import PhoneInterface from "@/components/PhoneInterface" // Import the PhoneInterface component

export default function LandingPage() {
  const chatbotRef = useRef<HTMLDivElement>(null)

  const scrollToChatbot = () => {
    chatbotRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  return (
    <div className="min-h-screen bg-black overflow-hidden">
      {/* Hero Section */}
      <section className="relative h-screen flex items-center justify-center px-4">
        {/* Background Gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-purple-900/20 via-pink-900/20 to-black" />

        {/* Animated Background Elements */}
        <div className="absolute inset-0 overflow-hidden">
          {[...Array(20)].map((_, i) => (
            <motion.div
              key={i}
              className="absolute h-px w-px bg-purple-400"
              initial={{
                x: Math.random() * window.innerWidth,
                y: Math.random() * window.innerHeight,
                scale: 0,
              }}
              animate={{
                scale: [0, 1, 0],
                opacity: [0, 1, 0],
              }}
              transition={{
                duration: Math.random() * 3 + 2,
                repeat: Number.POSITIVE_INFINITY,
                repeatType: "reverse",
              }}
            />
          ))}
        </div>

        <div className="relative z-10 text-center space-y-8 max-w-4xl mx-auto">
          {/* Main Heading */}
          <motion.h1
            className="text-5xl md:text-7xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-400 via-pink-400 to-purple-400 tracking-tight"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            Your AI Career Buddy
          </motion.h1>

          {/* Holographic Effect Subheading */}
          <motion.div
            className="text-xl md:text-2xl text-white/80 relative"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4, duration: 0.8 }}
          >
            <span className="relative">
              <span className="absolute -inset-0.5 bg-gradient-to-r from-purple-500 via-pink-500 to-purple-500 opacity-20 blur-sm" />
              <span className="relative">Personalized Guidance at Your Fingertips</span>
            </span>
          </motion.div>

          {/* Description */}
          <motion.p
            className="text-gray-400 text-lg max-w-2xl mx-auto"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.8 }}
          >
            Get career advice, resume tips, and job recommendations instantly
          </motion.p>

          {/* CTA Button */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8, duration: 0.8 }}
          >
            <Button
              onClick={scrollToChatbot}
              className="relative group px-8 py-6 text-lg rounded-full bg-gradient-to-r from-purple-600 via-pink-600 to-purple-600 hover:from-purple-500 hover:via-pink-500 hover:to-purple-500 text-white shadow-lg transition-all duration-300"
            >
              <span className="absolute -inset-1 bg-gradient-to-r from-purple-500 via-pink-500 to-purple-500 opacity-40 group-hover:opacity-60 blur-lg transition-all duration-300" />
              <span className="relative flex items-center gap-2">
                Start Chatting <MessageSquare className="w-5 h-5" />
              </span>
            </Button>
          </motion.div>
        </div>

        {/* Scroll Indicator */}
        <motion.div
          className="absolute bottom-8 left-1/2 -translate-x-1/2"
          animate={{ y: [0, 10, 0] }}
          transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
        >
          <Sparkles className="w-6 h-6 text-pink-400" />
        </motion.div>
      </section>

      {/* Chatbot Phone Interface Section */}
      <section ref={chatbotRef} className="min-h-screen flex items-center justify-center px-4 py-20">
        <PhoneInterface />
      </section>
    </div>
  )
}

