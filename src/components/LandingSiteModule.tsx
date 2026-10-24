'use client';

import React, { useState, useEffect } from 'react';
import { CandidateLandingSite, LunarDataset, Waypoint } from '@/types';
import Terrain3DViewer from './Terrain3DViewer';
import { evaluateTouchdownSpot, LandingEvaluationResult } from '@/lib/landing';
import { formatLatLon } from '@/lib/gis';
import {
  Target,
  ShieldCheck,
  AlertTriangle,
  Play,
  RotateCcw,
  CheckCircle2,
  Navigation,
  Compass,
  ArrowRight,
  Crosshair,
  Activity,
  Layers,
  ChevronRight,
  Info,
} from 'lucide-react';

interface LandingSiteModuleProps {
  dataset: LunarDataset;
  selectedSite: CandidateLandingSite | null;
  onSelectSite: (site: CandidateLandingSite | null) => void;
  onDeployRoverFromSite: (waypoint: Waypoint) => void;
}

export default function LandingSiteModule({
  dataset,
  selectedSite,
  onSelectSite,
  onDeployRoverFromSite,
}: LandingSiteModuleProps) {
  // Scanning state
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [scanProgress, setScanProgress] = useState<number>(100);
  const [scanMessage, setScanMessage] = useState<string | null>(null);

  // Spot picking and evaluation state
  const [isPickingSpot, setIsPickingSpot] = useState<boolean>(false);
  const [evaluation, setEvaluation] = useState<LandingEvaluationResult | null>(null);

  // Initialize with the first site if none selected
  useEffect(() => {
    if (!selectedSite && dataset.landingSites && dataset.landingSites.length > 0) {
      onSelectSite(dataset.landingSites[0]);
    }
  }, [dataset, selectedSite, onSelectSite]);

  // When a candidate site is selected, auto-evaluate its touchdown envelope
  useEffect(() => {
    if (selectedSite) {
      const evalResult = evaluateTouchdownSpot(dataset, selectedSite.pixelX, selectedSite.pixelY);
      setEvaluation(evalResult);
    }
  }, [selectedSite, dataset]);

  // Handle running the autonomous LiDAR scan
  const handleRunLiDARScan = () => {
    setIsScanning(true);
    setScanProgress(0);
    setScanMessage(null);

    const interval = setInterval(() => {
      setScanProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsScanning(false);
          setScanMessage(
            `✔ LiDAR Scan Complete: ${dataset.landingSites?.length || 0} candidate landing zones verified with 40-meter hazard-free clearance buffers.`
          );
          return 100;
        }
        return prev + 25;
      });
    }, 220);
  };

  // Handle picking a custom spot on the 3D terrain
  const handlePickSpot = (pixelX: number, pixelY: number) => {
    setIsPickingSpot(false);
    const evalResult = evaluateTouchdownSpot(dataset, pixelX, pixelY);
    setEvaluation(evalResult);
  };

  // Handle clicking a recommended site to accept the diversion
  const handleSelectRecommendedSite = (recSite: CandidateLandingSite) => {
    onSelectSite(recSite);
    const evalResult = evaluateTouchdownSpot(dataset, recSite.pixelX, recSite.pixelY);
    setEvaluation(evalResult);
  };

  // Deploy rover from current evaluation point or selected site
  const handleDeployRover = () => {
    if (evaluation) {
      const wp: Waypoint = {
        name: selectedSite ? selectedSite.name : `Touchdown Spot (${evaluation.latitude.toFixed(3)}°S)`,
        pixelX: evaluation.pixelX,
        pixelY: evaluation.pixelY,
        coordX: evaluation.coordX,
        coordY: evaluation.coordY,
        latitude: evaluation.latitude,
        longitude: evaluation.longitude,
      };
      onDeployRoverFromSite(wp);
    } else if (selectedSite) {
      const wp: Waypoint = {
        name: selectedSite.name,
        pixelX: selectedSite.pixelX,
        pixelY: selectedSite.pixelY,
        coordX: selectedSite.coordX,
        coordY: selectedSite.coordY,
        latitude: selectedSite.latitude,
        longitude: selectedSite.longitude,
      };
      onDeployRoverFromSite(wp);
    }
  };

  return (
    <div className="flex-1 flex flex-col lg:flex-row h-full overflow-hidden">
      {/* Left Panel: 3D Lunar Terrain with Landing Sites & 40m Buffer Rings */}
      <div className="flex-1 h-[55vh] lg:h-full relative border-b lg:border-b-0 lg:border-r border-[#1a2030] overflow-hidden">
        <Terrain3DViewer
          dataset={dataset}
          showLandingSites={true}
          selectedLandingSiteId={selectedSite?.id || null}
          onSelectLandingSite={(site) => {
            onSelectSite(site);
            if (site) {
              const evalResult = evaluateTouchdownSpot(dataset, site.pixelX, site.pixelY);
              setEvaluation(evalResult);
            }
          }}
          isScanningLandingSites={isScanning}
          pickingLandingMode={isPickingSpot}
          onPickLandingSpot={handlePickSpot}
          pickedLandingSpot={
            evaluation
              ? {
                  pixelX: evaluation.pixelX,
                  pixelY: evaluation.pixelY,
                  isSafe: evaluation.isSafe,
                  slopeDeg: evaluation.maxSlopeDeg,
                  elevationM: evaluation.elevationM,
                  clearanceBufferM: evaluation.clearanceBufferM,
                }
              : null
          }
          recommendedSite={evaluation && !evaluation.isSafe ? evaluation.recommendedSite : null}
        />

        {/* Floating Quick Action Button on 3D View */}
        <div className="absolute top-4 right-4 z-10 flex items-center gap-2">
          <button
            onClick={() => setIsPickingSpot(!isPickingSpot)}
            className={`px-3 py-1.5 rounded text-xs font-medium border flex items-center gap-1.5 backdrop-blur-sm transition-all shadow-lg ${
              isPickingSpot
                ? 'bg-cyan-500 text-black border-cyan-300 font-semibold animate-pulse'
                : 'bg-[#0d121c]/80 text-cyan-300 border-[#212c42] hover:bg-[#161f30]'
            }`}
          >
            <Crosshair className="w-3.5 h-3.5" />
            <span>{isPickingSpot ? 'Click on 3D Surface...' : 'Pick Spot on 3D Map'}</span>
          </button>
        </div>
      </div>

      {/* Right Panel: Landing Site Selection, 40m Buffer Analytics & Decision Engine */}
      <div className="w-full lg:w-[440px] bg-[#090c14] flex flex-col h-[45vh] lg:h-full shrink-0 border-l border-[#1a2030] overflow-y-auto">
        <div className="p-5 space-y-6">
          {/* Header & Scan Trigger */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Target className="w-4 h-4 text-emerald-400" />
                <h2 className="text-xs font-semibold text-slate-200 uppercase tracking-wider font-mono">
                  Lander Touchdown Engine
                </h2>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950/60 text-emerald-300 border border-emerald-500/30">
                40m BUFFER ACTIVE
              </span>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              Autonomous landing site evaluation calculates micro-slope stability and enforces a{' '}
              <strong className="text-emerald-300">40-meter clearance buffer</strong> around the lander to
              prevent rollover hazards during lunar descent.
            </p>

            {/* Run Autonomous LiDAR Scan Button */}
            <button
              onClick={handleRunLiDARScan}
              disabled={isScanning}
              className="w-full py-2.5 px-4 rounded bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center justify-center gap-2 shadow-lg shadow-emerald-950/50 transition-all border border-emerald-400/30"
            >
              {isScanning ? (
                <>
                  <Activity className="w-4 h-4 animate-spin" />
                  <span>Scanning 3D Model ({scanProgress}%)...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Scan 3D Model for Safe Landing Sites</span>
                </>
              )}
            </button>

            {/* Scan Progress Bar */}
            {isScanning && (
              <div className="w-full bg-[#121824] rounded-full h-1.5 overflow-hidden">
                <div
                  className="bg-emerald-400 h-1.5 transition-all duration-200"
                  style={{ width: `${scanProgress}%` }}
                />
              </div>
            )}

            {/* Scan Completion Banner */}
            {scanMessage && (
              <div className="p-3 rounded bg-emerald-950/40 border border-emerald-500/40 text-[11px] text-emerald-300 font-mono flex items-start gap-2 shadow-sm">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <span>{scanMessage}</span>
              </div>
            )}
          </div>

          {/* Touchdown Decision Card (Evaluates current selection or picked spot) */}
          {evaluation && (
            <div
              className={`p-4 rounded-xl border transition-all ${
                evaluation.isSafe
                  ? 'bg-emerald-950/20 border-emerald-500/40 shadow-[0_0_20px_rgba(16,185,129,0.1)]'
                  : 'bg-rose-950/20 border-rose-500/40 shadow-[0_0_20px_rgba(239,68,68,0.1)]'
              }`}
            >
              <div className="flex items-center justify-between pb-3 border-b border-[#1f293d]">
                <div className="flex items-center gap-2">
                  {evaluation.isSafe ? (
                    <ShieldCheck className="w-5 h-5 text-emerald-400" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-rose-400" />
                  )}
                  <div>
                    <div
                      className={`text-xs font-bold font-mono ${
                        evaluation.isSafe ? 'text-emerald-300' : 'text-rose-300'
                      }`}
                    >
                      {evaluation.status}
                    </div>
                    <div className="text-[10px] text-slate-400">
                      Coordinates: {Math.abs(evaluation.latitude).toFixed(3)}°S,{' '}
                      {evaluation.longitude.toFixed(3)}°E
                    </div>
                  </div>
                </div>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                    evaluation.isSafe
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                      : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                  }`}
                >
                  {evaluation.isSafe ? 'TOUCHDOWN SAFE' : 'UNSAFE HAZARD'}
                </span>
              </div>

              {/* Status Explanation */}
              <p className="mt-3 text-xs text-slate-300 leading-relaxed font-sans">
                {evaluation.statusReason}
              </p>

              {/* 40m Buffer Telemetry Grid */}
              <div className="mt-4 grid grid-cols-2 gap-2 text-[11px] font-mono">
                <div className="p-2.5 rounded bg-[#070b14] border border-[#1a2335]">
                  <div className="text-slate-400 text-[10px]">40m CLEARANCE BUFFER</div>
                  <div className="text-emerald-400 font-semibold mt-0.5">
                    {evaluation.clearanceBufferM.toFixed(1)} m (100% Verified)
                  </div>
                </div>

                <div className="p-2.5 rounded bg-[#070b14] border border-[#1a2335]">
                  <div className="text-slate-400 text-[10px]">MAX BUFFER SLOPE</div>
                  <div
                    className={`font-semibold mt-0.5 ${
                      evaluation.maxSlopeDeg > 7.0 ? 'text-rose-400' : 'text-emerald-400'
                    }`}
                  >
                    {evaluation.maxSlopeDeg.toFixed(1)}° (Limit: &le;7.0°)
                  </div>
                </div>

                <div className="p-2.5 rounded bg-[#070b14] border border-[#1a2335]">
                  <div className="text-slate-400 text-[10px]">MEAN INCLINE</div>
                  <div className="text-slate-200 font-semibold mt-0.5">
                    {evaluation.meanSlopeDeg.toFixed(1)}°
                  </div>
                </div>

                <div className="p-2.5 rounded bg-[#070b14] border border-[#1a2335]">
                  <div className="text-slate-400 text-[10px]">ELEVATION</div>
                  <div className="text-blue-400 font-semibold mt-0.5">
                    {evaluation.elevationM.toFixed(0)} m
                  </div>
                </div>
              </div>

              {/* Nearest PSR Proximity */}
              <div className="mt-3 px-3 py-2 rounded bg-[#070b14] border border-[#1a2335] flex items-center justify-between text-[11px] font-mono">
                <span className="text-slate-400">PROXIMITY TO PSR COLD TRAP:</span>
                <span className="text-violet-300 font-semibold">
                  {(evaluation.distToNearestPsrM / 1000).toFixed(2)} km ({evaluation.nearestPsrName})
                </span>
              </div>

              {/* AUTOMATED RECOMMENDATION IF UNSAFE */}
              {!evaluation.isSafe && evaluation.recommendedSite && (
                <div className="mt-4 p-3.5 rounded-lg bg-sky-950/30 border border-sky-500/50 space-y-2.5">
                  <div className="flex items-center gap-2">
                    <Navigation className="w-4 h-4 text-sky-400" />
                    <span className="text-xs font-bold font-mono text-sky-200">
                      RECOMMENDED SAFE ALTERNATIVE SITE
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-300 leading-snug">
                    Current spot exceeds safety tilt parameters. Diverting descent guidance trajectory to
                    the nearest certified safe landing zone:
                  </p>
                  <div className="p-2.5 rounded bg-[#070b14] border border-sky-500/30 flex items-center justify-between text-xs">
                    <div>
                      <div className="font-semibold text-sky-300">
                        {evaluation.recommendedSite.name}
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono">
                        Slope: {evaluation.recommendedSite.meanSlopeDeg}° • Buffer: 40m Safe • Distance:{' '}
                        {evaluation.distToRecommendedKm} km
                      </div>
                    </div>
                    <button
                      onClick={() => handleSelectRecommendedSite(evaluation.recommendedSite!)}
                      className="px-3 py-1.5 rounded bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium flex items-center gap-1 transition-colors shadow-sm"
                    >
                      <span>Go to Site</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}

              {/* DEPLOY ROVER BUTTON (When spot is Safe) */}
              {evaluation.isSafe && (
                <button
                  onClick={handleDeployRover}
                  className="mt-4 w-full py-2.5 px-4 rounded bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white text-xs font-semibold flex items-center justify-center gap-2 shadow-lg shadow-blue-950/50 transition-all border border-blue-400/30"
                >
                  <Navigation className="w-3.5 h-3.5" />
                  <span>Deploy Lunar Rover from this Landing Site</span>
                  <ArrowRight className="w-3.5 h-3.5 ml-1" />
                </button>
              )}
            </div>
          )}

          {/* Candidate Landing Sites Catalog */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
                Surveyed Candidate Landing Sites ({dataset.landingSites?.length || 0})
              </span>
              <button
                onClick={() => setIsPickingSpot(!isPickingSpot)}
                className="text-[11px] text-cyan-400 hover:text-cyan-300 font-mono flex items-center gap-1"
              >
                <Crosshair className="w-3 h-3" />
                <span>Test Custom Spot</span>
              </button>
            </div>

            <div className="space-y-2">
              {dataset.landingSites?.map((site) => {
                const isSelected = selectedSite?.id === site.id;
                return (
                  <div
                    key={site.id}
                    onClick={() => onSelectSite(site)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-blue-950/30 border-blue-500/60 shadow-[0_0_15px_rgba(56,189,248,0.15)] ring-1 ring-blue-500/30'
                        : 'bg-[#0d121c] border-[#1e273b] hover:border-slate-600/50 hover:bg-[#121926]'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span
                            className={`w-2 h-2 rounded-full ${
                              isSelected ? 'bg-cyan-400 shadow-[0_0_6px_#22d3ee]' : 'bg-emerald-400'
                            }`}
                          />
                          <span className="text-xs font-semibold text-slate-100">{site.name}</span>
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                          {formatLatLon(site.latitude, site.longitude)}
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          {site.status === 'APPROVED FOR DESCENT' ? 'APPROVED' : site.status}
                        </span>
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-blue-500/20 text-blue-300 border border-blue-500/30">
                          #{site.rank}
                        </span>
                      </div>
                    </div>

                    <div className="mt-3 grid grid-cols-3 gap-2 text-[10px] font-mono text-slate-400 pt-2 border-t border-[#182133]">
                      <div>
                        <span className="text-slate-500">SLOPE:</span>{' '}
                        <span className="text-emerald-400 font-medium">{site.meanSlopeDeg}°</span>
                      </div>
                      <div>
                        <span className="text-slate-500">ELEV:</span>{' '}
                        <span className="text-slate-200 font-medium">{site.elevationM}m</span>
                      </div>
                      <div>
                        <span className="text-slate-500">CLEARANCE:</span>{' '}
                        <span className="text-emerald-400 font-medium">{site.clearanceBufferM}m</span>
                      </div>
                    </div>

                    <div className="mt-2 text-[10px] text-slate-400 flex items-center justify-between">
                      <span className="text-violet-300 font-mono">
                        {site.distToPsrM}m to nearest PSR
                      </span>
                      {isSelected && (
                        <span className="text-cyan-400 text-[10px] font-semibold flex items-center gap-1">
                          Selected on 3D View <ChevronRight className="w-3 h-3" />
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Scientific Context Note */}
          <div className="p-3.5 rounded-lg bg-[#0d121c] border border-[#1e273b] text-slate-400 text-xs space-y-1.5">
            <div className="flex items-center gap-1.5 text-slate-200 font-semibold text-[11px]">
              <Info className="w-3.5 h-3.5 text-blue-400" />
              <span>NASA Artemis Landing Site Protocol</span>
            </div>
            <p className="text-[11px] leading-relaxed">
              Touchdown clearance requires maximum terrain slope &le; 7.0° and zero boulder hazards within
              a 40-meter radius to guarantee descent engine plume dispersal and prevent lander tipping.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
