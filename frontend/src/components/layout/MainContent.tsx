import { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'

interface MainContentProps {
  children: ReactNode
}

export default function MainContent({ children }: MainContentProps) {
  const location = useLocation()
  const isCanvasPage = location.pathname === '/canvas'
  
  // All pages should constrain to viewport height to prevent oversized content
  // Canvas gets minimal padding, other pages get standard padding
  const padding = isCanvasPage ? 'p-2' : 'p-4'
  
  return (
    <main className="flex-1 min-h-0 h-full overflow-hidden">
      <div className={`${padding} h-full flex flex-col overflow-hidden`}>
        <div className="glass-panel rounded-2xl shadow-2xl border border-border bg-card relative overflow-hidden flex-1 min-h-0 flex flex-col">
          {/* Decorative background elements - contained within bounds */}
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-primary/50 to-transparent opacity-50" />
          <div className="absolute -top-[200px] right-0 w-[400px] h-[400px] bg-primary/10 rounded-full blur-[100px] pointer-events-none opacity-50" />
          <div className="absolute -bottom-[200px] left-0 w-[400px] h-[400px] bg-accent/5 rounded-full blur-[100px] pointer-events-none opacity-50" />
          
          <div className="relative z-10 h-full overflow-y-auto overflow-x-hidden custom-scrollbar flex-1 min-h-0">
            {children}
          </div>
        </div>
      </div>
    </main>
  )
}
