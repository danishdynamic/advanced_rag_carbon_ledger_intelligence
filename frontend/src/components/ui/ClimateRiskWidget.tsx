import React, { useState, useEffect } from 'react';

interface ClimateRiskData {
  metrics: {
    total_tracked_facilities: number;
    total_estimated_exposure: number;
    average_facility_liability: number;
  };
  system_status: string;
}

export function ClimateRiskWidget() {
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

  if (loading) return <div className="p-6 text-zinc-400 animate-pulse text-sm font-medium">Loading compliance risk matrices...</div>;
  if (error) return <div className="p-4 text-rose-700 bg-rose-50 rounded-xl border border-rose-200 text-xs font-medium">Error: {error}</div>;
  if (!data) return null;

  const { metrics, system_status } = data;
  const isActionRequired = system_status === 'action_required';

  return (
    <div className="bg-white rounded-2xl p-2 text-zinc-900">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="text-base font-bold text-zinc-800 tracking-tight">Green Finance & Climate Risk</h2>
          <p className="text-xs text-zinc-400 font-medium">Real-time carbon tax liabilities & transition exposure metrics</p>
        </div>
        
        <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
          isActionRequired 
            ? 'bg-amber-50 text-amber-700 border-amber-200 animate-pulse' 
            : 'bg-emerald-50 text-emerald-700 border-emerald-200'
        }`}>
          {isActionRequired ? '⚠️ Action Required' : '✓ System Stable'}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-zinc-50 border border-zinc-200 p-4 rounded-xl shadow-2xs">
          <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Tracked Facilities</p>
          <p className="text-2xl font-extrabold mt-1 text-zinc-800 font-mono">
            {metrics.total_tracked_facilities}
          </p>
        </div>

        <div className="bg-zinc-50 border border-zinc-200 p-4 rounded-xl shadow-2xs">
          <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Total Est. Tax Liability</p>
          <p className={`text-2xl font-extrabold mt-1 font-mono ${isActionRequired ? 'text-amber-600' : 'text-emerald-600'}`}>
            ${metrics.total_estimated_exposure.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>

        <div className="bg-zinc-50 border border-zinc-200 p-4 rounded-xl shadow-2xs">
          <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Avg. Facility Exposure</p>
          <p className="text-2xl font-extrabold mt-1 text-zinc-800 font-mono">
            ${metrics.average_facility_liability.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
      </div>
    </div>
  );
}