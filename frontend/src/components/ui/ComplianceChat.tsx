import React, { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { 
  MessageSquare, 
  Send, 
  ShieldCheck, 
  AlertTriangle, 
  XCircle, 
  Search, 
  FileText, 
  Loader2
} from "lucide-react";

interface SourceReference {
  file_name: string;
  section: string;
  text_snippet: string;
  similarity: number;
}

interface ActiveTrace {
  subQueries: string[];
  evaluationStatus: 'IDLE' | 'CORRECT' | 'AMBIGUOUS' | 'IRRELEVANT';
  confidenceScore: number;
  sourceReferences: SourceReference[];
}

interface Message {
  sender: 'user' | 'bot';
  text: string;
}

export default function ComplianceChat() {
  const [prompt, setPrompt] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [messages, setMessages] = useState<Message[]>([]);
  
  const [activeTrace, setActiveTrace] = useState<ActiveTrace>({
    subQueries: [],
    evaluationStatus: 'IDLE',
    confidenceScore: 0.0,
    sourceReferences: []
  });

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  useEffect(() => { scrollToBottom(); }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || loading) return;

    const userMessage: Message = { sender: 'user', text: prompt };
    setMessages(prev => [...prev, userMessage]);
    setPrompt('');
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/chat/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: userMessage.text })
      });

      if (!response.ok) throw new Error('Network cluster response failure.');
      
      const data = await response.json();

      setMessages(prev => [...prev, { sender: 'bot', text: data.answer }]);
      setActiveTrace({
        subQueries: data.sub_queries || [],
        evaluationStatus: data.evaluation_status || 'AMBIGUOUS',
        confidenceScore: data.confidence_score || 0.0,
        sourceReferences: data.source_references || []
      });

    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { sender: 'bot', text: 'Error: Connection to RAG analytics thread was severed.' }]);
      setActiveTrace(prev => ({ ...prev, evaluationStatus: 'IRRELEVANT' }));
    } finally {
      setLoading(false);
    }
  };

  const renderStatusBadge = (status: ActiveTrace['evaluationStatus']) => {
    switch (status) {
      case 'CORRECT':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium bg-emerald-950 text-emerald-400 border border-emerald-800 rounded-full">
            <ShieldCheck className="w-3.5 h-3.5" /> CRAG PASS: RELIABLE
          </span>
        );
      case 'AMBIGUOUS':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium bg-amber-950 text-amber-400 border border-amber-800 rounded-full">
            <AlertTriangle className="w-3.5 h-3.5" /> AMBIGUOUS CONTEXT
          </span>
        );
      case 'IRRELEVANT':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium bg-destructive/20 text-destructive border border-destructive/30 rounded-full">
            <XCircle className="w-3.5 h-3.5" /> CONTEXT INSUFFICIENT
          </span>
        );
      default:
        return <span className="text-muted-foreground text-xs italic">Waiting for pipeline execution...</span>;
    }
  };

  return (
    <div className="flex w-full h-[calc(100vh-140px)] bg-slate-950 text-slate-100 rounded-b-xl overflow-hidden border border-slate-800">
      
      {/* 📥 LEFT PANEL: Chat Feed */}
      <div className="w-3/5 flex flex-col justify-between border-r border-slate-800 bg-slate-900/20">
        <div className="flex-1 p-6 overflow-y-auto space-y-4 classname-none">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 opacity-40">
              <MessageSquare className="w-12 h-12 text-teal-400 mb-3 animate-pulse" />
              <p className="text-sm font-medium">CarbonLedger Cognitive Retrieval</p>
              <p className="text-xs text-muted-foreground mt-1 max-w-sm">
                Ask cross-framework inquiries to trigger parallel hybrid vector executions.
              </p>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] rounded-2xl p-4 text-sm leading-relaxed ${
                  msg.sender === 'user' 
                    ? 'bg-teal-600 text-white rounded-tr-none' 
                    : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-tl-none'
                }`}>
                  <p className="whitespace-pre-wrap">{msg.text}</p>
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="flex items-center gap-2 text-xs text-teal-400 bg-slate-900 border border-slate-800 px-3 py-2 rounded-lg w-max animate-pulse">
              <Loader2 className="w-3.5 h-3.5 animate-spin" /> Analyzing parallel search indexes...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSubmit} className="p-4 bg-slate-900/60 border-t border-slate-800 flex gap-2">
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Ask a compliance framework verification prompt..."
            className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-teal-500 text-slate-100 placeholder-slate-600"
            disabled={loading}
          />
          <Button type="submit" disabled={loading || !prompt.trim()} className="bg-teal-600 hover:bg-teal-500 h-11 px-4 rounded-xl">
            <Send className="w-4 h-4" />
          </Button>
        </form>
      </div>

      {/* 🔍 RIGHT PANEL: Diagnostics Tracing */}
      <div className="w-2/5 flex flex-col bg-slate-950 overflow-y-auto p-6 space-y-6">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-2">Evaluation Guardrail</h3>
          <div className="py-1">{renderStatusBadge(activeTrace.evaluationStatus)}</div>
          {activeTrace.evaluationStatus !== 'IDLE' && (
            <div className="mt-2 text-xs text-muted-foreground">
              Confidence Matrix: <span className="font-mono font-bold text-teal-400">{(activeTrace.confidenceScore * 100).toFixed(1)}%</span>
            </div>
          )}
        </div>

        <hr className="border-slate-800" />

        <div>
          <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-2 flex items-center gap-1.5">
            <Search className="w-3.5 h-3.5 text-purple-400" /> Decomposed Sub-Queries
          </h3>
          {activeTrace.subQueries.length === 0 ? (
            <p className="text-xs text-slate-600 italic">No search streams tracked in this pipeline view block.</p>
          ) : (
            <ul className="space-y-2">
              {activeTrace.subQueries.map((sub, idx) => (
                <li key={idx} className="flex items-start gap-2 bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-xs font-mono">
                  <span className="text-purple-400 font-bold">#{idx + 1}</span>
                  <span className="text-slate-300">{sub}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <hr className="border-slate-800" />

        <div className="flex-1">
          <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-2 flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-teal-400" /> Fused Source Context (Top 3)
          </h3>
          {activeTrace.sourceReferences.length === 0 ? (
            <p className="text-xs text-slate-600 italic">No historical document records sourced.</p>
          ) : (
            <div className="space-y-3">
              {activeTrace.sourceReferences.map((ref, idx) => (
                <Card key={idx} className="bg-slate-900 border-slate-800 shadow-none">
                  <CardHeader className="p-3 pb-1">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-semibold text-teal-400 truncate max-w-[65%]">
                        📁 {ref.file_name}
                      </span>
                      <span className="font-mono text-slate-500">
                        RRF Match: <span className="text-slate-300 font-bold">{ref.similarity}%</span>
                      </span>
                    </div>
                    <CardDescription className="text-[10px] text-slate-500 font-medium truncate mt-0.5">
                      📍 {ref.section}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-3 pt-0">
                    <p className="text-xs bg-slate-950 border border-slate-800 p-2.5 rounded-lg text-slate-400 leading-normal max-h-24 overflow-y-auto">
                      "{ref.text_snippet}"
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}