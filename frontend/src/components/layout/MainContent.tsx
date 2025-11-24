import { ReactNode } from 'react'

interface MainContentProps {
  children: ReactNode
}

export default function MainContent({ children }: MainContentProps) {
  return (
    <main className="flex-1 overflow-y-auto custom-scrollbar h-full">
      <div className="max-w-full mx-auto h-full p-6">
        <div className="glass-panel rounded-2xl h-full overflow-y-auto custom-scrollbar shadow-2xl border border-border bg-card relative flex flex-col">
            {/* Decorative background elements */}
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-primary/50 to-transparent opacity-50" />
            <div className="absolute -top-[200px] -right-[200px] w-[400px] h-[400px] bg-primary/10 rounded-full blur-[100px] pointer-events-none" />
            <div className="absolute -bottom-[200px] -left-[200px] w-[400px] h-[400px] bg-accent/5 rounded-full blur-[100px] pointer-events-none" />
            
            <div className="relative z-10 h-full overflow-y-auto custom-scrollbar">
              {children}
            </div>
        </div>
      </div>
    </main>
  )
}
