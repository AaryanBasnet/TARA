import { useState } from 'react'
import ChatInterface from './components/ChatInterface'
import Header from './components/Header'
import InfoPanel from './components/InfoPanel'
import KYCModal from './components/KYCModal'
import BoardingPassModal from './components/BoardingPassModal'

function App() {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [showKYCModal, setShowKYCModal] = useState(false)
  const [showBoardingPassModal, setShowBoardingPassModal] = useState(false)

  const sendMessage = async (message) => {
    if (!message.trim()) return

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      })

      const data = await response.json()

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please make sure the backend is running.',
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const clearChat = () => setMessages([])

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      <Header onClearChat={clearChat} />

      <div className="flex-1 flex overflow-hidden">
        {/* Main Chat Area */}
        <main className="flex-1 overflow-hidden">
          <ChatInterface
            messages={messages}
            onSendMessage={sendMessage}
            isLoading={isLoading}
          />
        </main>

        {/* Info Panel - Desktop only */}
        <aside className="hidden lg:block w-80 border-l border-gray-200 bg-white overflow-y-auto">
          <InfoPanel
            onOpenKYC={() => setShowKYCModal(true)}
            onOpenBoardingPass={() => setShowBoardingPassModal(true)}
          />
        </aside>
      </div>

      {/* Modals */}
      <KYCModal
        isOpen={showKYCModal}
        onClose={() => setShowKYCModal(false)}
      />
      <BoardingPassModal
        isOpen={showBoardingPassModal}
        onClose={() => setShowBoardingPassModal(false)}
      />
    </div>
  )
}

export default App
