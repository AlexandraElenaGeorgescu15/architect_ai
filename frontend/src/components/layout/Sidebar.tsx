import { Link, useLocation } from 'react-router-dom'
import { 
  LayoutDashboard, 
  Brain, 
  FileCode,
  Activity,
  Sparkles,
  Moon,
  Sun
} from 'lucide-react'
import { useModelStore } from '../../stores/modelStore'
import { useTrainingStore } from '../../stores/trainingStore'
import { useWebSocketStatus } from '../../hooks/useWebSocket'
import { useUIStore } from '../../stores/uiStore'
import { useState, useEffect } from 'react'

const navigation = [
  { name: 'Studio', href: '/studio', icon: LayoutDashboard },
  { name: 'Intelligence', href: '/intelligence', icon: Brain },
  { name: 'Canvas', href: '/canvas', icon: FileCode },
]

export default function Sidebar() {
  const location = useLocation()
  const { models } = useModelStore()
  const { getActiveJobs } = useTrainingStore()
  const { isConnected } = useWebSocketStatus()
  const { darkMode, toggleDarkMode, sidebarOpen, setSidebarOpen } = useUIStore()
  const [ragStatus, setRagStatus] = useState<'indexed' | 'indexing' | 'not_indexed'>('indexed')

  // Force layout to match darkMode state on mount
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [darkMode])

  const activeJobs = getActiveJobs()
  const ollamaModels = models.filter(m => m.provider === 'ollama')
  const cloudModels = models.filter(m => m.provider !== 'ollama' && m.status === 'available')

  useEffect(() => {
    setRagStatus('indexed')
  }, [])

  const handleReplayTour = () => {
    localStorage.removeItem('architect_ai_onboarding_complete')
    window.dispatchEvent(new CustomEvent('replay-onboarding'))
  }

  return (
    <>
      {/* Mobile Overlay */}
      <div 
        className={`fixed inset-0 bg-background/80 backdrop-blur-sm z-40 lg:hidden transition-opacity duration-300 ${
          sidebarOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
        onClick={() => setSidebarOpen(false)}
      />

      <aside 
        className={`
          fixed lg:relative inset-y-0 left-0 z-50
          h-full glass-panel rounded-r-2xl lg:rounded-2xl flex flex-col border-r border-border shadow-2xl bg-card
          transition-all duration-500 ease-in-out
          ${sidebarOpen ? 'w-72 translate-x-0 opacity-100' : 'w-0 -translate-x-full lg:w-72 lg:translate-x-0 lg:opacity-100 pointer-events-none lg:pointer-events-auto'}
        `}
      >
        <div className={`w-72 h-full flex flex-col transition-all duration-500 ${sidebarOpen ? 'opacity-100' : 'opacity-0 lg:opacity-100'}`}>
          {/* Header */}
          <div className="p-8 border-b border-border/50 relative overflow-hidden group flex-shrink-0 bg-gradient-to-br from-primary/5 to-transparent">
        <div className="absolute inset-0 bg-primary/10 opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
        <div className="relative flex items-center gap-3 mb-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center border border-primary/30 shadow-lg group-hover:shadow-[0_0_25px_rgba(37,99,235,0.4)] transition-all duration-500 group-hover:scale-110">
            <Sparkles className="w-7 h-7 text-primary animate-pulse" />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight text-foreground">
              Architect<span className="bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">.AI</span>
            </h1>
          </div>
        </div>
        <div className="flex items-center gap-2 pl-1 text-xs font-mono text-muted-foreground font-bold">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.8)] animate-pulse' : 'bg-destructive'}`} />
          <span>SYSTEM</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2 mt-2 overflow-auto custom-scrollbar">
        <p className="px-4 text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-3">Main Menu</p>
        {navigation.map((item) => {
          const Icon = item.icon
          const isActive = location.pathname === item.href
          return (
            <Link
              key={item.name}
              to={item.href}
              className={`
                flex items-center gap-4 px-4 py-4 rounded-xl transition-all duration-500 group relative overflow-hidden
                ${isActive 
                  ? 'text-primary shadow-md' 
                  : 'text-muted-foreground hover:text-foreground'
                }
              `}
            >
              {/* Active Background */}
              {isActive && (
                <div className="absolute inset-0 bg-gradient-to-r from-primary/15 to-primary/5 border border-primary/30 rounded-xl shadow-inner" />
              )}
              {/* Hover Background */}
              {!isActive && (
                <div className="absolute inset-0 bg-foreground/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-xl" />
              )}
              
              <Icon className={`w-5 h-5 relative z-10 transition-all duration-300 group-hover:scale-125 ${isActive ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'}`} />
              <span className="font-bold tracking-wide text-sm relative z-10">{item.name}</span>
              {isActive && <div className="ml-auto w-2 h-2 rounded-full bg-primary shadow-[0_0_12px_rgba(37,99,235,0.8)] relative z-10 animate-pulse" />}
            </Link>
          )
        })}
      </nav>

      {/* System Status Section */}
      <div className="p-6 mx-4 mb-6 rounded-2xl bg-gradient-to-br from-secondary/30 to-secondary/10 border border-border/50 backdrop-blur-sm shadow-lg hover:shadow-xl transition-shadow duration-300">
        <div className="flex items-center justify-between mb-5">
          <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest">System Status</span>
          <Activity className="w-4 h-4 text-primary animate-pulse" />
        </div>
        
        <div className="space-y-5">
          {/* RAG Status */}
          <div className="space-y-2">
            <div className="flex justify-between text-[10px] text-muted-foreground font-mono font-bold">
              <span>RAG INDEX</span>
              <span className="text-green-500 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.6)]" />
                READY
              </span>
            </div>
            <div className="w-full bg-muted rounded-full h-2 overflow-hidden shadow-inner">
              <div className="h-full w-full bg-gradient-to-r from-primary to-primary/80 shadow-[0_0_12px_rgba(37,99,235,0.6)] animate-pulse" />
            </div>
          </div>

          {/* Theme Toggle */}
          <button
            onClick={() => toggleDarkMode()}
            className="w-full flex items-center justify-between px-4 py-3 rounded-xl bg-background/50 border border-border/50 hover:bg-background hover:border-primary/30 hover:shadow-md transition-all duration-300 group"
          >
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest group-hover:text-primary transition-colors">Theme Mode</span>
            {darkMode ? (
              <Moon className="w-5 h-5 text-primary group-hover:rotate-12 transition-transform duration-300" />
            ) : (
              <Sun className="w-5 h-5 text-accent group-hover:rotate-90 transition-transform duration-300" />
            )}
          </button>

          <button 
            onClick={handleReplayTour}
            className="w-full text-[10px] text-muted-foreground hover:text-primary transition-all duration-300 text-center uppercase tracking-widest hover:underline font-bold py-2"
          >
            🎓 Replay Onboarding
          </button>
        </div>
      </div>
        </div>
    </aside>
    </>
  )
}
