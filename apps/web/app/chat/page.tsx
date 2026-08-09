"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppNav } from "@/components/AppNav";
import { api, getTokens } from "@/lib/api";

type Citation = {
  chunk_id: string;
  document_id: string;
  excerpt: string;
};

type Message = {
  id: string;
  role: string;
  content: string;
  citations: Citation[];
  evidence_sufficient?: boolean;
};

export default function ChatPage() {
  const router = useRouter();
  const [question, setQuestion] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!getTokens()) {
      router.replace("/login");
    }
  }, [router]);

  async function onAsk(event: FormEvent) {
    event.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setError(null);
    const pending = question;
    setQuestion("");
    setMessages((prev) => [
      ...prev,
      { id: `local-${Date.now()}`, role: "user", content: pending, citations: [] },
    ]);
    try {
      let activeSessionId = sessionId;
      if (!activeSessionId) {
        const session = await api<{ id: string }>("/api/v1/chat/sessions", {
          method: "POST",
          body: JSON.stringify({ title: pending.slice(0, 80) || "New Chat" }),
        });
        activeSessionId = session.id;
        setSessionId(activeSessionId);
      }
      const answer = await api<Message>(`/api/v1/chat/sessions/${activeSessionId}/messages`, {
        method: "POST",
        body: JSON.stringify({ content: pending }),
      });
      setMessages((prev) => [...prev, answer]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <AppNav />
      <h1 className="hero-title">AI Chat</h1>
      <p className="lead">Ask questions grounded in uploaded evidence with citations.</p>

      <section className="panel">
        <div className="chat-log">
          {messages.length === 0 && (
            <p className="muted">Ask about KPIs, trends, or document findings.</p>
          )}
          {messages.map((msg) => (
            <div key={msg.id} className={`bubble ${msg.role === "user" ? "user" : ""}`}>
              <div className="muted">{msg.role}</div>
              <div>{msg.content}</div>
              {msg.role === "assistant" && msg.evidence_sufficient === false && (
                <p className="error">Insufficient evidence — answer is not grounded in uploaded sources.</p>
              )}
              {msg.citations?.map((c) => (
                <div className="citation" key={`${msg.id}-${c.chunk_id}`}>
                  [{String(c.chunk_id).slice(0, 8)}] {c.excerpt}
                </div>
              ))}
            </div>
          ))}
        </div>

        <form className="stack" style={{ marginTop: 16 }} onSubmit={onAsk}>
          <textarea
            rows={3}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="What happened to revenue this quarter?"
          />
          <button type="submit" disabled={busy}>
            {busy ? "Thinking…" : "Ask"}
          </button>
          {error && <p className="error">{error}</p>}
        </form>
      </section>
    </main>
  );
}
