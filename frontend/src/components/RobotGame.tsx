import { useEffect, useRef, useState } from 'react'

interface RobotGameProps {
  className?: string
}

export default function RobotGame({ className = '' }: RobotGameProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [score, setScore] = useState(0)
  const [highScore, setHighScore] = useState(0)
  const [gameStarted, setGameStarted] = useState(false)
  const [gameOver, setGameOver] = useState(false)
  
  // Use a ref for last restart time to avoid re-renders or dependency issues
  // Moved to top level to comply with React Rules of Hooks
  const lastRestartTime = useRef(0)
  
  // Store final score in ref so it persists across useEffect re-runs on game over
  const finalScoreRef = useRef(0)

  // Load high score
  useEffect(() => {
    const saved = localStorage.getItem('robotGameHighScore')
    if (saved) setHighScore(parseInt(saved))
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Set canvas size
    const canvasWidth = 600
    const canvasHeight = 200
    canvas.width = canvasWidth
    canvas.height = canvasHeight
    
    // Responsive display
    const container = canvas.parentElement
    if (container) {
      const maxDisplayWidth = Math.min(container.clientWidth - 32, canvasWidth)
      canvas.style.width = `${maxDisplayWidth}px`
      canvas.style.height = `${Math.floor(maxDisplayWidth * (canvasHeight / canvasWidth))}px`
    }

    // Game state
    let animationFrameId: number
    let frame = 0
    let robotY = 160 - 30 // Start on ground (groundY - robotSize)
    let robotVelocity = 0
    let isJumping = false
    let currentScore = 0
    let gameSpeed = 4 // Base speed
    
    // Constants
    const groundY = 160
    const robotX = 60
    const robotSize = 30
    const gravity = 0.6
    const jumpPower = -12

    // Particles system
    interface Particle {
      x: number
      y: number
      vx: number
      vy: number
      life: number
      color: string
      size: number
    }
    let particles: Particle[] = []

    const spawnParticles = (x: number, y: number, count: number, color: string) => {
      for (let i = 0; i < count; i++) {
        particles.push({
          x,
          y,
          vx: (Math.random() - 0.5) * 4,
          vy: (Math.random() - 1) * 3,
          life: 1.0,
          color,
          size: Math.random() * 3 + 1
        })
      }
    }

    // Background elements (stars/clouds)
    interface BgElement {
      x: number
      y: number
      type: 'cloud' | 'star'
      speed: number
    }
    const bgElements: BgElement[] = []
    
    // Initialize random background
    for (let i = 0; i < 10; i++) {
      bgElements.push({
        x: Math.random() * canvasWidth,
        y: Math.random() * (groundY - 50),
        type: Math.random() > 0.5 ? 'cloud' : 'star',
        speed: Math.random() * 0.5 + 0.1
      })
    }

    // Obstacles
    interface Obstacle {
      x: number
      width: number
      height: number
      type: 'cactus' | 'bird' | 'rock'
      y?: number
    }
    const obstacles: Obstacle[] = []
    let obstacleTimer = 0
    let minObstacleTime = 100 // Gets smaller as speed increases

    // Drawing functions
    const drawRobot = (x: number, y: number, frame: number, isJumping: boolean) => {
      const isDark = document.documentElement.classList.contains('dark')
      const mainColor = isDark ? '#60a5fa' : '#3b82f6'
      const accentColor = isDark ? '#a78bfa' : '#8b5cf6'

      // Glow effect in dark mode
      if (isDark) {
        ctx.shadowBlur = 10
        ctx.shadowColor = mainColor
      } else {
        ctx.shadowBlur = 0
      }

      // Body
      ctx.fillStyle = mainColor
      ctx.fillRect(x + 5, y + 10, 20, 20) // Main body
      
      // Head
      ctx.fillRect(x + 8, y + 2, 14, 10)
      
      // Eyes
      ctx.fillStyle = '#fff'
      ctx.fillRect(x + 10, y + 5, 4, 4)
      ctx.fillRect(x + 18, y + 5, 4, 4)
      
      // Antenna
      ctx.fillStyle = accentColor
      ctx.fillRect(x + 13, y - 4, 4, 6)
      
      // Jetpack / Backpack
      ctx.fillStyle = '#64748b'
      ctx.fillRect(x, y + 12, 5, 12)

      // Jetpack flame if jumping
      if (isJumping) {
        ctx.fillStyle = '#f59e0b'
        ctx.beginPath()
        ctx.moveTo(x, y + 24)
        ctx.lineTo(x + 5, y + 24)
        ctx.lineTo(x + 2.5, y + 24 + Math.random() * 10)
        ctx.fill()
        
        // Add smoke particles occasionally
        if (frame % 5 === 0) {
            spawnParticles(x + 2.5, y + 24, 1, '#94a3b8')
        }
      }
      
      // Arms (swinging)
      ctx.shadowBlur = 0
      ctx.fillStyle = mainColor
      if (!isJumping) {
        const armOffset = Math.sin(frame * 0.2) * 5
        ctx.fillRect(x + 10 + armOffset, y + 15, 6, 6)
      } else {
        // Arms up when jumping
        ctx.fillRect(x + 2, y + 8, 4, 8)
        ctx.fillRect(x + 26, y + 8, 4, 8)
      }
      
      // Legs (running animation)
      if (!isJumping) {
        const legOffset = Math.sin(frame * 0.3) * 5
        ctx.fillStyle = '#1e293b' // Darker legs
        if (isDark) ctx.fillStyle = '#cbd5e1'
        
        ctx.fillRect(x + 8 + legOffset, y + 30, 6, 8)
        ctx.fillRect(x + 18 - legOffset, y + 30, 6, 8)
      }
    }

    const drawObstacle = (obstacle: Obstacle) => {
        const isDark = document.documentElement.classList.contains('dark')
        
        if (obstacle.type === 'cactus') {
            ctx.fillStyle = '#22c55e' // Green
            if (isDark) ctx.shadowColor = '#22c55e'; if (isDark) ctx.shadowBlur = 5;
            
            // Main stem
            ctx.fillRect(obstacle.x + 5, groundY - obstacle.height, obstacle.width - 10, obstacle.height)
            // Arms
            ctx.fillRect(obstacle.x, groundY - obstacle.height + 10, 5, 5)
            ctx.fillRect(obstacle.x + obstacle.width - 5, groundY - obstacle.height + 5, 5, 5)
            
            ctx.shadowBlur = 0;
        } else if (obstacle.type === 'bird') {
            const obsY = obstacle.y ?? (groundY - obstacle.height)
            const centerY = obsY + obstacle.height/2
            
            // Body
            ctx.fillStyle = '#ef4444' // Red
            ctx.beginPath()
            ctx.moveTo(obstacle.x, centerY)
            ctx.lineTo(obstacle.x + obstacle.width - 5, centerY + 5) // Lower body
            ctx.lineTo(obstacle.x + obstacle.width, centerY - 2) // Beak tip
            ctx.lineTo(obstacle.x + 5, centerY - 5) // Upper body
            ctx.fill()
            
            // Wing (Flapping)
            const wingOffset = Math.sin(frame * 0.2) * 8
            ctx.fillStyle = isDark ? '#fca5a5' : '#b91c1c'
            ctx.beginPath()
            ctx.moveTo(obstacle.x + 8, centerY - 2)
            ctx.lineTo(obstacle.x + 18, centerY - 2)
            ctx.lineTo(obstacle.x + 2, centerY - 5 - wingOffset)
            ctx.fill()

            // Eye
            ctx.fillStyle = '#fff'
            ctx.fillRect(obstacle.x + obstacle.width - 8, centerY - 4, 2, 2)
        } else {
            // Rock
            ctx.fillStyle = isDark ? '#94a3b8' : '#64748b' // Slate
            ctx.beginPath()
            ctx.arc(obstacle.x + obstacle.width/2, groundY - obstacle.height + obstacle.height/2, obstacle.width/2, 0, Math.PI * 2)
            ctx.fill()
        }
    }

    // Input handling
    const jump = () => {
      if (!isJumping && robotY >= groundY - robotSize) {
        robotVelocity = jumpPower
        isJumping = true
        // Spawn dust particles
        const isDark = document.documentElement.classList.contains('dark')
        spawnParticles(robotX + robotSize/2, groundY, 10, isDark ? '#cbd5e1' : '#94a3b8')
      }
    }

    const restartGame = () => {
        // Clear all state
        frame = 0
        robotY = groundY - robotSize // Start on ground
        robotVelocity = 0
        isJumping = false
        obstacles.length = 0
        particles.length = 0
        currentScore = 0
        gameSpeed = 4
        
        // Update React state which triggers re-render
        setScore(0)
        setGameOver(false)
        setGameStarted(true)
    }

    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.code === 'Space' || e.key === ' ' || e.key === 'ArrowUp') {
        e.preventDefault()
        
        const now = Date.now()
        // Prevent accidental double-taps on restart
        if (gameOver && now - lastRestartTime.current < 500) return

        if (!gameStarted && !gameOver) {
          setGameStarted(true)
        } else if (gameOver) {
          lastRestartTime.current = now
          restartGame()
        } else {
          jump()
        }
      }
    }

    window.addEventListener('keydown', handleKeyPress)

    // Main Game Loop
    const animate = () => {
      // 1. Clear Canvas
      const isDark = document.documentElement.classList.contains('dark')
      ctx.fillStyle = isDark ? '#0f172a' : '#f8fafc'
      ctx.fillRect(0, 0, canvas.width, canvas.height)

      // 2. Draw Background (Parallax)
      bgElements.forEach(el => {
        if (gameStarted && !gameOver) el.x -= el.speed
        if (el.x < -20) el.x = canvasWidth + 20

        ctx.fillStyle = isDark ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.1)'
        if (el.type === 'cloud') {
           ctx.beginPath()
           ctx.arc(el.x, el.y, 10, 0, Math.PI * 2)
           ctx.arc(el.x + 8, el.y - 5, 12, 0, Math.PI * 2)
           ctx.arc(el.x + 16, el.y, 10, 0, Math.PI * 2)
           ctx.fill()
        } else {
           ctx.fillRect(el.x, el.y, 2, 2)
        }
      })

      // 3. Draw Ground
      ctx.strokeStyle = isDark ? '#334155' : '#cbd5e1'
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.moveTo(0, groundY)
      ctx.lineTo(canvas.width, groundY)
      ctx.stroke()

      if (gameStarted) {
        if (!gameOver) {
            frame++
            currentScore += 0.05 // Score based on distance/time
            
            // Progressive difficulty
            if (currentScore % 100 < 1) { // Every ~100 points
                gameSpeed += 0.05
                minObstacleTime = Math.max(40, minObstacleTime - 2)
            }

            setScore(Math.floor(currentScore))

            // Robot Physics
            robotVelocity += gravity
            robotY += robotVelocity

            // Ground Collision
            if (robotY >= groundY - robotSize) {
                if (isJumping) {
                    // Just landed
                    const isDark = document.documentElement.classList.contains('dark')
                    spawnParticles(robotX + robotSize/2, groundY, 5, isDark ? '#cbd5e1' : '#94a3b8')
                }
                robotY = groundY - robotSize
                robotVelocity = 0
                isJumping = false
            }

            // Spawn Obstacles
            obstacleTimer++
            if (obstacleTimer > minObstacleTime) {
                if (Math.random() < 0.02) { // Random chance to spawn
                    obstacleTimer = 0
                    const typeRoll = Math.random()
                    let type: 'cactus' | 'bird' | 'rock' = 'cactus'
                    let width = 20
                    let height = 30
                    let yPos: number | undefined = undefined

                    if (typeRoll > 0.7) {
                        type = 'bird'
                        width = 25
                        height = 20
                        yPos = groundY - 40 - Math.random() * 40 // Flying height
                    } else if (typeRoll > 0.4) {
                        type = 'rock'
                        width = 25
                        height = 20
                    }

                    obstacles.push({
                        x: canvas.width,
                        width,
                        height,
                        type,
                        y: yPos
                    })
                }
            }
        }

        // Draw & Update Obstacles
        for (let i = obstacles.length - 1; i >= 0; i--) {
            const obs = obstacles[i]
            if (!gameOver) obs.x -= gameSpeed
            
            drawObstacle(obs)

            // Collision Check
            const padding = 5 // Hitbox forgiveness
            const obsY = obs.y !== undefined ? obs.y : groundY - obs.height
            
            if (
                robotX + robotSize - padding > obs.x &&
                robotX + padding < obs.x + obs.width &&
                robotY + robotSize - padding > obsY &&
                robotY + padding < obsY + obs.height
            ) {
                if (!gameOver) {
                    // Store final score in ref before triggering re-render
                    const finalScore = Math.floor(currentScore)
                    finalScoreRef.current = finalScore
                    
                    setGameOver(true)
                    // High score check
                    const savedHigh = parseInt(localStorage.getItem('robotGameHighScore') || '0')
                    if (finalScore > savedHigh) {
                        localStorage.setItem('robotGameHighScore', finalScore.toString())
                        setHighScore(finalScore)
                    }
                    // Explosion particles
                    spawnParticles(robotX + robotSize/2, robotY + robotSize/2, 20, '#ef4444')
                }
            }
            
            // Remove offscreen
            if (obs.x + obs.width < 0) {
                obstacles.splice(i, 1)
            }
        }

        // Draw & Update Particles
        for (let i = particles.length - 1; i >= 0; i--) {
            const p = particles[i]
            if (!gameOver) {
                p.x += p.vx
                p.y += p.vy
                p.vy += 0.2 // Gravity
                p.life -= 0.05
            }
            
            ctx.fillStyle = p.color
            ctx.globalAlpha = p.life
            ctx.beginPath()
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
            ctx.fill()
            ctx.globalAlpha = 1.0

            if (p.life <= 0) particles.splice(i, 1)
        }
      } else {
        // Intro screen text
         ctx.fillStyle = isDark ? '#94a3b8' : '#64748b'
         ctx.font = '14px monospace'
         ctx.textAlign = 'center'
         ctx.fillText('Press SPACE to Jump', canvas.width / 2, canvas.height / 2 - 20)
         ctx.fillText('Avoid obstacles!', canvas.width / 2, canvas.height / 2 + 5)
      }

      // Draw Robot
      drawRobot(robotX, robotY, frame, isJumping)

      // UI Text (Score, etc)
      ctx.textAlign = 'left'
      ctx.fillStyle = isDark ? '#fff' : '#0f172a'
      ctx.font = 'bold 16px monospace'
      ctx.fillText(`Score: ${Math.floor(currentScore)}`, 10, 25)
      
      ctx.textAlign = 'right'
      ctx.font = '14px monospace'
      ctx.fillStyle = isDark ? '#94a3b8' : '#64748b'
      ctx.fillText(`HI: ${highScore}`, canvas.width - 10, 25)

      if (gameOver) {
        // Fully clear canvas for game over screen to prevent transparency stacking
        ctx.fillStyle = isDark ? '#0f172a' : '#f8fafc'
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        
        // Add semi-transparent overlay
        ctx.fillStyle = 'rgba(0,0,0,0.8)'
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        
        ctx.textAlign = 'center'
        ctx.fillStyle = '#fff'
        ctx.font = 'bold 24px monospace'
        ctx.fillText('GAME OVER', canvas.width/2, canvas.height/2 - 15)
        
        ctx.font = '16px monospace'
        ctx.fillStyle = '#cbd5e1'
        // Use ref for final score since useEffect re-runs on gameOver change and resets local currentScore
        ctx.fillText(`Score: ${finalScoreRef.current}`, canvas.width/2, canvas.height/2 + 15)
        
        ctx.fillStyle = '#fbbf24' // Amber
        ctx.font = 'bold 16px monospace'
        ctx.fillText('Press SPACE', canvas.width/2, canvas.height/2 + 45)
      }

      animationFrameId = requestAnimationFrame(animate)
    }

    animationFrameId = requestAnimationFrame(animate)

    return () => {
      window.removeEventListener('keydown', handleKeyPress)
      cancelAnimationFrame(animationFrameId)
    }
  }, [gameStarted, gameOver, highScore]) // Re-bind when high score updates to ensure display is correct

  return (
    <div className={`relative w-full ${className}`}>
      <canvas
        ref={canvasRef}
        className="w-full h-auto border border-border rounded-lg bg-card block shadow-inner"
        style={{ imageRendering: 'pixelated' }}
      />
    </div>
  )
}
