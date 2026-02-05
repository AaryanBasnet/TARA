import { useState, useEffect, useCallback } from 'react'

const API_BASE = '/api'

export const useFlights = () => {
  const [flights, setFlights] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)

  const fetchFlights = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE}/flights`)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()

      setFlights(data.flights || [])
      setLastUpdated(data.last_updated ? new Date(data.last_updated) : new Date())

    } catch (err) {
      console.error('Flights error:', err)
      setError(err.message)

      // Use mock data as fallback
      setFlights(getMockFlights())
      setLastUpdated(new Date())
    } finally {
      setIsLoading(false)
    }
  }, [])

  const refreshFlights = useCallback(async () => {
    setIsLoading(true)

    try {
      await fetch(`${API_BASE}/flights/refresh`, { method: 'POST' })
      await fetchFlights()
    } catch (err) {
      console.error('Refresh error:', err)
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }, [fetchFlights])

  useEffect(() => {
    fetchFlights()

    // Auto-refresh every 5 minutes
    const interval = setInterval(fetchFlights, 5 * 60 * 1000)

    return () => clearInterval(interval)
  }, [fetchFlights])

  return {
    flights,
    isLoading,
    error,
    lastUpdated,
    refreshFlights
  }
}

// Mock data fallback
const getMockFlights = () => [
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

export default useFlights
