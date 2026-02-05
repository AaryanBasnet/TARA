import { useState, useEffect } from 'react'
import { Plane, RotateCcw, Clock, MapPin, Wifi } from 'lucide-react'

const Header = ({ onClearChat }) => {
  const [currentTime, setCurrentTime] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
      timeZone: 'Asia/Kathmandu'
    })
  }

  return (
    <header className="bg-white border-b border-gray-200">
      {/* Top bar */}
      <div className="bg-blue-600 text-white px-4 py-2">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-sm">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <MapPin className="w-3 h-3" />
              Kathmandu, Nepal
            </span>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatTime(currentTime)} NPT
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Wifi className="w-3 h-3" />
            <span>Online</span>
          </div>
        </div>
      </div>

      {/* Main header */}
      <div className="px-4 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl flex items-center justify-center shadow-sm">
              <Plane className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                Smart Arrival Ecosystem
              </h1>
              <p className="text-sm text-gray-500">
                Tribhuvan International Airport (KTM)
              </p>
            </div>
          </div>

          {/* Status badges */}
          <div className="hidden md:flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 text-green-700 rounded-full text-sm">
              <span className="w-2 h-2 bg-green-500 rounded-full"></span>
              System Active
            </div>
            <button
              onClick={onClearChat}
              className="btn-secondary flex items-center gap-2 text-sm"
            >
              <RotateCcw className="w-4 h-4" />
              New Chat
            </button>
          </div>

          {/* Mobile menu */}
          <button
            onClick={onClearChat}
            className="md:hidden btn-secondary p-2"
          >
            <RotateCcw className="w-5 h-5" />
          </button>
        </div>
      </div>
    </header>
  )
}

export default Header
