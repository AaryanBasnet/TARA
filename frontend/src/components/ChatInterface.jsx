import { useState, useRef, useEffect } from 'react'
import { Send, User, Bot, Loader2, Plane, FileText, Smartphone, Cloud } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

const ChatInterface = ({ messages, onSendMessage, isLoading }) => {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef(null)

  const quickActions = [
    {
      icon: Plane,
      label: 'Flight Status',
      query: 'Show me today\'s flight arrivals',
      color: 'bg-blue-50 text-blue-600 border-blue-100'
    },
    {
      icon: FileText,
      label: 'Customs Rules',
      query: 'What items are prohibited at customs?',
      color: 'bg-green-50 text-green-600 border-green-100'
    },
    {
      icon: Smartphone,
      label: 'SIM Card',
      query: 'How do I get a tourist SIM card?',
      color: 'bg-purple-50 text-purple-600 border-purple-100'
    },
    {
      icon: Cloud,
      label: 'Weather',
      query: 'What\'s the weather in Kathmandu?',
      color: 'bg-orange-50 text-orange-600 border-orange-100'
    }
  ]

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (input.trim() && !isLoading) {
      onSendMessage(input)
      setInput('')
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="max-w-3xl mx-auto space-y-4">
          {/* Empty state */}
          {messages.length === 0 && (
            <div className="py-8">
              <div className="text-center mb-8">
                <div className="w-16 h-16 bg-blue-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <Bot className="w-8 h-8 text-blue-600" />
                </div>
                <h2 className="text-xl font-semibold text-gray-900 mb-2">
                  Welcome to TIA Assistant
                </h2>
                <p className="text-gray-500">
                  Your guide to Tribhuvan International Airport. Ask me anything about flights, customs, facilities, or travel tips.
                </p>
              </div>

              {/* Quick action cards */}
              <div className="grid grid-cols-2 gap-3">
                {quickActions.map((action) => (
                  <button
                    key={action.label}
                    onClick={() => onSendMessage(action.query)}
                    className={`flex items-center gap-3 p-4 rounded-xl border text-left transition-all hover:shadow-md ${action.color}`}
                  >
                    <action.icon className="w-5 h-5" />
                    <span className="font-medium">{action.label}</span>
                  </button>
                ))}
              </div>

              {/* Example questions */}
              <div className="mt-6 text-center">
                <p className="text-xs text-gray-400 mb-2">Or try asking:</p>
                <div className="flex flex-wrap justify-center gap-2">
                  {[
                    'Where is the smoking area?',
                    'Baggage allowance rules',
                    'Airport lounge access'
                  ].map((q) => (
                    <button
                      key={q}
                      onClick={() => onSendMessage(q)}
                      className="text-sm text-gray-500 hover:text-blue-600 hover:underline"
                    >
                      "{q}"
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Messages list */}
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}
            >
              {/* Avatar */}
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${message.role === 'user'
                    ? 'bg-blue-600'
                    : 'bg-gray-100 border border-gray-200'
                  }`}
              >
                {message.role === 'user' ? (
                  <User className="w-4 h-4 text-white" />
                ) : (
                  <Bot className="w-4 h-4 text-gray-600" />
                )}
              </div>

              {/* Message bubble */}
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${message.role === 'user'
                    ? 'bg-blue-600 text-white rounded-br-md'
                    : 'bg-white border border-gray-200 text-gray-900 rounded-bl-md shadow-sm'
                  }`}
              >
                <div className={`prose prose-sm max-w-none ${message.role === 'user' ? 'prose-invert' : ''}`}>
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                </div>

                {/* Accuracy/Metrics Footer for Thesis */}
                {message.metrics && (
                  <div className="mt-2 pt-2 border-t border-gray-100 flex flex-wrap gap-x-4 gap-y-1 text-[10px] uppercase tracking-wider text-gray-400 font-semibold">
                    <span className="flex items-center gap-1" title="Local Inference Time">
                      ⏱️ {message.metrics.time?.toFixed(2)}s
                    </span>
                    <span className="flex items-center gap-1" title="RAG Retrieval Confidence">
                      🎯 {message.metrics.confidence}% Conf.
                    </span>
                    <span className="flex items-center gap-1 text-green-600" title="Data Privacy Protected">
                      🛡️ Secure
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Typing indicator */}
          {isLoading && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-gray-100 border border-gray-200 flex items-center justify-center">
                <Bot className="w-4 h-4 text-gray-600" />
              </div>
              <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
                <div className="flex items-center gap-2 text-gray-500">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">Processing your request...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 bg-white p-4">
        <div className="max-w-3xl mx-auto">
          <form onSubmit={handleSubmit} className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about flights, customs, facilities..."
              className="input-field"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="btn-primary px-4 flex items-center gap-2"
            >
              <Send className="w-5 h-5" />
              <span className="hidden sm:inline">Send</span>
            </button>
          </form>
          <p className="text-xs text-gray-400 text-center mt-2">
            Supports English and Nepali (नेपाली)
          </p>
        </div>
      </div>
    </div>
  )
}

export default ChatInterface
