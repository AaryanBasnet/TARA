import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X,
  Upload,
  Camera,
  CheckCircle,
  AlertCircle,
  Loader2,
  Shield,
  Smartphone,
  FileText,
  QrCode,
  RotateCcw
} from 'lucide-react'

const KYCModal = ({ isOpen, onClose }) => {
  const [step, setStep] = useState(1)
  const [passportFile, setPassportFile] = useState(null)
  const [selfieFile, setSelfieFile] = useState(null)
  const [passportPreview, setPassportPreview] = useState(null)
  const [selfiePreview, setSelfiePreview] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState(null)
  const [kycResult, setKycResult] = useState(null)
  const [cameraActive, setCameraActive] = useState(false)
  const [cameraError, setCameraError] = useState(null)
  const [shouldStartCamera, setShouldStartCamera] = useState(false)

  const fileInputRef = useRef(null)
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const streamRef = useRef(null)

  // Camera start function
  const startCameraAsync = async () => {
    // Prevent double requests
    if (streamRef.current || cameraActive) {
      console.log('Camera already active, skipping')
      return
    }

    setCameraError(null)

    try {
      console.log('Requesting camera access...')
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } }
      })

      console.log('Camera stream obtained')
      streamRef.current = stream

      // Set active immediately
      setCameraActive(true)
      setShouldStartCamera(false)

      // Assign to video element if available
      if (videoRef.current) {
        videoRef.current.srcObject = stream
      }
    } catch (err) {
      console.error('Camera error:', err)
      setShouldStartCamera(false)
      setCameraActive(false)

      if (err.name === 'NotAllowedError') {
        setCameraError('Camera access denied. Please allow camera access in your browser settings.')
      } else if (err.name === 'NotFoundError') {
        setCameraError('No camera found. Please connect a camera and try again.')
      } else {
        setCameraError(`Camera error: ${err.message}`)
      }
    }
  }

  // Auto-start camera when step 2 and shouldStartCamera is true
  useEffect(() => {
    if (isOpen && step === 2 && shouldStartCamera && !cameraActive && !selfiePreview && !streamRef.current) {
      const timer = setTimeout(() => {
        startCameraAsync()
      }, 300)
      return () => clearTimeout(timer)
    }
  }, [isOpen, step, shouldStartCamera])

  // Assign stream to video element when both are ready
  useEffect(() => {
    if (cameraActive && streamRef.current && videoRef.current && !videoRef.current.srcObject) {
      console.log('Assigning stream to video element')
      videoRef.current.srcObject = streamRef.current
    }
  }, [cameraActive])

  // Cleanup camera on unmount or close
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }
    }
  }, [])

  // Don't render if modal is not open
  if (!isOpen) return null

  const handlePassportUpload = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      setPassportFile(file)
      setError(null)
      const reader = new FileReader()
      reader.onloadend = () => {
        setPassportPreview(reader.result)
      }
      reader.readAsDataURL(file)
    }
  }

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    setCameraActive(false)
    setShouldStartCamera(false)
  }

  const capturePhoto = () => {
    if (videoRef.current && canvasRef.current) {
      const canvas = canvasRef.current
      const video = videoRef.current
      canvas.width = video.videoWidth || 640
      canvas.height = video.videoHeight || 480
      const ctx = canvas.getContext('2d')
      // Mirror the image for selfie
      ctx.translate(canvas.width, 0)
      ctx.scale(-1, 1)
      ctx.drawImage(video, 0, 0)

      canvas.toBlob((blob) => {
        setSelfieFile(blob)
        setSelfiePreview(canvas.toDataURL('image/jpeg'))
        stopCamera()
      }, 'image/jpeg', 0.9)
    }
  }

  const retakeSelfie = () => {
    setSelfiePreview(null)
    setSelfieFile(null)
    setCameraError(null)
    setShouldStartCamera(true)
  }

  const goToSelfieStep = () => {
    if (passportPreview) {
      setStep(2)
      setShouldStartCamera(true)
    }
  }

  const handleSubmit = async () => {
    if (!passportFile || !selfieFile) {
      setError('Please upload passport and take a selfie')
      return
    }

    setStep(3)
    setIsProcessing(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('passport', passportFile)
      formData.append('selfie', selfieFile)

      const response = await fetch('/api/kyc/verify', {
        method: 'POST',
        body: formData,
      })

      const result = await response.json()

      if (result.status === 'approved') {
        setKycResult({
          status: 'approved',
          phone_number: result.sim_details?.phone_number || '+977-98XXXXXXXX',
          carrier: result.sim_details?.carrier || 'Nepal Telecom (NTC)',
          plan: result.sim_details?.plan || 'Tourist SIM - 30 Days',
          data: result.sim_details?.data || '5GB 4G Data',
          validity: result.sim_details?.validity || '30 Days',
          passport_number: result.passport_data?.passport_number || 'Unknown',
          qr_code: result.qr_code,
          face_match_confidence: result.face_match_confidence
        })
        setStep(4)
      } else {
        setError(result.message || 'Verification failed. Please try again.')
        setStep(2)
      }
    } catch (err) {
      console.error('KYC Error:', err)
      setError('Failed to connect to verification server. Please try again.')
      setStep(2)
    } finally {
      setIsProcessing(false)
    }
  }

  const handleClose = () => {
    stopCamera()
    onClose()
  }

  const renderStep = () => {
    switch (step) {
      case 1:
        return (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-5"
          >
            <div className="text-center">
              <div className="w-14 h-14 rounded-full bg-teal-100 flex items-center justify-center mx-auto mb-3">
                <FileText size={28} className="text-teal-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">
                Upload Passport Photo
              </h3>
              <p className="text-gray-500 text-sm mt-1">
                Take a clear photo of your passport's data page
              </p>
            </div>

            {/* Upload Area */}
            <div
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
                passportPreview
                  ? 'border-teal-400 bg-teal-50'
                  : 'border-gray-300 hover:border-teal-400 hover:bg-gray-50'
              }`}
            >
              {passportPreview ? (
                <div className="space-y-3">
                  <img
                    src={passportPreview}
                    alt="Passport"
                    className="max-h-40 mx-auto rounded-lg shadow-sm"
                  />
                  <p className="text-sm text-teal-600 font-medium">
                    <CheckCircle size={16} className="inline mr-1" />
                    Passport uploaded
                  </p>
                </div>
              ) : (
                <>
                  <Upload size={40} className="mx-auto text-gray-400 mb-3" />
                  <p className="text-gray-700 font-medium">
                    Click to upload or drag and drop
                  </p>
                  <p className="text-sm text-gray-400 mt-1">
                    JPG, PNG up to 10MB
                  </p>
                </>
              )}
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handlePassportUpload}
              className="hidden"
            />

            <button
              onClick={goToSelfieStep}
              disabled={!passportPreview}
              className={`w-full py-3 px-4 rounded-xl font-medium transition-all ${
                passportPreview
                  ? 'bg-teal-600 text-white hover:bg-teal-700'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              Continue to Selfie
            </button>
          </motion.div>
        )

      case 2:
        return (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-5"
          >
            <div className="text-center">
              <div className="w-14 h-14 rounded-full bg-blue-100 flex items-center justify-center mx-auto mb-3">
                <Camera size={28} className="text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">
                Take a Selfie
              </h3>
              <p className="text-gray-500 text-sm mt-1">
                Position your face within the circle
              </p>
            </div>

            {/* Camera Area */}
            <div className="relative rounded-xl overflow-hidden bg-gray-900 aspect-[4/3]">
              {selfiePreview ? (
                <img
                  src={selfiePreview}
                  alt="Selfie"
                  className="w-full h-full object-cover"
                />
              ) : cameraActive ? (
                <>
                  <video
                    ref={(el) => {
                      videoRef.current = el
                      if (el && streamRef.current && !el.srcObject) {
                        el.srcObject = streamRef.current
                      }
                    }}
                    autoPlay
                    playsInline
                    muted
                    className="w-full h-full object-cover"
                    style={{ transform: 'scaleX(-1)' }}
                  />
                  {/* Face guide overlay */}
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <div className="w-44 h-56 border-4 border-white/60 rounded-full shadow-lg" />
                  </div>
                  <div className="absolute bottom-2 left-0 right-0 text-center">
                    <span className="text-white text-xs bg-black/50 px-3 py-1 rounded-full">
                      Position your face in the oval
                    </span>
                  </div>
                </>
              ) : cameraError ? (
                <div className="flex flex-col items-center justify-center h-full p-6 text-center">
                  <AlertCircle size={40} className="text-red-400 mb-3" />
                  <p className="text-white text-sm mb-4">{cameraError}</p>
                  <button
                    onClick={() => setShouldStartCamera(true)}
                    className="px-4 py-2 bg-white text-gray-900 rounded-lg text-sm font-medium"
                  >
                    Try Again
                  </button>
                </div>
              ) : shouldStartCamera ? (
                <div className="flex flex-col items-center justify-center h-full">
                  <Loader2 size={32} className="text-white animate-spin mb-3" />
                  <p className="text-white text-sm">Starting camera...</p>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full">
                  <Camera size={48} className="text-gray-400 mb-3" />
                  <p className="text-white text-sm">Camera not started</p>
                </div>
              )}
            </div>

            <canvas ref={canvasRef} className="hidden" />

            {/* Action Buttons */}
            <div className="flex gap-3">
              {selfiePreview ? (
                <>
                  <button
                    onClick={retakeSelfie}
                    className="flex-1 py-3 px-4 border border-gray-300 rounded-xl font-medium text-gray-700 hover:bg-gray-50 flex items-center justify-center gap-2"
                  >
                    <RotateCcw size={18} />
                    Retake
                  </button>
                  <button
                    onClick={handleSubmit}
                    className="flex-1 py-3 px-4 bg-teal-600 text-white rounded-xl font-medium hover:bg-teal-700"
                  >
                    Verify Identity
                  </button>
                </>
              ) : cameraActive ? (
                <button
                  onClick={capturePhoto}
                  className="w-full py-3 px-4 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 flex items-center justify-center gap-2"
                >
                  <Camera size={20} />
                  Capture Photo
                </button>
              ) : shouldStartCamera ? (
                <button
                  disabled
                  className="w-full py-3 px-4 bg-gray-300 text-gray-500 rounded-xl font-medium cursor-not-allowed flex items-center justify-center gap-2"
                >
                  <Loader2 size={20} className="animate-spin" />
                  Starting Camera...
                </button>
              ) : (
                <button
                  onClick={() => setShouldStartCamera(true)}
                  className="w-full py-3 px-4 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700"
                >
                  Enable Camera
                </button>
              )}
            </div>

            {/* Back button */}
            <button
              onClick={() => { stopCamera(); setStep(1); }}
              className="w-full text-gray-500 text-sm hover:text-gray-700"
            >
              Back to passport upload
            </button>
          </motion.div>
        )

      case 3:
        return (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="py-8 text-center"
          >
            <div className="w-16 h-16 rounded-full bg-teal-100 flex items-center justify-center mx-auto mb-5">
              <Loader2 size={32} className="text-teal-600 animate-spin" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Verifying Your Identity
            </h3>
            <p className="text-gray-500 text-sm mb-6">
              This may take a few moments...
            </p>

            <div className="space-y-3 text-left max-w-xs mx-auto">
              {[
                'Reading MRZ data...',
                'Validating passport...',
                'Matching face biometrics...',
                'Generating SIM card...'
              ].map((text, i) => (
                <div key={i} className="flex items-center gap-3 text-sm">
                  <div className="w-5 h-5 rounded-full bg-teal-100 flex items-center justify-center">
                    <CheckCircle size={12} className="text-teal-600" />
                  </div>
                  <span className="text-gray-600">{text}</span>
                </div>
              ))}
            </div>
          </motion.div>
        )

      case 4:
        return (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="space-y-5"
          >
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
                <CheckCircle size={32} className="text-green-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">
                Verification Approved!
              </h3>
              <p className="text-gray-500 text-sm mt-1">
                Your SIM card is ready for collection
              </p>
            </div>

            {/* SIM Card Details */}
            <div className="bg-gray-50 rounded-xl p-4 space-y-3">
              <h4 className="font-medium text-gray-900 flex items-center gap-2">
                <Smartphone size={18} className="text-teal-600" />
                Your SIM Card Details
              </h4>

              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-gray-500">Phone Number</span>
                  <p className="text-gray-900 font-medium">{kycResult?.phone_number}</p>
                </div>
                <div>
                  <span className="text-gray-500">Carrier</span>
                  <p className="text-gray-900 font-medium">{kycResult?.carrier}</p>
                </div>
                <div>
                  <span className="text-gray-500">Plan</span>
                  <p className="text-gray-900 font-medium">{kycResult?.plan}</p>
                </div>
                <div>
                  <span className="text-gray-500">Data</span>
                  <p className="text-gray-900 font-medium">{kycResult?.data}</p>
                </div>
              </div>
            </div>

            {/* QR Code */}
            <div className="text-center">
              <div className="inline-block p-4 bg-white border-2 border-gray-200 rounded-xl shadow-sm mb-3">
                {kycResult?.qr_code ? (
                  <img
                    src={`data:image/png;base64,${kycResult.qr_code}`}
                    alt="QR Code"
                    className="w-36 h-36"
                  />
                ) : (
                  <QrCode size={144} className="text-gray-800" />
                )}
              </div>
              <p className="text-sm text-gray-600">
                Scan at TIA Kiosk to collect your SIM
              </p>
              {kycResult?.face_match_confidence && (
                <p className="text-xs text-teal-600 mt-1">
                  Face Match: {(kycResult.face_match_confidence * 100).toFixed(1)}%
                </p>
              )}
            </div>

            <button
              onClick={handleClose}
              className="w-full py-3 px-4 bg-teal-600 text-white rounded-xl font-medium hover:bg-teal-700"
            >
              Done
            </button>
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
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      onClick={handleClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="w-full max-w-md bg-white rounded-2xl p-6 relative shadow-2xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          onClick={handleClose}
          className="absolute top-4 right-4 p-2 rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
        >
          <X size={20} />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-xl bg-teal-100 flex items-center justify-center">
            <Shield size={20} className="text-teal-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">SIM Card KYC</h2>
            <p className="text-xs text-gray-500">ICAO 9303 Compliant</p>
          </div>
        </div>

        {/* Progress Indicator */}
        {step < 4 && (
          <div className="flex items-center gap-2 mb-5">
            {[1, 2, 3].map((s) => (
              <div
                key={s}
                className={`flex-1 h-1.5 rounded-full transition-colors ${
                  s <= step ? 'bg-teal-500' : 'bg-gray-200'
                }`}
              />
            ))}
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-red-600 text-sm flex items-center gap-2">
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

export default KYCModal
