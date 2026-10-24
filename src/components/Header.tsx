'use client';

import React from 'react';
import { ActiveModule, DatasetStatus } from '@/types';
import { Activity, Database, CheckCircle2, AlertCircle, RefreshCw, Cpu } from 'lucide-react';

interface HeaderProps {
  activeModule: ActiveModule;
  datasetStatus: DatasetStatus;
  processingMessage?: string;
  activeDatasetId: string;
  onSelectDataset: (id: string) => void;
  coverage: string;
}

export default function Header({
  activeModule,
  datasetStatus,
  processingMessage,
  activeDatasetId,
  onSelectDataset,
  coverage,
}: HeaderProps) {
  const moduleTitles: Record<ActiveModule, { title: string; subtitle: string }> = {
    psr: {
      title: 'PSR Detection + Interactive 3D Lunar Model',
      subtitle: 'Permanently Shadowed Region detection & interactive polar stereographic 3D elevation',
    },
    landing: {
      title: 'Candidate Landing Site & Touchdown Selection',
      subtitle: 'Autonomous 40m clearance buffer scanning, descent safety verification, and recommendation',
    },
    routing: {
      title: 'Rover Route Determination',
      subtitle: 'Kinematic A* traversability pathfinding across lunar slope & cold-trap constraints',
    },
    distribution: {
      title: 'Class Distribution Visualization',
      subtitle: 'Quantitative geomorphological terrain breakdown & spatial coverage metrics',
    },
  };

  const { title, subtitle } = moduleTitles[activeModule];

  return (
    <header className="h-16 bg-[#0a0d14] border-b border-[#1a2030] px-6 flex items-center justify-between shrink-0 select-none">
      {/* Module Title & Subtitle */}
      <div className="flex items-center gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-sm font-semibold text-slate-100 tracking-tight">
              {title}
            </h1>
            <span className="text-[10px] px-2 py-0.5 rounded bg-[#151c2c] text-slate-300 border border-[#232d42] font-mono">
              {coverage}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">
            {subtitle}
          </p>
        </div>
      </div>

      {/* Dataset & Processing Status */}
      <div className="flex items-center gap-4">
        {/* Processing Indicator */}
        {processingMessage && (
          <div className="flex items-center gap-2 px-3 py-1 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-mono animate-pulse">
            <Cpu className="w-3.5 h-3.5 animate-spin" />
            <span>{processingMessage}</span>
          </div>
        )}

        {/* Dataset Switcher */}
        <div className="flex items-center gap-2 bg-[#0e131d] px-2.5 py-1 rounded border border-[#1e2638]">
          <Database className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-[11px] text-slate-400 font-medium">Dataset:</span>
          <select
            id="header-dataset-selector"
            value={activeDatasetId}
            onChange={(e) => onSelectDataset(e.target.value)}
            className="bg-transparent text-xs text-slate-200 font-mono outline-none cursor-pointer hover:text-blue-400"
          >
            <option value="lola_south_pole" className="bg-[#0e131d] text-slate-200">
              NASA LRO LOLA South Pole (Scientific)
            </option>
            <option value="synthetic_benchmark" className="bg-[#0e131d] text-slate-200">
              Synthetic Benchmark Crater (Demo)
            </option>
          </select>
        </div>

        {/* Dataset Status Pill */}
        <div
          id="dataset-status-pill"
          className={`flex items-center gap-2 px-3 py-1 rounded border text-xs font-mono ${
            datasetStatus === 'ready'
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
              : datasetStatus === 'loading'
              ? 'bg-blue-500/10 text-blue-400 border-blue-500/30'
              : datasetStatus === 'processing'
              ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
              : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
          }`}
        >
          {datasetStatus === 'ready' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
          {datasetStatus === 'loading' && <RefreshCw className="w-3.5 h-3.5 animate-spin text-blue-400" />}
          {datasetStatus === 'processing' && <Activity className="w-3.5 h-3.5 animate-pulse text-amber-400" />}
          {datasetStatus === 'error' && <AlertCircle className="w-3.5 h-3.5 text-rose-400" />}
          <span className="uppercase text-[11px]">
            {datasetStatus === 'ready'
              ? 'Dataset Ready'
              : datasetStatus === 'loading'
              ? 'Loading Data'
              : datasetStatus === 'processing'
              ? 'Processing'
              : 'Data Error'}
          </span>
        </div>
      </div>
    </header>
  );
}
