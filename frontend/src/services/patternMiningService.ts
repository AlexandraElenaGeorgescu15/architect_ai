import api from './api'

export interface PatternSummary {
  name: string
  pattern_type: string
  description: string
  frequency: number
  severity: string
  files: string[]
  suggestions: string[]
}

export interface CodeSmellSummary {
  smell_type: string
  location: string
  severity: string
  description: string
  suggestion: string
}

export interface SecurityIssueSummary {
  issue_type: string
  location: string
  severity: string
  description: string
  recommendation: string
}

export interface PatternReport {
  analysis_id: string
  project_root: string
  patterns: PatternSummary[]
  code_smells: CodeSmellSummary[]
  security_issues: SecurityIssueSummary[]
  metrics: Record<string, number | Record<string, number>>
  recommendations: string[]
  code_quality_score: number
  created_at: string
}

export interface PatternAnalysisRequest {
  project_root?: string
  include_design_patterns?: boolean
  include_anti_patterns?: boolean
  include_code_smells?: boolean
  cache_key?: string
}

/**
 * Run pattern analysis against the active project.
 */
export async function analyzePatterns(request: PatternAnalysisRequest = {}): Promise<PatternReport> {
  const response = await api.post('/api/analysis/patterns', request)
  const data = response.data as Record<string, unknown>

  if (data && typeof data === 'object' && 'analysis' in data) {
    return (data.analysis ?? {}) as PatternReport
  }

  return (data ?? {}) as PatternReport
}

