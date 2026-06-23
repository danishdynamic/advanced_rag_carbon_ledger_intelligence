import { useState, useRef } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { toast } from 'sonner'
import { UploadCloud, FileText } from 'lucide-react'
import { apiClient } from '@/lib/api-client'

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
      // Swapped out raw fetch syntax for clean API Gateway abstraction
      const { data } = await apiClient.post('/api/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      toast.success(`${file.name} queued successfully!`, { id: toastId })
      
      setActiveTasks((prev) => [
        { id: data.task_id, fileName: data.file_name || file.name, status: 'pending', progress: 10 },
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
        <Card className="bg-neutral-900 border-neutral-800 shadow-xl">
          <CardHeader>
            <CardTitle className="text-lg text-neutral-200">Ingest New Regulations</CardTitle>
            <CardDescription className="text-neutral-400">
              Submit compliance documentation. Gemini Multi-format vision layer processes documents out-of-band.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" accept=".pdf,.txt" disabled={isUploading} />
            <div
              onClick={() => !isUploading && fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 text-center flex flex-col items-center justify-center gap-3 cursor-pointer transition-all ${
                isUploading 
                  ? 'border-neutral-800 bg-neutral-950/50 opacity-50 cursor-not-allowed' 
                  : 'border-neutral-800 hover:border-emerald-500/50 hover:bg-emerald-500/5 bg-neutral-950/30'
              }`}
            >
              <div className="p-4 bg-neutral-900 border border-neutral-800 rounded-full text-neutral-400">
                <UploadCloud className="h-6 w-6 text-emerald-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-neutral-200">Click to locate corporate report</p>
                <p className="text-xs text-neutral-500 mt-1">Accepts PDF layouts and plain-text files</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Active Pipeline List Status Tracker */}
      <div className="lg:col-span-2">
        <Card className="bg-neutral-900 border-neutral-800 h-full shadow-xl">
          <CardHeader>
            <CardTitle className="text-lg text-neutral-200">Background Worker Job Ingest Streams</CardTitle>
            <CardDescription className="text-neutral-400">
              Live asynchronous extraction, vision matrix parsing, and semantic chunking threads.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {activeTasks.length === 0 ? (
              <div className="h-40 border border-dashed border-neutral-800 rounded-xl flex items-center justify-center text-sm text-neutral-500">
                No files submitted during this frontend control session.
              </div>
            ) : (
              <div className="space-y-4 max-h-[350px] overflow-y-auto pr-2">
                {activeTasks.map((task) => (
                  <div key={task.id} className="p-4 bg-neutral-950 border border-neutral-800 rounded-xl space-y-3">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-neutral-300 truncate max-w-[250px]">{task.fileName}</span>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] uppercase font-bold tracking-wider ${
                        task.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                        task.status === 'failed' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                        'bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse'
                      }`}>
                        {task.status}
                      </span>
                    </div>
                    <Progress value={task.progress} className="h-1.5 bg-neutral-900" />
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}