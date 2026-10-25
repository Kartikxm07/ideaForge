import type { Metadata } from "next";
import { DM_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
  weight: ["300", "400", "500", "600", "700"],
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "ODIN – Contract Intelligence",
  description:
    "Autonomous multi-agent contract radar and dispute intelligence engine. Powered by Ragnarok local runtime.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${dmSans.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-dvh bg-[#FEFAF3] text-[#1A1208] antialiased selection:bg-amber-200/40 selection:text-amber-900">
        {children}
      </body>
    </html>
  );
}
