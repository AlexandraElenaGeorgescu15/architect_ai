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

      for (let i = 0; i < 15; i++) {
        newBalloons.push({
          id: i,
          left: Math.random() * 100,
          delay: Math.random() * 0.5,
          duration: 3 + Math.random() * 2,
          color: colors[Math.floor(Math.random() * colors.length)],
          size: 40 + Math.random() * 30,
        })
      }

      // Generate confetti
      const newConfetti: Confetti[] = []
      for (let i = 0; i < 50; i++) {
        newConfetti.push({
          id: i,
          left: 20 + Math.random() * 60,
          top: -10,
          rotation: Math.random() * 360,
          color: colors[Math.floor(Math.random() * colors.length)],
          duration: 2 + Math.random() * 1.5,
          delay: Math.random() * 0.3,
        })
      }

      setBalloons(newBalloons)
      setConfetti(newConfetti)

      // Clean up after animation
      setTimeout(() => {
        setIsVisible(false)
        setBalloons([])
        setConfetti([])
      }, 5000)
    }

    // Listen for celebration event
    window.addEventListener('celebrate-generation', handleCelebration)
    
    return () => {
      window.removeEventListener('celebrate-generation', handleCelebration)
    }
  }, [])

  if (!isVisible) {
    return null
  }

  return createPortal(
    <div className="fixed inset-0 pointer-events-none z-[9999] overflow-hidden">
      {/* Balloons */}
      {balloons.map((balloon) => (
        <div
          key={`balloon-${balloon.id}`}
          className="absolute bottom-0 animate-float-up"
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
              animation: 'balloon-sway 2s ease-in-out infinite',
              animationDelay: `${balloon.delay}s`,
            }}
          >
            {/* Balloon shine */}
            <div
              className="absolute top-2 left-3 w-4 h-6 bg-white/40 rounded-full blur-sm"
            />
            
            {/* Balloon knot */}
            <div
              className="absolute bottom-[-8px] left-1/2 transform -translate-x-1/2 w-3 h-3 rounded-full"
              style={{ backgroundColor: balloon.color, filter: 'brightness(0.8)' }}
            />
          </div>
          
          {/* String */}
          <div
            className="absolute top-full left-1/2 transform -translate-x-1/2 w-0.5 h-20 bg-gray-400/60"
            style={{
              animation: 'string-wave 1.5s ease-in-out infinite',
              animationDelay: `${balloon.delay}s`,
            }}
          />
        </div>
      ))}

      {/* Confetti */}
      {confetti.map((piece) => (
        <div
          key={`confetti-${piece.id}`}
          className="absolute animate-confetti-fall"
          style={{
            left: `${piece.left}%`,
            top: `${piece.top}%`,
            width: '10px',
            height: '10px',
            backgroundColor: piece.color,
            animationDuration: `${piece.duration}s`,
            animationDelay: `${piece.delay}s`,
            transform: `rotate(${piece.rotation}deg)`,
          }}
        />
      ))}

      {/* Success message */}
      <div className="absolute top-1/4 left-1/2 transform -translate-x-1/2 animate-bounce-in pointer-events-none">
        <div className="glass-panel px-8 py-4 rounded-2xl shadow-2xl backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <span className="text-4xl animate-pulse-glow">🎉</span>
            <div>
              <h3 className="text-2xl font-bold text-gradient-electric">Success!</h3>
              <p className="text-sm text-muted-foreground">Artifact generated successfully</p>
            </div>
            <span className="text-4xl animate-pulse-glow">🎊</span>
          </div>
        </div>
      </div>
    </div>,
    document.body
  )
}

