'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { LunarDataset, PSRRegion, RouteResult, Waypoint } from '@/types';
import Terrain3DViewer from './Terrain3DViewer';
import { computeRoverRoute } from '@/lib/pathfinding';
import { formatDistance, formatDuration, formatLatLon, gridToStereo, lonLatToStereo, stereoToGrid, stereoToLonLat } from '@/lib/gis';
import {
  Navigation,
  RotateCcw,
  Play,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Compass,
  Mountain,
  Moon,
  Crosshair,
  Sliders,
  ChevronDown,
} from 'lucide-react';

interface RoverRoutingModuleProps {
  dataset: LunarDataset;
  routeResult: RouteResult | null;
  onSetRouteResult: (result: RouteResult | null) => void;
  presetGoalRegion?: PSRRegion | null;
  presetStartPoint?: Waypoint | null;
}

export default function RoverRoutingModule({
  dataset,
  routeResult,
  onSetRouteResult,
  presetGoalRegion,
  presetStartPoint,
}: RoverRoutingModuleProps) {
  // Coordinates and grid points for Start and Goal
  const [startPoint, setStartPoint] = useState<Waypoint>(dataset.defaultStart);
  const [goalPoint, setGoalPoint] = useState<Waypoint>(dataset.defaultGoal);

  // Manual input fields for Lat/Lon
  const [startLat, setStartLat] = useState<string>(dataset.defaultStart.latitude.toString());
  const [startLon, setStartLon] = useState<string>(dataset.defaultStart.longitude.toString());
  const [goalLat, setGoalLat] = useState<string>(dataset.defaultGoal.latitude.toString());
  const [goalLon, setGoalLon] = useState<string>(dataset.defaultGoal.longitude.toString());

  // Interactive 3D Picking state
  const [pickingMode, setPickingMode] = useState<'start' | 'goal' | null>(null);

  // Rover Traversability constraints
  const [maxSlopeDeg, setMaxSlopeDeg] = useState<number>(16.0);
  const [isCalculating, setIsCalculating] = useState<boolean>(false);

  // If a preset start point was passed from Landing Site module, apply it
  useEffect(() => {
    if (presetStartPoint) {
      setStartPoint(presetStartPoint);
      setStartLat(presetStartPoint.latitude.toString());
      setStartLon(presetStartPoint.longitude.toString());
    }
  }, [presetStartPoint]);

  // If a preset goal region was passed from PSR module, apply it
  useEffect(() => {
    if (presetGoalRegion) {
      const newGoal: Waypoint = {
        name: presetGoalRegion.name,
        pixelX: presetGoalRegion.pixelX,
        pixelY: presetGoalRegion.pixelY,
        coordX: presetGoalRegion.coordX,
        coordY: presetGoalRegion.coordY,
        latitude: presetGoalRegion.latitude,
        longitude: presetGoalRegion.longitude,
      };
      setGoalPoint(newGoal);
      setGoalLat(newGoal.latitude.toString());
      setGoalLon(newGoal.longitude.toString());
    }
  }, [presetGoalRegion]);

  // Handle 3D terrain click to place start or goal
  const handlePickPoint = (type: 'start' | 'goal', px: number, py: number) => {
    const stereo = gridToStereo(px, py, dataset.bounds, dataset.pixelSizeM);
    const ll = stereoToLonLat(stereo.x, stereo.y);

    const point: Waypoint = {
      name: type === 'start' ? 'Custom Start Point' : 'Custom Destination Point',
      pixelX: px,
      pixelY: py,
      coordX: stereo.x,
      coordY: stereo.y,
      latitude: ll.lat,
      longitude: ll.lon,
    };

    if (type === 'start') {
      setStartPoint(point);
      setStartLat(ll.lat.toString());
      setStartLon(ll.lon.toString());
    } else {
      setGoalPoint(point);
      setGoalLat(ll.lat.toString());
      setGoalLon(ll.lon.toString());
    }

    setPickingMode(null);
  };

  // Sync manual lat/lon inputs to start point
  const handleApplyStartCoords = () => {
    const lat = parseFloat(startLat);
    const lon = parseFloat(startLon);
    if (isNaN(lat) || isNaN(lon)) return;

    const stereo = lonLatToStereo(lon, lat);
    const grid = stereoToGrid(
      stereo.x,
      stereo.y,
      dataset.bounds,
      dataset.pixelSizeM,
      dataset.width,
      dataset.height
    );

    setStartPoint({
      name: 'Custom Lat/Lon Start',
      pixelX: grid.col,
      pixelY: grid.row,
      coordX: stereo.x,
      coordY: stereo.y,
      latitude: Number(lat.toFixed(4)),
      longitude: Number(lon.toFixed(4)),
    });
  };

  // Sync manual lat/lon inputs to goal point
  const handleApplyGoalCoords = () => {
    const lat = parseFloat(goalLat);
    const lon = parseFloat(goalLon);
    if (isNaN(lat) || isNaN(lon)) return;

    const stereo = lonLatToStereo(lon, lat);
    const grid = stereoToGrid(
      stereo.x,
      stereo.y,
      dataset.bounds,
      dataset.pixelSizeM,
      dataset.width,
      dataset.height
    );

    setGoalPoint({
      name: 'Custom Lat/Lon Destination',
      pixelX: grid.col,
      pixelY: grid.row,
      coordX: stereo.x,
      coordY: stereo.y,
      latitude: Number(lat.toFixed(4)),
      longitude: Number(lon.toFixed(4)),
    });
  };

  // Quick Select PSR target from dropdown
  const handleSelectPsrGoal = (regionIdStr: string) => {
    const rId = parseInt(regionIdStr, 10);
    const region = dataset.regions.find((r) => r.id === rId);
    if (!region) return;

    const newGoal: Waypoint = {
      name: region.name,
      pixelX: region.pixelX,
      pixelY: region.pixelY,
      coordX: region.coordX,
      coordY: region.coordY,
      latitude: region.latitude,
      longitude: region.longitude,
    };
    setGoalPoint(newGoal);
    setGoalLat(newGoal.latitude.toString());
    setGoalLon(newGoal.longitude.toString());
  };

  // Execute A* route calculation
  const handleCalculateRoute = useCallback(() => {
    setIsCalculating(true);

    setTimeout(() => {
      const result = computeRoverRoute(
        dataset,
        startPoint.pixelX,
        startPoint.pixelY,
        goalPoint.pixelX,
        goalPoint.pixelY,
        maxSlopeDeg
      );

      onSetRouteResult(result);
      setIsCalculating(false);
    }, 60);
  }, [dataset, startPoint, goalPoint, maxSlopeDeg, onSetRouteResult]);

  // Reset route
  const handleResetRoute = () => {
    onSetRouteResult(null);
    setStartPoint(dataset.defaultStart);
    setGoalPoint(dataset.defaultGoal);
    setStartLat(dataset.defaultStart.latitude.toString());
    setStartLon(dataset.defaultStart.longitude.toString());
    setGoalLat(dataset.defaultGoal.latitude.toString());
    setGoalLon(dataset.defaultGoal.longitude.toString());
    setPickingMode(null);
  };

  return (
    <div className="flex-1 flex flex-col lg:flex-row h-full overflow-hidden">
      {/* Left Panel: 3D Route Map & Terrain (Dominates view) */}
      <div className="flex-1 h-[55vh] lg:h-full relative border-b lg:border-b-0 lg:border-r border-[#1a2030] overflow-hidden">
        <Terrain3DViewer
          dataset={dataset}
          startPoint={startPoint}
          goalPoint={goalPoint}
          routeResult={routeResult}
          pickingMode={pickingMode}
          onPickPoint={handlePickPoint}
          showPsrOverlay={true}
        />

        {/* Floating Quick Picking Toolbar */}
        <div className="absolute top-4 right-4 z-10 flex items-center gap-2">
          <button
            onClick={() => setPickingMode(pickingMode === 'start' ? null : 'start')}
            className={`px-3 py-1.5 rounded text-xs font-medium border flex items-center gap-1.5 backdrop-blur-sm transition-colors ${
              pickingMode === 'start'
                ? 'bg-emerald-600/30 text-emerald-300 border-emerald-400 shadow-sm'
                : 'bg-[#0d121c]/80 text-slate-300 border-[#212c42] hover:text-white'
            }`}
          >
            <Crosshair className="w-3.5 h-3.5 text-emerald-400" />
            <span>{pickingMode === 'start' ? 'Cancel Pick' : 'Pick Start on 3D'}</span>
          </button>

          <button
            onClick={() => setPickingMode(pickingMode === 'goal' ? null : 'goal')}
            className={`px-3 py-1.5 rounded text-xs font-medium border flex items-center gap-1.5 backdrop-blur-sm transition-colors ${
              pickingMode === 'goal'
                ? 'bg-amber-600/30 text-amber-300 border-amber-400 shadow-sm'
                : 'bg-[#0d121c]/80 text-slate-300 border-[#212c42] hover:text-white'
            }`}
          >
            <Crosshair className="w-3.5 h-3.5 text-amber-400" />
            <span>{pickingMode === 'goal' ? 'Cancel Pick' : 'Pick Goal on 3D'}</span>
          </button>
        </div>
      </div>

      {/* Right Panel: Route Controls & Results */}
      <div className="w-full lg:w-[430px] bg-[#090c14] flex flex-col h-[45vh] lg:h-full shrink-0 border-l border-[#1a2030] overflow-y-auto">
        <div className="p-5 space-y-5">
          {/* 1. Starting Location Card */}
          <div className="p-4 rounded-lg bg-[#0e131d] border border-[#1e2638] space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono tracking-wider uppercase text-emerald-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                1. Starting Location
              </span>
              <span className="text-[10px] text-slate-400 font-mono">
                X:{startPoint.pixelX}, Y:{startPoint.pixelY}
              </span>
            </div>

            <div className="text-xs font-medium text-slate-200">
              {startPoint.name}
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <label className="text-[10px] text-slate-400 font-mono block mb-1">
                  LATITUDE (DEG)
                </label>
                <input
                  type="text"
                  value={startLat}
                  onChange={(e) => setStartLat(e.target.value)}
                  onBlur={handleApplyStartCoords}
                  className="w-full bg-[#141b29] text-xs font-mono text-slate-200 rounded px-2.5 py-1.5 border border-[#232f45] outline-none focus:border-emerald-500"
                  placeholder="-89.840"
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-400 font-mono block mb-1">
                  LONGITUDE (DEG)
                </label>
                <input
                  type="text"
                  value={startLon}
                  onChange={(e) => setStartLon(e.target.value)}
                  onBlur={handleApplyStartCoords}
                  className="w-full bg-[#141b29] text-xs font-mono text-slate-200 rounded px-2.5 py-1.5 border border-[#232f45] outline-none focus:border-emerald-500"
                  placeholder="333.400"
                />
              </div>
            </div>
          </div>

          {/* 2. Destination Card */}
          <div className="p-4 rounded-lg bg-[#0e131d] border border-[#1e2638] space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono tracking-wider uppercase text-amber-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-amber-400" />
                2. Destination Point
              </span>
              <span className="text-[10px] text-slate-400 font-mono">
                X:{goalPoint.pixelX}, Y:{goalPoint.pixelY}
              </span>
            </div>

            {/* Quick PSR Destination Selector */}
            <div>
              <label className="text-[11px] text-slate-300 font-medium block mb-1">
                Choose Detected PSR Destination:
              </label>
              <select
                onChange={(e) => handleSelectPsrGoal(e.target.value)}
                className="w-full bg-[#141b29] text-xs text-slate-200 rounded p-2 border border-[#232f45] outline-none focus:border-amber-500"
              >
                <option value="">-- Select from Detected PSR Regions --</option>
                {dataset.regions.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} ({r.areaKm2} km²)
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <label className="text-[10px] text-slate-400 font-mono block mb-1">
                  LATITUDE (DEG)
                </label>
                <input
                  type="text"
                  value={goalLat}
                  onChange={(e) => setGoalLat(e.target.value)}
                  onBlur={handleApplyGoalCoords}
                  className="w-full bg-[#141b29] text-xs font-mono text-slate-200 rounded px-2.5 py-1.5 border border-[#232f45] outline-none focus:border-amber-500"
                  placeholder="-89.750"
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-400 font-mono block mb-1">
                  LONGITUDE (DEG)
                </label>
                <input
                  type="text"
                  value={goalLon}
                  onChange={(e) => setGoalLon(e.target.value)}
                  onBlur={handleApplyGoalCoords}
                  className="w-full bg-[#141b29] text-xs font-mono text-slate-200 rounded px-2.5 py-1.5 border border-[#232f45] outline-none focus:border-amber-500"
                  placeholder="120.400"
                />
              </div>
            </div>
          </div>

          {/* 3. Traversability Constraint & Actions */}
          <div className="p-4 rounded-lg bg-[#0e131d] border border-[#1e2638] space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-slate-300 font-medium flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-blue-400" />
                Rover Max Slope Limit
              </span>
              <span className="text-xs font-mono text-blue-400 font-semibold">
                {maxSlopeDeg.toFixed(0)}°
              </span>
            </div>
            <input
              type="range"
              min="10"
              max="22"
              step="1"
              value={maxSlopeDeg}
              onChange={(e) => setMaxSlopeDeg(Number(e.target.value))}
              className="w-full accent-blue-500 h-1 cursor-pointer"
            />
            <p className="text-[10px] text-slate-400">
              NASA VIPER threshold: 15° nominal limit. Cliffs &gt;{maxSlopeDeg}° treated as impassable.
            </p>

            <div className="flex items-center gap-2 pt-2 border-t border-[#1a2233]">
              <button
                id="btn-calculate-route"
                onClick={handleCalculateRoute}
                disabled={isCalculating}
                className="flex-1 py-2 px-3 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium flex items-center justify-center gap-2 transition-colors shadow-sm disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5" />
                <span>{isCalculating ? 'Computing A* Path...' : 'Calculate Route'}</span>
              </button>

              <button
                id="btn-reset-route"
                onClick={handleResetRoute}
                className="py-2 px-3 rounded bg-[#161e2e] hover:bg-[#1e293d] text-slate-300 hover:text-white text-xs font-medium flex items-center justify-center gap-1.5 border border-[#232f45] transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset</span>
              </button>
            </div>
          </div>

          {/* 4. Route Calculation Results */}
          {routeResult ? (
            <div
              className={`p-4 rounded-lg border space-y-3 ${
                routeResult.feasible
                  ? 'bg-[#0c1422] border-blue-500/40'
                  : 'bg-rose-950/20 border-rose-500/40'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono tracking-wider uppercase text-slate-400 flex items-center gap-1.5">
                  {routeResult.feasible ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
                  )}
                  4. Route Results
                </span>
                <span
                  className={`text-[10px] px-2 py-0.5 rounded font-mono font-medium ${
                    routeResult.feasible
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                      : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                  }`}
                >
                  {routeResult.feasible ? 'FEASIBLE ROUTE' : 'UNFEASIBLE'}
                </span>
              </div>

              <div className="text-xs text-slate-300 leading-relaxed">
                {routeResult.statusMessage}
              </div>

              {routeResult.feasible && (
                <div className="space-y-2 pt-2 border-t border-[#1a2233]">
                  {/* Primary Metrics Grid */}
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="p-2 rounded bg-[#090d16] border border-[#1a2336]">
                      <div className="text-[10px] text-slate-400 font-mono">TOTAL DISTANCE</div>
                      <div className="text-sm font-semibold text-cyan-300 font-mono mt-0.5">
                        {routeResult.distance3dKm} km
                      </div>
                      <div className="text-[10px] text-slate-400">
                        Planar: {routeResult.distance2dKm} km
                      </div>
                    </div>

                    <div className="p-2 rounded bg-[#090d16] border border-[#1a2336]">
                      <div className="text-[10px] text-slate-400 font-mono">ESTIMATED TIME</div>
                      <div className="text-sm font-semibold text-amber-300 font-mono mt-0.5">
                        {formatDuration(routeResult.estimatedDurationHours)}
                      </div>
                      <div className="text-[10px] text-slate-400">
                        At nominal 0.10 m/s
                      </div>
                    </div>
                  </div>

                  {/* Secondary Metrics */}
                  <div className="grid grid-cols-2 gap-2 text-[11px] font-mono bg-[#090d16] p-2.5 rounded border border-[#1a2336]">
                    <div>
                      <span className="text-slate-400">TRAVERSAL COST:</span>
                      <div className="text-slate-200">{routeResult.traversalCost} pts</div>
                    </div>
                    <div>
                      <span className="text-slate-400">STEPS:</span>
                      <div className="text-slate-200">
                        {routeResult.pathPoints.length} waypoints
                      </div>
                    </div>
                    <div>
                      <span className="text-slate-400">MAX / AVG SLOPE:</span>
                      <div
                        className={
                          routeResult.maxSlopeDeg > 12 ? 'text-amber-400' : 'text-slate-200'
                        }
                      >
                        {routeResult.maxSlopeDeg}° / {routeResult.avgSlopeDeg}°
                      </div>
                    </div>
                    <div>
                      <span className="text-slate-400">SHADOW EXPOSURE:</span>
                      <div className="text-violet-300">
                        {routeResult.shadowFractionPct}% ({routeResult.shadowDistanceKm} km)
                      </div>
                    </div>
                    <div>
                      <span className="text-slate-400">ELEV GAIN:</span>
                      <div className="text-emerald-400">+{routeResult.elevationGainM} m</div>
                    </div>
                    <div>
                      <span className="text-slate-400">ELEV LOSS:</span>
                      <div className="text-rose-400">-{routeResult.elevationLossM} m</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-3 rounded-lg bg-[#0e131d]/60 border border-[#1a2233] text-[11px] text-slate-400 flex items-center gap-2">
              <Compass className="w-4 h-4 text-blue-400 shrink-0" />
              <span>
                Click &quot;Calculate Route&quot; to compute kinematically valid rover pathfinding across the terrain elevation and slope grid.
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
