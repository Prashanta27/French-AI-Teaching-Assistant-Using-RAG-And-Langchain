const STARTERS = [
  "How do I say 'I would like...' in French?",
  "Explain the difference between être and avoir",
  "How do I order food at a French restaurant?",
  "What are common French greetings?",
  "Teach me how to count to 20 in French",
  "How do I ask for directions in French?",
];

export default function EmptyState({ onPick }) {
  return (
    <div className="empty-wrap">
      <span className="empty-icon">🇫🇷</span>
      <div className="empty-title">Bonjour ! How can I help?</div>
      <div className="empty-sub">
        Your personal French tutor — ask about grammar, vocabulary, pronunciation, or culture.
      </div>
      <div className="starter-grid">
        {STARTERS.map((prompt) => (
          <button key={prompt} className="starter-btn" onClick={() => onPick(prompt)}>
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}
