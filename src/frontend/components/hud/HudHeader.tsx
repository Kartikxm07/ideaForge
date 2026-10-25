"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Scale,
  Clock,
  PlusCircle,
  Download,
  LayoutDashboard,
  FilePlus,
  FileText,
  Settings,
  ChevronDown,
} from "lucide-react";
import { useOdinStore } from "@/store/useOdinStore";

export function HudHeader() {
  const pathname = usePathname();
  const { currentDate, activeCheckpoint, setCheckpoint, openAddEvent } = useOdinStore();

  const navLinks = [
    { href: "/",          label: "Onboard",     icon: FilePlus },
    { href: "/war-room",  label: "Portfolio Intelligence", icon: LayoutDashboard },
    { href: "/analysis",  label: "Agent Ops",   icon: Settings },
    { href: "/reports",   label: "Reports",     icon: FileText },
  ];

  const checkpoints = [
    { id: "CP1" as const, label: "Oct 2026" },
    { id: "CP2" as const, label: "Nov 2026" },
    { id: "CP3" as const, label: "Jan 2027" },
  ];

  return (
    <header className="sticky top-0 z-40 bg-header border-b border-white/[0.06]">
      <div className="max-w-[1600px] mx-auto px-6 h-14 flex items-center justify-between gap-6">

        {/* Logo */}
        <Link href="/war-room" className="flex items-center gap-3 shrink-0 group">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-yellow-400 to-amber-600 flex items-center justify-center shadow-lg shadow-amber-600/30">
            <Scale className="w-4 h-4 text-white" />
          </div>
          <div className="flex flex-col leading-none">
            <span className="font-bold text-sm tracking-wide text-white group-hover:text-amber-200 transition-colors">
              ODIN
            </span>
            <span className="text-[10px] text-white/40 font-medium tracking-widest uppercase">
              Financial Solutions
            </span>
          </div>
        </Link>

        {/* Nav */}
        <nav className="hidden lg:flex items-center gap-1">
          {navLinks.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || (href === "/war-room" && pathname === "/");
            return (
              <Link key={href} href={href} className={`nav-item ${active ? "active" : ""}`}>
                <Icon className="w-3.5 h-3.5" />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Clock + Checkpoint selector */}
        <div className="hidden md:flex items-center gap-2 bg-white/[0.06] border border-white/[0.08] rounded-lg px-3 py-1.5">
          <Clock className="w-3.5 h-3.5 text-amber-400/80 shrink-0" />
          <span className="font-mono text-xs text-white/70 tabular-nums">{currentDate}</span>
          <span className="w-px h-4 bg-white/10" />
          <div className="flex items-center gap-0.5">
            {checkpoints.map(({ id, label }) => (
              <button
                key={id}
                onClick={() => setCheckpoint(id)}
                className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-all ${
                  activeCheckpoint === id
                    ? "bg-amber-500 text-slate-900"
                    : "text-white/45 hover:text-white/80"
                }`}
              >
                {id}
              </button>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={openAddEvent}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-900 font-semibold text-xs transition-all shadow-md shadow-amber-500/25 hover:shadow-amber-400/35 hover:-translate-y-px"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            Add Event
          </button>

          <button
            onClick={() => alert("Exporting dossier…")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/[0.12] bg-white/[0.06] hover:bg-white/[0.10] text-white/70 hover:text-white font-medium text-xs transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            Export
          </button>

          <Link
            href="/login"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-amber-500/30 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 font-semibold text-xs transition-all"
          >
            Sign In
          </Link>
        </div>

      </div>
    </header>
  );
}
