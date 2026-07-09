import { useEffect, useRef, useState } from "react";
import Sidebar from "./components/Sidebar";
import TopBar from "./components/TopBar";
import EmptyState from "./components/EmptyState";
import ChatMessage from "./components/ChatMessage";
import ChatInput from "./components/ChatInput";
import TypingIndicator from "./components/TypingIndicator";
import { useSessions } from "./hooks/useSessions";
import { askQuestion } from "./api";

export default function App() {
  const {
    sessions,
    active,
    setActive,
    newSession,
    deleteSession,
    togglePin,
    clearActive,
    addMessage,
  } = useSessions();

  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef(null);
  const abortRef = useRef(null);

  const messages = active.messages;

  // Autoscroll to bottom whenever messages or the typing indicator change.
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, isTyping]);

  // Cancel any in-flight request if the user switches threads mid-reply.
  useEffect(() => {
    return () => abortRef.current?.abort();
  }, [active.id]);

  const send = async (question) => {
    addMessage("user", question);
    setIsTyping(true);

    const controller = new AbortController();
    abortRef.current = controller;

    const { answer } = await askQuestion(question, { signal: controller.signal });

    setIsTyping(false);
    addMessage("assistant", answer);
  };

  const handleRewrite = (msg) => {
    // Find the user question that preceded this assistant answer and resend it.
    const idx = messages.indexOf(msg);
    for (let i = idx - 1; i >= 0; i--) {
      if (messages[i].role === "user") {
        send(messages[i].content);
        return;
      }
    }
  };

  const handleCopy = (msg) => {
    navigator.clipboard?.writeText(msg.content);
  };

  return (
    <div className="app-shell">
      <Sidebar
        sessions={sessions}
        activeId={active.id}
        onSelect={setActive}
        onNew={newSession}
        onPin={togglePin}
        onDelete={deleteSession}
      />

      <div className="main-col">
        <TopBar sessionName={active.name} hasMessages={messages.length > 0} onClear={clearActive} />

        <div className="block-container" ref={scrollRef}>
          {messages.length === 0 ? (
            <EmptyState onPick={send} />
          ) : (
            messages.map((m, idx) => (
              <ChatMessage
                key={idx}
                message={m}
                showDivider={m.role === "user" && idx > 0}
                onCopy={handleCopy}
                onRewrite={handleRewrite}
              />
            ))
          )}
          {isTyping && <TypingIndicator />}
        </div>

        <ChatInput
          placeholder={messages.length ? "Ask a follow-up…" : "Ask anything about French…"}
          disabled={isTyping}
          onSend={send}
        />
      </div>
    </div>
  );
}
