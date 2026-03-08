import { Sparkles } from "lucide-react";
import Link from "next/link";

interface NavbarProps {
  onReset?: () => void;
}

export function Navbar({ onReset }: NavbarProps) {
  const LogoContent = (
    <>
      <div className="bg-indigo-600 p-1.5 rounded-lg text-white">
        <Sparkles className="w-5 h-5" />
      </div>
      <span className="font-display font-bold text-xl text-zinc-900 tracking-tight">NovaPilot</span>
    </>
  );

  return (
    <header className="w-full flex items-center justify-between p-6 lg:px-12 max-w-screen-2xl mx-auto absolute top-0 left-0 right-0 z-10">
      {onReset ? (
        <div className="flex items-center gap-2 cursor-pointer" onClick={onReset}>
          {LogoContent}
        </div>
      ) : (
        <Link href="/" className="flex items-center gap-2 cursor-pointer">
          {LogoContent}
        </Link>
      )}
      
      <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-zinc-600">
        <Link href="/how-it-works" className="hover:text-zinc-900 transition-colors">How it works</Link>
        <Link href="/categories" className="hover:text-zinc-900 transition-colors">Categories</Link>
        <Link href="/pricing" className="hover:text-zinc-900 transition-colors">Pricing</Link>
      </nav>
      
      <div className="flex items-center gap-4">
        <button className="hidden sm:block text-sm font-medium text-zinc-600 hover:text-zinc-900 transition-colors">
          Log in
        </button>
        <button className="text-sm font-medium bg-zinc-900 text-white px-5 py-2.5 rounded-full hover:bg-zinc-800 transition-colors shadow-sm">
          Sign up
        </button>
      </div>
    </header>
  );
}
