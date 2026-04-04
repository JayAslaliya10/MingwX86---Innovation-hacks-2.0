import { useState, useRef, useEffect } from 'react'
import { chatHttp } from '../../api/client'

const SUGGESTED = [
  "Which plans cover Adalimumab?",
  "What prior auth does Cigna require for Humira?",
  "Compare Infliximab policies across all payers",
  "What policy changes happened recently?",
]

export default function ChatWindow() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Hi! I'm MedPolicy AI. Ask me anything about drug coverage across UnitedHealthcare, Cigna, and Aetna.",
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async (text) => {
    const message = text || input.trim()
    if (!message || loading) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', content: message }])
    setLoading(true)

    try {
      const res = await chatHttp(message)
      setMessages((m) => [...m, { role: 'assistant', content: res.data.response }])
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap
                ${msg.role === 'user'
                  ? 'bg-brand-600 text-white rounded-br-sm'
                  : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm'
                }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Suggested prompts */}
      {messages.length <= 1 && (
        <div className="px-4 pb-2 flex flex-wrap gap-2">
          {SUGGESTED.map((s, i) => (
            <button
              key={i}
              onClick={() => send(s)}
              className="text-xs bg-brand-50 text-brand-700 border border-brand-200 rounded-full px-3 py-1.5 hover:bg-brand-100 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t bg-white">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
            placeholder="Ask about drug coverage, prior auth, policy changes..."
            className="input flex-1 text-sm"
            disabled={loading}
          />
          <button onClick={() => send()} disabled={!input.trim() || loading} className="btn-primary px-4">
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
