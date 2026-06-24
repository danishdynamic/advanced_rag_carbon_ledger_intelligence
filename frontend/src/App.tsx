import { useState, useEffect } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { FileText, MessageSquare } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { motion, AnimatePresence } from 'framer-motion'

// Component Imports
import { DashboardStats } from '@/components/ui/DashboardStats'
import { DocumentManager } from '@/components/ui/DocumentManager'
import { ClimateRiskWidget } from '@/components/ui/ClimateRiskWidget'
import ComplianceChat from '@/components/ui/ComplianceChat'

export default function App() {
  const [activeTab, setActiveTab] = useState('documents')
  const [stats, setStats] = useState({
    total_indexed_chunks: 0,
    tasks_pending: 0,
    tasks_processing: 0,
    tasks_completed: 0,
    tasks_failed: 0
  })

  const fetchMetrics = async () => {
    try {
      const { data } = await apiClient.get('/api/system/stats')
      setStats(data)
    } catch (err) {
      console.error('System inventory synchronization failure:', err)
    }
  }

  useEffect(() => {
    const timeoutId = setTimeout(() => { fetchMetrics() }, 0)
    const intervalId = setInterval(fetchMetrics, 5000)
    return () => {
      clearTimeout(timeoutId)
      clearInterval(intervalId)
    }
  }, [])

  return (
    <div className="min-h-screen bg-slate-50/50 text-zinc-900 font-sans antialiased selection:bg-emerald-500/10 selection:text-emerald-800">
      
      {/* 🌌 Premium Light Header */}
      <motion.header 
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="border-b border-zinc-200/80 bg-white/80 backdrop-blur-md sticky top-0 z-50 shadow-sm"
      >
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <motion.div 
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="h-9 w-9 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center font-bold text-white text-lg shadow-md"
            >
              C
            </motion.div>
            <div>
              <h1 className="text-sm font-bold tracking-wide uppercase text-zinc-800">CarbonLedger</h1>
              <p className="text-xs text-zinc-500 font-medium">Compliance Verification Intelligence</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-emerald-100 bg-emerald-50 text-emerald-700 text-xs font-semibold">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Backend Cluster Active
          </div>
        </div>
      </motion.header>

      {/* 🚀 Animated Main Workspace Container */}
      <motion.main 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.05 }}
        className="max-w-7xl mx-auto p-6 space-y-6"
      >
        
        {/* Analytics Banner Wrapper */}
        <div className="bg-white rounded-2xl border border-zinc-200 shadow-sm p-1">
          <DashboardStats stats={stats} />
        </div>

        {/* Navigation Matrix */}
        <Tabs defaultValue="documents" value={activeTab} onValueChange={setActiveTab} className="w-full space-y-6">
          <TabsList className="bg-zinc-100/80 border border-zinc-200/60 p-1 rounded-xl inline-flex relative">
            
            <TabsTrigger 
              value="documents" 
              className="relative px-5 py-2 rounded-lg text-sm font-medium text-zinc-500 transition-all data-[state=active]:text-zinc-900 z-10"
            >
              <FileText className="h-4 w-4 mr-2 inline-block" />
              Document Lifecycle Control
              {activeTab === 'documents' && (
                <motion.div 
                  layoutId="activeTabGlow" 
                  className="absolute inset-0 bg-white rounded-lg -z-10 shadow-sm border border-zinc-200/50"
                  transition={{ type: "spring", stiffness: 400, damping: 32 }}
                />
              )}
            </TabsTrigger>

            <TabsTrigger 
              value="chat" 
              className="relative px-5 py-2 rounded-lg text-sm font-medium text-zinc-500 transition-all data-[state=active]:text-zinc-900 z-10"
            >
              <MessageSquare className="h-4 w-4 mr-2 inline-block" />
              Compliance RAG Engine Chat
              {activeTab === 'chat' && (
                <motion.div 
                  layoutId="activeTabGlow" 
                  className="absolute inset-0 bg-white rounded-lg -z-10 shadow-sm border border-zinc-200/50"
                  transition={{ type: "spring", stiffness: 400, damping: 32 }}
                />
              )}
            </TabsTrigger>
          </TabsList>

          {/* Tab Screen Content Pipeline */}
          <div className="relative min-h-[500px]">
            <AnimatePresence mode="wait">
              {activeTab === 'documents' && (
                <TabsContent value="documents" className="outline-none m-0">
                  <motion.div
                    key="documents-panel"
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 6 }}
                    transition={{ duration: 0.2 }}
                  >
                    <DocumentManager onUploadSuccess={fetchMetrics} />
                  </motion.div>
                </TabsContent>
              )}

              {activeTab === 'chat' && (
                <TabsContent value="chat" className="outline-none m-0">
                  <motion.div
                    key="chat-panel"
                    initial={{ opacity: 0, x: 6 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -6 }}
                    transition={{ duration: 0.2 }}
                  >
                    <ComplianceChat />
                  </motion.div>
                </TabsContent>
              )}
            </AnimatePresence>
          </div>
        </Tabs>

        {/* Global Widgets Section */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
          className="bg-white rounded-2xl border border-zinc-200 shadow-sm p-4"
        >
          <ClimateRiskWidget />
        </motion.div>
        
      </motion.main>
    </div>
  )
}