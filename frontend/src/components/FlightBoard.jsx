import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plane,
  PlaneLanding,
  PlaneTakeoff,
  Search,
  RefreshCw,
  Clock,
  MapPin,
  Filter,
  ChevronDown
} from 'lucide-react'

const FlightBoard = () => {
  const [flights, setFlights] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all') // all, arrivals, departures
  const [searchQuery, setSearchQuery] = useState('')
  const [lastUpdated, setLastUpdated] = useState(null)

  // Mock flight data - will be replaced with API call
  useEffect(() => {
    fetchFlights()
  }, [])

  const fetchFlights = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/flights')
      const data = await response.json()
      setFlights(data.flights || [])
      setLastUpdated(new Date())
    } catch (error) {
      // Use mock data if API fails
      setFlights(mockFlights)
      setLastUpdated(new Date())
    } finally {
      setLoading(false)
    }
  }

  const mockFlights = [
    {
      id: 1,
      flight_number: 'RA205',
      airline: 'Nepal Airlines',
      origin: 'Delhi (DEL)',
      destination: 'Kathmandu (KTM)',
      scheduled: '14:30',
      estimated: '14:45',
      status: 'On Time',
      type: 'arrival',
      gate: 'A3'
    },
    {
      id: 2,
      flight_number: 'FZ575',
      airline: 'FlyDubai',
      origin: 'Dubai (DXB)',
      destination: 'Kathmandu (KTM)',
      scheduled: '15:00',
      estimated: '15:20',
      status: 'Delayed',
      type: 'arrival',
      gate: 'B2'
    },
    {
      id: 3,
      flight_number: 'SQ700',
      airline: 'Singapore Airlines',
      origin: 'Singapore (SIN)',
      destination: 'Kathmandu (KTM)',
      scheduled: '16:30',
      estimated: '16:30',
      status: 'On Time',
      type: 'arrival',
      gate: 'A1'
    },
    {
      id: 4,
      flight_number: 'QR654',
      airline: 'Qatar Airways',
      origin: 'Doha (DOH)',
      destination: 'Kathmandu (KTM)',
      scheduled: '17:15',
      estimated: '17:15',
      status: 'On Time',
      type: 'arrival',
      gate: 'C1'
    },
    {
      id: 5,
      flight_number: 'RA206',
      airline: 'Nepal Airlines',
      origin: 'Kathmandu (KTM)',
      destination: 'Delhi (DEL)',
      scheduled: '18:00',
      estimated: '18:00',
      status: 'Boarding',
      type: 'departure',
      gate: 'A5'
    },
    {
      id: 6,
      flight_number: 'TG320',
      airline: 'Thai Airways',
      origin: 'Bangkok (BKK)',
      destination: 'Kathmandu (KTM)',
      scheduled: '19:45',
      estimated: '19:45',
      status: 'Scheduled',
      type: 'arrival',
      gate: 'B1'
    },
  ]

  const getStatusBadge = (status) => {
    const statusMap = {
      'On Time': 'badge-ontime',
      'Delayed': 'badge-delayed',
      'Cancelled': 'badge-cancelled',
      'Landed': 'badge-landed',
      'Boarding': 'badge-ontime',
      'Scheduled': 'badge-ontime',
    }
    return statusMap[status] || 'badge-ontime'
  }

  const filteredFlights = flights.filter(flight => {
    const matchesFilter = filter === 'all' || flight.type === filter.slice(0, -1)
    const matchesSearch =
      flight.flight_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
      flight.airline.toLowerCase().includes(searchQuery.toLowerCase()) ||
      flight.origin.toLowerCase().includes(searchQuery.toLowerCase()) ||
      flight.destination.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesFilter && matchesSearch
  })

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Plane className="text-tia-primary" />
            Live Flight Board
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            Tribhuvan International Airport (KTM)
          </p>
        </div>

        {/* Last Updated */}
        {lastUpdated && (
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <Clock size={14} />
            <span>Updated {lastUpdated.toLocaleTimeString()}</span>
            <button
              onClick={fetchFlights}
              className="btn-icon ml-2"
              disabled={loading}
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        )}
      </div>

      {/* Filters & Search */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        {/* Filter Tabs */}
        <div className="flex items-center gap-1 bg-dark-700/50 p-1 rounded-xl">
          {[
            { id: 'all', label: 'All Flights', icon: Plane },
            { id: 'arrivals', label: 'Arrivals', icon: PlaneLanding },
            { id: 'departures', label: 'Departures', icon: PlaneTakeoff },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilter(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
                filter === tab.id
                  ? 'bg-tia-primary/20 text-tia-primary border border-tia-primary/30'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <tab.icon size={16} />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="flex-1 relative">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search flights, airlines, cities..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full input-field pl-10"
          />
        </div>
      </div>

      {/* Flight Table */}
      <div className="glass-card overflow-hidden">
        {/* Table Header */}
        <div className="grid grid-cols-12 gap-4 p-4 bg-dark-700/50 text-sm font-medium text-gray-400 border-b border-white/10">
          <div className="col-span-2">Flight</div>
          <div className="col-span-3 hidden md:block">Airline</div>
          <div className="col-span-3">Route</div>
          <div className="col-span-2">Time</div>
          <div className="col-span-2">Status</div>
        </div>

        {/* Flight Rows */}
        <div className="divide-y divide-white/5">
          {loading ? (
            // Loading skeleton
            [...Array(5)].map((_, i) => (
              <div key={i} className="grid grid-cols-12 gap-4 p-4 animate-pulse">
                <div className="col-span-2">
                  <div className="h-4 bg-dark-600 rounded w-16" />
                </div>
                <div className="col-span-3 hidden md:block">
                  <div className="h-4 bg-dark-600 rounded w-32" />
                </div>
                <div className="col-span-3">
                  <div className="h-4 bg-dark-600 rounded w-24" />
                </div>
                <div className="col-span-2">
                  <div className="h-4 bg-dark-600 rounded w-12" />
                </div>
                <div className="col-span-2">
                  <div className="h-4 bg-dark-600 rounded w-16" />
                </div>
              </div>
            ))
          ) : filteredFlights.length > 0 ? (
            <AnimatePresence>
              {filteredFlights.map((flight, index) => (
                <motion.div
                  key={flight.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="grid grid-cols-12 gap-4 p-4 hover:bg-white/5 transition-colors cursor-pointer"
                >
                  {/* Flight Number */}
                  <div className="col-span-2">
                    <div className="flex items-center gap-2">
                      {flight.type === 'arrival' ? (
                        <PlaneLanding size={16} className="text-green-400" />
                      ) : (
                        <PlaneTakeoff size={16} className="text-blue-400" />
                      )}
                      <span className="font-semibold text-white">
                        {flight.flight_number}
                      </span>
                    </div>
                  </div>

                  {/* Airline */}
                  <div className="col-span-3 hidden md:flex items-center text-gray-300">
                    {flight.airline}
                  </div>

                  {/* Route */}
                  <div className="col-span-3">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-gray-400">
                        {flight.type === 'arrival' ? flight.origin.split(' ')[0] : 'KTM'}
                      </span>
                      <span className="text-tia-primary">→</span>
                      <span className="text-white">
                        {flight.type === 'arrival' ? 'KTM' : flight.destination.split(' ')[0]}
                      </span>
                    </div>
                  </div>

                  {/* Time */}
                  <div className="col-span-2">
                    <div className="text-white font-medium">{flight.scheduled}</div>
                    {flight.estimated !== flight.scheduled && (
                      <div className="text-xs text-yellow-400">
                        Est: {flight.estimated}
                      </div>
                    )}
                  </div>

                  {/* Status */}
                  <div className="col-span-2">
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${getStatusBadge(flight.status)}`}>
                      {flight.status}
                    </span>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          ) : (
            <div className="p-12 text-center text-gray-400">
              <Plane size={48} className="mx-auto mb-4 opacity-50" />
              <p>No flights found matching your criteria</p>
            </div>
          )}
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
        {[
          { label: 'Total Flights', value: flights.length, color: 'text-white' },
          { label: 'On Time', value: flights.filter(f => f.status === 'On Time').length, color: 'text-green-400' },
          { label: 'Delayed', value: flights.filter(f => f.status === 'Delayed').length, color: 'text-yellow-400' },
          { label: 'Arrivals Today', value: flights.filter(f => f.type === 'arrival').length, color: 'text-blue-400' },
        ].map((stat, index) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 + index * 0.1 }}
            className="glass-card p-4 text-center"
          >
            <div className={`text-2xl font-bold ${stat.color}`}>{stat.value}</div>
            <div className="text-sm text-gray-400">{stat.label}</div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}

export default FlightBoard
