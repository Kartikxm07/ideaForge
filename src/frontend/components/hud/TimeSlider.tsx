"use client";

import React, { useEffect } from "react";
import {
  Play,
  Pause,
  ChevronLeft,
  ChevronRight,
  FastForward,
  Flag,
  Calendar,
  Sparkles,
} from "lucide-react";
import { useOdinStore } from "@/store/useOdinStore";
import { toast } from "sonner";

export function TimeSlider() {
  const {
    currentDate,
    activeCheckpoint,
    isPlaying,
    playbackSpeed,
    setCheckpoint,
    setDate,
    togglePlay,
    setSpeed,
    stepDays,
    jumpNextDeadline,
    jumpPrevDeadline,
  } = useOdinStore();

  // Keyboard navigation support: Arrow Left/Right (+-1 day), Shift (+-7 days)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      if (e.key === "ArrowRight") {
        e.preventDefault();
        const delta = e.shiftKey ? 7 : 1;
        stepDays(delta);
        toast.info(`Clock Advanced +${delta}d`, { description: `New Date: ${currentDate}` });
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        const delta = e.shiftKey ? -7 : -1;
        stepDays(delta);
        toast.info(`Clock Rewound ${delta}d`, { description: `New Date: ${currentDate}` });
      } else if (e.key === " ") {
        e.preventDefault();
        togglePlay();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [stepDays, togglePlay, currentDate]);

  // Autoplay simulation loop
  useEffect(() => {
    if (!isPlaying) return;
    const intervalTime = 1200 / playbackSpeed;
    const interval = setInterval(() => {
      stepDays(1);
    }, intervalTime);
    return () => clearInterval(interval);
  }, [isPlaying, playbackSpeed, stepDays]);

  // Date range from 2026-08-01 to 2027-04-30
  const minDate = new Date("2026-08-01").getTime();
  const maxDate = new Date("2027-04-30").getTime();
  const currentTimestamp = new Date(currentDate).getTime();
  const progressPercent = Math.min(
    100,
    Math.max(0, ((currentTimestamp - minDate) / (maxDate - minDate)) * 100)
  );

  const checkpoints = [
    { id: "CP1" as const, date: "2026-10-01", label: "CP1 Baseline", pct: 16.5 },
    { id: "CP2" as const, date: "2026-11-15", label: "CP2 Drop 1 Outage", pct: 33.8 },
    { id: "CP3" as const, date: "2027-01-10", label: "CP3 Drop 2 Rulings", pct: 57.2 },
  ];

  return (
    <div className="fixed bottom-0 left-0 right-0 z-30 border-t border-cyan-500/20 bg-[#070b14]/95 backdrop-blur-md px-6 py-2.5 shadow-2xl">
      <div className="max-w-[1720px] mx-auto flex items-center justify-between gap-6">
        {/* Playback Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={jumpPrevDeadline}
            title="Jump to Previous Critical Deadline"
            className="p-1.5 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800 text-slate-400 hover:text-white transition-all"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          <button
            onClick={togglePlay}
            className={`p-2 rounded-lg font-bold flex items-center justify-center transition-all ${
              isPlaying
                ? "bg-amber-400 text-slate-950 shadow-md shadow-amber-400/40"
                : "bg-cyan-500 hover:bg-cyan-400 text-slate-950 shadow-md shadow-cyan-500/30"
            }`}
            title="Spacebar to Play/Pause temporal axis"
          >
            {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 fill-current ml-0.5" />}
          </button>

          <button
            onClick={jumpNextDeadline}
            title="Jump to Next Critical Deadline"
            className="p-1.5 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800 text-slate-400 hover:text-white transition-all"
          >
            <ChevronRight className="w-4 h-4" />
          </button>

          {/* Speed multiplier pill */}
          <div className="flex items-center rounded-lg border border-slate-800 bg-slate-900/80 p-0.5 ml-1">
            {([1, 4, 16] as const).map((spd) => (
              <button
                key={spd}
                onClick={() => setSpeed(spd)}
                className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold transition-all ${
                  playbackSpeed === spd
                    ? "bg-cyan-500 text-slate-950"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {spd}x
              </button>
            ))}
          </div>
        </div>

        {/* Center: Scrubber Track with Checkpoint Flags & Event Dots */}
        <div className="flex-1 relative flex flex-col justify-center">
          <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 mb-1">
            <span>2026-08-01 (Contract Start)</span>
            <div className="flex items-center gap-1.5 text-cyan-300 font-bold font-jetbrains">
              <Calendar className="w-3.5 h-3.5 text-cyan-400" />
              <span>CURRENT: {currentDate}</span>
            </div>
            <span>2027-04-30 (Cyber Renewal)</span>
          </div>

          {/* Interactive track */}
          <div className="relative h-3 w-full bg-slate-900 border border-slate-800 rounded-full flex items-center overflow-visible">
            {/* Filled progress glow bar */}
            <div
              style={{ width: `${progressPercent}%` }}
              className="h-full bg-gradient-to-r from-blue-600 via-cyan-500 to-amber-400 rounded-full shadow-sm shadow-cyan-500/50"
            />

            {/* Checkpoint Flag Markers */}
            {checkpoints.map((cp) => (
              <button
                key={cp.id}
                onClick={() => {
                  setCheckpoint(cp.id);
                  toast.success(`Loaded Checkpoint ${cp.id}`, { description: cp.label });
                }}
                style={{ left: `${cp.pct}%` }}
                className={`absolute -top-3 transform -translate-x-1/2 flex flex-col items-center group cursor-pointer z-20`}
              >
                <div
                  className={`w-3.5 h-3.5 rounded-full border-2 transition-all flex items-center justify-center ${
                    activeCheckpoint === cp.id
                      ? "border-amber-300 bg-amber-400 shadow-lg shadow-amber-400/80 scale-125"
                      : "border-slate-500 bg-slate-900 hover:border-cyan-400"
                  }`}
                />
                <span className="text-[9px] font-rajdhani font-bold uppercase tracking-wider text-slate-400 group-hover:text-cyan-300 whitespace-nowrap mt-0.5">
                  {cp.id}
                </span>
              </button>
            ))}

            {/* Range input scrubber */}
            <input
              type="range"
              min={minDate}
              max={maxDate}
              value={currentTimestamp}
              onChange={(e) => {
                const ts = Number(e.target.value);
                const d = new Date(ts).toISOString().split("T")[0];
                setDate(d);
              }}
              className="absolute inset-0 w-full opacity-0 cursor-ew-resize z-10"
            />
          </div>
        </div>

        {/* Right: Keyboard Shortcut Legend */}
        <div className="hidden lg:flex items-center gap-2 text-[10px] font-mono text-slate-500 border-l border-slate-800 pl-4">
          <span className="px-1.5 py-0.5 rounded border border-slate-700 bg-slate-900 text-slate-300 font-bold">
            ← / →
          </span>
          <span>±1d</span>
          <span className="px-1.5 py-0.5 rounded border border-slate-700 bg-slate-900 text-slate-300 font-bold ml-1">
            Shift+←/→
          </span>
          <span>±7d</span>
          <span className="px-1.5 py-0.5 rounded border border-slate-700 bg-slate-900 text-slate-300 font-bold ml-1">
            Space
          </span>
          <span>Play</span>
        </div>
      </div>
    </div>
  );
}
