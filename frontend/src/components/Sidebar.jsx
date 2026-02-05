import { motion } from 'framer-motion'
import {
  Shield,
  Plane,
  Cloud,
  Phone,
  FileText,
  Trash2,
  RefreshCw,
  Info,
  CheckCircle,
  AlertCircle,
  Zap,
  Globe,
  MessageSquare
} from 'lucide-react'
import { useState, useEffect } from 'react'

const Sidebar = ({ onOpenKYC, onClearChat, messagesCount }) => {
  const [flightDataStatus, setFlightDataStatus] = useState('loading')
  const [weatherData, setWeatherData] = useState(null)

  useEffect(() => {
    // Simulate checking flight data status
    setTimeout(() => {
      setFlightDataStatus('fresh')
    }, 1000)

    // Fetch weather data
    fetchWeather()
  }, [])

  const fetchWeather = async () => {
    try {
      const response = await fetch('/api/weather')
      const data = await response.json()
      setWeatherData(data)
    } catch (error) {
      // Use mock data if API fails
      setWeatherData({
        temperature: 18,
        condition: 'Partly Cloudy',
        humidity: 65
      })
    }
  }

  const capabilities = [
    { icon: Plane, label: 'Flight Status & Search', color: 'text-blue-400' },
    { icon: Cloud, label: 'Live Weather Updates', color: 'text-yellow-400' },
    { icon: Shield, label: 'Airport Rules & Customs', color: 'text-green-400' },
    { icon: Phone, label: 'SIM Card KYC (ICAO 9303)', color: 'text-purple-400' },
    { icon: Globe, label: 'Nepali/English Support', color: 'text-pink-400' },
  ]

  return (
    <motion.aside
      initial={{ x: -280, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: -280, opacity: 0 }}
      transition={{ type: 'spring', bounce: 0.1, duration: 0.5 }}
      className="w-72 glass-card border-r border-white/10 flex flex-col h-full overflow-hidden"
    >
      {/* Header */}
      <div className="p-4 border-b border-white/10">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Shield size={20} className="text-tia-primary" />
          Smart Arrival
        </h2>
        <p className="text-xs text-gray-400 mt-1">
          Powered by LangGraph ReAct Agent
        </p>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-hide">
        {/* Flight Data Status */}
        <section>
          <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
            <Plane size={16} />
            Flight Data
          </h3>
          <div className="glass-card p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Status</span>
              <div className="flex items-center gap-2">
                {flightDataStatus === 'fresh' ? (
                  <>
                    <CheckCircle size={14} className="text-green-400" />
                    <span className="text-xs text-green-400">Live</span>
                  </>
                ) : flightDataStatus === 'stale' ? (
                  <>
                    <AlertCircle size={14} className="text-yellow-400" />
                    <span className="text-xs text-yellow-400">Stale</span>
                  </>
                ) : (
                  <>
                    <RefreshCw size={14} className="text-gray-400 animate-spin" />
                    <span className="text-xs text-gray-400">Loading</span>
                  </>
                )}
              </div>
            </div>
            <button className="w-full btn-secondary text-xs flex items-center justify-center gap-2">
              <RefreshCw size={14} />
              Force Refresh
            </button>
          </div>
        </section>

        {/* Weather Widget */}
        <section>
          <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
            <Cloud size={16} />
            Kathmandu Weather
          </h3>
          <div className="glass-card p-4">
            {weatherData ? (
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-3xl font-bold text-white">
                    {weatherData.temperature}°C
                  </div>
                  <div className="text-sm text-gray-400">
                    {weatherData.condition}
                  </div>
                </div>
                <div className="text-5xl">
                  {weatherData.condition?.includes('Cloud') ? '⛅' :
                   weatherData.condition?.includes('Rain') ? '🌧️' :
                   weatherData.condition?.includes('Clear') ? '☀️' : '🌤️'}
                </div>
              </div>
            ) : (
              <div className="animate-pulse flex items-center gap-4">
                <div className="w-16 h-16 bg-dark-600 rounded-lg" />
                <div className="space-y-2">
                  <div className="h-4 w-20 bg-dark-600 rounded" />
                  <div className="h-3 w-16 bg-dark-600 rounded" />
                </div>
              </div>
            )}
          </div>
        </section>

        {/* KYC Services */}
        <section>
          <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
            <Shield size={16} />
            Identity Services
          </h3>
          <button
            onClick={onOpenKYC}
            className="w-full glass-card p-4 text-left hover:border-tia-primary/30 transition-all group"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-tia-primary/10 flex items-center justify-center text-tia-primary group-hover:bg-tia-primary group-hover:text-white transition-colors">
                <Phone size={20} />
              </div>
              <div>
                <div className="font-medium text-white">Verify Identity</div>
                <div className="text-xs text-gray-400">Get SIM Card instantly</div>
              </div>
            </div>
          </button>
        </section>

        {/* Capabilities */}
        <section>
          <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
            <Zap size={16} />
            Capabilities
          </h3>
          <div className="space-y-2">
            {capabilities.map((cap, index) => (
              <div
                key={index}
                className="flex items-center gap-3 text-sm text-gray-400"
              >
                <cap.icon size={16} className={cap.color} />
                <span>{cap.label}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Performance Stats */}
        <section>
          <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
            <Info size={16} />
            Session Info
          </h3>
          <div className="glass-card p-3 space-y-2 text-sm">
            <div className="flex justify-between text-gray-400">
              <span>Messages</span>
              <span className="text-white">{messagesCount}</span>
            </div>
            <div className="flex justify-between text-gray-400">
              <span>Model</span>
              <span className="text-white">qwen2.5:3b</span>
            </div>
            <div className="flex justify-between text-gray-400">
              <span>RAG Timeout</span>
              <span className="text-white">15s</span>
            </div>
          </div>
        </section>
      </div>

      {/* Footer Actions */}
      <div className="p-4 border-t border-white/10 space-y-2">
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={onClearChat}
            className="btn-secondary text-sm flex items-center justify-center gap-2"
          >
            <Trash2 size={14} />
            Clear
          </button>
          <button
            onClick={() => window.location.reload()}
            className="btn-secondary text-sm flex items-center justify-center gap-2"
          >
            <RefreshCw size={14} />
            Reset
          </button>
        </div>

        <div className="text-center text-xs text-gray-500 pt-2">
          <div className="flex items-center justify-center gap-1">
            <span className="w-2 h-2 bg-nepal-red rounded-full" />
            <span className="w-2 h-2 bg-nepal-blue rounded-full" />
          </div>
          <p className="mt-1">Tribhuvan International Airport</p>
          <p>Version 2.0 | Thesis Project 2024</p>
        </div>
      </div>
    </motion.aside>
  )
}

export default Sidebar
