/**
 * Comprehensive App Loading Hook
 * Tracks all data loading states to ensure UI only shows when everything is ready
 */

import { useState, useEffect, useCallback } from 'react'
import { useSystemStatus } from './useSystemStatus'
import { useArtifactStore } from '../stores/artifactStore'
import { useModelStore } from '../stores/modelStore'
import { listArtifacts } from '../services/generationService'
import api from '../services/api'

interface LoadingState {
  backend: boolean
  artifacts: boolean
  models: boolean
  versions: boolean
  routing: boolean
}

interface UseAppLoadingResult {
  isFullyLoaded: boolean
  loadingState: LoadingState
  loadingProgress: number
  loadingMessage: string
}

export function useAppLoading(): UseAppLoadingResult {
  // Use a shorter poll interval during loading for better responsiveness
  const { isReady: backendReady, status: systemStatus } = useSystemStatus(2000)
  const { artifacts, setArtifacts, setLoading: setArtifactLoading } = useArtifactStore()
  const { models, fetchModels, isLoading: modelsLoading } = useModelStore()

  const [loadingState, setLoadingState] = useState<LoadingState>({
    backend: false,
    artifacts: false,
    models: false,
    versions: false,
    routing: false,
  })

  const [versionsLoaded, setVersionsLoaded] = useState<Set<string>>(new Set())
  const [routingLoaded, setRoutingLoaded] = useState(false)

  // Load backend status
  useEffect(() => {
    setLoadingState(prev => ({ ...prev, backend: backendReady }))
  }, [backendReady])

  // Load artifacts
  const loadArtifacts = useCallback(async () => {
    if (!backendReady) return

    try {
      setArtifactLoading(true)
      setLoadingState(prev => ({ ...prev, artifacts: false }))
      console.log('📥 [APP_LOADING] Loading artifacts...')
      const loadedArtifacts = await listArtifacts()
      console.log(`✅ [APP_LOADING] Loaded ${loadedArtifacts.length} artifacts`)
      setArtifacts(loadedArtifacts)
      setLoadingState(prev => ({ ...prev, artifacts: true }))
    } catch (error) {
      console.error('❌ [APP_LOADING] Failed to load artifacts:', error)
      setLoadingState(prev => ({ ...prev, artifacts: true })) // Mark as done even on error
    } finally {
      setArtifactLoading(false)
    }
  }, [backendReady, setArtifacts, setArtifactLoading])

  // Load models
  const loadModels = useCallback(async () => {
    if (!backendReady) return

    try {
      setLoadingState(prev => ({ ...prev, models: false }))
      console.log('📥 [APP_LOADING] Loading models...')
      await fetchModels()
      console.log(`✅ [APP_LOADING] Models loaded`)
      setLoadingState(prev => ({ ...prev, models: true }))
    } catch (error) {
      console.error('❌ [APP_LOADING] Failed to load models:', error)
      setLoadingState(prev => ({ ...prev, models: true })) // Mark as done even on error
    }
  }, [backendReady, fetchModels])

  // Load routing
  const loadRouting = useCallback(async () => {
    if (!backendReady) return

    try {
      setLoadingState(prev => ({ ...prev, routing: false }))
      console.log('📥 [APP_LOADING] Loading model routing...')
      await api.get('/api/models/routing')
      console.log(`✅ [APP_LOADING] Routing loaded`)
      setLoadingState(prev => ({ ...prev, routing: true }))
      setRoutingLoaded(true)
    } catch (error) {
      console.error('❌ [APP_LOADING] Failed to load routing:', error)
      setLoadingState(prev => ({ ...prev, routing: true })) // Mark as done even on error
    }
  }, [backendReady])

  // Load versions for all artifacts
  const loadVersions = useCallback(async () => {
    if (!backendReady || artifacts.length === 0) return

    try {
      setLoadingState(prev => ({ ...prev, versions: false }))
      console.log(`📥 [APP_LOADING] Loading versions for ${artifacts.length} artifacts...`)

      const versionPromises = artifacts.map(async (artifact) => {
        try {
          await api.get(`/api/versions/${artifact.id}`)
          return artifact.id
        } catch (error) {
          // Artifact may not have versions yet, that's ok
          return artifact.id
        }
      })

      await Promise.all(versionPromises)
      setVersionsLoaded(new Set(artifacts.map(a => a.id)))
      console.log(`✅ [APP_LOADING] Versions loaded for all artifacts`)
      setLoadingState(prev => ({ ...prev, versions: true }))
    } catch (error) {
      console.error('❌ [APP_LOADING] Failed to load versions:', error)
      setLoadingState(prev => ({ ...prev, versions: true })) // Mark as done even on error
    }
  }, [backendReady, artifacts])

  // Initial load sequence
  useEffect(() => {
    if (!backendReady) {
      console.log('⏳ [APP_LOADING] Waiting for backend to be ready...')
      return
    }

    console.log('🚀 [APP_LOADING] Starting initial load sequence...')
    const loadAll = async () => {
      // Load in sequence to avoid overwhelming the backend
      await loadArtifacts()
      await loadModels()
      await loadRouting()
      // Versions will load after artifacts are loaded
    }

    loadAll().catch(error => {
      console.error('❌ [APP_LOADING] Error in load sequence:', error)
    })
  }, [backendReady, loadArtifacts, loadModels, loadRouting])

  // Load versions after artifacts are available
  useEffect(() => {
    if (loadingState.artifacts && artifacts.length > 0 && !loadingState.versions) {
      loadVersions()
    }
  }, [loadingState.artifacts, artifacts.length, loadingState.versions, loadVersions])

  // Calculate loading progress
  const loadingProgress = useCallback(() => {
    // Weights for different stages
    const WEIGHTS = {
      backend: 60,   // Backend initialization is the biggest chunk
      artifacts: 10,
      models: 10,
      routing: 10,
      versions: 10
    }

    let progress = 0

    // 1. Backend Progress
    if (loadingState.backend) {
      progress += WEIGHTS.backend
    } else if (systemStatus?.phases) {
      // Calculate partial progress based on backend phases
      const phases = Object.values(systemStatus.phases)
      if (phases.length > 0) {
        const completedCount = phases.filter((p: any) => p.status === 'complete' || p.status === 'skipped').length
        const runningCount = phases.filter((p: any) => p.status === 'running').length

        // Calculate fraction of backend phases done
        // Give 0.5 weight to running phases
        const phaseFraction = (completedCount + (runningCount * 0.5)) / phases.length

        // Apply to backend weight, capped at 95% of backend weight to ensure a jump when actually ready
        progress += Math.min(phaseFraction * WEIGHTS.backend, WEIGHTS.backend * 0.95)
      }
    }

    // 2. Application Loading Steps
    if (loadingState.artifacts) progress += WEIGHTS.artifacts
    if (loadingState.models) progress += WEIGHTS.models
    if (loadingState.routing) progress += WEIGHTS.routing
    if (loadingState.versions) progress += WEIGHTS.versions

    return Math.min(progress, 100)
  }, [loadingState, systemStatus])

  // Determine loading message
  const loadingMessage = useCallback(() => {
    if (!loadingState.backend) {
      // If we have detailed phase info, show it
      if (systemStatus?.phases) {
        const runningPhase = Object.values(systemStatus.phases).find((p: any) => p.status === 'running')
        if (runningPhase) {
          return `Initializing: ${runningPhase.title || runningPhase.name}...`
        }
      }
      return 'Initializing backend services...'
    }
    if (!loadingState.artifacts) return 'Loading artifacts...'
    if (!loadingState.models) return 'Loading models...'
    if (!loadingState.routing) return 'Loading model routing...'
    if (!loadingState.versions) return 'Loading artifact versions...'
    return 'Almost ready...'
  }, [loadingState, systemStatus])

  // Check for strict skip flag
  const skipFlag = localStorage.getItem('skip_loading_overlay') === 'true'

  // If skipped, we consider it fully loaded regardless of actual state
  const isFullyLoaded = skipFlag || Object.values(loadingState).every(Boolean)

  return {
    isFullyLoaded,
    loadingState,
    loadingProgress: loadingProgress(),
    loadingMessage: loadingMessage(),
  }
}

