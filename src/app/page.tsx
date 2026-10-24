'use client';

import React, { useState, useEffect } from 'react';
import { ActiveModule, CandidateLandingSite, DatasetStatus, LunarDataset, PSRRegion, RouteResult, Waypoint } from '@/types';
import Sidebar from '@/components/Sidebar';
import Header from '@/components/Header';
import PsrDetectionModule from '@/components/PsrDetectionModule';
import LandingSiteModule from '@/components/LandingSiteModule';
import RoverRoutingModule from '@/components/RoverRoutingModule';
import ClassDistributionModule from '@/components/ClassDistributionModule';
import { Loader2, AlertCircle } from 'lucide-react';

export default function App() {
  const [isMounted, setIsMounted] = useState<boolean>(false);

  // Navigation State
  const [activeModule, setActiveModule] = useState<ActiveModule>('psr');

  // Dataset State
  const [activeDatasetId, setActiveDatasetId] = useState<string>('lola_south_pole');
  const [dataset, setDataset] = useState<LunarDataset | null>(null);
  const [datasetStatus, setDatasetStatus] = useState<DatasetStatus>('loading');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Cross-module interaction states
  const [selectedRegion, setSelectedRegion] = useState<PSRRegion | null>(null);
  const [selectedLandingSite, setSelectedLandingSite] = useState<CandidateLandingSite | null>(null);
  const [routeResult, setRouteResult] = useState<RouteResult | null>(null);
  const [presetGoalRegion, setPresetGoalRegion] = useState<PSRRegion | null>(null);
  const [presetStartPoint, setPresetStartPoint] = useState<Waypoint | null>(null);
  const [processingMessage, setProcessingMessage] = useState<string | undefined>(undefined);

  // Client mounting guard
  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Load dataset JSON
  const loadDataset = async (datasetId: string) => {
    try {
      setDatasetStatus('loading');
      setErrorMessage(null);
      setProcessingMessage(
        `Loading ${datasetId === 'lola_south_pole' ? 'NASA LOLA South Pole' : 'Synthetic Benchmark'} dataset...`
      );

      const res = await fetch(`/data/${datasetId}.json`);
      if (!res.ok) {
        throw new Error(`Failed to load dataset: ${res.statusText}`);
      }
      const data: LunarDataset = await res.json();

      setDataset(data);
      setDatasetStatus('ready');
      setProcessingMessage(undefined);

      // Select first large PSR region by default
      if (data.regions && data.regions.length > 0) {
        setSelectedRegion(data.regions[1] || data.regions[0]);
      }
      // Select first candidate landing site by default
      if (data.landingSites && data.landingSites.length > 0) {
        setSelectedLandingSite(data.landingSites[0]);
      }
      // Reset active route when dataset changes
      setRouteResult(null);
      setPresetGoalRegion(null);
      setPresetStartPoint(null);
    } catch (err: unknown) {
      console.error('Dataset loading error:', err);
      const msg = err instanceof Error ? err.message : 'Unknown dataset loading error';
      setErrorMessage(msg);
      setDatasetStatus('error');
      setProcessingMessage(undefined);
    }
  };

  // Load on mount and when activeDatasetId changes
  useEffect(() => {
    if (isMounted) {
      loadDataset(activeDatasetId);
    }
  }, [activeDatasetId, isMounted]);

  // Handle switching to Rover Routing with a selected PSR as the goal
  const handleSwitchToRoutingWithGoal = (region: PSRRegion) => {
    setSelectedRegion(region);
    setPresetGoalRegion(region);
    setActiveModule('routing');
  };

  // Handle deploying rover from a selected landing site
  const handleDeployRoverFromLandingSite = (waypoint: Waypoint) => {
    setPresetStartPoint(waypoint);
    setActiveModule('routing');
  };

  if (!isMounted) {
    return (
      <div className="flex h-screen w-screen bg-[#07090e] items-center justify-center">
        <div className="flex items-center gap-3 text-xs font-mono text-slate-300">
          <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
          <span>Initializing OrbisLuna Mission Platform...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#07090e]">
      {/* 1. Left Sidebar Navigation */}
      <Sidebar
        activeModule={activeModule}
        onSelectModule={setActiveModule}
        datasetName={dataset?.name || 'Loading...'}
        isRealDataset={dataset?.isReal ?? true}
      />

      {/* Main App Container */}
      <div className="flex-1 flex flex-col h-screen min-w-0 overflow-hidden">
        {/* 2. Top Header */}
        <Header
          activeModule={activeModule}
          datasetStatus={datasetStatus}
          processingMessage={processingMessage}
          activeDatasetId={activeDatasetId}
          onSelectDataset={(id) => setActiveDatasetId(id)}
          coverage={dataset?.coverage || 'Lunar South Pole'}
        />

        {/* 3. Main Content Views */}
        <main className="flex-1 flex flex-col min-h-0 overflow-hidden relative">
          {datasetStatus === 'loading' && (
            <div className="absolute inset-0 z-50 bg-[#07090e]/90 flex flex-col items-center justify-center space-y-3">
              <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
              <p className="text-xs font-mono text-slate-300">
                Loading lunar digital elevation model &amp; PSR masks...
              </p>
            </div>
          )}

          {datasetStatus === 'error' && (
            <div className="p-8 flex flex-col items-center justify-center h-full text-center space-y-3">
              <AlertCircle className="w-10 h-10 text-rose-400" />
              <h2 className="text-sm font-semibold text-slate-100">
                Failed to Load Lunar Dataset
              </h2>
              <p className="text-xs text-slate-400 max-w-md">{errorMessage}</p>
              <button
                onClick={() => loadDataset(activeDatasetId)}
                className="mt-2 px-4 py-2 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition-colors"
              >
                Retry Loading
              </button>
            </div>
          )}

          {dataset && datasetStatus === 'ready' && (
            <>
              {activeModule === 'psr' && (
                <PsrDetectionModule
                  dataset={dataset}
                  selectedRegion={selectedRegion}
                  onSelectRegion={setSelectedRegion}
                  onSwitchToRoutingWithGoal={handleSwitchToRoutingWithGoal}
                  activeDatasetId={activeDatasetId}
                  onSelectDataset={setActiveDatasetId}
                />
              )}

              {activeModule === 'landing' && (
                <LandingSiteModule
                  dataset={dataset}
                  selectedSite={selectedLandingSite}
                  onSelectSite={setSelectedLandingSite}
                  onDeployRoverFromSite={handleDeployRoverFromLandingSite}
                />
              )}

              {activeModule === 'routing' && (
                <RoverRoutingModule
                  dataset={dataset}
                  routeResult={routeResult}
                  onSetRouteResult={setRouteResult}
                  presetGoalRegion={presetGoalRegion}
                  presetStartPoint={presetStartPoint}
                />
              )}

              {activeModule === 'distribution' && (
                <ClassDistributionModule
                  dataset={dataset}
                  activeDatasetId={activeDatasetId}
                  onSelectDataset={setActiveDatasetId}
                />
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
