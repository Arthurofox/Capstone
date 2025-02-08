"use client"

import { motion } from "framer-motion"
import { MessageSquare, Sparkles, Brain, Target, Star } from "lucide-react"
import { Button } from "@/components/ui/button"
import { PhonePreview } from "@/components/phone-preview"
import Link from "next/link"

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-black overflow-hidden">
      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center px-4">
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
          <motion.h1
            className="text-5xl md:text-7xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-400 via-pink-400 to-purple-400 tracking-tight"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            Your AI Career Buddy
          </motion.h1>

          <motion.div
            className="text-xl md:text-2xl text-white/80 relative"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4, duration: 0.8 }}
          >
            <span className="relative">
              <span className="absolute -inset-0.5 bg-gradient-to-r from-purple-500 via-pink-500 to-purple-500 opacity-20 blur-sm" />
              <span className="relative">Navigate Your Career Path with AI-Powered Guidance</span>
            </span>
          </motion.div>

          <motion.p
            className="text-gray-400 text-lg max-w-2xl mx-auto"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.8 }}
          >
            Get personalized career advice, resume optimization, and job recommendations tailored to your skills and
            aspirations
          </motion.p>
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

      {/* Features Section */}
      <section className="py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <motion.h2
            className="text-3xl md:text-4xl font-bold text-center text-white mb-16"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
          >
            Your Personal Career Assistant
          </motion.h2>

          <div className="grid md:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                className="relative group"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.2 }}
                viewport={{ once: true }}
              >
                <div className="absolute -inset-0.5 bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg blur opacity-30 group-hover:opacity-100 transition duration-1000"></div>
                <div className="relative bg-gray-900 p-6 rounded-lg">
                  <feature.icon className="w-12 h-12 text-purple-400 mb-4" />
                  <h3 className="text-xl font-bold text-white mb-2">{feature.title}</h3>
                  <p className="text-gray-400">{feature.description}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section with Phone Preview */}
      <section className="relative py-20 px-4">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center gap-12">
          <div className="flex-1 space-y-6">
            <motion.h2
              className="text-3xl md:text-4xl font-bold text-white"
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
            >
              Ready to Start Your Journey?
            </motion.h2>
            <motion.p
              className="text-gray-400 text-lg"
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 }}
            >
              Click on the phone to start chatting with your AI Career Buddy. Get instant answers to your career
              questions and personalized guidance for your professional growth.
            </motion.p>
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.4 }}
            >
              <Link href="/chat">
                <Button className="relative group px-8 py-6 text-lg rounded-full bg-gradient-to-r from-purple-600 via-pink-600 to-purple-600 hover:from-purple-500 hover:via-pink-500 hover:to-purple-500 text-white shadow-lg transition-all duration-300">
                  <span className="absolute -inset-1 bg-gradient-to-r from-purple-500 via-pink-500 to-purple-500 opacity-40 group-hover:opacity-60 blur-lg transition-all duration-300" />
                  <span className="relative flex items-center gap-2">
                    Start Chatting <MessageSquare className="w-5 h-5" />
                  </span>
                </Button>
              </Link>
            </motion.div>
          </div>

          <div className="flex-1 flex justify-center">
            <Link href="/chat">
              <PhonePreview />
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}

const features = [
  {
    icon: Brain,
    title: "Smart Career Analysis",
    description:
      "Get AI-powered insights about your career path and potential opportunities based on your skills and experience.",
  },
  {
    icon: Target,
    title: "Personalized Advice",
    description:
      "Receive tailored recommendations for skill development, job roles, and career advancement strategies.",
  },
  {
    icon: Star,
    title: "Resume Enhancement",
    description: "Get expert suggestions to optimize your resume and make it stand out to potential employers.",
  },
]

