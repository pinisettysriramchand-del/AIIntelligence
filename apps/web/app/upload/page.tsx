"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppNav } from "@/components/AppNav";
import { api, getTokens } from "@/lib/api";

type DocumentItem = {
  id: string;
  filename: string;
  status: string;
  error_message?: string | null;
  quality_warnings?: Array<{ code: string; message: string; severity?: string }>;
};

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [items, setItems] = useState<DocumentItem[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    const list = await api<{ items: DocumentItem[] }>("/api/v1/documents");
    setItems(list.items);
  }

  useEffect(() => {
    if (!getTokens()) {
      router.replace("/login");
      return;
    }
    refresh().catch((err) => setError(err instanceof Error ? err.message : "Failed"));
  }, [router]);

  async function onUpload(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const body = new FormData();
      body.append("file", file);
      const doc = await api<DocumentItem>("/api/v1/documents", {
        method: "POST",
        body,
      });
      await api(`/api/v1/documents/${doc.id}/process`, { method: "POST" });
      setMessage(`Uploaded and queued: ${doc.filename}`);
      setFile(null);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <AppNav />
      <h1 className="hero-title">Upload evidence</h1>
      <p className="lead">PDF, CSV, or Excel. Processing runs asynchronously via the worker.</p>

      <section className="panel" style={{ maxWidth: 560 }}>
        <form className="stack" onSubmit={onUpload}>
          <div>
            <label htmlFor="file">Business document</label>
            <input
              id="file"
              type="file"
              accept=".pdf,.csv,.xlsx,.xls"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              required
            />
          </div>
          <button type="submit" disabled={busy || !file}>
            {busy ? "Uploading…" : "Upload & process"}
          </button>
          {message && <p>{message}</p>}
          {error && <p className="error">{error}</p>}
        </form>
      </section>

      <section className="panel">
        <h2>Your documents</h2>
        {items.length === 0 && <p className="muted">No uploads yet.</p>}
        {items.map((item) => (
          <div className="kpi-row" key={item.id}>
            <div>
              <strong>{item.filename}</strong>
              {item.error_message && <div className="error">{item.error_message}</div>}
              {(item.quality_warnings || []).slice(0, 3).map((w, idx) => (
                <div className="error" key={`${item.id}-${w.code}-${idx}`}>
                  [{w.code}] {w.message}
                </div>
              ))}
            </div>
            <div className="muted">{item.status}</div>
          </div>
        ))}
      </section>
    </main>
  );
}
