import { formatMessage } from "../format";

export default function ChatMessage({ message, showDivider, onCopy, onRewrite }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <>
        {showDivider && <hr className="msg-divider" />}
        <div className="user-msg-wrap">
          <div
            className="user-bubble"
            dangerouslySetInnerHTML={{ __html: formatMessage(message.content) }}
          />
        </div>
        <div className="msg-time-user">{message.time}</div>
      </>
    );
  }

  return (
    <>
      <div className="ai-msg-wrap">
        <div className="ai-avatar">🇫🇷</div>
        <div className="ai-body">
          <div className="ai-name">FrenchAI</div>
          <div
            className="ai-text"
            dangerouslySetInnerHTML={{ __html: formatMessage(message.content) }}
          />
        </div>
      </div>
      <div className="msg-time">{message.time}</div>
      <div className="ai-actions">
        <button className="ai-act" onClick={() => onRewrite?.(message)}>
          ↻ Rewrite
        </button>
        <button className="ai-act" onClick={() => onCopy?.(message)}>
          ⎘ Copy
        </button>
      </div>
    </>
  );
}
