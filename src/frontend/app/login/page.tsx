"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, LockKeyhole, ShieldCheck } from "lucide-react";
import { odinApi } from "@/lib/odin-api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [organization, setOrganization] = useState("");
  const [visible, setVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "register") {
        await odinApi("/auth/register", { method: "POST", body: JSON.stringify({ email, password, name, organization, terms: true }) });
        router.push("/onboarding");
      } else {
        await odinApi("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
        router.push("/war-room");
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to sign in");
    } finally {
      setLoading(false);
    }
  }

  return <main className="min-h-screen bg-[#eaf2fa] p-4 md:p-8 flex items-center justify-center text-[#10233e]">
    <div className="w-full max-w-[1050px] min-h-[620px] overflow-hidden rounded-2xl bg-white shadow-2xl shadow-[#122845]/15 grid md:grid-cols-[0.95fr_1.05fr]">
      <section className="relative min-h-[320px] md:min-h-full bg-[#102742] bg-cover bg-center text-white p-9 flex flex-col justify-between" style={{ backgroundImage: "linear-gradient(180deg,rgba(8,24,44,.30),rgba(3,16,32,.91)),url('/odin_login_bg.jpg')" }}>
        <div><span className="text-4xl text-[#f3bd55]">◭</span><h1 className="text-5xl font-bold tracking-[.18em]">ODIN</h1><p className="mt-2 text-sm text-white/85">Contract Intelligence<br/>for a Safer Tomorrow</p></div>
        <div><p className="text-2xl font-semibold leading-tight max-w-xs">Turn contracts into foresight, not risk.</p><div className="mt-7 space-y-3 text-sm text-white/90"><p className="flex gap-2"><ShieldCheck size={17}/> Evidence checked analysis</p><p className="flex gap-2"><LockKeyhole size={17}/> Private organization workspace</p></div></div>
      </section>
      <section className="px-7 py-10 sm:px-14 flex flex-col justify-center">
        <div className="max-w-sm mx-auto w-full">
          <p className="text-xs font-bold uppercase tracking-[.22em] text-[#c38b23]">ODIN workspace</p>
          <h2 className="mt-3 text-3xl font-bold">{mode === "login" ? "Welcome back" : "Create your workspace"}</h2>
          <p className="text-sm text-slate-500 mt-2">{mode === "login" ? "Sign in to your contract intelligence dashboard." : "Your organization name appears across your workspace."}</p>
          <form className="mt-8 space-y-4" onSubmit={submit}>
            {mode === "register" && <><label className="block text-sm font-medium">Your name<input required minLength={2} value={name} onChange={e => setName(e.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-[#d4a017]" placeholder="Your full name"/></label><label className="block text-sm font-medium">Company name<input required minLength={2} value={organization} onChange={e => setOrganization(e.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-[#d4a017]" placeholder="Your legal entity"/></label></>}
            <label className="block text-sm font-medium">Email<input required type="email" value={email} onChange={e => setEmail(e.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-[#d4a017]" placeholder="you@company.com"/></label>
            <label className="block text-sm font-medium">Password<div className="relative mt-1.5"><input required minLength={12} type={visible ? "text" : "password"} value={password} onChange={e => setPassword(e.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 pr-10 outline-none focus:border-[#d4a017]" placeholder="At least 12 characters"/><button type="button" aria-label={visible ? "Hide password" : "Show password"} onClick={() => setVisible(!visible)} className="absolute right-3 top-3 text-slate-400">{visible ? <EyeOff size={17}/> : <Eye size={17}/>}</button></div></label>
            {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
            <button disabled={loading} className="w-full rounded-lg bg-[#112b49] py-3 text-white font-semibold hover:bg-[#1c4169] disabled:opacity-60">{loading ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}</button>
          </form>
          <p className="mt-7 text-center text-sm text-slate-500">{mode === "login" ? "New to ODIN?" : "Already have an account?"} <button onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }} className="font-semibold text-[#a87816] hover:underline">{mode === "login" ? "Create an account" : "Sign in"}</button></p>
        </div>
      </section>
    </div>
  </main>;
}
