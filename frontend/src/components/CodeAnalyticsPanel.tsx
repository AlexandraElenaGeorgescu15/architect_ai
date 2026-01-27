import { useState } from 'react'
import { clusterProjectCode, ClusterResult } from '../services/mlService'
import { Brain, RefreshCw, Loader2, Code as CodeIcon, BarChart3, Binary, ScatterChart } from 'lucide-react'

export default function CodeAnalyticsPanel() {
    const [loading, setLoading] = useState(false)
    const [data, setData] = useState<ClusterResult | null>(null)
    const [filesAnalyzed, setFilesAnalyzed] = useState(0)
    const [error, setError] = useState<string | null>(null)

    const handleAnalyze = async () => {
        setLoading(true)
        setError(null)
        try {
            const response = await clusterProjectCode({ n_clusters: 5, max_files: 50 })
            if (response.success) {
                setData(response.result)
                setFilesAnalyzed(response.files_analyzed)
            } else {
                setError(response.message || 'Analysis failed')
            }
        } catch (err: any) {
            setError(err.message || 'Failed to connect to ML service')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
                        <Brain className="w-5 h-5 text-purple-500" />
                        ML Code Clustering
                    </h3>
                    <p className="text-sm text-muted-foreground">
                        Uses Scikit-Learn (K-Means) to group code files by complexity and structure.
                    </p>
                </div>
                <button
                    onClick={handleAnalyze}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50"
                >
                    {loading ? (
                        <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Analyzing...
                        </>
                    ) : (
                        <>
                            <ScatterChart className="w-4 h-4" />
                            Cluster Code
                        </>
                    )}
                </button>
            </div>

            {error && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-500 text-sm">
                    {error}
                </div>
            )}

            {data && (
                <div className="space-y-6 animate-in fade-in duration-500">
                    <div className="flex items-center gap-4 text-sm text-muted-foreground bg-card/50 p-3 rounded-lg border border-border/50">
                        <div className="flex items-center gap-2">
                            <Binary className="w-4 h-4" />
                            <span>Files Analyzed: <span className="font-mono text-foreground">{filesAnalyzed}</span></span>
                        </div>
                        <div className="h-4 w-px bg-border" />
                        <div className="flex items-center gap-2">
                            <BarChart3 className="w-4 h-4" />
                            <span>Clusters Found: <span className="font-mono text-foreground">{data.n_clusters}</span></span>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {Object.entries(data.cluster_stats).map(([clusterId, stats]) => (
                            <div
                                key={clusterId}
                                className="bg-card/40 border border-border/50 rounded-xl p-5 hover:border-purple-500/30 transition-all group"
                            >
                                <div className="flex items-start justify-between mb-4">
                                    <div className="w-8 h-8 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-500 font-bold text-sm">
                                        {clusterId}
                                    </div>
                                    <div className="text-xs px-2 py-1 bg-background/50 rounded border border-border text-muted-foreground">
                                        {stats.size} files
                                    </div>
                                </div>

                                <div className="space-y-3">
                                    <div>
                                        <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Avg Complexity</div>
                                        <div className="text-xl font-mono text-foreground">
                                            {stats.avg_complexity.toFixed(1)}
                                        </div>
                                    </div>

                                    <div>
                                        <div className="text-xs text-muted-foreground uppercase tracking-wider mb-2">Representative Files</div>
                                        <div className="flex flex-wrap gap-1.5">
                                            {stats.samples.slice(0, 3).map((file, i) => (
                                                <span key={i} className="inline-flex items-center gap-1 px-2 py-1 rounded bg-background/80 border border-border text-[10px] font-mono text-foreground truncate max-w-full">
                                                    <CodeIcon className="w-3 h-3 text-purple-500/70" />
                                                    {file}
                                                </span>
                                            ))}
                                            {stats.samples.length > 3 && (
                                                <span className="text-[10px] text-muted-foreground self-center">
                                                    +{stats.samples.length - 3} more
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}
