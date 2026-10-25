"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Scale,
  KeyRound,
  Mail,
  Lock,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Eye,
  EyeOff,
  Sparkles,
} from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [tab, setTab] = useState<"credentials" | "token">("credentials");

  // Credential state
  const [email, setEmail] = useState("counsel@asgard-holdings.corp");
  const [password, setPassword] = useState("••••••••••••");
  const [showPassword, setShowPassword] = useState(false);

  // Token state
  const [bearerToken, setBearerToken] = useState(
    "8wkDxPPFyixSS6vVx2jWyEzt07Bfg_NDDxaDiO630jkHFC2EHQBshbm7NJO5ZJh_"
  );

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    setTimeout(() => {
      if (tab === "credentials") {
        if (!email.includes("@")) {
          setError("Please provide a valid legal officer email address.");
          setLoading(false);
          return;
        }
      } else {
        if (bearerToken.trim().length < 16) {
          setError("Bearer token is too short or malformed.");
          setLoading(false);
          return;
        }
        if (typeof window !== "undefined") {
          localStorage.setItem("odin_bearer_token", bearerToken.trim());
        }
      }

      setSuccess("Authentication granted. Accessing ODIN Command Center…");
      setLoading(false);
      setTimeout(() => {
        router.push("/war-room");
      }, 900);
    }, 600);
  };

  return (
    <div className="min-h-screen bg-page flex flex-col justify-between p-4 sm:p-8">
      {/* Top Bar */}
      <div className="max-w-6xl mx-auto w-full flex items-center justify-between py-2">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center shadow-lg shadow-amber-600/25">
            <Scale className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="font-bold text-base tracking-tight text-slate-900 group-hover:text-amber-700 transition-colors">
              ODIN
            </span>
            <span className="ml-2 text-xs text-amber-800/60 font-semibold tracking-wider uppercase">
              Contract War Room
            </span>
          </div>
        </Link>

        <Link
          href="/"
          className="text-xs font-semibold text-amber-800/80 hover:text-amber-900 bg-amber-500/10 hover:bg-amber-500/20 px-3.5 py-1.5 rounded-lg border border-amber-500/20 transition-all"
        >
          Back to Onboarding
        </Link>
      </div>

      {/* Main Card */}
      <div className="flex-1 flex items-center justify-center py-10">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: "easeOut" }}
          className="w-full max-w-md bg-white border border-amber-600/20 rounded-2xl shadow-xl shadow-amber-900/5 p-8 relative overflow-hidden"
        >
          {/* Subtle gold accent top bar */}
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-amber-400 via-amber-500 to-amber-600" />

          {/* Header */}
          <div className="text-center mb-6 pt-2">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-amber-50 border border-amber-200 text-amber-700 mb-3 shadow-inner">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Sign In to ODIN
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Autonomous legal operations & multi-agent war room
            </p>
          </div>

          {/* Tab Switcher */}
          <div className="flex p-1 bg-amber-50/70 border border-amber-200/60 rounded-xl mb-6">
            <button
              type="button"
              onClick={() => {
                setTab("credentials");
                setError(null);
              }}
              className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-semibold rounded-lg transition-all ${
                tab === "credentials"
                  ? "bg-white text-slate-900 shadow-sm border border-amber-200/60"
                  : "text-slate-500 hover:text-slate-800"
              }`}
            >
              <Mail className="w-3.5 h-3.5" />
              Legal Officer
            </button>
            <button
              type="button"
              onClick={() => {
                setTab("token");
                setError(null);
              }}
              className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-semibold rounded-lg transition-all ${
                tab === "token"
                  ? "bg-white text-slate-900 shadow-sm border border-amber-200/60"
                  : "text-slate-500 hover:text-slate-800"
              }`}
            >
              <KeyRound className="w-3.5 h-3.5" />
              API Bearer Token
            </button>
          </div>

          {/* Alerts */}
          {error && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              className="mb-5 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2 font-medium"
            >
              <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
              <span>{error}</span>
            </motion.div>
          )}

          {success && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              className="mb-5 p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs flex items-center gap-2 font-medium"
            >
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
              <span>{success}</span>
            </motion.div>
          )}

          {/* Form */}
          <form onSubmit={handleLogin} className="space-y-4">
            {tab === "credentials" ? (
              <>
                <div>
                  <label className="input-label">Corporate Email</label>
                  <div className="relative">
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="counsel@company.com"
                      required
                      className="input-field pl-10"
                    />
                    <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="input-label mb-0">Password / Passkey</label>
                    <a
                      href="#"
                      onClick={(e) => {
                        e.preventDefault();
                        alert("Demo Mode: Click 'Authorize & Launch' to continue.");
                      }}
                      className="text-[11px] font-semibold text-amber-700 hover:underline"
                    >
                      Forgot?
                    </a>
                  </div>
                  <div className="relative">
                    <input
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Enter security key"
                      required
                      className="input-field pl-10 pr-10 font-mono text-sm"
                    />
                    <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    >
                      {showPassword ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div>
                <label className="input-label">RAGNAROK / ODIN API Token</label>
                <div className="relative">
                  <input
                    type="password"
                    value={bearerToken}
                    onChange={(e) => setBearerToken(e.target.value)}
                    placeholder="Enter 64-char API Bearer Token"
                    required
                    className="input-field pl-10 font-mono text-xs tracking-wider"
                  />
                  <KeyRound className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                </div>
                <p className="text-[11px] text-slate-500 mt-1.5 flex items-center gap-1">
                  <Sparkles className="w-3 h-3 text-amber-600" />
                  Pre-filled with the active server session key
                </p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full py-3 mt-2 text-sm font-semibold flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  <span>Verifying Credentials…</span>
                </>
              ) : (
                <>
                  <span>Authorize & Launch War Room</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Access info */}
          <div className="mt-6 pt-5 border-t border-slate-100 text-center">
            <p className="text-xs text-slate-500">
              Demo Environment • Pre-authorized as{" "}
              <span className="font-semibold text-slate-700">General Counsel</span>
            </p>
          </div>
        </motion.div>
      </div>

      {/* Footer */}
      <div className="max-w-6xl mx-auto w-full text-center py-4 text-xs text-slate-400">
        ODIN Intelligence Platform • Multi-Agent Legal Consensus Framework
      </div>
    </div>
  );
}
