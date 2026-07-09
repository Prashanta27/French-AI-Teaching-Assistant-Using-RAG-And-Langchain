function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * Very small markdown-lite formatter, same rules the Streamlit app
 * used: **bold**, *italic*, `code`, and newlines -> <br>. Input is
 * HTML-escaped first so nothing in the question/answer text can
 * inject markup.
 */
export function formatMessage(text) {
  let t = escapeHtml(text ?? "");
  t = t.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  t = t.replace(/(?<!\*)\*(?!\*)(.+?)\*(?!\*)/g, "<em>$1</em>");
  t = t.replace(/`([^`]+)`/g, "<code>$1</code>");
  t = t.replace(/\n/g, "<br>");
  return t;
}
