import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'

interface Balloon {
  id: number
  left: number
  delay: number
  duration: number
  color: string
  size: number
}

interface Confetti {
  id: number
  left: number
  top: number
  rotation: number
  color: string
  duration: number
  delay: number
}

export default function CelebrationEffect() {
  const [balloons, setBalloons] = useState<Balloon[]>([])
  const [confetti, setConfetti] = useState<Confetti[]>([])
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const handleCelebration = () => {
      console.log('🎉 [CelebrationEffect] Received celebration event! Triggering animation...')
      setIsVisible(true)

      // Generate balloons
      const newBalloons: Balloon[] = []
      const colors = [
        'rgb(59, 130, 246)',   // Blue
        'rgb(168, 85, 247)',   // Purple
        'rgb(236, 72, 153)',   // Pink
        'rgb(249, 115, 22)',   // Orange
        'rgb(34, 197, 94)',    // Green
        'rgb(251, 191, 36)',   // Yellow
      ]

      for (let i = 0; i < 20; i++) {
        newBalloons.push({
          id: i,
          left: 10 + Math.random() * 80, // Keep within centralized area
          delay: Math.random() * 0.5,
          duration: 4 + Math.random() * 3,
          color: colors[Math.floor(Math.random() * colors.length)],
          size: 50 + Math.random() * 40,
        })
      }

      // Generate confetti
      const newConfetti: Confetti[] = []
      for (let i = 0; i < 100; i++) {
        newConfetti.push({
          id: i,
          left: Math.random() * 100,
          top: -20,
          rotation: Math.random() * 360,
          color: colors[Math.floor(Math.random() * colors.length)],
          duration: 2.5 + Math.random() * 2,
          delay: Math.random() * 1.5,
        })
      }

      setBalloons(newBalloons)
      setConfetti(newConfetti)

      // Clean up after animation
      setTimeout(() => {
        console.log('🎉 [CelebrationEffect] Animation complete, cleaning up')
        setIsVisible(false)
        setBalloons([])
        setConfetti([])
      }, 7000)
    }

    // Listen for celebration event
    window.addEventListener('celebrate-generation', handleCelebration)

    // Also listen for a specific test event for debugging
    const handleTest = () => {
      console.log('🧪 [CelebrationEffect] Test event received')
      handleCelebration()
    }
    window.addEventListener('test-celebration', handleTest)

    return () => {
      window.removeEventListener('celebrate-generation', handleCelebration)
      window.removeEventListener('test-celebration', handleTest)
    }
  }, [])

  if (!isVisible) {
    return null
  }

  // Use a very high Z-index to ensure it sits on top of everything including modals
  return createPortal(
    <div className="fixed inset-0 pointer-events-none z-[99999] overflow-hidden flex items-end justify-center">
      {/* Balloons Container */}
      <div className="absolute inset-0 overflow-hidden">
        {balloons.map((balloon) => (
          <div
            key={`balloon-${balloon.id}`}
            className="absolute bottom-[-100px] animate-float-up"
            style={{
              left: `${balloon.left}%`,
              animationDelay: `${balloon.delay}s`,
              animationDuration: `${balloon.duration}s`,
              width: `${balloon.size}px`,
              height: `${balloon.size * 1.2}px`,
            }}
          >
            {/* Balloon body */}
            <div
              className="relative w-full h-full rounded-full shadow-lg"
              style={{
                backgroundColor: balloon.color,
                animation: 'balloon-sway 3s ease-in-out infinite alternate',
                animationDelay: `${balloon.delay}s`,
                boxShadow: 'inset -10px -10px 20px rgba(0,0,0,0.1)'
              }}
            >
              {/* Balloon shine */}
              <div
                className="absolute top-[15%] left-[20%] w-[15%] h-[25%] bg-white/40 rounded-[50%] blur-[2px]"
              />

              {/* Balloon knot */}
              <div
                className="absolute bottom-[-6px] left-1/2 transform -translate-x-1/2 w-[15%] h-[10%] rounded-sm"
                style={{ backgroundColor: balloon.color, filter: 'brightness(0.8)' }}
              />
            </div>

            {/* String */}
            <div
              className="absolute top-full left-1/2 transform -translate-x-1/2 w-[1px] h-[100px] bg-slate-400/60"
              style={{
                animation: 'string-wave 2s ease-in-out infinite',
                animationDelay: `${balloon.delay}s`,
                transformOrigin: 'top center'
              }}
            />
          </div>
        ))}
      </div>

      {/* Confetti Container (Full Screen) */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {confetti.map((piece) => (
          <div
            key={`confetti-${piece.id}`}
            className="absolute animate-confetti-fall"
            style={{
              left: `${piece.left}%`,
              top: `-10px`,
              width: '8px',
              height: '8px',
              backgroundColor: piece.color,
              animationDuration: `${piece.duration}s`,
              animationDelay: `${piece.delay}s`,
              transform: `rotate(${piece.rotation}deg)`,
              borderRadius: Math.random() > 0.5 ? '50%' : '2px'
            }}
          />
        ))}
      </div>

      {/* Success message - Centered and flashy */}
      <div className="absolute top-1/4 left-1/2 transform -translate-x-1/2 -translate-y-1/2 animate-bounce-in pointer-events-auto z-[100000]">
        <div className="glass-panel px-10 py-8 rounded-3xl shadow-2xl backdrop-blur-xl border border-white/20 bg-white/10 flex flex-col items-center text-center">
          <div className="flex items-center gap-4 mb-2">
            <span className="text-5xl animate-bounce" style={{ animationDelay: '0.1s' }}>🎉</span>
            <span className="text-5xl animate-bounce" style={{ animationDelay: '0.2s' }}>✨</span>
            <span className="text-5xl animate-bounce" style={{ animationDelay: '0.3s' }}>🚀</span>
          </div>
          <h3 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 drop-shadow-sm mb-2">
            Generation Complete!
          </h3>
          <p className="text-lg text-slate-700 dark:text-slate-200 font-medium">
            Your artifact has been created successfully.
          </p>
        </div>
      </div>
    </div>,
    document.body
  )
}

