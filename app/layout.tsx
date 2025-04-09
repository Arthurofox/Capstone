// app/layout.tsx
import { Inter } from "next/font/google";
import "./globals.css";
import { Footer } from "@/components/ui/footer";
import { AudioPlayer } from "@/components/ui/audio-player";

const inter = Inter({ subsets: ["latin"] });

export const metadata = {
  title: "PathFinder | Your AI Career Advisor",
  description: "Personal career guidance chatbot for students",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="relative min-h-screen flex flex-col">
          <div style={{ position: 'absolute', top: '90px', left: '16px', zIndex: 50 }}>
            <AudioPlayer />
          </div>
          <main className="flex-grow z-10 relative">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}