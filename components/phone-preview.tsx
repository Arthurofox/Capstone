"use client"

import { motion } from "framer-motion"
import { MessageSquare } from "lucide-react"

export function PhonePreview() {
  return (
    <motion.div
      className="relative max-w-[300px] w-full h-[600px] rounded-[3rem] border-8 border-gray-800 bg-gray-900 overflow-hidden cursor-pointer transform transition-transform duration-500 hover:scale-105"
      whileHover={{ y: -5 }}
      initial={{ opacity: 0, scale: 0.9 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once: true }}
    >
      {/* Phone Notch */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-6 bg-gray-800 rounded-b-2xl z-20" />

      {/* Preview Content */}
      <div className="relative h-full flex flex-col">
        {/* Chat Header */}
        <div className="p-4 bg-gradient-to-r from-purple-900 via-pink-900 to-purple-900">
          <h3 className="text-white font-semibold text-lg text-center">AI Career Buddy</h3>
        </div>

        {/* Preview Messages */}
        <div className="flex-1 p-4 space-y-4">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.5 }}
            className="flex justify-start"
          >
            <div className="max-w-[80%] rounded-2xl px-4 py-2 bg-gray-800 text-gray-100">
              Hey there! 👋 I'm your AI career buddy.
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1 }}
            className="flex justify-start"
          >
            <div className="max-w-[80%] rounded-2xl px-4 py-2 bg-gray-800 text-gray-100">
              Want some resume tips or job suggestions?
            </div>
          </motion.div>

          {/* Blinking Cursor */}
          <motion.div
            animate={{ opacity: [0, 1] }}
            transition={{ duration: 0.8, repeat: Number.POSITIVE_INFINITY }}
            className="w-3 h-6 bg-purple-400"
          />
        </div>

        {/* Click to Chat Overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/50 to-transparent flex items-center justify-center">
          <motion.div
            className="flex flex-col items-center gap-4"
            animate={{ y: [0, -10, 0] }}
            transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
          >
            <MessageSquare className="w-12 h-12 text-purple-400" />
            <p className="text-white font-medium">Click to Start Chatting</p>
          </motion.div>
        </div>
      </div>
    </motion.div>
  )
}

