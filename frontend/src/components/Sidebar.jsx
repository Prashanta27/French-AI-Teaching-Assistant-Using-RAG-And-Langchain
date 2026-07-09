import { useState } from "react";

function HistoryItem({ s, isActive, onSelect, onPin, onDelete }) {
  const [confirming, setConfirming] = useState(false);

  if (confirming) {
    return (
      <div className="sb-hist-item">
        <div className="sb-confirm-row">
          <button
            className="sb-confirm-btn yes"
            onClick={() => {
              onDelete(s.id);
              setConfirming(false);
            }}
          >
            🗑 Yes
          </button>
          <button className="sb-confirm-btn" onClick={() => setConfirming(false)}>
            ✕ No
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="sb-hist-item">
      <button
        className={`sb-hist-text ${isActive ? "active" : ""}`}
        onClick={() => onSelect(s.id)}
        title={s.name}
      >
        {s.pinned && <span className="sb-hist-pin">📌</span>}
        <span className="sb-hist-label">{s.name}</span>
      </button>
      <div className="sb-hist-actions">
        <button
          className={`sb-act-btn ${s.pinned ? "pin-active" : ""}`}
          title="Pin / Unpin"
          onClick={() => onPin(s.id)}
        >
          {s.pinned ? "📍" : "📌"}
        </button>
        <button className="sb-act-btn danger" title="Delete" onClick={() => setConfirming(true)}>
          🗑
        </button>
      </div>
    </div>
  );
}

function HistoryGroup({ label, items, activeId, onSelect, onPin, onDelete }) {
  if (!items.length) return null;
  return (
    <>
      <div className="sb-section-label">{label}</div>
      {items.map((s) => (
        <HistoryItem
          key={s.id}
          s={s}
          isActive={s.id === activeId}
          onSelect={onSelect}
          onPin={onPin}
          onDelete={onDelete}
        />
      ))}
    </>
  );
}

export default function Sidebar({ sessions, activeId, onSelect, onNew, onPin, onDelete }) {
  const pinned = sessions.filter((s) => s.pinned);
  const unpinned = [...sessions].reverse().filter((s) => !s.pinned);

  return (
    <aside className="sidebar">
      <div className="sb-topbar">
        <div className="sb-brand">
          <div className="sb-brand-icon">🇫🇷</div>
          FrenchAI
        </div>
      </div>

      <div className="sb-new-btn-wrap">
        <button className="sb-new-btn" onClick={onNew}>
          ＋ New Thread
        </button>
      </div>

      <nav className="sb-nav">
        <div className="sb-nav-item active">
          <span className="sb-nav-icon">🏠</span> Home
        </div>
        <div className="sb-nav-item">
          <span className="sb-nav-icon">🔍</span> Discover
        </div>
        <div className="sb-nav-item">
          <span className="sb-nav-icon">📚</span> Library
        </div>
      </nav>

      <HistoryGroup
        label="📌 Pinned"
        items={pinned}
        activeId={activeId}
        onSelect={onSelect}
        onPin={onPin}
        onDelete={onDelete}
      />
      <HistoryGroup
        label="🕘 Recent"
        items={unpinned}
        activeId={activeId}
        onSelect={onSelect}
        onPin={onPin}
        onDelete={onDelete}
      />
    </aside>
  );
}
