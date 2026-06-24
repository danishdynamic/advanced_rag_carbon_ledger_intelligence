import { useState, useRef, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { toast } from 'sonner'
import { UploadCloud, FileText, Loader2, CheckCircle2, AlertCircle } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { motion, AnimatePresence } from 'framer-motion'

export interface IngestionTask {
  id: string
  fileName: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
}

interface DocumentManagerProps {
  onUploadSuccess: () => void
}

export function DocumentManager({ onUploadSuccess }: DocumentManagerProps) {
  const [activeTasks, setActiveTasks] = useState<IngestionTask[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // 🎯 Fix: Active status polling mechanism for pending/processing tasks
  useEffect(() => {
    const incompleteTasks = activeTasks.filter(t => t.status === 'pending' || t.status === 'processing')
    if (incompleteTasks.length === 0) return

    const pollInterval = setInterval(async () => {
      try {
        // Fetch fresh pipeline statuses for all incomplete ingestion tasks
        const updatedTasks = await Promise.all(
          activeTasks.map(async (task) => {
            if (task.status === 'completed' || task.status === 'failed') return task

            try {
              const { data } = await apiClient.get(`/api/documents/tasks/${task.id}`)
              return {
                ...task,
                status: data.status, // 'processing', 'completed', etc.
                progress: data.progress ?? (data.status === 'completed' ? 100 : 50)
              }
            } catch {
              return task // Fallback to current state if a single task lookup slips
            }
          })
        )

        setActiveTasks(updatedTasks)

        // If a task just crossed the finish line, update global dashboard stats
        const anyJustFinished = updatedTasks.some((t, i) => t.status === 'completed' && activeTasks[i]?.status !== 'completed')
        if (anyJustFinished) {
          onUploadSuccess()
        }
      } catch (err) {
    console.error('Error updating processing stream telemetries:', err)
      }
    }, 3000) // Poll background worker records every 3 seconds

    return () => clearInterval(pollInterval)
  }, [activeTasks, onUploadSuccess])

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const nameLower = file.name.toLowerCase()
    if (!nameLower.endsWith('.pdf') && !nameLower.endsWith('.txt')) {
      toast.error('Unsupported file format. Please upload a .pdf or .txt file.')
      return
    }

    const formData = new FormData()
    formData.append('file', file)

    setIsUploading(true)
    const toastId = toast.loading(`Uploading ${file.name} to background parser...`)

    try {
      const { data } = await apiClient.post('/api/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      toast.success(`${file.name} queued successfully!`, { id: toastId })
      
      setActiveTasks((prev) => [
        { id: data.task_id, fileName: data.file_name || file.name, status: 'pending', progress: 15 },
        ...prev
      ])
      
      onUploadSuccess()
    } catch (error: any) {
      const fallbackMsg = error.response?.data?.detail || 'File transmission infrastructure failure.'
      toast.error(fallbackMsg, { id: toastId })
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Upload Column Dropzone */}
      <div className="lg:col-span-1">
        <Card className="bg-white border-zinc-200 shadow-sm rounded-2xl">
          <CardHeader className="pb-4">
            <CardTitle className="text-base font-bold text-zinc-800">Ingest New Regulations</CardTitle>
            <CardDescription className="text-zinc-500 text-xs leading-relaxed">
              Submit compliance documentation. Gemini Multi-format vision layer processes layout extractions out-of-band.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <input 
                type="file" 
                ref={fileInputRef} 
                onChange={handleFileUpload} 
                className="hidden" 
                accept=".pdf,.txt" 
                disabled={isUploading} 
                aria-label="Upload regulatory corporate report" 
                />
            <div
              onClick={() => !isUploading && fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-6 text-center flex flex-col items-center justify-center gap-3 cursor-pointer transition-all ${
                isUploading 
                  ? 'border-zinc-200 bg-zinc-50/50 opacity-60 cursor-not-allowed' 
                  : 'border-zinc-200 hover:border-emerald-500/40 hover:bg-emerald-50/30 bg-zinc-50/50'
              }`}
            >
              <div className="p-3 bg-white border border-zinc-200 rounded-xl shadow-xs text-zinc-400">
                {isUploading ? (
                  <Loader2 className="h-5 w-5 text-emerald-600 animate-spin" />
                ) : (
                  <UploadCloud className="h-5 w-5 text-emerald-600" />
                )}
              </div>
              <div>
                <p className="text-xs font-semibold text-zinc-700">Click to locate corporate report</p>
                <p className="text-[11px] text-zinc-400 mt-0.5">Accepts structural PDF layouts and plain-text files</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Active Pipeline List Status Tracker */}
      <div className="lg:col-span-2">
        <Card className="bg-white border-zinc-200 h-full shadow-sm rounded-2xl">
          <CardHeader className="pb-4">
            <CardTitle className="text-base font-bold text-zinc-800">Background Worker Job Ingest Streams</CardTitle>
            <CardDescription className="text-zinc-500 text-xs leading-relaxed">
              Live asynchronous extraction, vision matrix parsing, and semantic chunking threads.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {activeTasks.length === 0 ? (
              <div className="h-36 border border-dashed border-zinc-200 rounded-xl flex flex-col items-center justify-center text-xs text-zinc-400 gap-2 bg-zinc-50/30">
                <FileText className="w-5 h-5 text-zinc-300" />
                No files submitted during this session.
              </div>
            ) : (
              <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
                <AnimatePresence initial={false}>
                  {activeTasks.map((task) => (
                    <motion.div 
                      key={task.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      className="p-3.5 bg-white border border-zinc-200 rounded-xl space-y-2.5 shadow-2xs"
                    >
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-zinc-700 truncate max-w-[70%]">📄 {task.fileName}</span>
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wide border ${
                          task.status === 'completed' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                          task.status === 'failed' ? 'bg-rose-50 text-rose-700 border-rose-200' :
                          'bg-amber-50 text-amber-700 border-amber-200 animate-pulse'
                        }`}>
                          {task.status === 'processing' && <Loader2 className="w-2.5 h-2.5 animate-spin" />}
                          {task.status === 'completed' && <CheckCircle2 className="w-2.5 h-2.5" />}
                          {task.status === 'failed' && <AlertCircle className="w-2.5 h-2.5" />}
                          {task.status}
                        </span>
                      </div>
                      <Progress value={task.progress} className="h-1.5 bg-zinc-100" />
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}