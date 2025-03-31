// app/chat/page.tsx
import { ChatbotInterface } from "@/components/ui/chatbot-interface";

export default function ChatPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white bg-opacity-90 backdrop-blur-sm rounded-xl p-6 shadow-lg mb-8">
          <h1 className="text-3xl font-bold mb-4 text-center">Your Career Advisor</h1>
          <p className="text-lg text-center mb-0 text-slate-600">
            Ask questions, get personalized advice, and plan your career journey
          </p>
        </div>
        
        <div className="mt-8">
          <ChatbotInterface />
        </div>
      </div>
    </div>
  );
}