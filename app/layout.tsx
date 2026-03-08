import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import "./globals.css"; // Global styles

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display",
});

export const metadata: Metadata = {
  title: "NovaPilot - AI Shopping Assistant",
  description:
    "AI-powered shopping comparison agent that searches e-commerce websites and recommends the best options.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${spaceGrotesk.variable}`}>
      <body
        suppressHydrationWarning
        className="font-sans bg-zinc-50 text-zinc-900 antialiased selection:bg-indigo-100 selection:text-indigo-900"
      >
        {children}
      </body>
    </html>
  );
}
