// components/ui/footer.tsx
import Link from "next/link";
import { Heart } from "lucide-react";

export function Footer() {
  return (
    <footer className="relative z-10 bg-transparent py-6">
      <div className="container mx-auto px-4">
        <div className="flex flex-col md:flex-row justify-between items-center">
          <div className="mb-4 md:mb-0">
            <Link href="/" className="flex items-center space-x-2">
              <Heart className="h-5 w-5 text-yellow-500" fill="#FFD700" />
              <span className="text-xl font-semibold text-white drop-shadow-sm">PathFinder</span>
            </Link>
            <p className="text-sm text-white/70 mt-2">
              Your AI career advisor for the student journey
            </p>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-3 gap-8 md:gap-16">
            <div>
              <h3 className="font-medium mb-2 text-white">Resources</h3>
              <ul className="space-y-1 text-sm">
                <li>
                  <Link href="/resources/resume" className="text-white/70 hover:text-white">
                    Resume Templates
                  </Link>
                </li>
                <li>
                  <Link href="/resources/interviews" className="text-white/70 hover:text-white">
                    Interview Prep
                  </Link>
                </li>
              </ul>
            </div>
            
            <div>
              <h3 className="font-medium mb-2 text-white">Company</h3>
              <ul className="space-y-1 text-sm">
                <li>
                  <Link href="/about" className="text-white/70 hover:text-white">
                    About Us
                  </Link>
                </li>
                <li>
                  <Link href="/contact" className="text-white/70 hover:text-white">
                    Contact
                  </Link>
                </li>
              </ul>
            </div>
            
            <div>
              <h3 className="font-medium mb-2 text-white">Legal</h3>
              <ul className="space-y-1 text-sm">
                <li>
                  <Link href="/privacy" className="text-white/70 hover:text-white">
                    Privacy Policy
                  </Link>
                </li>
                <li>
                  <Link href="/terms" className="text-white/70 hover:text-white">
                    Terms of Service
                  </Link>
                </li>
              </ul>
            </div>
          </div>
        </div>
        
        <div className="mt-8 pt-4 text-center text-sm text-white/60 border-t border-white/20">
          <p>© {new Date().getFullYear()} PathFinder. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}