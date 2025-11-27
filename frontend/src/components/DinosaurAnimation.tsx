import { useEffect, useRef } from 'react'

interface DinosaurAnimationProps {
  className?: string
}

export default function DinosaurAnimation({ className = '' }: DinosaurAnimationProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Set canvas size
    canvas.width = 200
    canvas.height = 100

    // Animation state
    let frame = 0
    let dinoY = 0
    let isJumping = false
    let jumpVelocity = 0
    const groundY = 80
    const dinoX = 30
    let dinoHeight = 40

    // Simple dinosaur sprite (pixel art style)
    const drawDino = (x: number, y: number, frame: number) => {
      ctx.fillStyle = '#333'
      
      // Body
      ctx.fillRect(x + 10, y + 20, 20, 15)
      
      // Head
      ctx.fillRect(x + 5, y + 10, 15, 12)
      
      // Eye (blinking animation)
      if (frame % 60 < 50) {
        ctx.fillStyle = '#fff'
        ctx.fillRect(x + 8, y + 13, 3, 3)
      }
      
      // Legs (running animation)
      const legOffset = (frame % 20 < 10) ? 0 : 5
      ctx.fillStyle = '#333'
      ctx.fillRect(x + 12, y + 35, 4, 8 - legOffset)
      ctx.fillRect(x + 18, y + 35, 4, 8 + legOffset)
      
      // Tail
      ctx.fillRect(x + 28, y + 22, 8, 4)
    }

    // Ground line
    const drawGround = () => {
      ctx.strokeStyle = '#666'
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.moveTo(0, groundY)
      ctx.lineTo(canvas.width, groundY)
      ctx.stroke()
    }

    // Animation loop
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      
      // Update jump physics
      if (isJumping) {
        dinoY += jumpVelocity
        jumpVelocity += 0.8 // gravity
        
        if (dinoY >= 0) {
          dinoY = 0
          isJumping = false
          jumpVelocity = 0
        }
      } else {
        // Auto-jump every 3 seconds
        if (frame % 180 === 0) {
          isJumping = true
          jumpVelocity = -12
        }
      }
      
      drawGround()
      drawDino(dinoX, groundY - dinoHeight + dinoY, frame)
      
      frame++
      requestAnimationFrame(animate)
    }

    animate()
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className={className}
      style={{ imageRendering: 'pixelated' }}
    />
  )
}

