import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X,
  Upload,
  Plane,
  CheckCircle,
  AlertCircle,
  Loader2,
  Clock,
  MapPin,
  Users,
  Calendar,
  Ticket
} from 'lucide-react'

const BoardingPassModal = ({ isOpen, onClose }) => {
  const [step, setStep] = useState(1) // 1: upload, 2: processing, 3: result
  const [imageFile, setImageFile] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)
  const [scanResult, setScanResult] = useState(null)
  const [error, setError] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)

  const fileInputRef = useRef(null)

  if (!isOpen) return null

  const handleImageUpload = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      setImageFile(file)
      setError(null)
      const reader = new FileReader()
      reader.onloadend = () => {
        setImagePreview(reader.result)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    const file = e.dataTransfer.files?.[0]
    if (file && file.type.startsWith('image/')) {
      setImageFile(file)
      setError(null)
      const reader = new FileReader()
      reader.onloadend = () => {
        setImagePreview(reader.result)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleScan = async () => {
    if (!imageFile) {
      setError('Please upload a boarding pass image')
      return
    }

    setStep(2)
    setIsProcessing(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('image', imageFile)

      const response = await fetch('/api/boarding-pass/scan', {
        method: 'POST',
        body: formData,
      })

      const result = await response.json()

      if (result.status === 'success' || result.status === 'partial') {
        setScanResult(result)
        setStep(3)
      } else {
        setError(result.message || 'Failed to scan boarding pass')
        setStep(1)
      }
    } catch (err) {
      console.error('Scan Error:', err)
      setError('Failed to connect to scanner. Please try again.')
      setStep(1)
    } finally {
      setIsProcessing(false)
    }
  }

  const handleReset = () => {
    setStep(1)
    setImageFile(null)
    setImagePreview(null)
    setScanResult(null)
    setError(null)
  }

  const renderStep = () => {
    switch (step) {
      case 1:
        return (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-6"
          >
            <div className="text-center">
              <div className="w-16 h-16 rounded-2xl bg-blue-500/10 flex items-center justify-center mx-auto mb-4">
                <Ticket size={32} className="text-blue-500" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">
                Scan Boarding Pass
              </h3>
              <p className="text-gray-400 text-sm">
                Upload a photo of your boarding pass to get flight details
              </p>
            </div>

            {/* Upload Area */}
            <div
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-colors
                ${imagePreview
                  ? 'border-blue-500/50 bg-blue-500/5'
                  : 'border-dark-500 hover:border-blue-500/50'
                }`}
            >
              {imagePreview ? (
                <div className="space-y-3">
                  <img
                    src={imagePreview}
                    alt="Boarding Pass"
                    className="max-h-48 mx-auto rounded-lg"
                  />
                  <p className="text-sm text-blue-500">
                    <CheckCircle size={16} className="inline mr-2" />
                    Image uploaded successfully
                  </p>
                </div>
              ) : (
                <>
                  <Upload size={48} className="mx-auto text-gray-400 mb-4" />
                  <p className="text-white font-medium mb-2">
                    Click to upload or drag and drop
                  </p>
                  <p className="text-sm text-gray-400">
                    JPG, PNG up to 10MB
                  </p>
                </>
              )}
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageUpload}
              className="hidden"
            />

            <button
              onClick={handleScan}
              disabled={!imagePreview}
              className="w-full btn-primary bg-blue-600 hover:bg-blue-700"
            >
              <Plane size={18} className="mr-2" />
              Scan Boarding Pass
            </button>
          </motion.div>
        )

      case 2:
        return (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="py-12 text-center"
          >
            <div className="w-20 h-20 rounded-full bg-blue-500/10 flex items-center justify-center mx-auto mb-6">
              <Loader2 size={40} className="text-blue-500 animate-spin" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">
              Scanning Boarding Pass
            </h3>
            <p className="text-gray-400 text-sm mb-6">
              Extracting flight information...
            </p>

            <div className="space-y-3 text-left max-w-xs mx-auto">
              {[
                'Running OCR analysis...',
                'Extracting flight number...',
                'Finding passenger details...',
                'Looking up flight status...'
              ].map((text, i) => (
                <div key={i} className="flex items-center gap-3 text-sm">
                  <div className="w-5 h-5 rounded-full bg-blue-500/20 flex items-center justify-center">
                    <CheckCircle size={12} className="text-blue-500" />
                  </div>
                  <span className="text-gray-400">{text}</span>
                </div>
              ))}
            </div>
          </motion.div>
        )

      case 3:
        const bp = scanResult?.boarding_pass || {}
        const fs = scanResult?.flight_status

        return (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="space-y-6"
          >
            <div className="text-center">
              <div className="w-20 h-20 rounded-full bg-green-500/10 flex items-center justify-center mx-auto mb-4">
                <CheckCircle size={40} className="text-green-500" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">
                Boarding Pass Scanned!
              </h3>
              <p className="text-gray-400 text-sm">
                {scanResult?.message}
              </p>
            </div>

            {/* Flight Details Card */}
            <div className="glass-card p-4 space-y-4">
              {/* Flight Header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
                    <Plane size={20} className="text-blue-500" />
                  </div>
                  <div>
                    <p className="text-white font-bold text-lg">
                      {bp.flight_number || 'Unknown'}
                    </p>
                    <p className="text-xs text-gray-400">
                      {bp.airline || 'Airline'}
                    </p>
                  </div>
                </div>
                {fs && (
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                    fs.status === 'On Time' || fs.status === 'Landed'
                      ? 'bg-green-500/20 text-green-400'
                      : fs.status === 'Delayed'
                        ? 'bg-amber-500/20 text-amber-400'
                        : 'bg-gray-500/20 text-gray-400'
                  }`}>
                    {fs.status}
                  </span>
                )}
              </div>

              {/* Route */}
              {(bp.origin || bp.destination) && (
                <div className="flex items-center justify-between py-3 border-t border-b border-dark-600">
                  <div className="text-center">
                    <p className="text-xs text-gray-400">From</p>
                    <p className="text-white font-medium">{bp.origin || 'N/A'}</p>
                  </div>
                  <div className="flex-1 px-4">
                    <div className="h-px bg-gradient-to-r from-blue-500 to-tia-primary relative">
                      <Plane size={14} className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-blue-500 rotate-90" />
                    </div>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-gray-400">To</p>
                    <p className="text-white font-medium">{bp.destination || 'N/A'}</p>
                  </div>
                </div>
              )}

              {/* Details Grid */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                {bp.passenger_name && (
                  <div className="flex items-start gap-2">
                    <Users size={16} className="text-gray-400 mt-0.5" />
                    <div>
                      <p className="text-gray-400">Passenger</p>
                      <p className="text-white font-medium">{bp.passenger_name}</p>
                    </div>
                  </div>
                )}
                {bp.date && (
                  <div className="flex items-start gap-2">
                    <Calendar size={16} className="text-gray-400 mt-0.5" />
                    <div>
                      <p className="text-gray-400">Date</p>
                      <p className="text-white font-medium">{bp.date}</p>
                    </div>
                  </div>
                )}
                {bp.seat && (
                  <div className="flex items-start gap-2">
                    <Ticket size={16} className="text-gray-400 mt-0.5" />
                    <div>
                      <p className="text-gray-400">Seat</p>
                      <p className="text-white font-medium">{bp.seat}</p>
                    </div>
                  </div>
                )}
                {bp.gate && (
                  <div className="flex items-start gap-2">
                    <MapPin size={16} className="text-gray-400 mt-0.5" />
                    <div>
                      <p className="text-gray-400">Gate</p>
                      <p className="text-white font-medium">{bp.gate}</p>
                    </div>
                  </div>
                )}
                {bp.boarding_time && (
                  <div className="flex items-start gap-2">
                    <Clock size={16} className="text-gray-400 mt-0.5" />
                    <div>
                      <p className="text-gray-400">Boarding</p>
                      <p className="text-white font-medium">{bp.boarding_time}</p>
                    </div>
                  </div>
                )}
                {bp.class && (
                  <div className="flex items-start gap-2">
                    <Plane size={16} className="text-gray-400 mt-0.5" />
                    <div>
                      <p className="text-gray-400">Class</p>
                      <p className="text-white font-medium">{bp.class}</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Confidence */}
              {bp.confidence && (
                <div className="pt-2 border-t border-dark-600">
                  <p className="text-xs text-gray-400 text-center">
                    Scan Confidence: {bp.confidence}%
                  </p>
                </div>
              )}
            </div>

            {/* Live Flight Status */}
            {fs && fs.status !== 'not_found' && (
              <div className="glass-card p-4">
                <h4 className="font-medium text-white mb-3 flex items-center gap-2">
                  <Clock size={16} className="text-blue-500" />
                  Live Flight Status
                </h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {fs.scheduled_arrival && (
                    <div>
                      <p className="text-gray-400">Scheduled Arrival</p>
                      <p className="text-white">{fs.scheduled_arrival}</p>
                    </div>
                  )}
                  {fs.terminal && (
                    <div>
                      <p className="text-gray-400">Terminal</p>
                      <p className="text-white">{fs.terminal}</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            <div className="flex gap-3">
              <button onClick={handleReset} className="flex-1 btn-secondary">
                Scan Another
              </button>
              <button onClick={onClose} className="flex-1 btn-primary bg-blue-600 hover:bg-blue-700">
                Done
              </button>
            </div>
          </motion.div>
        )

      default:
        return null
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="w-full max-w-md glass-card p-6 relative max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 btn-icon text-gray-400 hover:text-white"
        >
          <X size={20} />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
            <Ticket size={20} className="text-blue-500" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Boarding Pass Scanner</h2>
            <p className="text-xs text-gray-400">OCR-powered extraction</p>
          </div>
        </div>

        {/* Progress Indicator */}
        {step < 3 && (
          <div className="flex items-center gap-2 mb-6">
            {[1, 2].map((s) => (
              <div
                key={s}
                className={`flex-1 h-1 rounded-full transition-colors ${
                  s <= step ? 'bg-blue-500' : 'bg-dark-600'
                }`}
              />
            ))}
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm flex items-center gap-2">
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        {/* Step Content */}
        <AnimatePresence mode="wait">
          {renderStep()}
        </AnimatePresence>
      </motion.div>
    </motion.div>
  )
}

export default BoardingPassModal
