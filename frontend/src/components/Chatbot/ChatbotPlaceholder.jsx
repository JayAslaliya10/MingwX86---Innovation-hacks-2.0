export default function ChatbotPlaceholder() {
  return (
    <div className="fixed bottom-6 right-6 z-50">
      <button
        className="w-14 h-14 bg-brand-600 hover:bg-brand-700 text-white rounded-full shadow-lg flex items-center justify-center text-2xl transition-colors"
        title="AI Assistant (coming soon)"
        onClick={() => alert('AI Assistant coming soon!')}
      >
        🤖
      </button>
    </div>
  )
}
