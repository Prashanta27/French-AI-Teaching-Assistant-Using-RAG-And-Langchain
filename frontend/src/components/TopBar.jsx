export default function TopBar({ sessionName, hasMessages, onClear }) {
  return (
    <div className="main-topbar">
      <div className="main-topbar-title">{sessionName}</div>
      {hasMessages && (
        <button className="topbar-btn" onClick={onClear}>
          Clear chat
        </button>
      )}
    </div>
  );
}
