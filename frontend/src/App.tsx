import { useState, useEffect } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { FileText, MessageSquare } from 'lucide-react'
import { apiClient } from '@/lib/api-client'

// Component Imports
import { DashboardStats } from '@/components/ui/DashboardStats'
import { DocumentManager } from '@/components/ui/DocumentManager'
import { ComplianceChat } from '@/components/ui/ComplianceChat'
import { ClimateRiskWidget } from '@/components/ui/ClimateRiskWidget';

export default function App() {
  // Global shared stats state for the overview row
  const [stats, setStats] = useState({
    total_indexed_chunks: 0,
    tasks_pending: 0,
    tasks_processing: 0,
    tasks_completed: 0,
    tasks_failed: 0
  })

  // Synchronize system health and parsing metrics from FastAPI gateway
  const fetchMetrics = async () => {
    try {
      const { data } = await apiClient.get('/api/system/stats')
      setStats(data)
    } catch (err) {
      console.error('System inventory synchronization failure:', err)
    }
  }

  // Handle active background polling every 5 seconds
  useEffect(() => {
      // 1. Defer the initial call to the next event loop tick
      const timeoutId = setTimeout(() => {
        fetchMetrics()
      }, 0)

      // 2. Establish the steady-state polling interval
      const intervalId = setInterval(fetchMetrics, 5000)

      // 3. Clean up both timers if the component unmounts
      return () => {
        clearTimeout(timeoutId)
        clearInterval(intervalId)
      }
    }, [])

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 font-sans selection:bg-emerald-500/30 selection:text-emerald-300">
      
      {/* Global Header Navigation Panel */}
      <header className="border-b border-neutral-800 bg-neutral-900/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center font-bold text-neutral-950 text-lg shadow-lg shadow-emerald-500/20">
              C
            </div>
            <div>
              <h1 className="text-sm font-semibold tracking-wide uppercase text-neutral-200">CarbonLedger</h1>
              <p className="text-xs text-neutral-400">Compliance Verification Intelligence</p>
            </div>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/10 text-emerald-400 text-xs font-medium">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            Backend Cluster Active
          </div>
        </div>
      </header>

      {/* Main Control Center Grid */}
      <main className="max-w-7xl mx-auto p-6 space-y-8">
        
        {/* 1. Modular Analytics Banner Row */}
        <DashboardStats stats={stats} />

        {/* 2. Primary Sub-system Navigation Matrix */}
        <Tabs defaultValue="documents" className="w-full space-y-6">
          <TabsList className="bg-neutral-900 border border-neutral-800 p-1 rounded-xl">
            <TabsTrigger 
              value="documents" 
              className="data-[state=active]:bg-neutral-800 data-[state=active]:text-emerald-400 px-5 py-2 rounded-lg text-sm transition-all"
            >
              <FileText className="h-4 w-4 mr-2 inline-block" />
              Document Lifecycle Control
            </TabsTrigger>
            <TabsTrigger 
              value="chat" 
              className="data-[state=active]:bg-neutral-800 data-[state=active]:text-emerald-400 px-5 py-2 rounded-lg text-sm transition-all"
            >
              <MessageSquare className="h-4 w-4 mr-2 inline-block" />
              Compliance RAG Engine Chat
            </TabsTrigger>
          </TabsList>

          {/* Document File Manager Section */}
          <TabsContent value="documents" className="outline-none">
            <DocumentManager onUploadSuccess={fetchMetrics} />
          </TabsContent>

          {/* RAG Conversation Section */}
          <TabsContent value="chat" className="outline-none">
            <ComplianceChat />
          </TabsContent>
        </Tabs>

        <ClimateRiskWidget />
        
      </main>
    </div>
  )
}