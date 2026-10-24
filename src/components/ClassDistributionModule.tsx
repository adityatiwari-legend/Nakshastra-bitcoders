'use client';

import React, { useState } from 'react';
import { LunarDataset, ClassStat } from '@/types';
import { PieChart, BarChart2, Database, ShieldCheck, Info } from 'lucide-react';

interface ClassDistributionModuleProps {
  dataset: LunarDataset;
  activeDatasetId: string;
  onSelectDataset: (id: string) => void;
}

export default function ClassDistributionModule({
  dataset,
  activeDatasetId,
  onSelectDataset,
}: ClassDistributionModuleProps) {
  const [hoveredClassId, setHoveredClassId] = useState<string | null>(null);

  const { classes, totalAreaKm2, validAreaKm2, totalPixels, validPixels } = dataset;

  // Donut chart SVG calculations
  const radius = 80;
  const strokeWidth = 26;
  const circumference = 2 * Math.PI * radius;

  // Compute stroke offsets for each class in donut
  let cumulativePct = 0;
  const donutSegments = classes.map((c) => {
    const strokeDasharray = `${(c.percentage / 100) * circumference} ${circumference}`;
    const strokeDashoffset = -((cumulativePct / 100) * circumference);
    cumulativePct += c.percentage;

    return {
      ...c,
      strokeDasharray,
      strokeDashoffset,
    };
  });

  const activeHovered = classes.find((c) => c.id === hoveredClassId) || null;

  return (
    <div className="flex-1 flex flex-col h-full bg-[#07090e] overflow-y-auto p-6 space-y-6 select-none">
      {/* Header Overview Card */}
      <div className="p-5 rounded-lg bg-[#0b0f18] border border-[#1a2336] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-mono tracking-wider uppercase text-blue-400 flex items-center gap-1.5">
              <PieChart className="w-3.5 h-3.5" />
              Terrain Composition Analysis
            </span>
            <span
              className={`text-[10px] px-2 py-0.5 rounded font-mono font-medium ${
                dataset.isReal
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                  : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
              }`}
            >
              {dataset.tag}
            </span>
          </div>
          <h2 className="text-base font-semibold text-slate-100">
            {dataset.name} — Geomorphological Class Distribution
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Classified across {totalPixels.toLocaleString()} raster grid cells ({dataset.pixelSizeM} m spatial resolution)
          </p>
        </div>

        {/* Quick Dataset Switcher */}
        <div className="flex items-center gap-2 bg-[#0e1422] px-3 py-1.5 rounded border border-[#1e293f] self-start md:self-auto">
          <Database className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-xs text-slate-400">Dataset:</span>
          <select
            value={activeDatasetId}
            onChange={(e) => onSelectDataset(e.target.value)}
            className="bg-transparent text-xs text-slate-200 font-mono outline-none cursor-pointer hover:text-blue-400"
          >
            <option value="lola_south_pole" className="bg-[#0e1422]">
              NASA LRO LOLA South Pole (Scientific)
            </option>
            <option value="synthetic_benchmark" className="bg-[#0e1422]">
              Synthetic Benchmark Crater (Demo)
            </option>
          </select>
        </div>
      </div>

      {/* Primary KPI Ribbon */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-lg bg-[#0d121d] border border-[#1a2336]">
          <div className="text-[10px] font-mono text-slate-400 uppercase">Total Geographic Area</div>
          <div className="text-xl font-bold font-mono text-slate-100 mt-1">
            {totalAreaKm2.toLocaleString()} km²
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">
            {totalPixels.toLocaleString()} total pixels
          </div>
        </div>

        <div className="p-4 rounded-lg bg-[#0d121d] border border-[#1a2336]">
          <div className="text-[10px] font-mono text-slate-400 uppercase">Valid Lunar Surface</div>
          <div className="text-xl font-bold font-mono text-blue-400 mt-1">
            {validAreaKm2.toLocaleString()} km²
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">
            {((validPixels / totalPixels) * 100).toFixed(1)}% of total raster
          </div>
        </div>

        <div className="p-4 rounded-lg bg-[#0d121d] border border-[#1a2336]">
          <div className="text-[10px] font-mono text-violet-400 uppercase">Permanently Shadowed (PSR)</div>
          <div className="text-xl font-bold font-mono text-violet-300 mt-1">
            {dataset.psrAreaKm2.toLocaleString()} km²
          </div>
          <div className="text-[11px] text-violet-400 mt-0.5">
            {((dataset.psrAreaKm2 / validAreaKm2) * 100).toFixed(1)}% of valid terrain
          </div>
        </div>

        <div className="p-4 rounded-lg bg-[#0d121d] border border-[#1a2336]">
          <div className="text-[10px] font-mono text-emerald-400 uppercase">Safe Non-PSR Corridor</div>
          <div className="text-xl font-bold font-mono text-emerald-400 mt-1">
            {classes.find((c) => c.id === 'safe')?.areaKm2 || 0} km²
          </div>
          <div className="text-[11px] text-emerald-400 mt-0.5">
            Slope &lt;10° (VIPER traversable)
          </div>
        </div>
      </div>

      {/* Main Visual Panels: Donut Chart & Proportional Bar Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* A. Donut Chart Visualization (5 Cols) */}
        <div className="lg:col-span-5 p-5 rounded-lg bg-[#0b0f18] border border-[#1a2336] flex flex-col items-center justify-center space-y-4">
          <div className="w-full flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-200">Class Distribution Chart</span>
            <span className="text-[10px] text-slate-400 font-mono">HOVER TO INSPECT</span>
          </div>

          <div className="relative w-64 h-64 flex items-center justify-center my-2">
            <svg className="w-full h-full -rotate-90 transform" viewBox="0 0 220 220">
              {/* Background circle track */}
              <circle
                cx="110"
                cy="110"
                r={radius}
                fill="none"
                stroke="#121824"
                strokeWidth={strokeWidth}
              />
              {/* Colored Segments */}
              {donutSegments.map((seg) => {
                const isHovered = hoveredClassId === seg.id;
                return (
                  <circle
                    key={seg.id}
                    cx="110"
                    cy="110"
                    r={radius}
                    fill="none"
                    stroke={seg.color}
                    strokeWidth={isHovered ? strokeWidth + 4 : strokeWidth}
                    strokeDasharray={seg.strokeDasharray}
                    strokeDashoffset={seg.strokeDashoffset}
                    className="transition-all duration-300 cursor-pointer"
                    onMouseEnter={() => setHoveredClassId(seg.id)}
                    onMouseLeave={() => setHoveredClassId(null)}
                  />
                );
              })}
            </svg>

            {/* Donut Center Display */}
            <div className="absolute flex flex-col items-center justify-center text-center pointer-events-none px-4">
              {activeHovered ? (
                <>
                  <span
                    className="text-[10px] font-mono font-semibold uppercase truncate max-w-[140px]"
                    style={{ color: activeHovered.color }}
                  >
                    {activeHovered.name}
                  </span>
                  <span className="text-lg font-bold font-mono text-slate-100">
                    {activeHovered.percentage}%
                  </span>
                  <span className="text-[10px] font-mono text-slate-400">
                    {activeHovered.areaKm2} km²
                  </span>
                </>
              ) : (
                <>
                  <span className="text-[10px] font-mono text-slate-400 uppercase">
                    Total Extent
                  </span>
                  <span className="text-base font-bold font-mono text-slate-100">
                    {totalAreaKm2.toLocaleString()} km²
                  </span>
                  <span className="text-[10px] font-mono text-blue-400">
                    100% Raster
                  </span>
                </>
              )}
            </div>
          </div>

          {/* Quick Color Swatches below Donut */}
          <div className="w-full flex flex-wrap items-center justify-center gap-3 pt-2 border-t border-[#1a2336] text-[11px]">
            {classes.map((c) => (
              <div
                key={c.id}
                onMouseEnter={() => setHoveredClassId(c.id)}
                onMouseLeave={() => setHoveredClassId(null)}
                className={`flex items-center gap-1.5 px-2 py-1 rounded cursor-pointer transition-colors ${
                  hoveredClassId === c.id ? 'bg-[#151c2c]' : 'hover:bg-[#101522]'
                }`}
              >
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: c.color }} />
                <span className="text-slate-300 text-[11px] truncate">{c.name.split(' (')[0]}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Proportional Segmented Bar Breakdown (7 Cols) */}
        <div className="lg:col-span-7 p-5 rounded-lg bg-[#0b0f18] border border-[#1a2336] flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-200">
                Spatial Coverage Breakdown (100% Proportional)
              </span>
              <span className="text-[10px] text-slate-400 font-mono">
                {totalPixels.toLocaleString()} Grid Cells
              </span>
            </div>

            {/* Proportional Segmented Bar */}
            <div className="w-full h-8 rounded-lg overflow-hidden flex border border-[#1e273a] shadow-inner mb-4">
              {classes.map((c) => (
                <div
                  key={c.id}
                  style={{
                    width: `${c.percentage}%`,
                    backgroundColor: c.color,
                  }}
                  onMouseEnter={() => setHoveredClassId(c.id)}
                  onMouseLeave={() => setHoveredClassId(null)}
                  className={`h-full transition-opacity cursor-pointer relative group ${
                    hoveredClassId && hoveredClassId !== c.id ? 'opacity-40' : 'opacity-100'
                  }`}
                  title={`${c.name}: ${c.percentage}% (${c.areaKm2} km²)`}
                />
              ))}
            </div>

            {/* Detailed Class Cards List */}
            <div className="space-y-2">
              {classes.map((c) => {
                const isHovered = hoveredClassId === c.id;
                return (
                  <div
                    key={c.id}
                    onMouseEnter={() => setHoveredClassId(c.id)}
                    onMouseLeave={() => setHoveredClassId(null)}
                    className={`p-2.5 rounded border transition-colors flex items-center justify-between ${
                      isHovered
                        ? 'bg-[#141c2c] border-blue-500/50'
                        : 'bg-[#0e131e] border-[#1a2336] hover:bg-[#121826]'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className="w-3 h-3 rounded shrink-0"
                        style={{ backgroundColor: c.color }}
                      />
                      <div>
                        <div className="text-xs font-medium text-slate-200 flex items-center gap-2">
                          <span>{c.name}</span>
                          {c.id === 'psr' && (
                            <span className="text-[9px] px-1.5 py-0.2 rounded bg-violet-500/20 text-violet-300 font-mono">
                              CRITICAL
                            </span>
                          )}
                        </div>
                        <div className="text-[10px] text-slate-400 mt-0.5">
                          {c.description}
                        </div>
                      </div>
                    </div>

                    <div className="text-right shrink-0">
                      <div className="text-xs font-bold font-mono text-slate-100">
                        {c.areaKm2.toLocaleString()} km²
                      </div>
                      <div className="text-[10px] font-mono text-slate-400">
                        {c.percentage}% ({c.pixelCount.toLocaleString()} px)
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="p-3 rounded bg-[#0e1422] border border-[#1b2538] text-[11px] text-slate-400 flex items-center gap-2">
            <Info className="w-4 h-4 text-blue-400 shrink-0" />
            <span>
              All measurements are calculated dynamically from the active digital elevation model and aligned NASA PSR mask. Colors correspond directly to the 3D terrain visualizer.
            </span>
          </div>
        </div>
      </div>

      {/* B. Full Quantitative Class Statistics Table */}
      <div className="p-5 rounded-lg bg-[#0b0f18] border border-[#1a2336] space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-200 flex items-center gap-2">
            <BarChart2 className="w-3.5 h-3.5 text-blue-400" />
            B. Complete Scientific Class Statistics Table
          </span>
          <span className="text-[10px] text-slate-400 font-mono">
            Spatial Resolution: {dataset.pixelSizeM} m/cell
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-[#1e273a] text-[10px] text-slate-400 uppercase">
                <th className="py-2.5 px-3">Class Name</th>
                <th className="py-2.5 px-3 text-right">Pixel Count</th>
                <th className="py-2.5 px-3 text-right">Physical Area (km²)</th>
                <th className="py-2.5 px-3 text-right">% Valid Terrain</th>
                <th className="py-2.5 px-3 text-right">% Total Raster</th>
                <th className="py-2.5 px-3">Interpretation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#151c2a]">
              {classes.map((c) => (
                <tr
                  key={c.id}
                  className={`hover:bg-[#111726] transition-colors ${
                    hoveredClassId === c.id ? 'bg-[#151d2e]' : ''
                  }`}
                  onMouseEnter={() => setHoveredClassId(c.id)}
                  onMouseLeave={() => setHoveredClassId(null)}
                >
                  <td className="py-2.5 px-3 flex items-center gap-2">
                    <span
                      className="w-2.5 h-2.5 rounded-full shrink-0"
                      style={{ backgroundColor: c.color }}
                    />
                    <span className="text-slate-200 font-sans font-medium text-xs">
                      {c.name}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-right text-slate-300">
                    {c.pixelCount.toLocaleString()}
                  </td>
                  <td className="py-2.5 px-3 text-right text-slate-100 font-semibold">
                    {c.areaKm2.toLocaleString()}
                  </td>
                  <td className="py-2.5 px-3 text-right text-blue-400">
                    {c.percentageValid > 0 ? `${c.percentageValid.toFixed(2)}%` : '—'}
                  </td>
                  <td className="py-2.5 px-3 text-right text-slate-300">
                    {c.percentage.toFixed(2)}%
                  </td>
                  <td className="py-2.5 px-3 text-slate-400 text-[11px] font-sans">
                    {c.description}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-[#1e273a] text-slate-100 font-semibold text-xs">
                <td className="py-3 px-3">TOTAL ANALYZED EXTENT</td>
                <td className="py-3 px-3 text-right">{totalPixels.toLocaleString()}</td>
                <td className="py-3 px-3 text-right">{totalAreaKm2.toLocaleString()} km²</td>
                <td className="py-3 px-3 text-right text-blue-400">100.00%</td>
                <td className="py-3 px-3 text-right">100.00%</td>
                <td className="py-3 px-3 text-[11px] text-slate-400 font-normal font-sans">
                  Moon 2000 Polar Stereographic Projection
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
}
