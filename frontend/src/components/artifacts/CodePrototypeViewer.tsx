import React, { useState, useMemo } from 'react'
import {
    Code2,
    TestTube,
    FileJson,
    FileText,
    Copy,
    Download,
    Check,
    GitBranch,
    Terminal,
    ChevronRight,
    Monitor,
    Cpu
} from 'lucide-react'
import { Artifact } from '../../types'
import { useUIStore } from '../../stores/uiStore'

interface CodePrototypeViewerProps {
    artifact: Artifact
    onUpdate?: (content: string) => Promise<void>
}

interface ParsedSections {
    plan: string
    backend: { path: string; code: string } | null
    frontend: { path: string; code: string } | null
    tests: string
}

export default function CodePrototypeViewer({ artifact }: CodePrototypeViewerProps) {
    const { addNotification } = useUIStore()
    const [activeTab, setActiveTab] = useState<'plan' | 'backend' | 'frontend' | 'tests'>('plan')
    const [copied, setCopied] = useState(false)
    const [isCommitting, setIsCommitting] = useState(false)

    const sections = useMemo<ParsedSections>(() => {
        const content = artifact.content
        const parsed: ParsedSections = {
            plan: '',
            backend: null,
            frontend: null,
            tests: ''
        }

        // Extract sections
        const planMatch = content.match(/===\s*INTEGRATION\s*PLAN\s*===\s*([\s\S]*?)\s*===/i)
        if (planMatch) parsed.plan = planMatch[1].trim()

        const backendMatch = content.match(/===\s*BACKEND\s*IMPLEMENTATION\s*===\s*([\s\S]*?)\s*===/i)
        if (backendMatch) {
            const code = backendMatch[1].trim()
            const pathMatch = code.match(/\/\/\s*File:\s*(.*)/i)
            parsed.backend = {
                path: pathMatch ? pathMatch[1].trim() : 'backend/implementation.py',
                code: code
            }
        }

        const frontendMatch = content.match(/===\s*FRONTEND\s*IMPLEMENTATION\s*===\s*([\s\S]*?)\s*===/i)
        if (frontendMatch) {
            const code = frontendMatch[1].trim()
            const pathMatch = code.match(/\/\/\s*File:\s*(.*)/i)
            parsed.frontend = {
                path: pathMatch ? pathMatch[1].trim() : 'frontend/src/component.tsx',
                code: code
            }
        }

        const testsMatch = content.match(/===\s*TESTS\s*===\s*([\s\S]*?)\s*===\s*END\s*===/i)
        if (testsMatch) parsed.tests = testsMatch[1].trim()

        // Fallback for older formats
        if (!parsed.backend && !parsed.frontend) {
            const implMatch = content.match(/===\s*IMPLEMENTATION\s*===\s*([\s\S]*?)\s*===/i)
            if (implMatch) {
                parsed.backend = {
                    path: 'implementation.py',
                    code: implMatch[1].trim()
                }
            }
        }

        return parsed
    }, [artifact.content])

    const handleCopy = async () => {
        let textToCopy = ''
        if (activeTab === 'plan') textToCopy = sections.plan
        if (activeTab === 'backend') textToCopy = sections.backend?.code || ''
        if (activeTab === 'frontend') textToCopy = sections.frontend?.code || ''
        if (activeTab === 'tests') textToCopy = sections.tests

        try {
            await navigator.clipboard.writeText(textToCopy)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
            addNotification('success', 'Copied to clipboard')
        } catch (err) {
            addNotification('error', 'Failed to copy')
        }
    }

    const handlePostToGitHub = async () => {
        setIsCommitting(true)
        try {
            const { commitArtifactToRepo } = await import('../../services/gitService')
            addNotification('info', '🤖 Agent is applying changes and pushing to GitHub...')
            const result = await commitArtifactToRepo(artifact.id)
            if (result.success) {
                addNotification('success', result.message)
                if (result.pr_url) {
                    window.open(result.pr_url, '_blank')
                }
            }
        } catch (error: any) {
            console.error('Git Commit Error:', error)
            addNotification('error', error.response?.data?.detail || 'Failed to post to GitHub')
        } finally {
            setIsCommitting(false)
        }
    }

    const currentCode = activeTab === 'plan' ? sections.plan :
        activeTab === 'backend' ? sections.backend?.code :
            activeTab === 'frontend' ? sections.frontend?.code :
                sections.tests

    return (
        <div className="flex flex-col h-full bg-card rounded-2xl border border-border overflow-hidden shadow-elevated">
            {/* Tab Navigation */}
            <div className="flex items-center justify-between px-4 py-2 bg-secondary/30 border-b border-border backdrop-blur-md">
                <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
                    <TabButton
                        active={activeTab === 'plan'}
                        onClick={() => setActiveTab('plan')}
                        icon={<FileText size={14} />}
                        label="Integration Plan"
                    />
                    {sections.backend && (
                        <TabButton
                            active={activeTab === 'backend'}
                            onClick={() => setActiveTab('backend')}
                            icon={<Cpu size={14} />}
                            label="Backend"
                        />
                    )}
                    {sections.frontend && (
                        <TabButton
                            active={activeTab === 'frontend'}
                            onClick={() => setActiveTab('frontend')}
                            icon={<Monitor size={14} />}
                            label="Frontend"
                        />
                    )}
                    <TabButton
                        active={activeTab === 'tests'}
                        onClick={() => setActiveTab('tests')}
                        icon={<TestTube size={14} />}
                        label="Tests"
                    />
                </div>

                <div className="flex items-center gap-2">
                    <button
                        onClick={handleCopy}
                        className="p-1.5 hover:bg-muted text-muted-foreground hover:text-foreground rounded-lg transition-colors flex items-center gap-1.5 text-xs font-medium"
                    >
                        {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
                        <span className="hidden sm:inline">{copied ? 'Copied' : 'Copy'}</span>
                    </button>

                    <button
                        onClick={handlePostToGitHub}
                        disabled={isCommitting}
                        className="ml-2 px-3 py-1.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-all flex items-center gap-2 text-xs font-bold shadow-lg shadow-primary/20 disabled:opacity-70"
                    >
                        <GitBranch size={14} className={isCommitting ? 'animate-spin' : ''} />
                        {isCommitting ? 'INTEGRATING...' : 'CREATE PULL REQUEST'}
                    </button>
                </div>
            </div>

            {/* Editor/Viewer Area */}
            <div className="flex-1 overflow-hidden flex flex-col relative bg-zinc-950">
                <div className="flex-none px-4 py-2 border-b border-white/5 bg-white/5 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Terminal size={12} className="text-green-500" />
                        <span className="text-[10px] font-mono text-white/40 uppercase tracking-widest">
                            {activeTab === 'plan' ? 'Integration Strategy' :
                                activeTab === 'backend' ? sections.backend?.path :
                                    activeTab === 'frontend' ? sections.frontend?.path :
                                        'Test Suite'}
                        </span>
                    </div>
                    <div className="flex gap-1">
                        <div className="w-1.5 h-1.5 rounded-full bg-white/10" />
                        <div className="w-1.5 h-1.5 rounded-full bg-white/10" />
                        <div className="w-1.5 h-1.5 rounded-full bg-white/10" />
                    </div>
                </div>

                <div className="flex-1 overflow-auto custom-scrollbar p-6">
                    <pre className="font-mono text-sm leading-relaxed text-zinc-300 whitespace-pre">
                        {activeTab === 'plan' ? (
                            <PlanHighlight plan={sections.plan} />
                        ) : (
                            <code>{currentCode}</code>
                        )}
                    </pre>
                </div>

                {/* Floating Decoration */}
                <div className="absolute top-1/2 right-4 -translate-y-1/2 pointer-events-none opacity-5">
                    <Code2 size={200} className="text-primary" />
                </div>
            </div>

            {/* Footer Info */}
            <div className="px-4 py-2 border-t border-border bg-secondary/10 flex items-center justify-between text-[10px] text-muted-foreground font-medium uppercase tracking-wider">
                <div className="flex items-center gap-4">
                    <span>{artifact.model_used || 'AI Optimized'}</span>
                    <span>•</span>
                    <span>{currentCode?.split('\n').length || 0} Lines</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-green-500 shadow-[0_0_5px_rgba(34,197,94,0.5)]" />
                    Ready to Merge
                </div>
            </div>
        </div>
    )
}

function TabButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
    return (
        <button
            onClick={onClick}
            className={`
        px-3 py-1.5 rounded-lg flex items-center gap-2 text-xs font-bold transition-all duration-300
        ${active
                    ? 'bg-primary text-primary-foreground shadow-md'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                }
      `}
        >
            {icon}
            <span>{label}</span>
        </button>
    )
}

function PlanHighlight({ plan }: { plan: string }) {
    // Simple highlighter for the plan items
    return (
        <div className="space-y-4">
            {plan.split('\n').map((line, i) => {
                if (line.startsWith('- ')) {
                    const [key, ...rest] = line.substring(2).split(':')
                    return (
                        <div key={i} className="flex gap-2">
                            <ChevronRight size={14} className="mt-1 text-primary shrink-0" />
                            <div className="flex flex-col">
                                <span className="text-primary font-bold text-xs uppercase tracking-tighter">{key}</span>
                                <span className="text-zinc-300">{rest.join(':')}</span>
                            </div>
                        </div>
                    )
                }
                return <div key={i} className="pl-6 text-zinc-400 italic text-xs">{line}</div>
            })}
        </div>
    )
}
