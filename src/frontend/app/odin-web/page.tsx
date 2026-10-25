"use client";

import React from "react";
import { HudHeader } from "@/components/hud/HudHeader";
import { OdinWebView } from "@/components/views/OdinWebView";

export default function OdinWebPage() {
  return (
    <div className="min-h-screen bg-[#FEFAF3] text-[#1A1208] flex flex-col font-sans">
      <HudHeader />
      <main className="flex-1 max-w-[1600px] w-full mx-auto px-6 py-6">
        <OdinWebView />
      </main>
    </div>
  );
}
