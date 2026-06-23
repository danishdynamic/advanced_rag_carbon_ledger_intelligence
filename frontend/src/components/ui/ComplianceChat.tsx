import { Card } from '@/components/ui/card'
import { MessageSquare } from 'lucide-react'

export function ComplianceChat() {
  return (
    <Card className="bg-neutral-900 border-neutral-800 min-h-[450px] flex flex-col items-center justify-center p-8 text-center shadow-xl">
      <div className="h-12 w-12 rounded-full bg-emerald-500/10 text-emerald-400 flex items-center justify-center border border-emerald-500/20 mb-4 shadow-inner">
        <MessageSquare className="h-5 w-5" />
      </div>
      <h3 className="text-lg font-medium text-neutral-200">Compliance Cognitive Trace Interface</h3>
      <p className="text-sm text-neutral-400 max-w-md mt-2">
        This workbench layer will hold the chat panel, tracing sub-queries, source document reference blocks, and CRAG verification warnings.
      </p>
    </Card>
  )
}