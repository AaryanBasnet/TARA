import { motion } from 'framer-motion'
import {
  Plane,
  MessageSquare,
  Shield,
  Smartphone,
  Cloud,
  Globe,
  ArrowRight,
  MapPin
} from 'lucide-react'

const WelcomeScreen = ({ onStart }) => {
  const features = [
    {
      icon: Plane,
      title: 'Flight Status',
      description: 'Real-time arrivals & departures'
    },
    {
      icon: Shield,
      title: 'Customs Guide',
      description: 'What you can bring to Nepal'
    },
    {
      icon: Smartphone,
      title: 'SIM Card KYC',
      description: 'Instant mobile activation'
    },
    {
      icon: Cloud,
      title: 'Live Weather',
      description: 'Kathmandu weather updates'
    },
    {
      icon: Globe,
      title: 'Multilingual',
      description: 'English & Nepali support'
    },
    {
      icon: MapPin,
      title: 'Airport Info',
      description: 'Facilities & services'
    }
  ]

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-dark-900 bg-pattern flex items-center justify-center p-4 overflow-auto"
    >
      <div className="max-w-4xl w-full">
        {/* Hero Section */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-center mb-12"
        >
          {/* Logo */}
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', bounce: 0.5, delay: 0.3 }}
            className="inline-flex items-center justify-center w-24 h-24 rounded-3xl nepal-gradient shadow-2xl mb-6"
          >
            <span className="text-white font-bold text-3xl">TIA</span>
          </motion.div>

          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            <span className="gradient-text">Smart Arrival</span>
            <span className="text-white"> Ecosystem</span>
          </h1>

          <p className="text-xl text-gray-400 mb-2">
            Welcome to Tribhuvan International Airport
          </p>

          <p className="text-gray-500">
            नेपालमा स्वागत छ • Welcome to Nepal
          </p>
        </motion.div>

        {/* Features Grid */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-12"
        >
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 + index * 0.1 }}
              className="glass-card p-4 text-center hover:border-tia-primary/30 transition-colors"
            >
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-tia-primary/10 text-tia-primary mb-3">
                <feature.icon size={24} />
              </div>
              <h3 className="font-semibold text-white mb-1">{feature.title}</h3>
              <p className="text-sm text-gray-400">{feature.description}</p>
            </motion.div>
          ))}
        </motion.div>

        {/* CTA Button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
          className="text-center"
        >
          <button
            onClick={onStart}
            className="group inline-flex items-center gap-3 btn-primary text-lg px-8 py-4 rounded-2xl"
          >
            <MessageSquare size={24} />
            <span>Start Chatting</span>
            <ArrowRight
              size={20}
              className="group-hover:translate-x-1 transition-transform"
            />
          </button>

          <p className="text-gray-500 text-sm mt-4">
            Ask me anything about your arrival in Nepal
          </p>
        </motion.div>

        {/* Footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="text-center mt-12 text-gray-600 text-sm"
        >
          <p>Powered by AI • Thesis Project 2024</p>
        </motion.div>
      </div>
    </motion.div>
  )
}

export default WelcomeScreen
