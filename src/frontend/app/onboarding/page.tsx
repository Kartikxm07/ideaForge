"use client";

import { useEffect, useState, type ChangeEvent } from "react";
import { useRouter } from "next/navigation";
import { Building2, FileText, UploadCloud } from "lucide-react";
import { odinApi, odinUploadFile } from "@/lib/odin-api";

type Settings = { name: string; organization: string; notifications: boolean };

export default function OnboardingPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [organization, setOrganization] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [pasteTitle, setPasteTitle] = useState("");
  const [pasteText, setPasteText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");

  useEffect(() => {
    odinApi<Settings>("/workspace/settings").then(s => { setName(s.name); setOrganization(s.organization); }).catch(() => router.replace("/login"));
  }, [router]);

  function pick(event: ChangeEvent<HTMLInputElement>) {
    const chosen = Array.from(event.target.files || []);
    setFiles(previous => [...previous, ...chosen]);
    event.target.value = "";
  }

  async function save() {
    setBusy(true); setError(""); setSaved("");
    try {
      await odinApi("/workspace/settings", { method: "PATCH", body: JSON.stringify({ name, organization, notifications: true }) });
      const reports: string[] = [];
      const failures: string[] = [];
      const retryFiles: File[] = [];
      if (pasteText.trim()) {
        try {
          const stem = pasteTitle.trim().replace(/\.[^.]+$/, "").replace(/[^A-Za-z0-9_.-]/g, "-").slice(0, 80);
          if (!stem) throw new Error("Give pasted contract text a document name");
          await odinApi("/workspace/upload", { method: "POST", body: JSON.stringify({ document_key: stem, title: pasteTitle.trim(), content: pasteText.trim() }) });
          reports.push("Pasted contract saved"); setPasteTitle(""); setPasteText("");
        } catch (cause) { failures.push(`Pasted text: ${cause instanceof Error ? cause.message : "Upload failed"}`); }
      }
      for (const file of files) {
        try {
          const result = await odinUploadFile(file);
          reports.push(result.kind === "events" ? `${file.name}: ${result.created ?? 0} events imported${result.quarantined ? `, ${result.quarantined} malformed lines skipped` : ""}` : `${file.name}: contract saved${result.quarantined ? `, ${result.quarantined} malformed lines skipped` : ""}`);
        } catch (cause) { retryFiles.push(file); failures.push(`${file.name}: ${cause instanceof Error ? cause.message : "Upload failed"}`); }
      }
      setSaved(reports.length ? reports.join(" · ") : "Organization saved");
      setFiles(retryFiles);
      if (failures.length) setError(failures.join(" · "));
      else router.push("/war-room");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Save failed"); }
    finally { setBusy(false); }
  }

  return <main className="min-h-screen bg-[#eaf2fa] px-5 py-12 text-[#112b49]">
    <div className="max-w-2xl mx-auto"><header className="flex items-center gap-3 mb-9"><span className="text-3xl text-[#d4a017]">◭</span><div><b className="text-xl">ODIN</b><p className="text-xs text-slate-500">Workspace setup</p></div></header>
      <div className="bg-white rounded-2xl border border-slate-200 shadow-lg p-7 sm:p-9">
        <p className="text-xs font-bold uppercase tracking-widest text-[#b98721]">Organization</p>
        <h1 className="text-2xl font-bold mt-2">Set up your contract workspace</h1>
        <p className="text-sm text-slate-500 mt-2">Your entered company name appears in the dashboard. Upload contracts and event records, or paste source text below.</p>
        <div className="mt-7 space-y-4">
          <label className="block text-sm font-semibold">Your name<input required value={name} onChange={e => setName(e.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2.5 focus:border-[#d4a017] outline-none"/></label>
          <label className="block text-sm font-semibold">Company name<div className="relative mt-2"><Building2 className="absolute left-3 top-3 text-slate-400" size={18}/><input required value={organization} onChange={e => setOrganization(e.target.value)} className="w-full rounded-lg border border-slate-200 pl-10 pr-3 py-2.5 focus:border-[#d4a017] outline-none"/></div></label>
        </div>
        <div className="mt-9"><p className="text-sm font-semibold">Source files</p><p className="text-xs text-slate-500 mt-1">TXT and text-based PDF become cited contracts. JSONL event records go to the event feed; JSONL text records become contract clauses.</p>
          <label onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); setFiles(previous => [...previous, ...Array.from(event.dataTransfer.files)]); }} className="mt-3 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 p-8 hover:border-[#d4a017]"><UploadCloud size={27} className="text-[#d4a017]"/><span className="mt-2 text-sm font-medium">Choose or drop .txt, .pdf or .jsonl files</span><span className="mt-1 text-xs text-slate-500">Up to 12 MB per file · scanned PDFs need OCR or pasted text</span><input multiple type="file" accept=".txt,.pdf,.jsonl,text/plain,application/pdf,application/x-ndjson" className="sr-only" onChange={pick}/></label>
          {files.length > 0 && <div className="mt-3 space-y-2">{files.map((file, index) => <div key={`${file.name}-${index}`} className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2 text-sm"><span className="flex min-w-0 items-center gap-2 truncate"><FileText size={16}/>{file.name}</span><button type="button" onClick={() => setFiles(previous => previous.filter((_, i) => i !== index))} className="text-xs font-semibold text-slate-500 hover:text-red-700">Remove</button></div>)}</div>}
          <div className="mt-6 border-t border-slate-100 pt-5"><p className="text-sm font-semibold">Or paste contract text</p><p className="mt-1 text-xs text-slate-500">Use this for copied PDF text or a contract from another source. ODIN checks citations against exactly what you paste.</p><input value={pasteTitle} onChange={event => setPasteTitle(event.target.value)} placeholder="Document name, e.g. Vendor Agreement" className="mt-3 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-[#d4a017]"/><textarea value={pasteText} onChange={event => setPasteText(event.target.value)} placeholder="Paste the agreement or clause text here…" rows={7} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-[#d4a017]"/></div>
        </div>
        {error && <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        {saved && <p role="status" className="mt-4 text-sm text-emerald-700">{saved}</p>}
        <button disabled={busy || !name.trim() || !organization.trim()} onClick={save} className="mt-8 w-full rounded-lg bg-[#112b49] py-3 text-sm font-semibold text-white hover:bg-[#1c4169] disabled:opacity-50">{busy ? "Saving…" : "Open dashboard"}</button>
      </div>
    </div>
  </main>;
}
