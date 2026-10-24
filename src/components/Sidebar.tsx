'use client';

import React from 'react';
import { ActiveModule } from '@/types';
import { Eye, Navigation, BarChart2, Orbit, ShieldCheck, Target } from 'lucide-react';

interface SidebarProps {
  activeModule: ActiveModule;
  onSelectModule: (module: ActiveModule) => void;
  datasetName: string;
  isRealDataset: boolean;
}

export default function Sidebar({
  activeModule,
  onSelectModule,
  datasetName,
  isRealDataset,
}: SidebarProps) {
  const navItems = [
    {
      id: 'psr' as ActiveModule,
      label: 'PSR Detection',
      icon: Eye,
      description: '3D Terrain & Cold-Trap Masks',
    },
    {
      id: 'landing' as ActiveModule,
      label: 'Landing Sites',
      icon: Target,
      description: '40m Buffer Scanner & Touchdown',
    },
    {
      id: 'routing' as ActiveModule,
      label: 'Rover Routing',
      icon: Navigation,
      description: 'A* Mobility & Traverse Planning',
    },
    {
      id: 'distribution' as ActiveModule,
      label: 'Class Distribution',
      icon: BarChart2,
      description: 'Composition & Area Statistics',
    },
  ];

  return (
    <aside className="w-64 bg-[#0a0d14] border-r border-[#1a2030] flex flex-col justify-between h-screen shrink-0 select-none">
      {/* Brand Header */}
      <div>
        <div className="p-5 border-b border-[#1a2030] flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-600/30 to-indigo-900/40 border border-blue-500/40 flex items-center justify-center text-blue-400">
            <Orbit className="w-5 h-5 animate-pulse text-blue-400" />
          </div>
          <div>
            <div className="font-semibold text-slate-100 tracking-wide text-base flex items-center gap-1.5">
              <span>OrbisLuna</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono">
                PSR
              </span>
            </div>
            <p className="text-[11px] text-slate-400 tracking-tight">Lunar Surface Analysis</p>
          </div>
        </div>

        {/* Navigation Section */}
        <div className="px-3 py-4">
          <p className="px-3 mb-2 text-[10px] font-medium tracking-wider text-slate-400 uppercase">
            Core Modules
          </p>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeModule === item.id;
              return (
                <button
                  key={item.id}
                  id={`nav-btn-${item.id}`}
                  onClick={() => onSelectModule(item.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-left transition-colors ${
                    isActive
                      ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-[#121724] border border-transparent'
                  }`}
                >
                  <Icon
                    className={`w-4 h-4 shrink-0 ${
                      isActive ? 'text-blue-400' : 'text-slate-400'
                    }`}
                  />
                  <div className="flex-1 truncate">
                    <div className="text-xs font-medium leading-none mb-1">
                      {item.label}
                    </div>
                    <div className="text-[10px] text-slate-400 leading-none truncate">
                      {item.description}
                    </div>
                  </div>
                  {isActive && (
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-400 shadow-[0_0_8px_#60a5fa]" />
                  )}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Dataset & CRS Footer */}
      <div className="p-4 border-t border-[#1a2030] bg-[#080b11]">
        <div className="flex items-center gap-2 mb-2">
          <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-[10px] font-mono tracking-wider uppercase text-slate-400">
            Active Dataset
          </span>
        </div>
        <div className="text-xs text-slate-200 font-medium truncate mb-1" title={datasetName}>
          {datasetName}
        </div>
        <div className="flex items-center gap-1.5 mb-2">
          <span
            className={`w-2 h-2 rounded-full ${
              isRealDataset ? 'bg-emerald-400' : 'bg-amber-400'
            }`}
          />
          <span className="text-[11px] font-mono text-slate-400">
            {isRealDataset ? 'NASA LRO LOLA (Scientific)' : 'Analytical (Demo Benchmark)'}
          </span>
        </div>
        <div className="text-[10px] text-slate-400 font-mono">
          CRS: Moon 2000 Polar Stereographic
        </div>
      </div>
    </aside>
  );
}
