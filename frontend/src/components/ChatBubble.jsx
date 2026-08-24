export default function ChatBubble({ from, children }) {
  return <div className={`bubble bubble-${from}`}>{children}</div>;
}
