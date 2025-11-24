/**
 * Code With Tests Editor
 * Shows implementation code and tests in separate tabs
 */

import { useState, useEffect } from 'react'
import { Code, TestTube, Copy, Download, Check, Play, AlertCircle } from 'lucide-react'
import { useArtifactStore } from '../stores/artifactStore'
import { useUIStore } from '../stores/uiStore'

interface ParsedCode {
  implementation: string
  tests: string
  hasTests: boolean
}

/**
 * Parse code prototype content into implementation and tests
 */
function parseCodePrototype(content: string): ParsedCode {
  // Try to parse structured output
  const implMatch = content.match(/===\s*IMPLEMENTATION\s*===\s*([\s\S]*?)\s*===\s*TESTS\s*===/i)
  const testsMatch = content.match(/===\s*TESTS\s*===\s*([\s\S]*?)\s*===\s*END\s*===/i)

  if (implMatch && testsMatch) {
    return {
      implementation: implMatch[1].trim(),
      tests: testsMatch[1].trim(),
      hasTests: true,
    }
  }

  // Fallback: Try to detect test files based on common patterns
  const lines = content.split('\n')
  let inTestSection = false
  let implementationLines: string[] = []
  let testLines: string[] = []

  for (const line of lines) {
    // Detect test file markers
    if (
      line.includes('test.ts') ||
      line.includes('test.js') ||
      line.includes('test.py') ||
      line.includes('Test.cs') ||
      line.includes('_test.') ||
      line.includes('.spec.') ||
      line.includes('describe(') ||
      line.includes('it(') ||
      line.includes('test(') ||
      line.includes('[Test]') ||
      line.includes('[Fact]')
    ) {
      inTestSection = true
    }

    if (inTestSection) {
      testLines.push(line)
    } else {
      implementationLines.push(line)
    }
  }

  // If we found distinct sections
  if (testLines.length > 5) {
    return {
      implementation: implementationLines.join('\n').trim(),
      tests: testLines.join('\n').trim(),
      hasTests: true,
    }
  }

  // No tests found - return all as implementation
  return {
    implementation: content.trim(),
    tests: '// No tests found in the generated code\n// Tests should be generated automatically',
    hasTests: false,
  }
}

export default function CodeWithTestsEditor() {
  const { artifacts } = useArtifactStore()
  const { addNotification } = useUIStore()

  const [selectedTab, setSelectedTab] = useState<'implementation' | 'tests'>('implementation')
  const [copiedTab, setCopiedTab] = useState<string | null>(null)

  // Get code prototype artifacts
  const codeArtifacts = artifacts.filter((a) => a.type === 'code_prototype')
  const latestCode = codeArtifacts[0] || null

  // Parse code
  const parsedCode: ParsedCode = latestCode
    ? parseCodePrototype(latestCode.content)
    : { implementation: '', tests: '', hasTests: false }

  // Auto-select tests tab if tests are available
  useEffect(() => {
    if (parsedCode.hasTests && selectedTab === 'implementation') {
      // Don't auto-switch, let user control
    }
  }, [parsedCode.hasTests])

  /**
   * Copy code to clipboard
   */
  const handleCopy = async (tab: 'implementation' | 'tests') => {
    const code = tab === 'implementation' ? parsedCode.implementation : parsedCode.tests

    try {
      await navigator.clipboard.writeText(code)
      setCopiedTab(tab)
      setTimeout(() => setCopiedTab(null), 2000)
      addNotification({
        type: 'success',
        message: `${tab === 'implementation' ? 'Implementation' : 'Tests'} copied to clipboard!`,
      })
    } catch (error) {
      addNotification({
        type: 'error',
        message: 'Failed to copy to clipboard',
      })
    }
  }

  /**
   * Download code as file
   */
  const handleDownload = (tab: 'implementation' | 'tests') => {
    const code = tab === 'implementation' ? parsedCode.implementation : parsedCode.tests
    const filename =
      tab === 'implementation'
        ? 'implementation.ts' // Default to .ts, could be smarter
        : 'implementation.test.ts'

    const blob = new Blob([code], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    addNotification({
      type: 'success',
      message: `Downloaded ${filename}`,
    })
  }

  // Empty state
  if (!latestCode) {
    return (
      <div className="h-full flex items-center justify-center bg-background">
        <div className="text-center max-w-md">
          <Code className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-50" />
          <p className="text-lg font-medium text-muted-foreground mb-2">No code prototype available</p>
          <p className="text-sm text-muted-foreground">
            Generate a code prototype to see implementation and tests here
          </p>
        </div>
      </div>
    )
  }

  const currentCode =
    selectedTab === 'implementation' ? parsedCode.implementation : parsedCode.tests

  return (
    <div className="h-full flex flex-col bg-card">
      {/* Header with tabs */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2 bg-secondary/20">
        <div className="flex items-center gap-2">
          {/* Tab buttons */}
          <button
            onClick={() => setSelectedTab('implementation')}
            className={`px-4 py-2 rounded-md text-sm font-medium flex items-center gap-2 transition-all ${
              selectedTab === 'implementation'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'bg-background text-muted-foreground hover:text-foreground hover:bg-secondary'
            }`}
          >
            <Code size={16} />
            Implementation
          </button>
          <button
            onClick={() => setSelectedTab('tests')}
            className={`px-4 py-2 rounded-md text-sm font-medium flex items-center gap-2 transition-all ${
              selectedTab === 'tests'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'bg-background text-muted-foreground hover:text-foreground hover:bg-secondary'
            }`}
          >
            <TestTube size={16} />
            Tests
            {parsedCode.hasTests && (
              <span className="ml-1 px-1.5 py-0.5 bg-green-500 text-white text-xs rounded-full">
                ✓
              </span>
            )}
          </button>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleCopy(selectedTab)}
            className="px-3 py-1.5 rounded-md text-sm font-medium flex items-center gap-1.5 bg-background text-muted-foreground hover:text-foreground hover:bg-secondary transition-all"
            title="Copy to clipboard"
          >
            {copiedTab === selectedTab ? (
              <>
                <Check size={14} />
                Copied!
              </>
            ) : (
              <>
                <Copy size={14} />
                Copy
              </>
            )}
          </button>
          <button
            onClick={() => handleDownload(selectedTab)}
            className="px-3 py-1.5 rounded-md text-sm font-medium flex items-center gap-1.5 bg-background text-muted-foreground hover:text-foreground hover:bg-secondary transition-all"
            title="Download file"
          >
            <Download size={14} />
            Download
          </button>
        </div>
      </div>

      {/* Warning banner if no tests */}
      {!parsedCode.hasTests && selectedTab === 'tests' && (
        <div className="px-4 py-3 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-amber-900 dark:text-amber-100">
              No tests detected
            </p>
            <p className="text-xs text-amber-700 dark:text-amber-300 mt-1">
              Tests should be generated automatically with code prototypes. Try regenerating this
              artifact.
            </p>
          </div>
        </div>
      )}

      {/* Code display */}
      <div className="flex-1 overflow-auto bg-background">
        <pre className="p-4 text-sm font-mono leading-relaxed">
          <code className="text-foreground">{currentCode || '// No code available'}</code>
        </pre>
      </div>

      {/* Footer info */}
      <div className="px-4 py-2 border-t border-border bg-secondary/10 flex items-center justify-between text-xs">
        <div className="flex items-center gap-4 text-muted-foreground">
          <span>
            {selectedTab === 'implementation' ? 'Implementation Code' : 'Test Suite'}
          </span>
          <span>•</span>
          <span>{currentCode.split('\n').length} lines</span>
        </div>
        {parsedCode.hasTests && (
          <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
            <TestTube size={12} />
            <span className="font-medium">Tests included</span>
          </div>
        )}
      </div>
    </div>
  )
}

