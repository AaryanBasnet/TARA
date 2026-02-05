import { useState, useEffect } from 'react'
import {
  Plane,
  Cloud,
  FileText,
  Smartphone,
  MapPin,
  AlertCircle,
  CheckCircle,
  ExternalLink,
  Ticket,
  Cpu,
  ChevronRight
} from 'lucide-react'

const InfoPanel = ({ onOpenKYC, onOpenBoardingPass }) => {
  const [weather, setWeather] = useState(null)

  useEffect(() => {
    // Fetch weather
    fetch('/api/weather')
      .then(res => res.json())
      .then(data => setWeather(data.data))
      .catch(() => setWeather({ temperature: 18, condition: 'Partly Cloudy' }))
  }, [])

  const services = [
    {
      icon: Plane,
      title: 'Flight Information',
      desc: 'Real-time arrivals & departures',
      status: 'active'
    },
    {
      icon: FileText,
      title: 'Customs & Immigration',
      desc: 'Rules and regulations',
      status: 'active'
    },
    {
      icon: Smartphone,
      title: 'SIM Card Services',
      desc: 'Tourist SIM activation',
      status: 'active'
    },
    {
      icon: MapPin,
      title: 'Airport Facilities',
      desc: 'Lounges, services, transport',
      status: 'active'
    }
  ]

  return (
    <div className="p-4 space-y-6">
      {/* Weather Card */}
      <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-4 text-white">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm opacity-80">Kathmandu Weather</span>
          <Cloud className="w-5 h-5 opacity-80" />
        </div>
        {weather ? (
          <div className="flex items-end justify-between">
            <div>
              <div className="text-3xl font-bold">{weather.temperature}°C</div>
              <div className="text-sm opacity-80">{weather.condition}</div>
            </div>
            <div className="text-5xl">
              {weather.condition?.includes('Clear') ? '☀️' :
               weather.condition?.includes('Cloud') || weather.condition?.includes('Overcast') ? '⛅' :
               weather.condition?.includes('Rain') || weather.condition?.includes('Shower') ? '🌧️' :
               weather.condition?.includes('Drizzle') ? '🌦️' :
               weather.condition?.includes('Thunder') ? '⛈️' :
               weather.condition?.includes('Fog') ? '🌫️' : '🌤️'}
            </div>
          </div>
        ) : (
          <div className="animate-pulse">
            <div className="h-8 w-20 bg-white/20 rounded mb-2"></div>
            <div className="h-4 w-24 bg-white/20 rounded"></div>
          </div>
        )}
      </div>

      {/* Document AI Section */}
      <div>
        <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
          <Cpu className="w-4 h-4 text-purple-600" />
          Document AI
        </h3>
        <div className="space-y-2">
          {/* SIM Card KYC */}
          <button
            onClick={onOpenKYC}
            className="w-full flex items-center gap-3 p-3 bg-gradient-to-r from-teal-50 to-green-50 hover:from-teal-100 hover:to-green-100 rounded-lg transition-colors text-left group"
          >
            <div className="w-10 h-10 bg-teal-500 rounded-lg flex items-center justify-center flex-shrink-0">
              <Smartphone className="w-5 h-5 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <span className="text-sm font-medium text-gray-900 flex items-center gap-1">
                SIM Card KYC
                <span className="text-xs bg-teal-100 text-teal-700 px-1.5 py-0.5 rounded">ICAO</span>
              </span>
              <p className="text-xs text-gray-500">Passport + Face verification</p>
            </div>
            <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-teal-600" />
          </button>

          {/* Boarding Pass Scanner */}
          <button
            onClick={onOpenBoardingPass}
            className="w-full flex items-center gap-3 p-3 bg-gradient-to-r from-blue-50 to-indigo-50 hover:from-blue-100 hover:to-indigo-100 rounded-lg transition-colors text-left group"
          >
            <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center flex-shrink-0">
              <Ticket className="w-5 h-5 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <span className="text-sm font-medium text-gray-900 flex items-center gap-1">
                Boarding Pass Scanner
                <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">OCR</span>
              </span>
              <p className="text-xs text-gray-500">Extract flight info from photo</p>
            </div>
            <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-blue-600" />
          </button>
        </div>
      </div>

      {/* Services */}
      <div>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">
          Chatbot Services
        </h3>
        <div className="space-y-2">
          {services.map((service) => (
            <div
              key={service.title}
              className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg"
            >
              <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <service.icon className="w-4 h-4 text-blue-600" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900">
                    {service.title}
                  </span>
                  {service.status === 'active' && (
                    <CheckCircle className="w-3 h-3 text-green-500" />
                  )}
                </div>
                <p className="text-xs text-gray-500">{service.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Info */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
        <div className="flex gap-2">
          <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-amber-800">Travel Tip</p>
            <p className="text-xs text-amber-700 mt-1">
              Arrive at least 3 hours before international flights for smooth check-in and immigration.
            </p>
          </div>
        </div>
      </div>

      {/* Airport Info */}
      <div className="text-center pt-4 border-t border-gray-100">
        <p className="text-xs text-gray-400">
          Tribhuvan International Airport
        </p>
        <p className="text-xs text-gray-400">
          IATA: KTM | ICAO: VNKT
        </p>
        <a
          href="https://tiairport.com.np"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline mt-2"
        >
          Official Website
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>
    </div>
  )
}

export default InfoPanel
