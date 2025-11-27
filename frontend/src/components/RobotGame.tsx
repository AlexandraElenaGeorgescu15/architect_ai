import { useEffect, useRef, useState } from 'react'

interface RobotGameProps {
  className?: string
}

export default function RobotGame({ className = '' }: RobotGameProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [score, setScore] = useState(0)
  const [gameStarted, setGameStarted] = useState(false)
  const [gameOver, setGameOver] = useState(false)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Set canvas size - fixed for consistent gameplay
    const canvasWidth = 400
    const canvasHeight = 150
    canvas.width = canvasWidth
    canvas.height = canvasHeight
    
    // Set display size to be responsive (CSS sizing, internal resolution stays fixed)
    const container = canvas.parentElement
    if (container) {
      const maxDisplayWidth = Math.min(container.clientWidth - 32, canvasWidth) // -32 for padding
      canvas.style.width = `${maxDisplayWidth}px`
      canvas.style.height = `${Math.floor(maxDisplayWidth * 0.375)}px`
    }

    // Game state
    let frame = 0
    let robotY = 0
    let robotVelocity = 0
    let isJumping = false
    const groundY = 120
    const robotX = 50
    const robotSize = 30
    const gravity = 0.8
    const jumpPower = -15

    // Obstacles
    interface Obstacle {
      x: number
      width: number
      height: number
      type: 'cactus' | 'bird'
      y?: number // Only for birds
    }
    const obstacles: Obstacle[] = []
    let obstacleTimer = 0
    const obstacleInterval = 120 // Frames between obstacles
    const gameSpeed = 3

    // Score tracking
    let currentScore = 0
    let lastScoreUpdate = 0

    // Draw robot (pixel art style)
    const drawRobot = (x: number, y: number, frame: number) => {
      ctx.fillStyle = '#3b82f6' // Blue robot
      
      // Body (square)
      ctx.fillRect(x + 5, y + 10, 20, 20)
      
      // Head
      ctx.fillRect(x + 8, y + 5, 14, 8)
      
      // Eyes (animated)
      ctx.fillStyle = '#fff'
      ctx.fillRect(x + 10, y + 7, 3, 3)
      ctx.fillRect(x + 17, y + 7, 3, 3)
      
      // Antenna
      ctx.fillStyle = '#8b5cf6'
      ctx.fillRect(x + 13, y, 4, 5)
      ctx.fillRect(x + 14, y - 2, 2, 2)
      
      // Arms (animated)
      const armOffset = Math.sin(frame * 0.3) * 3
      ctx.fillStyle = '#3b82f6'
      ctx.fillRect(x, y + 12, 5, 8)
      ctx.fillRect(x + 25, y + 12, 5, 8)
      
      // Legs (running animation)
      const legOffset = (frame % 20 < 10) ? 0 : 3
      ctx.fillRect(x + 8, y + 30, 4, 6 - legOffset)
      ctx.fillRect(x + 18, y + 30, 4, 6 + legOffset)
    }

    // Draw obstacle
    const drawObstacle = (obstacle: Obstacle) => {
      if (obstacle.type === 'cactus') {
        // Cactus obstacle
        ctx.fillStyle = '#22c55e'
        ctx.fillRect(obstacle.x, groundY - obstacle.height, obstacle.width, obstacle.height)
        // Cactus details
        ctx.fillRect(obstacle.x + 3, groundY - obstacle.height - 5, 4, 5)
        ctx.fillRect(obstacle.x + obstacle.width - 7, groundY - obstacle.height - 5, 4, 5)
      } else {
        // Bird obstacle (flying)
        if (obstacle.y !== undefined) {
          ctx.fillStyle = '#ef4444'
          ctx.fillRect(obstacle.x, obstacle.y, obstacle.width, obstacle.height)
          // Wings (animated)
          const wingOffset = Math.sin(frame * 0.5) * 2
          ctx.fillRect(obstacle.x - 3, obstacle.y + wingOffset, 3, 4)
          ctx.fillRect(obstacle.x + obstacle.width, obstacle.y - wingOffset, 3, 4)
        }
      }
    }

    // Draw ground
    const drawGround = () => {
      ctx.strokeStyle = '#64748b'
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.moveTo(0, groundY)
      ctx.lineTo(canvas.width, groundY)
      ctx.stroke()
      
      // Ground pattern (moving)
      ctx.strokeStyle = '#94a3b8'
      ctx.lineWidth = 1
      for (let i = 0; i < canvas.width; i += 20) {
        const x = (i - (frame * gameSpeed) % 20) % canvas.width
        ctx.beginPath()
        ctx.moveTo(x, groundY)
        ctx.lineTo(x, groundY + 2)
        ctx.stroke()
      }
    }

    // Check collision
    const checkCollision = (robotX: number, robotY: number, robotSize: number, obstacle: Obstacle): boolean => {
      const robotLeft = robotX
      const robotRight = robotX + robotSize
      const robotTop = robotY
      const robotBottom = robotY + robotSize

      const obstacleLeft = obstacle.x
      const obstacleRight = obstacle.x + obstacle.width
      const obstacleTop = obstacle.type === 'bird' && obstacle.y !== undefined ? obstacle.y : groundY - obstacle.height
      const obstacleBottom = obstacle.type === 'bird' && obstacle.y !== undefined ? obstacle.y + obstacle.height : groundY

      return (
        robotRight > obstacleLeft &&
        robotLeft < obstacleRight &&
        robotBottom > obstacleTop &&
        robotTop < obstacleBottom
      )
    }

    // Jump function
    const jump = () => {
      if (!isJumping && robotY >= groundY - robotSize) {
        robotVelocity = jumpPower
        isJumping = true
      }
    }

    // Keyboard controls
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.code === 'Space' || e.key === ' ' || e.key === 'ArrowUp') {
        e.preventDefault()
        if (!gameStarted) {
          setGameStarted(true)
        }
        jump()
      }
    }

    window.addEventListener('keydown', handleKeyPress)

    // Game loop
    const animate = () => {
      if (gameOver) return

      // Clear canvas
      ctx.fillStyle = '#f8fafc'
      ctx.fillRect(0, 0, canvas.width, canvas.height)

      // Draw ground
      drawGround()

      if (gameStarted) {
        frame++

        // Update robot physics
        robotVelocity += gravity
        robotY += robotVelocity

        // Ground collision
        if (robotY >= groundY - robotSize) {
          robotY = groundY - robotSize
          robotVelocity = 0
          isJumping = false
        }

        // Spawn obstacles
        obstacleTimer++
        if (obstacleTimer >= obstacleInterval) {
          obstacleTimer = 0
          const obstacleType = Math.random() > 0.7 ? 'bird' : 'cactus'
          const obstacleHeight = obstacleType === 'bird' ? 15 : 30 + Math.random() * 20
          const obstacle: Obstacle = {
            x: canvas.width,
            width: obstacleType === 'bird' ? 20 : 15,
            height: obstacleHeight,
            type: obstacleType
          }
          if (obstacleType === 'bird') {
            obstacle.y = groundY - 50 - Math.random() * 20
          }
          obstacles.push(obstacle)
        }

        // Update and draw obstacles
        for (let i = obstacles.length - 1; i >= 0; i--) {
          const obstacle = obstacles[i]
          obstacle.x -= gameSpeed

          // Remove off-screen obstacles
          if (obstacle.x + obstacle.width < 0) {
            obstacles.splice(i, 1)
            currentScore++
            continue
          }

          // Check collision
          if (checkCollision(robotX, robotY, robotSize, obstacle)) {
            setGameOver(true)
            return
          }

          drawObstacle(obstacle)
        }

        // Update score
        if (frame - lastScoreUpdate >= 10) {
          currentScore++
          setScore(currentScore)
          lastScoreUpdate = frame
        }
      } else {
        // Show "Press SPACE to start" message
        ctx.fillStyle = '#64748b'
        ctx.font = '12px monospace'
        ctx.textAlign = 'center'
        ctx.fillText('Press SPACE to start', canvas.width / 2, groundY + 20)
      }

      // Draw robot
      drawRobot(robotX, robotY, frame)

      // Draw score
      if (gameStarted) {
        ctx.fillStyle = '#1e293b'
        ctx.font = 'bold 14px monospace'
        ctx.textAlign = 'left'
        ctx.fillText(`Score: ${currentScore}`, 10, 20)
      }

      // Draw game over
      if (gameOver) {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.7)'
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        ctx.fillStyle = '#fff'
        ctx.font = 'bold 16px monospace'
        ctx.textAlign = 'center'
        ctx.fillText('Game Over!', canvas.width / 2, canvas.height / 2 - 10)
        ctx.font = '12px monospace'
        ctx.fillText(`Final Score: ${currentScore}`, canvas.width / 2, canvas.height / 2 + 10)
        ctx.fillText('Press SPACE to restart', canvas.width / 2, canvas.height / 2 + 30)
      }

      requestAnimationFrame(animate)
    }

    // Start animation
    animate()

    // Restart game on space when game over
    const handleRestart = (e: KeyboardEvent) => {
      if (gameOver && (e.code === 'Space' || e.key === ' ' || e.key === 'ArrowUp')) {
        e.preventDefault()
        // Reset game state
        frame = 0
        robotY = groundY - robotSize
        robotVelocity = 0
        isJumping = false
        obstacles.length = 0
        obstacleTimer = 0
        currentScore = 0
        lastScoreUpdate = 0
        setScore(0)
        setGameOver(false)
        setGameStarted(true)
      }
    }

    window.addEventListener('keydown', handleRestart)

    return () => {
      window.removeEventListener('keydown', handleKeyPress)
      window.removeEventListener('keydown', handleRestart)
    }
  }, [gameStarted, gameOver])

  return (
    <div className={`relative w-full ${className}`}>
      <canvas
        ref={canvasRef}
        className="w-full h-auto border border-slate-300 rounded-lg bg-slate-50 block"
        style={{ imageRendering: 'pixelated', maxWidth: '100%', height: 'auto' }}
      />
      {!gameStarted && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-xs text-slate-500 text-center bg-white/90 px-3 py-1.5 rounded shadow-sm">
            Press SPACE to play
          </div>
        </div>
      )}
    </div>
  )
}

