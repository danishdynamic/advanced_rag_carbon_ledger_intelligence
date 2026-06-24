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
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
      
      {/* Vectorized Text Chunks Card */}
      <Card className="bg-white border-slate-200 shadow-sm hover:shadow-md transition-all duration-200">
        <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
          <CardTitle className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Vectorized Text Chunks</CardTitle>
          <Server className="h-4 w-4 text-slate-400" />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold tracking-tight text-slate-900">{stats.total_indexed_chunks}</div>
          <p className="text-xs text-slate-500 mt-1">Available across pgvector layers</p>
        </CardContent>
      </Card>

      {/* Active Workers Card */}
      <Card className="bg-white border-slate-200 shadow-sm hover:shadow-md transition-all duration-200">
        <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
          <CardTitle className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Workers</CardTitle>
          <RefreshCw className={`h-4 w-4 text-amber-500 ${stats.tasks_processing > 0 ? 'animate-spin' : ''}`} />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold tracking-tight text-amber-600">{activeCount}</div>
          <p className="text-xs text-slate-500 mt-1">
            <span className="font-medium text-slate-700">{stats.tasks_processing}</span> processing, <span className="font-medium text-slate-700">{stats.tasks_pending}</span> pending
          </p>
        </CardContent>
      </Card>

      {/* Successful Ingests Card */}
      <Card className="bg-white border-slate-200 shadow-sm hover:shadow-md transition-all duration-200">
        <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
          <CardTitle className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Successful Ingests</CardTitle>
          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold tracking-tight text-emerald-600">{stats.tasks_completed}</div>
          <p className="text-xs text-slate-500 mt-1">Fully parsed compliance documents</p>
        </CardContent>
      </Card>

      {/* Pipeline Failures Card */}
      <Card className="bg-white border-slate-200 shadow-sm hover:shadow-md transition-all duration-200">
        <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
          <CardTitle className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Pipeline Failures</CardTitle>
          <AlertTriangle className="h-4 w-4 text-rose-500" />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold tracking-tight text-rose-600">{stats.tasks_failed}</div>
          <p className="text-xs text-slate-500 mt-1">Halted parsing executions</p>
        </CardContent>
      </Card>
      
    </div>
  );
}