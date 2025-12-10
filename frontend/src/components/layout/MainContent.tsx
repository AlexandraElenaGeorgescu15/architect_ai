import { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'

interface MainContentProps {
  children: ReactNode
}

export default function MainContent({ children }: MainContentProps) {
  const location = useLocation()
  const isCanvasPage = location.pathname === '/canvas'
  
  return (
    <main className="flex-1 min-h-0 overflow-y-auto">
      <div className={`${isCanvasPage ? 'p-2' : 'p-4'} ${isCanvasPage ? 'h-full' : ''}`}>
        <div className={`glass-panel rounded-2xl shadow-2xl border border-border bg-card relative ${isCanvasPage ? 'h-full min-h-[calc(100vh-48px)]' : ''}`}>
          {/* Decorative background elements */}
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-primary/50 to-transparent opacity-50" />
          <div className="absolute -top-[200px] -right-[200px] w-[400px] h-[400px] bg-primary/10 rounded-full blur-[100px] pointer-events-none" />
          <div className="absolute -bottom-[200px] -left-[200px] w-[400px] h-[400px] bg-accent/5 rounded-full blur-[100px] pointer-events-none" />
          
          <div className="relative z-10">
            {children}
          </div>
        </div>
      </div>
    </main>
  )
}
