import React, { useState, useEffect } from 'react';

// 1. 🛡️ Define the TypeScript interface for your API response
interface ClimateRiskData {
  metrics: {
    total_tracked_facilities: number;
    total_estimated_exposure: number;
    average_facility_liability: number;
  };
  system_status: string;
}

export function ClimateRiskWidget() {
  // 2. ⚡ Tell TypeScript that data can be this interface OR null initially
  const [data, setData] = useState<ClimateRiskData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('http://localhost:8000/api/analytics/climate-risk')
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch climate risk analytics');
        return res.json();
      })
      .then((incomingData: ClimateRiskData) => {
        setData(incomingData);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="p-6 text-slate-400 animate-pulse">Loading financial risk metrics...</div>;
  if (error) return <div className="p-6 text-red-400 bg-red-950/20 rounded-xl border border-red-900/50">Error: {error}</div>;
  
  // 3. 🔒 Guard clause to guarantee to TypeScript that data is not null past this point
  if (!data) return null;

  const { metrics, system_status } = data;
  const isActionRequired = system_status === 'action_required';

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl text-slate-100">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Green Finance & Climate Risk</h2>
          <p className="text-sm text-slate-400">Real-time carbon tax liabilities & transition exposure</p>
        </div>
        
        <span className={`px-3 py-1 rounded-full text-xs font-semibold tracking-wide uppercase shadow-sm border ${
          isActionRequired 
            ? 'bg-amber-500/10 text-amber-400 border-amber-500/30 animate-pulse' 
            : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
        }`}>
          {isActionRequired ? '⚠️ Action Required' : '✓ System Stable'}
        </span>
      </div>

      <hr className="border-slate-800 mb-6" />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-slate-950/40 border border-slate-800/60 p-4 rounded-xl">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Tracked Facilities</p>
          <p className="text-3xl font-extrabold mt-2 text-slate-200">
            {metrics.total_tracked_facilities}
          </p>
        </div>

        <div className="bg-slate-950/40 border border-slate-800/60 p-4 rounded-xl">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Total Est. Tax Liability</p>
          <p className={`text-3xl font-extrabold mt-2 ${isActionRequired ? 'text-amber-400' : 'text-emerald-400'}`}>
            ${metrics.total_estimated_exposure.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>

        <div className="bg-slate-950/40 border border-slate-800/60 p-4 rounded-xl">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Avg. Facility Exposure</p>
          <p className="text-3xl font-extrabold mt-2 text-slate-200">
            ${metrics.average_facility_liability.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
      </div>
      
      <div className="mt-6 text-xs text-slate-500 italic">
        * Estimates are calculated using regional ETS baseline carbon tax formulas.
      </div>
    </div>
  );
}