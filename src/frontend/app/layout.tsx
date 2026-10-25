import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ODIN – Financial & Contract Solutions",
  description:
    "Institutional financial risk radar, contract analytics and compliance intelligence platform.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-dvh bg-[#FEFAF3] text-[#1A1208] antialiased selection:bg-amber-200/40 selection:text-amber-900">
        {children}
      </body>
    </html>
  );
}
