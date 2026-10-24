'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { LunarDataset, PSRRegion, RoutePoint, RouteResult, CandidateLandingSite } from '@/types';
import { gridToStereo, stereoToLonLat } from '@/lib/gis';
import { Sun, RotateCcw, Eye, Compass, Navigation, Target } from 'lucide-react';

interface Terrain3DViewerProps {
  dataset: LunarDataset;
  selectedRegionId?: number | null;
  onSelectRegion?: (region: PSRRegion | null) => void;
  // Routing props
  startPoint?: { pixelX: number; pixelY: number } | null;
  goalPoint?: { pixelX: number; pixelY: number } | null;
  routeResult?: RouteResult | null;
  pickingMode?: 'start' | 'goal' | null;
  onPickPoint?: (type: 'start' | 'goal', pixelX: number, pixelY: number) => void;
  showPsrOverlay?: boolean;
  minAreaFilter?: number;
  isAnalyzing?: boolean;
  // Candidate Landing Sites props
  showLandingSites?: boolean;
  selectedLandingSiteId?: string | null;
  onSelectLandingSite?: (site: CandidateLandingSite | null) => void;
  isScanningLandingSites?: boolean;
  pickedLandingSpot?: {
    pixelX: number;
    pixelY: number;
    isSafe: boolean;
    slopeDeg: number;
    elevationM: number;
    clearanceBufferM: number;
  } | null;
  recommendedSite?: CandidateLandingSite | null;
  pickingLandingMode?: boolean;
  onPickLandingSpot?: (pixelX: number, pixelY: number) => void;
}

export default function Terrain3DViewer({
  dataset,
  selectedRegionId,
  onSelectRegion,
  startPoint,
  goalPoint,
  routeResult,
  pickingMode,
  onPickPoint,
  showPsrOverlay = true,
  minAreaFilter = 0,
  isAnalyzing = false,
  showLandingSites = false,
  selectedLandingSiteId,
  onSelectLandingSite,
  isScanningLandingSites = false,
  pickedLandingSpot,
  recommendedSite,
  pickingLandingMode = false,
  onPickLandingSpot,
}: Terrain3DViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Three.js internal references
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const terrainMeshRef = useRef<THREE.Mesh | null>(null);
  const terrainGeoRef = useRef<THREE.PlaneGeometry | null>(null);
  const sunLightRef = useRef<THREE.DirectionalLight | null>(null);
  const routeLineRef = useRef<THREE.Line | null>(null);
  const startMarkerRef = useRef<THREE.Group | null>(null);
  const goalMarkerRef = useRef<THREE.Group | null>(null);
  const regionMarkersRef = useRef<THREE.Group | null>(null);
  const landingSitesGroupRef = useRef<THREE.Group | null>(null);
  const pickedSpotMarkerRef = useRef<THREE.Group | null>(null);
  const recommendationLineRef = useRef<THREE.Line | null>(null);

  // UI state
  const [verticalExag, setVerticalExag] = useState<number>(2.0);
  const [sunAzimuth, setSunAzimuth] = useState<number>(45);
  const [hoverInfo, setHoverInfo] = useState<{
    pixelX: number;
    pixelY: number;
    elevM: number;
    slopeDeg: number;
    isPSR: boolean;
    lat: number;
    lon: number;
  } | null>(null);

  const SCENE_SIZE = 100; // Three.js units for terrain plane

  // Helper to convert grid (col, row) to Three.js coordinates
  const gridTo3D = useCallback(
    (col: number, row: number, elevExag: number) => {
      const { width, height, dem, minElev } = dataset;
      const x = (col / (width - 1) - 0.5) * SCENE_SIZE;
      const z = (row / (height - 1) - 0.5) * SCENE_SIZE;

      const idx = row * width + col;
      const rawElev = dem[idx];
      const validElev = rawElev > dataset.nodata + 1.0 ? rawElev : minElev;
      const elevNorm = (validElev - minElev) / Math.max(1, dataset.maxElev - minElev);
      const y = elevNorm * 12.0 * elevExag;

      return new THREE.Vector3(x, y, z);
    },
    [dataset]
  );

  // Generate scientific lunar regolith & PSR texture
  const generateTerrainTexture = useCallback(() => {
    const { width, height, dem, slope, psr, nodata, minElev, maxElev } = dataset;
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    const imgData = ctx.createImageData(width, height);
    const data = imgData.data;

    // Check if a specific region is selected
    const selectedRegion = dataset.regions.find((r) => r.id === selectedRegionId);

    for (let r = 0; r < height; r++) {
      for (let c = 0; c < width; c++) {
        const idx = r * width + c;
        const pIdx = idx * 4;

        const elev = dem[idx];
        const s = slope[idx];
        const isP = psr[idx] > 0;

        if (elev <= nodata + 1.0 || isNaN(elev)) {
          // NoData / Sensor void - dark slate
          data[pIdx] = 20;
          data[pIdx + 1] = 24;
          data[pIdx + 2] = 33;
          data[pIdx + 3] = 255;
          continue;
        }

        // Base lunar regolith shading (grey basalt/anorthosite tones)
        const elevNorm = (elev - minElev) / Math.max(1, maxElev - minElev);
        let baseShade = 60 + elevNorm * 110 - Math.min(45, s * 2.2);
        baseShade = Math.max(25, Math.min(220, baseShade));

        if (showPsrOverlay && isP) {
          // Check if pixel belongs near the selected region
          let isSelectedPixel = false;
          if (selectedRegion) {
            const dist = Math.hypot(c - selectedRegion.pixelX, r - selectedRegion.pixelY);
            if (dist < 12) isSelectedPixel = true;
          }

          if (isSelectedPixel) {
            // Highlighted selected PSR: Electric cyan glow
            data[pIdx] = 6;
            data[pIdx + 1] = 182;
            data[pIdx + 2] = 212;
            data[pIdx + 3] = 255;
          } else {
            // Detected PSR cold trap: Deep luminous violet/indigo (#8b5cf6)
            data[pIdx] = Math.min(255, 139 + Math.floor(baseShade * 0.2));
            data[pIdx + 1] = Math.min(255, 92 + Math.floor(baseShade * 0.2));
            data[pIdx + 2] = 246;
            data[pIdx + 3] = 255;
          }
        } else {
          // Non-PSR terrain: Natural lunar surface
          data[pIdx] = baseShade;
          data[pIdx + 1] = baseShade + 2;
          data[pIdx + 2] = baseShade + 6;
          data[pIdx + 3] = 255;
        }
      }
    }

    ctx.putImageData(imgData, 0, 0);

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;
    texture.needsUpdate = true;
    return texture;
  }, [dataset, selectedRegionId, showPsrOverlay]);

  // Build terrain geometry
  const buildGeometry = useCallback(
    (exag: number) => {
      const { width, height, dem, minElev, maxElev, nodata } = dataset;
      const geo = new THREE.PlaneGeometry(SCENE_SIZE, SCENE_SIZE, width - 1, height - 1);
      geo.rotateX(-Math.PI / 2); // Orient horizontally

      const pos = geo.attributes.position;
      const elevSpan = Math.max(1, maxElev - minElev);

      for (let r = 0; r < height; r++) {
        for (let c = 0; c < width; c++) {
          const vertIdx = r * width + c;
          const elev = dem[vertIdx];
          const validElev = elev > nodata + 1.0 ? elev : minElev;
          const elevNorm = (validElev - minElev) / elevSpan;
          const y = elevNorm * 12.0 * exag;

          pos.setY(vertIdx, y);
        }
      }

      geo.computeVertexNormals();
      return geo;
    },
    [dataset]
  );

  // Initialize Three.js Scene
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const width = container.clientWidth;
    const height = container.clientHeight;

    // 1. Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x07090e);
    sceneRef.current = scene;

    // Subtle starfield
    const starGeo = new THREE.BufferGeometry();
    const starCount = 300;
    const starPositions = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount * 3; i += 3) {
      starPositions[i] = (Math.random() - 0.5) * 600;
      starPositions[i + 1] = Math.random() * 250 + 50;
      starPositions[i + 2] = (Math.random() - 0.5) * 600;
    }
    starGeo.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
    const starMat = new THREE.PointsMaterial({
      color: 0x94a3b8,
      size: 1.2,
      transparent: true,
      opacity: 0.6,
    });
    const stars = new THREE.Points(starGeo, starMat);
    scene.add(stars);

    // 2. Camera
    const camera = new THREE.PerspectiveCamera(40, width / height, 0.5, 1000);
    camera.position.set(0, 85, 110);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    // 3. Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    rendererRef.current = renderer;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // 4. OrbitControls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2.05; // Prevent camera from going under terrain
    controls.minDistance = 20;
    controls.maxDistance = 250;
    controlsRef.current = controls;

    // 5. Lighting
    // Ambient starlight/earthshine
    const ambientLight = new THREE.AmbientLight(0x0f172a, 0.7);
    scene.add(ambientLight);

    // Low-angle grazing lunar sunlight
    const sunLight = new THREE.DirectionalLight(0xfffaed, 2.5);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 10;
    sunLight.shadow.camera.far = 300;
    const d = 75;
    sunLight.shadow.camera.left = -d;
    sunLight.shadow.camera.right = d;
    sunLight.shadow.camera.top = d;
    sunLight.shadow.camera.bottom = -d;
    scene.add(sunLight);
    sunLightRef.current = sunLight;

    // 6. Terrain Mesh
    const geo = buildGeometry(verticalExag);
    terrainGeoRef.current = geo;

    const texture = generateTerrainTexture();
    const mat = new THREE.MeshStandardMaterial({
      map: texture,
      roughness: 0.85,
      metalness: 0.08,
      flatShading: false,
    });

    const terrainMesh = new THREE.Mesh(geo, mat);
    terrainMesh.receiveShadow = true;
    terrainMesh.castShadow = true;
    scene.add(terrainMesh);
    terrainMeshRef.current = terrainMesh;

    // 7. Group for PSR region pin markers
    const regionGroup = new THREE.Group();
    scene.add(regionGroup);
    regionMarkersRef.current = regionGroup;

    // 8. Group for Candidate Landing Site markers & 40m buffer rings
    const landingGroup = new THREE.Group();
    scene.add(landingGroup);
    landingSitesGroupRef.current = landingGroup;

    // 9. Group for picked touchdown spot marker & recommendation trajectory
    const pickedSpotGroup = new THREE.Group();
    scene.add(pickedSpotGroup);
    pickedSpotMarkerRef.current = pickedSpotGroup;

    // 8. Animation loop
    let animId: number;
    const animate = () => {
      animId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // 9. Resize handler
    const handleResize = () => {
      if (!container || !renderer || !camera) return;
      const nw = container.clientWidth;
      const nh = container.clientHeight;
      camera.aspect = nw / nh;
      camera.updateProjectionMatrix();
      renderer.setSize(nw, nh);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      geo.dispose();
      mat.dispose();
      texture?.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [dataset, buildGeometry, generateTerrainTexture]);

  // Update vertical exaggeration dynamically
  useEffect(() => {
    if (!terrainMeshRef.current) return;
    const newGeo = buildGeometry(verticalExag);
    terrainMeshRef.current.geometry.dispose();
    terrainMeshRef.current.geometry = newGeo;
    terrainGeoRef.current = newGeo;
  }, [verticalExag, buildGeometry]);

  // Update texture when selected region or overlay toggles
  useEffect(() => {
    if (!terrainMeshRef.current) return;
    const newTex = generateTerrainTexture();
    if (newTex) {
      const mat = terrainMeshRef.current.material as THREE.MeshStandardMaterial;
      mat.map?.dispose();
      mat.map = newTex;
      mat.needsUpdate = true;
    }
  }, [selectedRegionId, showPsrOverlay, generateTerrainTexture]);

  // Update low-angle sun position based on azimuth
  useEffect(() => {
    if (!sunLightRef.current) return;
    const rad = (sunAzimuth * Math.PI) / 180.0;
    const sunDist = 90;
    const sunHeight = 12; // Grazing low-angle south polar elevation (~1.5° - 2.0°)
    sunLightRef.current.position.set(
      Math.sin(rad) * sunDist,
      sunHeight,
      Math.cos(rad) * sunDist
    );
  }, [sunAzimuth]);

  // Update PSR region markers
  useEffect(() => {
    const group = regionMarkersRef.current;
    if (!group) return;

    // Clear old markers
    while (group.children.length > 0) {
      const child = group.children[0];
      group.remove(child);
    }

    if (!showPsrOverlay) return;

    const qualifyingRegions = dataset.regions.filter(
      (r) => r.areaKm2 >= (minAreaFilter || 0)
    );

    qualifyingRegions.forEach((region) => {
      const isSelected = region.id === selectedRegionId;
      const pos = gridTo3D(region.pixelX, region.pixelY, verticalExag);

      const marker = new THREE.Group();
      marker.position.set(pos.x, pos.y + 0.8, pos.z);

      // Pin head sphere
      const sphereGeo = new THREE.SphereGeometry(isSelected ? 1.4 : 0.9, 16, 16);
      const sphereMat = new THREE.MeshBasicMaterial({
        color: isSelected ? 0x06b6d4 : 0x8b5cf6,
      });
      const sphere = new THREE.Mesh(sphereGeo, sphereMat);
      sphere.position.y = 2.2;
      marker.add(sphere);

      // Pin stem
      const stemGeo = new THREE.CylinderGeometry(0.12, 0.12, 2.2, 8);
      const stemMat = new THREE.MeshBasicMaterial({
        color: isSelected ? 0x22d3ee : 0xa78bfa,
      });
      const stem = new THREE.Mesh(stemGeo, stemMat);
      stem.position.y = 1.1;
      marker.add(stem);

      // Base glow ring
      const ringGeo = new THREE.RingGeometry(0.8, 1.4, 16);
      ringGeo.rotateX(-Math.PI / 2);
      const ringMat = new THREE.MeshBasicMaterial({
        color: isSelected ? 0x06b6d4 : 0x8b5cf6,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: isSelected ? 0.9 : 0.45,
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.position.y = 0.05;
      marker.add(ring);

      group.add(marker);
    });
  }, [dataset, selectedRegionId, verticalExag, gridTo3D, showPsrOverlay, minAreaFilter]);

  // Update Start & Goal Markers
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;

    // Start Marker
    if (startMarkerRef.current) {
      scene.remove(startMarkerRef.current);
      startMarkerRef.current = null;
    }
    if (startPoint) {
      const pos = gridTo3D(startPoint.pixelX, startPoint.pixelY, verticalExag);
      const group = new THREE.Group();
      group.position.set(pos.x, pos.y + 0.2, pos.z);

      // Beacon cone
      const coneGeo = new THREE.ConeGeometry(1.2, 3.2, 8);
      coneGeo.rotateX(Math.PI);
      const coneMat = new THREE.MeshBasicMaterial({ color: 0x10b981 });
      const cone = new THREE.Mesh(coneGeo, coneMat);
      cone.position.y = 2.2;
      group.add(cone);

      // Base ring
      const ringGeo = new THREE.RingGeometry(1.0, 1.8, 16);
      ringGeo.rotateX(-Math.PI / 2);
      const ringMat = new THREE.MeshBasicMaterial({
        color: 0x10b981,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.8,
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.position.y = 0.1;
      group.add(ring);

      scene.add(group);
      startMarkerRef.current = group;
    }

    // Goal Marker
    if (goalMarkerRef.current) {
      scene.remove(goalMarkerRef.current);
      goalMarkerRef.current = null;
    }
    if (goalPoint) {
      const pos = gridTo3D(goalPoint.pixelX, goalPoint.pixelY, verticalExag);
      const group = new THREE.Group();
      group.position.set(pos.x, pos.y + 0.2, pos.z);

      // Beacon cone
      const coneGeo = new THREE.ConeGeometry(1.2, 3.2, 8);
      coneGeo.rotateX(Math.PI);
      const coneMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b });
      const cone = new THREE.Mesh(coneGeo, coneMat);
      cone.position.y = 2.2;
      group.add(cone);

      // Base ring
      const ringGeo = new THREE.RingGeometry(1.0, 1.8, 16);
      ringGeo.rotateX(-Math.PI / 2);
      const ringMat = new THREE.MeshBasicMaterial({
        color: 0xf59e0b,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.8,
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.position.y = 0.1;
      group.add(ring);

      scene.add(group);
      goalMarkerRef.current = group;
    }
  }, [startPoint, goalPoint, verticalExag, gridTo3D]);

  // Update Route Polyline in 3D
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;

    if (routeLineRef.current) {
      scene.remove(routeLineRef.current);
      routeLineRef.current = null;
    }

    if (routeResult && routeResult.feasible && routeResult.pathPoints.length > 1) {
      const points: THREE.Vector3[] = routeResult.pathPoints.map((pt) => {
        const v = gridTo3D(pt.pixelX, pt.pixelY, verticalExag);
        v.y += 0.5; // Drape slightly above surface to avoid z-fighting
        return v;
      });

      const lineGeo = new THREE.BufferGeometry().setFromPoints(points);
      const lineMat = new THREE.LineBasicMaterial({
        color: 0x06b6d4, // Glowing cyan rover traverse path
        linewidth: 3,
        transparent: true,
        opacity: 0.95,
      });

      const line = new THREE.Line(lineGeo, lineMat);
      scene.add(line);
      routeLineRef.current = line;
    }
  }, [routeResult, verticalExag, gridTo3D]);

  // Update Candidate Landing Sites and 40m Buffer Rings in 3D
  useEffect(() => {
    const group = landingSitesGroupRef.current;
    if (!group) return;

    while (group.children.length > 0) {
      const child = group.children[0];
      group.remove(child);
    }

    if (!showLandingSites || !dataset.landingSites) return;

    dataset.landingSites.forEach((site) => {
      const isSelected = site.id === selectedLandingSiteId;
      const pos = gridTo3D(site.pixelX, site.pixelY, verticalExag);

      const siteGroup = new THREE.Group();
      siteGroup.position.set(pos.x, pos.y, pos.z);

      // 1. Lunar Lander Model (Descent Stage)
      const lander = new THREE.Group();
      lander.position.y = 0.4;

      // Octagonal golden foil descent stage
      const baseGeo = new THREE.CylinderGeometry(0.8, 1.0, 0.6, 8);
      const baseMat = new THREE.MeshStandardMaterial({
        color: isSelected ? 0x06b6d4 : 0xf59e0b,
        metalness: 0.85,
        roughness: 0.25,
      });
      const base = new THREE.Mesh(baseGeo, baseMat);
      base.position.y = 0.5;
      lander.add(base);

      // Ascent stage / Crew hab sphere
      const habGeo = new THREE.SphereGeometry(0.55, 12, 12);
      const habMat = new THREE.MeshStandardMaterial({
        color: 0xf1f5f9,
        metalness: 0.3,
        roughness: 0.5,
      });
      const hab = new THREE.Mesh(habGeo, habMat);
      hab.position.y = 0.95;
      lander.add(hab);

      // Comms antenna / beacon
      const antGeo = new THREE.CylinderGeometry(0.04, 0.04, 0.8, 6);
      const antMat = new THREE.MeshBasicMaterial({ color: isSelected ? 0x22d3ee : 0xfde047 });
      const ant = new THREE.Mesh(antGeo, antMat);
      ant.position.y = 1.45;
      lander.add(ant);

      const beaconLightGeo = new THREE.SphereGeometry(0.12, 8, 8);
      const beaconLightMat = new THREE.MeshBasicMaterial({
        color: isSelected ? 0x38bdf8 : 0x10b981,
      });
      const beaconLight = new THREE.Mesh(beaconLightGeo, beaconLightMat);
      beaconLight.position.y = 1.85;
      lander.add(beaconLight);

      // 4 Angled Landing Legs with Footpads
      const legMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.8 });
      for (let i = 0; i < 4; i++) {
        const angle = (i * Math.PI) / 2 + Math.PI / 4;
        const legGeo = new THREE.CylinderGeometry(0.05, 0.05, 0.9, 6);
        const leg = new THREE.Mesh(legGeo, legMat);
        leg.position.set(Math.cos(angle) * 0.75, 0.35, Math.sin(angle) * 0.75);
        leg.rotation.z = Math.cos(angle) * 0.45;
        leg.rotation.x = -Math.sin(angle) * 0.45;
        lander.add(leg);

        const padGeo = new THREE.CylinderGeometry(0.18, 0.18, 0.04, 8);
        const pad = new THREE.Mesh(padGeo, legMat);
        pad.position.set(Math.cos(angle) * 1.05, 0.02, Math.sin(angle) * 1.05);
        lander.add(pad);
      }

      siteGroup.add(lander);

      // 2. 40-Meter Safety Clearance Buffer Ring
      const trueBufferRadius = (40.0 / dataset.pixelSizeM) * (SCENE_SIZE / (dataset.width - 1));
      const displayRadius = Math.max(2.6, trueBufferRadius * 3.0);

      const bufferRingGeo = new THREE.RingGeometry(displayRadius - 0.25, displayRadius + 0.1, 32);
      bufferRingGeo.rotateX(-Math.PI / 2);
      const bufferRingMat = new THREE.MeshBasicMaterial({
        color: isSelected ? 0x06b6d4 : 0x10b981,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: isSelected ? 0.95 : 0.65,
      });
      const bufferRing = new THREE.Mesh(bufferRingGeo, bufferRingMat);
      bufferRing.position.y = 0.08;
      siteGroup.add(bufferRing);

      // Inner disc fill
      const discGeo = new THREE.CircleGeometry(displayRadius - 0.25, 32);
      discGeo.rotateX(-Math.PI / 2);
      const discMat = new THREE.MeshBasicMaterial({
        color: isSelected ? 0x06b6d4 : 0x10b981,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: isSelected ? 0.2 : 0.08,
      });
      const disc = new THREE.Mesh(discGeo, discMat);
      disc.position.y = 0.06;
      siteGroup.add(disc);

      // If selected, add skyward guidance beacon
      if (isSelected) {
        const beamGeo = new THREE.CylinderGeometry(0.1, 0.5, 20, 16);
        const beamMat = new THREE.MeshBasicMaterial({
          color: 0x38bdf8,
          transparent: true,
          opacity: 0.35,
          side: THREE.DoubleSide,
        });
        const beam = new THREE.Mesh(beamGeo, beamMat);
        beam.position.y = 10;
        siteGroup.add(beam);
      }

      group.add(siteGroup);
    });
  }, [dataset, showLandingSites, selectedLandingSiteId, verticalExag, gridTo3D]);

  // Update User-Picked Landing Spot Marker and Recommendation Arc
  useEffect(() => {
    const scene = sceneRef.current;
    const group = pickedSpotMarkerRef.current;
    if (!scene || !group) return;

    while (group.children.length > 0) {
      const child = group.children[0];
      group.remove(child);
    }

    if (recommendationLineRef.current) {
      scene.remove(recommendationLineRef.current);
      recommendationLineRef.current = null;
    }

    if (!pickedLandingSpot) return;

    const pos = gridTo3D(pickedLandingSpot.pixelX, pickedLandingSpot.pixelY, verticalExag);
    const spotGroup = new THREE.Group();
    spotGroup.position.set(pos.x, pos.y + 0.1, pos.z);

    const isSafe = pickedLandingSpot.isSafe;
    const themeColor = isSafe ? 0x10b981 : 0xef4444;

    // 40m Clearance Buffer Ring
    const trueBufferRadius = (40.0 / dataset.pixelSizeM) * (SCENE_SIZE / (dataset.width - 1));
    const displayRadius = Math.max(2.6, trueBufferRadius * 3.0);

    const ringGeo = new THREE.RingGeometry(displayRadius - 0.25, displayRadius + 0.1, 32);
    ringGeo.rotateX(-Math.PI / 2);
    const ringMat = new THREE.MeshBasicMaterial({
      color: themeColor,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.9,
    });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    spotGroup.add(ring);

    // Inner buffer fill
    const discGeo = new THREE.CircleGeometry(displayRadius - 0.25, 32);
    discGeo.rotateX(-Math.PI / 2);
    const discMat = new THREE.MeshBasicMaterial({
      color: themeColor,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.22,
    });
    const disc = new THREE.Mesh(discGeo, discMat);
    spotGroup.add(disc);

    // Crosshair Reticle
    const crossGeo = new THREE.BufferGeometry();
    const armLen = displayRadius * 1.5;
    const crossPoints = [
      new THREE.Vector3(-armLen, 0.05, 0),
      new THREE.Vector3(armLen, 0.05, 0),
      new THREE.Vector3(0, 0.05, -armLen),
      new THREE.Vector3(0, 0.05, armLen),
    ];
    crossGeo.setFromPoints(crossPoints);
    const crossMat = new THREE.LineBasicMaterial({
      color: themeColor,
      linewidth: 2,
    });
    const crossLines = new THREE.LineSegments(crossGeo, crossMat);
    spotGroup.add(crossLines);

    // Center Touchdown Pointer Cone
    const pointerGeo = new THREE.ConeGeometry(0.8, 2.5, 6);
    pointerGeo.rotateX(Math.PI);
    const pointerMat = new THREE.MeshBasicMaterial({ color: themeColor });
    const pointer = new THREE.Mesh(pointerGeo, pointerMat);
    pointer.position.y = 2.4;
    spotGroup.add(pointer);

    group.add(spotGroup);

    // If Unsafe, render 3D parabolic trajectory arc diverting to recommended candidate site!
    if (!isSafe && recommendedSite) {
      const recPos = gridTo3D(recommendedSite.pixelX, recommendedSite.pixelY, verticalExag);

      const p1 = new THREE.Vector3(pos.x, pos.y + 1.0, pos.z);
      const p3 = new THREE.Vector3(recPos.x, recPos.y + 1.0, recPos.z);
      const midX = (pos.x + recPos.x) / 2;
      const midZ = (pos.z + recPos.z) / 2;
      const midY = Math.max(pos.y, recPos.y) + 18.0; // Suborbital parabolic trajectory peak
      const p2 = new THREE.Vector3(midX, midY, midZ);

      const curve = new THREE.QuadraticBezierCurve3(p1, p2, p3);
      const curvePoints = curve.getPoints(50);
      const arcGeo = new THREE.BufferGeometry().setFromPoints(curvePoints);
      const arcMat = new THREE.LineDashedMaterial({
        color: 0x38bdf8,
        dashSize: 1.5,
        gapSize: 0.8,
        linewidth: 2,
        transparent: true,
        opacity: 0.95,
      });
      const arcLine = new THREE.Line(arcGeo, arcMat);
      arcLine.computeLineDistances();
      scene.add(arcLine);
      recommendationLineRef.current = arcLine;
    }
  }, [pickedLandingSpot, recommendedSite, dataset, verticalExag, gridTo3D]);

  // Raycasting for click interaction & hover
  const handlePointerDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current || !cameraRef.current || !terrainMeshRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const mouseX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    const mouseY = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(new THREE.Vector2(mouseX, mouseY), cameraRef.current);

    const intersects = raycaster.intersectObject(terrainMeshRef.current);
    if (intersects.length > 0 && intersects[0].uv) {
      const uv = intersects[0].uv;
      const pixelX = Math.min(dataset.width - 1, Math.max(0, Math.round(uv.x * (dataset.width - 1))));
      // Flip Y because Three.js plane UV.y starts at bottom
      const pixelY = Math.min(
        dataset.height - 1,
        Math.max(0, Math.round((1.0 - uv.y) * (dataset.height - 1)))
      );

      // Handle point picking for candidate touchdown evaluation
      if (pickingLandingMode && onPickLandingSpot) {
        onPickLandingSpot(pixelX, pixelY);
        return;
      }

      // Check if user clicked on or near a Candidate Landing Site
      if (showLandingSites && onSelectLandingSite && dataset.landingSites) {
        let clickedSite: CandidateLandingSite | null = null;
        let minSiteDist = 14;
        for (const site of dataset.landingSites) {
          const d = Math.hypot(pixelX - site.pixelX, pixelY - site.pixelY);
          if (d < minSiteDist) {
            minSiteDist = d;
            clickedSite = site;
          }
        }
        if (clickedSite) {
          onSelectLandingSite(clickedSite);
          return;
        }
      }

      // Handle point picking for rover route
      if (pickingMode && onPickPoint) {
        onPickPoint(pickingMode, pixelX, pixelY);
        return;
      }

      // Check if user clicked on or near a PSR region
      let clickedRegion: PSRRegion | null = null;
      let minDistance = 14; // pixel threshold

      for (const r of dataset.regions) {
        const dist = Math.hypot(pixelX - r.pixelX, pixelY - r.pixelY);
        if (dist < minDistance) {
          minDistance = dist;
          clickedRegion = r;
        }
      }

      if (onSelectRegion) {
        onSelectRegion(clickedRegion);
      }
    }
  };

  const handlePointerMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current || !cameraRef.current || !terrainMeshRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const mouseX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    const mouseY = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(new THREE.Vector2(mouseX, mouseY), cameraRef.current);

    const intersects = raycaster.intersectObject(terrainMeshRef.current);
    if (intersects.length > 0 && intersects[0].uv) {
      const uv = intersects[0].uv;
      const px = Math.min(dataset.width - 1, Math.max(0, Math.round(uv.x * (dataset.width - 1))));
      const py = Math.min(
        dataset.height - 1,
        Math.max(0, Math.round((1.0 - uv.y) * (dataset.height - 1)))
      );
      const idx = py * dataset.width + px;

      const stereo = gridToStereo(px, py, dataset.bounds, dataset.pixelSizeM);
      const ll = stereoToLonLat(stereo.x, stereo.y);

      setHoverInfo({
        pixelX: px,
        pixelY: py,
        elevM: Number(dataset.dem[idx].toFixed(1)),
        slopeDeg: Number(dataset.slope[idx].toFixed(1)),
        isPSR: dataset.psr[idx] > 0,
        lat: ll.lat,
        lon: ll.lon,
      });
    } else {
      setHoverInfo(null);
    }
  };

  // Reset Camera View
  const handleResetCamera = (viewType: 'perspective' | 'top') => {
    if (!cameraRef.current || !controlsRef.current) return;
    if (viewType === 'top') {
      cameraRef.current.position.set(0, 140, 0.001);
      controlsRef.current.target.set(0, 0, 0);
    } else {
      cameraRef.current.position.set(0, 85, 110);
      controlsRef.current.target.set(0, 0, 0);
    }
    controlsRef.current.update();
  };

  return (
    <div className="relative w-full h-full bg-[#07090e] overflow-hidden select-none">
      {/* 3D WebGL Canvas Container */}
      <div
        ref={containerRef}
        id="three-terrain-canvas"
        onMouseDown={handlePointerDown}
        onMouseMove={handlePointerMove}
        className={`w-full h-full ${
          pickingMode || pickingLandingMode ? 'cursor-crosshair' : 'cursor-grab active:cursor-grabbing'
        }`}
      />

      {/* Active Sensor Scan Beam during PSR Analysis */}
      {isAnalyzing && (
        <div className="absolute inset-0 z-30 pointer-events-none flex flex-col items-center justify-center bg-blue-950/20 backdrop-blur-[1px]">
          <div className="w-80 h-80 rounded-full border-2 border-blue-400/50 animate-ping" />
          <div className="absolute w-96 h-96 rounded-full border border-cyan-400/30 animate-pulse" />
          <div className="mt-6 px-4 py-2 rounded-full bg-[#0a0f1d]/90 border border-blue-400 text-blue-300 font-mono text-xs shadow-2xl flex items-center gap-2.5 animate-bounce">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
            <span>ALIGNING LOLA PSR MASK AGAINST 240m ELEVATION GRID...</span>
          </div>
        </div>
      )}

      {/* LiDAR Surface Hazard Scanning Animation during Candidate Site Scan */}
      {isScanningLandingSites && (
        <div className="absolute inset-0 z-30 pointer-events-none flex flex-col items-center justify-center bg-emerald-950/20 backdrop-blur-[1px] overflow-hidden">
          <div className="w-96 h-96 rounded-full border-2 border-emerald-400/60 animate-ping" />
          <div className="absolute w-[32rem] h-[32rem] rounded-full border border-cyan-400/40 animate-pulse" />
          <div className="absolute w-72 h-72 rounded-full border border-emerald-300/30 animate-spin" />
          <div className="mt-8 px-5 py-3 rounded-xl bg-[#070b14]/95 border border-emerald-400/80 text-emerald-300 font-mono text-xs shadow-2xl flex flex-col items-center gap-2">
            <div className="flex items-center gap-2.5">
              <span className="w-3 h-3 rounded-full bg-emerald-400 animate-ping" />
              <span className="font-semibold tracking-wider uppercase text-emerald-200">
                AUTONOMOUS LIDAR SURFACE SCAN IN PROGRESS...
              </span>
            </div>
            <div className="text-[11px] text-emerald-400/80 flex items-center gap-3">
              <span>BUFFER: 40.0m RADIUS</span>
              <span>•</span>
              <span>SLOPE TOLERANCE: &le; 6.5°</span>
              <span>•</span>
              <span>GEAR CLEARANCE ENVELOPE: 100%</span>
            </div>
          </div>
        </div>
      )}

      {/* Picking Landing Spot Banner */}
      {pickingLandingMode && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 px-5 py-2.5 rounded-full bg-cyan-600/90 text-white text-xs font-mono font-medium border border-cyan-400 shadow-2xl flex items-center gap-2.5 animate-bounce">
          <Target className="w-4 h-4 text-cyan-200" />
          <span>CLICK ANYWHERE ON 3D TERRAIN TO TEST TOUCHDOWN SPOT (40m BUFFER)</span>
        </div>
      )}

      {/* Picking Mode Banner for Rover Route */}
      {pickingMode && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 px-4 py-2 rounded-full bg-blue-600/90 text-white text-xs font-medium border border-blue-400 shadow-lg flex items-center gap-2 animate-bounce">
          <Navigation className="w-3.5 h-3.5" />
          <span>Click anywhere on 3D terrain to place {pickingMode.toUpperCase()} point</span>
        </div>
      )}

      {/* Top Controls Overlay */}
      <div className="absolute top-4 left-4 z-10 flex items-center gap-2">
        <button
          onClick={() => handleResetCamera('perspective')}
          title="Reset 3D Perspective View"
          className="p-2 rounded bg-[#0d121c]/80 hover:bg-[#161f30] text-slate-300 hover:text-white border border-[#212c42] backdrop-blur-sm transition-colors text-xs flex items-center gap-1.5"
        >
          <RotateCcw className="w-3.5 h-3.5 text-blue-400" />
          <span>3D View</span>
        </button>
        <button
          onClick={() => handleResetCamera('top')}
          title="Top-Down Nadir View"
          className="p-2 rounded bg-[#0d121c]/80 hover:bg-[#161f30] text-slate-300 hover:text-white border border-[#212c42] backdrop-blur-sm transition-colors text-xs flex items-center gap-1.5"
        >
          <Compass className="w-3.5 h-3.5 text-cyan-400" />
          <span>Nadir View</span>
        </button>

        {/* Sun Angle Slider */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-[#0d121c]/80 border border-[#212c42] backdrop-blur-sm">
          <Sun className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-[11px] text-slate-400">Sun Azimuth:</span>
          <input
            type="range"
            min="0"
            max="360"
            value={sunAzimuth}
            onChange={(e) => setSunAzimuth(Number(e.target.value))}
            className="w-20 accent-amber-400 h-1 cursor-pointer"
          />
          <span className="text-[11px] font-mono text-slate-200">{sunAzimuth}°</span>
        </div>

        {/* Vertical Exaggeration Slider */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-[#0d121c]/80 border border-[#212c42] backdrop-blur-sm">
          <span className="text-[11px] text-slate-400">Z-Exag:</span>
          <input
            type="range"
            min="1.0"
            max="3.5"
            step="0.5"
            value={verticalExag}
            onChange={(e) => setVerticalExag(Number(e.target.value))}
            className="w-16 accent-blue-400 h-1 cursor-pointer"
          />
          <span className="text-[11px] font-mono text-slate-200">{verticalExag}x</span>
        </div>
      </div>

      {/* Hover Telemetry HUD */}
      {hoverInfo && (
        <div className="absolute bottom-4 left-4 z-10 px-3.5 py-2.5 rounded bg-[#0b0f19]/90 border border-[#1e273b] backdrop-blur-md text-[11px] font-mono shadow-xl space-y-1">
          <div className="flex items-center justify-between gap-4 text-slate-400">
            <span>COORDS:</span>
            <span className="text-slate-200">
              {Math.abs(hoverInfo.lat).toFixed(3)}°S, {hoverInfo.lon.toFixed(3)}°E
            </span>
          </div>
          <div className="flex items-center justify-between gap-4 text-slate-400">
            <span>ELEVATION:</span>
            <span
              className={
                hoverInfo.elevM <= dataset.nodata + 1.0
                  ? 'text-slate-500'
                  : 'text-blue-400 font-semibold'
              }
            >
              {hoverInfo.elevM <= dataset.nodata + 1.0 ? 'NODATA' : `${hoverInfo.elevM.toFixed(1)} m`}
            </span>
          </div>
          <div className="flex items-center justify-between gap-4 text-slate-400">
            <span>SLOPE:</span>
            <span
              className={
                hoverInfo.slopeDeg > 15
                  ? 'text-rose-400'
                  : hoverInfo.slopeDeg > 10
                  ? 'text-amber-400'
                  : 'text-emerald-400'
              }
            >
              {hoverInfo.slopeDeg.toFixed(1)}°
            </span>
          </div>
          <div className="flex items-center justify-between gap-4 text-slate-400">
            <span>STATUS:</span>
            <span
              className={`font-semibold ${
                hoverInfo.isPSR ? 'text-violet-400' : 'text-slate-300'
              }`}
            >
              {hoverInfo.isPSR ? 'PERMANENTLY SHADOWED' : 'SUNLIT / ILLUMINATED'}
            </span>
          </div>
        </div>
      )}

      {/* Minimal Scientific Legend */}
      <div className="absolute bottom-4 right-4 z-10 px-3 py-2.5 rounded bg-[#0b0f19]/90 border border-[#1e273b] backdrop-blur-md text-[11px] shadow-xl space-y-1.5">
        <div className="text-[10px] font-medium tracking-wider text-slate-400 uppercase font-mono mb-1">
          Terrain Classification
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-[#8b5cf6] shadow-[0_0_6px_#8b5cf6]" />
          <span className="text-slate-200">Permanently Shadowed (PSR)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-[#10b981]" />
          <span className="text-slate-200">Safe Corridor (&lt;10° Slope)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-[#f59e0b]" />
          <span className="text-slate-200">Moderate Slope (10°–15°)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-[#ef4444]" />
          <span className="text-slate-200">Steep Wall / Hazard (&gt;15°)</span>
        </div>
        {routeResult && routeResult.feasible && (
          <div className="pt-1 mt-1 border-t border-[#1e273b] flex items-center gap-2">
            <span className="w-3 h-0.5 bg-[#06b6d4] shadow-[0_0_6px_#06b6d4]" />
            <span className="text-cyan-300 font-mono">Calculated Rover Path</span>
          </div>
        )}
        {showLandingSites && (
          <div className="pt-1 mt-1 border-t border-[#1e273b] space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-sm bg-[#f59e0b] shadow-[0_0_6px_#f59e0b]" />
              <span className="text-amber-300">Candidate Landing Site</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full border border-[#10b981] bg-[#10b981]/30" />
              <span className="text-emerald-300">40m Safety Clearance Buffer</span>
            </div>
            {pickedLandingSpot && (
              <div className="flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full ${pickedLandingSpot.isSafe ? 'bg-emerald-400' : 'bg-rose-500 animate-ping'}`} />
                <span className={pickedLandingSpot.isSafe ? 'text-emerald-400' : 'text-rose-400'}>
                  {pickedLandingSpot.isSafe ? 'Touchdown Approved' : 'Hazard / Rollover Detected'}
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
