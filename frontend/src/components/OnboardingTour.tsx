import { useEffect, useMemo, useState } from 'react'
import { BookOpenCheck, ChevronRight, SkipForward, X, RefreshCcw } from 'lucide-react'

const STORAGE_KEY = 'architect_ai_onboarding_complete'

interface TourStep {
  id: string
  title: string
  description: string
  highlightSelector?: string
}

const TOUR_STEPS: TourStep[] = [
  {
    id: 'meeting-notes',
    title: '1. Add Meeting Notes',
    description: 'Start by capturing your project requirements in the Meeting Notes panel on the left. You can type directly, paste text, or upload files (.txt, .md, .pdf). Architect.AI automatically organizes your notes into folders based on content - think "database", "authentication", "frontend", etc. This structured approach keeps large projects tidy and makes it easy to generate context-aware artifacts later.',
    highlightSelector: '[data-tour="meeting-notes-panel"]',
  },
  {
    id: 'build-generate',
    title: '2. Build Context & Generate Artifacts',
    description: 'Click "Build Context" to activate Architect.AI\'s 5-layer intelligence system: (1) RAG pulls relevant code from your project, (2) Knowledge Graph maps your architecture, (3) Pattern Mining detects design patterns, (4) Meeting Notes provide requirements, and (5) AI Analysis ties it all together. Then select any artifact type (ERD, architecture diagram, code, API docs, etc.) and click "Generate" - your artifact will be ready in seconds, fully tailored to YOUR project.',
    highlightSelector: '[data-tour="generate-primary"]',
  },
  {
    id: 'outputs',
    title: '3. Review & Refine Outputs',
    description: 'All generated artifacts appear in the Outputs panel on the right. Click any artifact to open the interactive viewer where you can preview diagrams (with live rendering for Mermaid), edit code, download files, or provide feedback. Use the feedback system to rate artifacts - thumbs up/down with comments help the AI learn your preferences. Filter artifacts by type, search by name, or sort by date to quickly find what you need.',
    highlightSelector: '[data-tour="artifacts-panel"]',
  },
  {
    id: 'intelligence',
    title: '4. Iterate with AI Intelligence',
    description: 'Visit the Intelligence page to see your project\'s "brain": view the Knowledge Graph (class/function relationships), explore Pattern Mining results (design patterns, code smells, security issues), manage training data, and configure model routing. Use "Ask AI" for quick questions about your codebase. The AI continuously learns from your feedback - every thumbs up/down trains the model to generate better artifacts for YOUR specific architecture and coding style.',
  },
]

export default function OnboardingTour() {
  const [hasCompleted, setHasCompleted] = useState(
    () => typeof window !== 'undefined' && localStorage.getItem(STORAGE_KEY) === 'true'
  )
  const [isOpen, setIsOpen] = useState(!hasCompleted)
  const [currentStep, setCurrentStep] = useState(0)

  useEffect(() => {
    setIsOpen(!hasCompleted)
  }, [hasCompleted])

  // Listen for replay onboarding event
  useEffect(() => {
    const handleReplay = () => {
      setHasCompleted(false)
      setCurrentStep(0)
      setIsOpen(true)
      localStorage.removeItem(STORAGE_KEY)
    }

    window.addEventListener('replay-onboarding', handleReplay)
    return () => window.removeEventListener('replay-onboarding', handleReplay)
  }, [])

  useEffect(() => {
    if (!isOpen) {
      return
    }

    const selector = TOUR_STEPS[currentStep]?.highlightSelector
    if (!selector) {
      return
    }

    const element = document.querySelector<HTMLElement>(selector)
    if (!element) {
      return
    }

    const originalOutline = element.style.outline
    const originalOutlineOffset = element.style.outlineOffset

    element.style.outline = '2px solid rgba(0, 154, 217, 0.8)'
    element.style.outlineOffset = '4px'
    element.style.boxShadow = '0 0 20px rgba(0, 154, 217, 0.5)'

    return () => {
      element.style.outline = originalOutline
      element.style.outlineOffset = originalOutlineOffset
      element.style.boxShadow = ''
    }
  }, [currentStep, isOpen])

  const handleSkip = () => {
    setIsOpen(false)
    setHasCompleted(true)
    localStorage.setItem(STORAGE_KEY, 'true')
  }

  const handleNext = () => {
    if (currentStep === TOUR_STEPS.length - 1) {
      handleSkip()
    } else {
      setCurrentStep((prev) => prev + 1)
    }
  }

  const handleRestart = () => {
    setHasCompleted(false)
    setCurrentStep(0)
    setIsOpen(true)
    localStorage.removeItem(STORAGE_KEY)
  }

  if (!isOpen) {
    return null
  }

  const step = TOUR_STEPS[currentStep]

  return (
    <>
      {/* Overlay - greyed out background */}
      <div 
        className="fixed inset-0 z-[99] bg-black/60 backdrop-blur-sm animate-fade-in"
        onClick={handleSkip}
      />
      
      {/* Centered tour modal */}
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 pointer-events-none">
        <div className="max-w-2xl w-full glass-panel border-2 border-primary/20 rounded-2xl shadow-2xl p-8 space-y-6 animate-scale-in backdrop-blur-xl bg-card pointer-events-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary/20 border border-primary/30 rounded-full flex items-center justify-center animate-pulse-glow">
                <BookOpenCheck className="w-5 h-5 text-primary" />
              </div>
              <p className="text-sm font-bold uppercase tracking-widest text-primary">
                Quick Tour
              </p>
            </div>
            <button
              type="button"
              onClick={handleSkip}
              className="text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all duration-200 p-2 rounded-full group"
              title="Skip tour"
            >
              <X className="w-5 h-5 group-hover:rotate-90 transition-transform duration-300" />
            </button>
          </div>

          <div>
            <h3 className="text-2xl font-bold text-foreground mb-4">{step.title}</h3>
            <p className="text-base text-muted-foreground leading-relaxed">{step.description}</p>
          </div>

          <div className="w-full bg-border/50 h-3 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-primary to-accent transition-all duration-500 shadow-md shadow-primary/30"
              style={{ width: `${((currentStep + 1) / TOUR_STEPS.length) * 100}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-sm text-muted-foreground pt-2">
            <div className="font-mono font-semibold px-3 py-2 bg-primary/10 rounded-lg border border-primary/20">
              Step {currentStep + 1} / {TOUR_STEPS.length}
            </div>
            <button
              type="button"
              onClick={handleRestart}
              className="flex items-center gap-2 text-sm text-primary hover:text-accent transition-colors font-medium px-3 py-2 hover:bg-primary/10 rounded-lg"
            >
              <RefreshCcw className="w-4 h-4" />
              Restart
            </button>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={handleSkip}
              className="flex-1 py-3 bg-border/50 hover:bg-border text-foreground rounded-xl transition-all duration-300 flex items-center justify-center gap-2 font-bold hover:scale-105 active:scale-95"
            >
              <SkipForward className="w-4 h-4" />
              Skip Tour
            </button>
            <button
              type="button"
              onClick={handleNext}
              className="flex-1 py-3 bg-primary hover:bg-primary/90 text-primary-foreground rounded-xl transition-all duration-300 flex items-center justify-center gap-2 font-bold shadow-lg shadow-primary/30 hover:scale-105 active:scale-95"
            >
              {currentStep === TOUR_STEPS.length - 1 ? 'Finish Tour' : 'Next Step'}
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
