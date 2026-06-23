import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Server, RefreshCw, CheckCircle2, AlertTriangle } from 'lucide-react'

interface DashboardStatsProps {
  stats: {
    total_indexed_chunks: number
    tasks_pending: number
    tasks_processing: number
    tasks_completed: number
    tasks_failed: number
  }
}

export function DashboardStats({ stats }: DashboardStatsProps) {
  const activeCount = stats.tasks_processing + stats.tasks_pending

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <Card className="bg-neutral-900 border-neutral-800 shadow-xl">
        <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
          <CardTitle className="text-xs font-medium text-neutral-400 uppercase tracking-wider">Vectorized Text Chunks</CardTitle>
          <Server className="h-4 w-4 text-emerald-400" />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold tracking-tight text-neutral-100">{stats.total_indexed_chunks}</div>
          <p className="text-xs text-neutral-400 mt-1">Available across pgvector layers</p>
        </CardContent>
      </Card>

      <Card className="bg-neutral-900 border-neutral-800 shadow-xl">
        <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
          <CardTitle className="text-xs font-medium text-neutral-400 uppercase tracking-wider">Active Workers</CardTitle>
          <RefreshCw className={`h-4 w-4 text-amber-400 ${stats.tasks_processing > 0 ? 'animate-spin' : ''}`} />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold tracking-tight text-amber-400">{activeCount}</div>
          <p className="text-xs text-neutral-400 mt-1">{stats.tasks_processing} processing, {stats.tasks_pending} pending</p>
        </CardContent>
      </Card>

      <Card className="bg-neutral-900 border-neutral-800 shadow-xl">
        <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
          <CardTitle className="text-xs font-medium text-neutral-400 uppercase tracking-wider">Successful Ingests</CardTitle>
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold tracking-tight text-emerald-400">{stats.tasks_completed}</div>
          <p className="text-xs text-neutral-400 mt-1">Fully parsed documents</p>
        </CardContent>
      </Card>

      <Card className="bg-neutral-900 border-neutral-800 shadow-xl">
        <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
          <CardTitle className="text-xs font-medium text-neutral-400 uppercase tracking-wider">Pipeline Failures</CardTitle>
          <AlertTriangle className="h-4 w-4 text-rose-400" />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold tracking-tight text-rose-500">{stats.tasks_failed}</div>
          <p className="text-xs text-neutral-400 mt-1">Halted parsing executions</p>
        </CardContent>
      </Card>
    </div>
  )
}