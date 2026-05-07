import type { Metadata } from "next";
import { Space_Grotesk, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-space",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "PolyTrade Pro · v3.6",
  description: "Quant Engine Dashboard — Polymarket 5-min BTC/ETH/SOL Scalper",
  keywords: ["polymarket", "crypto", "quant", "trading", "bot"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="th" className={`${spaceGrotesk.variable} ${jetbrainsMono.variable}`}>
      <body style={{ fontFamily: "var(--font-space, 'Space Grotesk'), sans-serif" }}>
        {children}
      </body>
    </html>
  );
}
