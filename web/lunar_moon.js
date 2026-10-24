/**
 * lunar_moon.js — Interactive 3D Lunar Intelligence Engine for OrbisLuna
 *
 * Implements:
 * 1. 3D Moon visualization using NASA Moon .glb model (with procedural fallback)
 * 2. Exact mathematical coordinate transformation:
 *    - Model Local XYZ (R=500) <-> Lunar Spherical (Lat, Lon)
 *    - Lunar Spherical <-> South Pole Polar Stereographic (IAU 2015 Sphere R=1,737,400m)
 *    - Polar Stereographic <-> Active Scientific Raster Grid (Easting, Northing -> Row, Col)
 * 3. Raycasting for hover tooltip & click-to-select exploration
 * 4. Smooth camera transitions (Slerp / Easing) to selected lunar regions
 * 5. Interactive terrain layers:
 *    - 'realistic': High-resolution NASA surface texture
 *    - 'elevation': Hypsometric elevation tint
 *    - 'slope': Slope heatmap (safe <5°, caution <10°, unsafe >=15°)
 *    - 'illumination': Solar visibility / illumination fraction
 *    - 'psr': Permanently Shadowed Regions cold traps
 *    - 'hazard': Classified hazard map (Safe, Caution, Unsafe, Shadow, NoData)
 *    - 'candidates': Landing ellipses & candidate markers
 * 6. 3D Candidate Site Markers & Artemis III Region Pins
 * 7. Synchronized event callbacks for Contextual Drawer & Regional Metrics
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.LunarMoon = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // Constants for Lunar Physics and Coordinate Systems
  const MOON_RADIUS_METERS = 1737400.0; // IAU 2015 Lunar Reference Spheroid (m)
  const SCENE_SPHERE_RADIUS = 500.0;    // GLB Model Radius in Three.js units

  // NASA Artemis III candidate region catalog (official Oct 2024 down-select)
  const ARTEMIS_REGIONS = [
    { id: 'artemis_peak_cabeus_b', name: 'Peak near Cabeus B', lat: -83.5732, lon: -69.0850, type: 'artemis' },
    { id: 'artemis_haworth', name: 'Haworth', lat: -86.7920, lon: -22.9474, type: 'artemis' },
    { id: 'artemis_malapert_massif', name: 'Malapert Massif', lat: -86.0434, lon: 0.1514, type: 'artemis' },
    { id: 'artemis_mons_mouton', name: 'Mons Mouton', lat: -85.3955, lon: 31.1899, type: 'artemis' },
    { id: 'artemis_mons_mouton_plateau', name: 'Mons Mouton Plateau', lat: -84.5061, lon: 30.5135, type: 'artemis' },
    { id: 'artemis_nobile_rim_1', name: 'Nobile Rim 1', lat: -85.1876, lon: 37.2379, type: 'artemis' },
    { id: 'artemis_nobile_rim_2', name: 'Nobile Rim 2', lat: -83.8864, lon: 58.4089, type: 'artemis' },
    { id: 'artemis_de_gerlache_rim_2', name: 'de Gerlache Rim 2', lat: -88.3691, lon: -67.4597, type: 'artemis' },
    { id: 'artemis_slater_plain', name: 'Slater Plain', lat: -87.2013, lon: 126.5711, type: 'artemis' },
    // South Pole Prominent Reference Features
    { id: 'shackleton', name: 'Shackleton Crater (89.9°S)', lat: -89.9000, lon: 0.0000, type: 'crater' },
    { id: 'faustini', name: 'Faustini Basin (87.3°S)', lat: -87.3000, lon: 77.0000, type: 'crater' },
    { id: 'malapert', name: 'Malapert Mountain (84.9°S)', lat: -84.9000, lon: 12.9000, type: 'crater' },
    { id: 'nobile', name: 'Nobile Crater Rim (VIPER Site)', lat: -85.2000, lon: 37.8000, type: 'crater' },
    { id: 'lola_crop', name: 'NASA LOLA South Pole ROI', lat: -89.5000, lon: 0.0000, type: 'lola' }
  ];

  class LunarMoonEngine {
    constructor() {
      this.container = null;
      this.scene = null;
      this.camera = null;
      this.renderer = null;
      this.controls = null;
      this.moonGroup = null;
      this.moonMesh = null;
      this.polarOverlayMesh = null;
      this.markersGroup = null;
      this.raycaster = null;
      this.mouse = null;
      this.sunLight = null;
      this.ambientLight = null;
      this.stars = null;

      this.activeLayer = 'realistic'; // 'realistic' | 'elevation' | 'slope' | 'illumination' | 'psr' | 'hazard' | 'candidates'
      this.activeRasterData = null;   // Active dataset bundle from /api/data
      this.candidateSites = [];       // Ranked candidate landing sites
      this.selectedLocation = null;
      this.hoveredFeature = null;

      this.animatingCamera = false;
      this.camTarget = null;
      this.camPosTarget = null;
      this.camAnimStart = 0;
      this.camAnimDuration = 1200;

      // Event listeners
      this.onLocationSelectedCallback = null;
      this.onHoverCallback = null;

      this.initialized = false;
    }

    /**
     * Initializes the 3D Moon viewport inside the target container element.
     */
    init(containerElement, onSelected, onHover) {
      if (!containerElement) return false;
      this.container = containerElement;
      this.onLocationSelectedCallback = onSelected;
      this.onHoverCallback = onHover;

      if (typeof THREE === 'undefined') {
        console.error('Three.js must be loaded before initializing LunarMoon');
        return false;
      }

      const width = this.container.clientWidth || 800;
      const height = this.container.clientHeight || 600;

      // 1. Scene
      this.scene = new THREE.Scene();
      this.scene.background = new THREE.Color(0x050B12);

      // 2. Camera
      this.camera = new THREE.PerspectiveCamera(40, width / height, 10, 8000);
      this.defaultCamPos = new THREE.Vector3(0, -320, 1450);
      this.defaultLookAt = new THREE.Vector3(0, -80, 0);
      this.camera.position.copy(this.defaultCamPos);
      this.camera.lookAt(this.defaultLookAt);

      // 3. Renderer
      this.renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: false,
        powerPreference: 'high-performance'
      });
      this.renderer.setSize(width, height);
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
      this.renderer.toneMappingExposure = 1.05;
      this.container.appendChild(this.renderer.domElement);

      // 4. OrbitControls
      if (typeof THREE.OrbitControls !== 'undefined') {
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.06;
        this.controls.rotateSpeed = 0.7;
        this.controls.zoomSpeed = 0.9;
        this.controls.panSpeed = 0.5;
        this.controls.minDistance = 550;  // Cannot zoom inside Moon surface (R=500)
        this.controls.maxDistance = 2800; // Cannot lose Moon in deep space
        this.controls.target.copy(this.defaultLookAt);
      }

      // 5. Lighting
      this.ambientLight = new THREE.AmbientLight(0x0e1b2a, 0.45);
      this.scene.add(this.ambientLight);

      this.sunLight = new THREE.DirectionalLight(0xfff8ee, 1.8);
      this.sunLight.position.set(1200, -300, 800);
      this.scene.add(this.sunLight);

      // Secondary soft fill light for night-side details
      const earthFillLight = new THREE.DirectionalLight(0x1a334d, 0.35);
      earthFillLight.position.set(-1000, 200, -500);
      this.scene.add(earthFillLight);

      // 6. Realistic Cosmic Starfield
      this.createStarfield();

      // 7. Moon Container Group
      this.moonGroup = new THREE.Group();
      this.scene.add(this.moonGroup);

      // 8. Markers Group
      this.markersGroup = new THREE.Group();
      this.moonGroup.add(this.markersGroup);

      // 9. Load Moon .glb Model
      this.loadMoonModel();

      // 10. Interaction Setup
      this.raycaster = new THREE.Raycaster();
      this.mouse = new THREE.Vector2();

      this.bindEvents();
      this.animate();
      this.initialized = true;
      return true;
    }

    /**
     * Builds a procedurally distributed realistic starfield background.
     */
    createStarfield() {
      const starCount = 1800;
      const positions = new Float32Array(starCount * 3);
      const colors = new Float32Array(starCount * 3);

      for (let i = 0; i < starCount; i++) {
        const theta = 2 * Math.PI * Math.random();
        const phi = Math.acos(2 * Math.random() - 1);
        const r = 3500 + Math.random() * 1500;

        positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
        positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
        positions[i * 3 + 2] = r * Math.cos(phi);

        // Subtle stellar temperature colors (blue-white to warm amber)
        const temp = Math.random();
        if (temp > 0.8) {
          colors[i * 3] = 0.7; colors[i * 3 + 1] = 0.85; colors[i * 3 + 2] = 1.0;
        } else if (temp < 0.2) {
          colors[i * 3] = 1.0; colors[i * 3 + 1] = 0.8; colors[i * 3 + 2] = 0.6;
        } else {
          colors[i * 3] = 0.95; colors[i * 3 + 1] = 0.95; colors[i * 3 + 2] = 1.0;
        }
      }

      const starGeometry = new THREE.BufferGeometry();
      starGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      starGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

      const starMaterial = new THREE.PointsMaterial({
        size: 1.6,
        vertexColors: true,
        transparent: true,
        opacity: 0.75
      });

      this.stars = new THREE.Points(starGeometry, starMaterial);
      this.scene.add(this.stars);
    }

    /**
     * Loads the provided Moon .glb model via GLTFLoader.
     * Falls back seamlessly to procedural textured sphere if unavailable.
     */
    loadMoonModel() {
      const glbUrl = '/assets/moon.glb';
      const textureUrl = '/assets/moon_texture.jpg';

      if (typeof THREE.GLTFLoader !== 'undefined') {
        const loader = new THREE.GLTFLoader();
        loader.load(
          glbUrl,
          (gltf) => {
            const rootNode = gltf.scene;
            let foundMesh = null;
            rootNode.traverse((child) => {
              if (child.isMesh && !foundMesh) {
                foundMesh = child;
              }
            });

            if (foundMesh) {
              this.moonMesh = foundMesh;
              // Ensure standard material properties
              if (this.moonMesh.material) {
                this.moonMesh.material.roughness = 0.92;
                this.moonMesh.material.metalness = 0.05;
              }
              this.moonGroup.add(this.moonMesh);
              this.alignMoonOrientation();
              this.initPolarOverlay();
              this.renderArtemisMarkers();
              console.log('[LunarMoon] Successfully loaded primary NASA Moon .glb model.');
            } else {
              this.createFallbackMoon(textureUrl);
            }
          },
          undefined,
          (err) => {
            console.warn('[LunarMoon] Primary GLB load returned fallback notice:', err);
            this.createFallbackMoon(textureUrl);
          }
        );
      } else {
        this.createFallbackMoon(textureUrl);
      }
    }

    /**
     * Procedural Fallback Moon using SphereGeometry + high-res texture.
     */
    createFallbackMoon(textureUrl) {
      console.log('[LunarMoon] Initializing procedural textured Moon sphere.');
      const geometry = new THREE.SphereGeometry(SCENE_SPHERE_RADIUS, 96, 96);
      
      const textureLoader = new THREE.TextureLoader();
      textureLoader.load(
        textureUrl,
        (texture) => {
          texture.anisotropy = 4;
          const material = new THREE.MeshStandardMaterial({
            map: texture,
            roughness: 0.92,
            metalness: 0.05
          });
          this.moonMesh = new THREE.Mesh(geometry, material);
          this.moonGroup.add(this.moonMesh);
          this.alignMoonOrientation();
          this.initPolarOverlay();
          this.renderArtemisMarkers();
        },
        undefined,
        () => {
          // High-contrast procedural cratered material if texture missing
          const canvas = document.createElement('canvas');
          canvas.width = 1024; canvas.height = 512;
          const ctx = canvas.getContext('2d');
          ctx.fillStyle = '#808791';
          ctx.fillRect(0, 0, 1024, 512);
          ctx.fillStyle = '#4c535e';
          for (let i = 0; i < 80; i++) {
            const x = Math.random() * 1024, y = Math.random() * 512, r = 5 + Math.random() * 45;
            ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
          }
          const proceduralTex = new THREE.CanvasTexture(canvas);
          const material = new THREE.MeshStandardMaterial({ map: proceduralTex, roughness: 0.95 });
          this.moonMesh = new THREE.Mesh(geometry, material);
          this.moonGroup.add(this.moonMesh);
          this.alignMoonOrientation();
          this.initPolarOverlay();
          this.renderArtemisMarkers();
        }
      );
    }

    /**
     * Aligns the Moon model so that:
     * - +Y is the North Pole (lat = +90°)
     * - -Y is the South Pole (lat = -90°)
     * - +Z is the Prime Meridian (lon = 0°, facing default camera)
     * - +X is Longitude 90° East
     * - -X is Longitude 90° West
     */
    alignMoonOrientation() {
      if (!this.moonMesh) return;
      // The NASA GLB prime meridian lies at angle 135° in local XZ plane.
      // Rotating by -45 degrees (-Math.PI / 4) aligns Prime Meridian directly along +Z axis.
      this.moonMesh.rotation.y = -Math.PI / 4;
    }

    /**
     * Initializes the dynamic polar scientific cap overlay that drapes over the
     * South Pole region (lat -75° to -90°) to faithfully display real scientific rasters.
     */
    initPolarOverlay() {
      if (this.polarOverlayMesh) {
        this.moonGroup.remove(this.polarOverlayMesh);
      }

      // Dome cap covering the South Pole (latitude -70° to -90°)
      // Cap radius is slightly elevated (+1.2 units) to prevent z-fighting
      const capRadius = SCENE_SPHERE_RADIUS + 1.2;
      const phiStart = Math.PI * 0.88; // ~79° South down to 90° South
      const phiLength = Math.PI * 0.12;

      const capGeo = new THREE.SphereGeometry(capRadius, 64, 32, 0, Math.PI * 2, phiStart, phiLength);
      
      this.overlayCanvas = document.createElement('canvas');
      this.overlayCanvas.width = 512;
      this.overlayCanvas.height = 512;
      this.overlayTexture = new THREE.CanvasTexture(this.overlayCanvas);
      this.overlayTexture.minFilter = THREE.LinearFilter;
      this.overlayTexture.magFilter = THREE.LinearFilter;

      const capMat = new THREE.MeshBasicMaterial({
        map: this.overlayTexture,
        transparent: true,
        opacity: 0.82,
        depthWrite: false,
        side: THREE.DoubleSide
      });

      this.polarOverlayMesh = new THREE.Mesh(capGeo, capMat);
      this.polarOverlayMesh.visible = (this.activeLayer !== 'realistic');
      this.moonGroup.add(this.polarOverlayMesh);

      this.updatePolarOverlayTexture();
    }

    /**
     * Paints the scientific layer onto the polar overlay texture canvas.
     */
    updatePolarOverlayTexture() {
      if (!this.overlayCanvas) return;
      const ctx = this.overlayCanvas.getContext('2d');
      const w = this.overlayCanvas.width;
      const h = this.overlayCanvas.height;
      ctx.clearRect(0, 0, w, h);

      if (this.activeLayer === 'realistic' || !this.activeRasterData) {
        if (this.polarOverlayMesh) this.polarOverlayMesh.visible = false;
        if (this.overlayTexture) this.overlayTexture.needsUpdate = true;
        return;
      }

      if (this.polarOverlayMesh) this.polarOverlayMesh.visible = true;

      const data = this.activeRasterData;
      const gridW = data.width || 250;
      const gridH = data.height || 250;
      const dem = data.dem || [];
      const slope = data.slope || [];
      const psr = data.psr || [];
      const hazardClasses = data.hazard_classes || [];
      const illumination = data.illumination || [];
      const nodata = data.nodata || -9999;

      const imgData = ctx.createImageData(w, h);
      const pixels = imgData.data;

      // Color palettes for scientific layers
      // Layer: 'hazard' -> Class 1 (Safe, #29E59A), Class 2 (Caution, #FFB52E), Class 3 (Unsafe, #FF5263), Class 4 (Shadow, #9B7BFF)
      for (let py = 0; py < h; py++) {
        const ry = Math.floor((py / h) * gridH);
        for (let px = 0; px < w; px++) {
          const rx = Math.floor((px / w) * gridW);
          const idx = ry * gridW + rx;
          const pIdx = (py * w + px) * 4;

          const dVal = dem[idx];
          if (dVal === nodata || isNaN(dVal) || dVal <= -9990) {
            pixels[pIdx + 3] = 0; // Transparent for nodata
            continue;
          }

          if (this.activeLayer === 'hazard') {
            const hClass = hazardClasses[idx] !== undefined ? hazardClasses[idx] : 1;
            if (hClass === 1) { // Safe
              pixels[pIdx] = 41; pixels[pIdx + 1] = 229; pixels[pIdx + 2] = 154; pixels[pIdx + 3] = 210;
            } else if (hClass === 2) { // Caution
              pixels[pIdx] = 255; pixels[pIdx + 1] = 181; pixels[pIdx + 2] = 46; pixels[pIdx + 3] = 210;
            } else if (hClass === 3) { // Unsafe
              pixels[pIdx] = 255; pixels[pIdx + 1] = 82; pixels[pIdx + 2] = 99; pixels[pIdx + 3] = 230;
            } else if (hClass === 4) { // Shadowed PSR
              pixels[pIdx] = 155; pixels[pIdx + 1] = 123; pixels[pIdx + 2] = 255; pixels[pIdx + 3] = 220;
            } else {
              pixels[pIdx + 3] = 0;
            }
          } else if (this.activeLayer === 'slope') {
            const sVal = slope[idx] || 0;
            const norm = Math.min(1.0, sVal / 25.0);
            // Green (low slope) -> Amber -> Red (steep)
            if (norm < 0.2) {
              pixels[pIdx] = 41; pixels[pIdx + 1] = 229; pixels[pIdx + 2] = 154; pixels[pIdx + 3] = 200;
            } else if (norm < 0.5) {
              pixels[pIdx] = 255; pixels[pIdx + 1] = 181; pixels[pIdx + 2] = 46; pixels[pIdx + 3] = 210;
            } else {
              pixels[pIdx] = 255; pixels[pIdx + 1] = 82; pixels[pIdx + 2] = 99; pixels[pIdx + 3] = 225;
            }
          } else if (this.activeLayer === 'elevation') {
            // Hypsometric tint
            const elevNorm = Math.min(1.0, Math.max(0.0, (dVal + 4000) / 6000));
            pixels[pIdx] = Math.floor(elevNorm * 50);
            pixels[pIdx + 1] = Math.floor(100 + elevNorm * 155);
            pixels[pIdx + 2] = Math.floor(200 + elevNorm * 55);
            pixels[pIdx + 3] = 200;
          } else if (this.activeLayer === 'psr' || this.activeLayer === 'shadow') {
            const pVal = psr[idx] || 0;
            if (pVal > 0) {
              pixels[pIdx] = 155; pixels[pIdx + 1] = 123; pixels[pIdx + 2] = 255; pixels[pIdx + 3] = 235;
            } else {
              pixels[pIdx + 3] = 20; // Very faint tint for sunlit
            }
          } else if (this.activeLayer === 'illumination') {
            const illum = illumination[idx] !== undefined ? illumination[idx] : 0.5;
            const b = Math.floor(illum * 255);
            pixels[pIdx] = b; pixels[pIdx + 1] = Math.floor(b * 0.95); pixels[pIdx + 2] = Math.floor(b * 0.7);
            pixels[pIdx + 3] = 210;
          } else if (this.activeLayer === 'candidates') {
            // Highlight candidates overlay
            pixels[pIdx + 3] = 0;
          }
        }
      }

      ctx.putImageData(imgData, 0, 0);
      if (this.overlayTexture) this.overlayTexture.needsUpdate = true;
    }

    /**
     * Renders 3D Markers on the lunar surface for Artemis III candidates & prominent craters.
     */
    renderArtemisMarkers() {
      if (!this.markersGroup) return;
      // Clear previous markers
      while (this.markersGroup.children.length > 0) {
        const obj = this.markersGroup.children[0];
        this.markersGroup.remove(obj);
      }

      const allTargets = [...ARTEMIS_REGIONS];
      
      // Also add any active candidate sites (Alpha, Beta, Gamma)
      if (this.candidateSites && this.candidateSites.length > 0) {
        this.candidateSites.forEach((site) => {
          allTargets.push({
            id: site.designation || site.name,
            name: site.name,
            lat: site.lat !== undefined ? site.lat : -89.85,
            lon: site.lon !== undefined ? site.lon : 0.05,
            type: 'candidate',
            suitability: site.suitability_pct,
            rank: site.rank
          });
        });
      }

      allTargets.forEach((target) => {
        const spherePos = this.latLonToSphere(target.lat, target.lon, SCENE_SPHERE_RADIUS + 2.5);

        // Marker container
        const markerObj = new THREE.Group();
        markerObj.position.set(spherePos.x, spherePos.y, spherePos.z);
        markerObj.userData = { ...target };

        // Normal vector pointing outwards from sphere center
        const normal = new THREE.Vector3(spherePos.x, spherePos.y, spherePos.z).normalize();

        // 1. Base Ring
        const ringColor = target.type === 'candidate' ? 0x29E59A : (target.type === 'artemis' ? 0x00D9F5 : 0xFFB52E);
        const ringGeo = new THREE.RingGeometry(2.0, 3.2, 24);
        const ringMat = new THREE.MeshBasicMaterial({
          color: ringColor,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.95
        });
        const ringMesh = new THREE.Mesh(ringGeo, ringMat);
        ringMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), normal);
        markerObj.add(ringMesh);

        // 2. Center Glowing Core
        const coreGeo = new THREE.SphereGeometry(1.6, 12, 12);
        const coreMat = new THREE.MeshBasicMaterial({
          color: ringColor
        });
        const coreMesh = new THREE.Mesh(coreGeo, coreMat);
        markerObj.add(coreMesh);

        // 3. Standoff Pin
        const pinHeight = 12.0;
        const pinGeo = new THREE.CylinderGeometry(0.3, 0.3, pinHeight, 8);
        const pinMat = new THREE.MeshBasicMaterial({
          color: ringColor,
          transparent: true,
          opacity: 0.7
        });
        const pinMesh = new THREE.Mesh(pinGeo, pinMat);
        pinMesh.position.addScaledVector(normal, pinHeight / 2);
        pinMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), normal);
        markerObj.add(pinMesh);

        this.markersGroup.add(markerObj);
      });
    }

    /**
     * Mathematical Coordinate Transformation:
     * Lunar Spherical (lat, lon in degrees) -> 3D Sphere Local Vector (x, y, z)
     */
    latLonToSphere(latDeg, lonDeg, radius = SCENE_SPHERE_RADIUS) {
      if (!Number.isFinite(latDeg) || !Number.isFinite(lonDeg)) {
        return { x: 0, y: -radius, z: 0 };
      }
      const phi = THREE.MathUtils.degToRad(latDeg);
      const lam = THREE.MathUtils.degToRad(lonDeg);

      // Model orientation:
      // +Y: North Pole (+90°)
      // -Y: South Pole (-90°)
      // +Z: Prime Meridian (0°)
      // +X: Longitude 90° East
      const x = radius * Math.cos(phi) * Math.sin(lam);
      const y = radius * Math.sin(phi);
      const z = radius * Math.cos(phi) * Math.cos(lam);

      return { x, y, z };
    }

    /**
     * Inverse Coordinate Transformation:
     * 3D Sphere Local Vector (x, y, z) -> Lunar Spherical (lat, lon in degrees)
     */
    sphereToLatLon(x, y, z) {
      if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) {
        return { lat: -89.9, lon: 0.0 };
      }
      const r = Math.sqrt(x * x + y * y + z * z);
      if (r === 0) return { lat: -90.0, lon: 0.0 };

      const latRad = Math.asin(Math.max(-1.0, Math.min(1.0, y / r)));
      const lonRad = Math.atan2(x, z);

      const latDeg = THREE.MathUtils.radToDeg(latRad);
      const lonDeg = THREE.MathUtils.radToDeg(lonRad);

      return {
        lat: Number.isFinite(latDeg) ? parseFloat(latDeg.toFixed(4)) : -89.9,
        lon: Number.isFinite(lonDeg) ? parseFloat(lonDeg.toFixed(4)) : 0.0
      };
    }

    /**
     * Map Lunar Spherical (lat, lon in degrees) -> South Pole Polar Stereographic (easting, northing in meters)
     * IAU 2015 Lunar Reference Spheroid (R=1,737,400m), lat_0 = -90°, lon_0 = 0°
     */
    latLonToStereo(latDeg, lonDeg) {
      if (!Number.isFinite(latDeg) || !Number.isFinite(lonDeg)) {
        return { easting: 0.0, northing: 0.0 };
      }
      const phi = THREE.MathUtils.degToRad(latDeg);
      const lam = THREE.MathUtils.degToRad(lonDeg);

      // Colatitude from South Pole:
      const c = Math.PI / 2 + phi; // 0 at South Pole, increases northward
      const rho = 2 * MOON_RADIUS_METERS * Math.tan(c / 2);

      const easting = rho * Math.sin(lam);
      const northing = rho * Math.cos(lam);

      return {
        easting: parseFloat(easting.toFixed(1)),
        northing: parseFloat(northing.toFixed(1))
      };
    }

    /**
     * Inverse: South Pole Polar Stereographic (easting, northing in meters) -> Lunar Spherical (lat, lon)
     */
    stereoToLatLon(eastingM, northingM) {
      if (!Number.isFinite(eastingM) || !Number.isFinite(northingM)) {
        return { lat: -89.9, lon: 0.0 };
      }
      const rho = Math.sqrt(eastingM * eastingM + northingM * northingM);
      const c = 2 * Math.atan(rho / (2 * MOON_RADIUS_METERS));
      const latRad = c - Math.PI / 2;
      const lonRad = Math.atan2(eastingM, northingM);

      const latDeg = THREE.MathUtils.radToDeg(latRad);
      const lonDeg = THREE.MathUtils.radToDeg(lonRad);

      return {
        lat: Number.isFinite(latDeg) ? parseFloat(latDeg.toFixed(4)) : -89.9,
        lon: Number.isFinite(lonDeg) ? parseFloat(lonDeg.toFixed(4)) : 0.0
      };
    }

    /**
     * Queries active scientific raster data at given coordinates.
     */
    queryScientificDataAt(latDeg, lonDeg) {
      const validLat = Number.isFinite(latDeg) ? latDeg : -89.9;
      const validLon = Number.isFinite(lonDeg) ? lonDeg : 0.0;
      const stereo = this.latLonToStereo(validLat, validLon);
      const result = {
        lat: validLat,
        lon: validLon,
        easting_m: stereo.easting,
        northing_m: stereo.northing,
        in_coverage: false,
        elevation_m: null,
        slope_deg: null,
        roughness_m: null,
        psr_flag: null,
        hazard_class: null,
        illumination_pct: null,
        suitability_score: null,
        dataset_name: 'NASA LRO LOLA South Pole Workspace',
        provenance: 'NASA Planetary Data System (240 m/px)'
      };

      if (!this.activeRasterData) {
        return result;
      }

      const d = this.activeRasterData;
      const bounds = d.bounds;
      if (!bounds) {
        return result;
      }

      // Support bounds as array [left, bottom, right, top] or object {left, bottom, right, top}
      const left = typeof bounds.left === 'number' ? bounds.left : bounds[0];
      const bottom = typeof bounds.bottom === 'number' ? bounds.bottom : bounds[1];
      const right = typeof bounds.right === 'number' ? bounds.right : bounds[2];
      const top = typeof bounds.top === 'number' ? bounds.top : bounds[3];

      if (left === undefined || bottom === undefined || right === undefined || top === undefined) {
        return result;
      }

      // Check if coordinate is within active raster bounds
      if (
        stereo.easting >= left &&
        stereo.easting <= right &&
        stereo.northing >= bottom &&
        stereo.northing <= top
      ) {
        const pxW = d.pixel_size_x || 240.0;
        const pxH = d.pixel_size_y || 240.0;
        const col = Math.floor((stereo.easting - left) / pxW);
        const row = Math.floor((top - stereo.northing) / pxH);

        if (col >= 0 && col < d.width && row >= 0 && row < d.height) {
          const idx = row * d.width + col;
          const nodata = d.nodata || -9999;
          const elev = d.dem ? d.dem[idx] : null;

          if (elev !== null && elev !== nodata && !isNaN(elev)) {
            result.in_coverage = true;
            result.elevation_m = parseFloat(elev.toFixed(1));
            result.slope_deg = d.slope ? parseFloat(d.slope[idx].toFixed(2)) : null;
            result.roughness_m = d.roughness ? parseFloat(d.roughness[idx].toFixed(2)) : null;
            result.psr_flag = d.psr ? (d.psr[idx] > 0 ? 1 : 0) : 0;
            result.hazard_class = d.hazard_classes ? d.hazard_classes[idx] : 1;
            result.illumination_pct = d.illumination
              ? parseFloat((d.illumination[idx] * 100).toFixed(1))
              : (result.psr_flag ? 0.0 : 65.0);
            
            // Continuous suitability score S = 1 - H (Strict PSR exclusion: cold traps are 100% unfit)
            if (result.slope_deg !== null && result.roughness_m !== null) {
              if (result.psr_flag === 1) {
                result.suitability_score = 0.0;
              } else {
                const sNorm = Math.min(1.0, result.slope_deg / 15.0);
                const rNorm = Math.min(1.0, result.roughness_m / 5.0);
                const hScore = 0.5 * sNorm + 0.3 * rNorm;
                result.suitability_score = parseFloat((Math.max(0, 1.0 - hScore) * 100).toFixed(1));
              }
            }
          }
        }
      }

      // Check nearest named crater or Artemis III region
      let nearestFeature = null;
      let minDistKm = 999999;
      ARTEMIS_REGIONS.forEach((r) => {
        const dLat = (r.lat - latDeg) * (Math.PI / 180);
        const dLon = (r.lon - lonDeg) * (Math.PI / 180);
        const a = Math.sin(dLat / 2) ** 2 + Math.cos(r.lat * Math.PI / 180) * Math.cos(latDeg * Math.PI / 180) * Math.sin(dLon / 2) ** 2;
        const distKm = (MOON_RADIUS_METERS / 1000) * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        if (distKm < minDistKm) {
          minDistKm = distKm;
          nearestFeature = r;
        }
      });

      result.nearest_feature = nearestFeature;
      result.dist_to_feature_km = parseFloat(minDistKm.toFixed(1));

      return result;
    }

    /**
     * Sets the active terrain visualization layer.
     */
    setLayer(layerName) {
      this.activeLayer = layerName;
      this.updatePolarOverlayTexture();
    }

    /**
     * Smoothly navigates camera to focus on given coordinates (lat, lon).
     */
    focusLocation(latDeg, lonDeg, distance = 780, durationMs = 1200) {
      if (!Number.isFinite(latDeg) || !Number.isFinite(lonDeg)) {
        console.warn('[LunarMoon] Invalid focus coordinates rejected:', latDeg, lonDeg);
        return;
      }
      const spherePos = this.latLonToSphere(latDeg, lonDeg, SCENE_SPHERE_RADIUS);
      const targetLookAt = new THREE.Vector3(spherePos.x, spherePos.y, spherePos.z);

      // Camera position offset along normal vector
      const normal = targetLookAt.clone().normalize();
      const targetCamPos = targetLookAt.clone().addScaledVector(normal, distance - SCENE_SPHERE_RADIUS);

      this.startCameraTransition(targetCamPos, targetLookAt, durationMs);
    }

    /**
     * Smoothly returns camera to the full-Moon executive overview.
     */
    resetView(durationMs = 1200) {
      this.startCameraTransition(this.defaultCamPos, this.defaultLookAt, durationMs);
      this.selectedLocation = null;
    }

    /**
     * Focus camera directly on the Lunar South Pole (89.9°S, 0°E).
     */
    focusSouthPole(durationMs = 1200) {
      this.focusLocation(-89.9, 0.0, 780, durationMs);
    }

    /**
     * Zoom camera in or out relative to current orbit target.
     */
    zoom(factor) {
      if (!this.camera || !this.controls) return;
      const target = this.controls.target;
      const offset = this.camera.position.clone().sub(target);
      const minD = this.controls.minDistance || 550;
      const maxD = this.controls.maxDistance || 2800;
      const newLen = THREE.MathUtils.clamp(offset.length() / factor, minD, maxD);
      offset.setLength(newLen);
      this.startCameraTransition(target.clone().add(offset), target, 450);
    }

    /**
     * Fly camera to named candidate landing site or Artemis region.
     */
    focusCandidate(designation) {
      const q = String(designation || '').toLowerCase().trim();
      if (!q) return null;

      // 1. Check loaded candidate sites
      if (this.candidateSites && this.candidateSites.length > 0) {
        const match = this.candidateSites.find(s =>
          (s.name && s.name.toLowerCase().includes(q)) ||
          (s.designation && s.designation.toLowerCase().includes(q))
        );
        if (match && typeof match.center_lat === 'number') {
          this.focusLocation(match.center_lat, match.center_lon, 680);
          return match;
        }
      }

      // 2. Check Artemis regions and prominent craters catalog
      const artemisMatch = ARTEMIS_REGIONS.find(r =>
        r.id.toLowerCase().includes(q) ||
        r.name.toLowerCase().includes(q)
      );
      if (artemisMatch) {
        this.focusLocation(artemisMatch.lat, artemisMatch.lon, 720);
        return artemisMatch;
      }
      return null;
    }

    /**
     * Trigger manual viewport resize.
     */
    onWindowResize() {
      if (!this.container || !this.camera || !this.renderer) return;
      const w = this.container.clientWidth;
      const h = this.container.clientHeight;
      if (w > 0 && h > 0) {
        this.camera.aspect = w / h;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(w, h);
      }
    }

    /**
     * Check if scientific dataset bundle is loaded.
     */
    hasScientificData() {
      return !!this.activeRasterData;
    }

    /**
     * Re-renders the draped polar overlay canvas with current dataset.
     */
    refreshOverlay() {
      this.updatePolarOverlayTexture();
    }

    /**
     * Internal smooth camera interpolation loop.
     */
    startCameraTransition(targetPos, targetLookAt, durationMs = 1200) {
      if (!this.camera || !targetPos || !targetLookAt) return;
      if (!Number.isFinite(targetPos.x) || !Number.isFinite(targetPos.y) || !Number.isFinite(targetPos.z) ||
          !Number.isFinite(targetLookAt.x) || !Number.isFinite(targetLookAt.y) || !Number.isFinite(targetLookAt.z)) {
        console.warn('[LunarMoon] Invalid camera target vectors discarded:', targetPos, targetLookAt);
        return;
      }
      this.camPosStart = this.camera.position.clone();
      this.camLookStart = this.controls ? this.controls.target.clone() : new THREE.Vector3();
      this.camPosTarget = targetPos.clone();
      this.camLookTarget = targetLookAt.clone();
      this.camAnimStart = performance.now();
      this.camAnimDuration = Math.max(100, durationMs);
      this.animatingCamera = true;
    }

    /**
     * Updates solar light position based on azimuth and elevation angles.
     */
    setSunPosition(azimuthDeg, elevationDeg) {
      const azRad = THREE.MathUtils.degToRad(azimuthDeg);
      const elRad = THREE.MathUtils.degToRad(elevationDeg);
      const dist = 1400;

      const x = dist * Math.cos(elRad) * Math.sin(azRad);
      const y = -dist * Math.sin(elRad); // South pole lighting
      const z = dist * Math.cos(elRad) * Math.cos(azRad);

      if (this.sunLight) {
        this.sunLight.position.set(x, y, z);
      }
    }

    /**
     * Updates active scientific dataset bundle.
     */
    setScientificData(bundleData) {
      this.activeRasterData = bundleData;
      if (bundleData.landing_sites) {
        this.candidateSites = Array.isArray(bundleData.landing_sites)
          ? bundleData.landing_sites
          : (bundleData.landing_sites.top_sites || []);
      }
      this.updatePolarOverlayTexture();
      this.renderArtemisMarkers();
    }

    /**
     * Pointer and Interaction event bindings.
     */
    bindEvents() {
      const dom = this.renderer.domElement;

      dom.addEventListener('pointermove', (e) => this.onPointerMove(e));
      dom.addEventListener('click', (e) => this.onPointerClick(e));

      window.addEventListener('resize', () => {
        if (!this.container) return;
        const w = this.container.clientWidth;
        const h = this.container.clientHeight;
        if (w > 0 && h > 0) {
          this.camera.aspect = w / h;
          this.camera.updateProjectionMatrix();
          this.renderer.setSize(w, h);
        }
      });
    }

    getPointerPos(e) {
      const rect = this.renderer.domElement.getBoundingClientRect();
      this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      return { clientX: e.clientX, clientY: e.clientY };
    }

    onPointerMove(e) {
      const pos = this.getPointerPos(e);
      this.raycaster.setFromCamera(this.mouse, this.camera);

      // Check markers first
      const markerHits = this.raycaster.intersectObjects(this.markersGroup.children, true);
      if (markerHits.length > 0) {
        let parentMarker = markerHits[0].object;
        while (parentMarker.parent && parentMarker.parent !== this.markersGroup) {
          parentMarker = parentMarker.parent;
        }
        if (parentMarker.userData && parentMarker.userData.name) {
          this.renderer.domElement.style.cursor = 'pointer';
          if (this.onHoverCallback) {
            this.onHoverCallback({
              type: 'marker',
              data: parentMarker.userData,
              clientX: pos.clientX,
              clientY: pos.clientY
            });
          }
          return;
        }
      }

      // Check Moon surface mesh
      if (this.moonMesh) {
        const hits = this.raycaster.intersectObject(this.moonMesh, true);
        if (hits.length > 0) {
          this.renderer.domElement.style.cursor = 'crosshair';
          const hitPoint = hits[0].point;
          const coords = this.sphereToLatLon(hitPoint.x, hitPoint.y, hitPoint.z);
          const telemetry = this.queryScientificDataAt(coords.lat, coords.lon);

          if (this.onHoverCallback) {
            this.onHoverCallback({
              type: 'surface',
              telemetry: telemetry,
              clientX: pos.clientX,
              clientY: pos.clientY
            });
          }
          return;
        }
      }

      this.renderer.domElement.style.cursor = 'default';
      if (this.onHoverCallback) {
        this.onHoverCallback(null);
      }
    }

    onPointerClick(e) {
      this.getPointerPos(e);
      this.raycaster.setFromCamera(this.mouse, this.camera);

      // Check markers first
      const markerHits = this.raycaster.intersectObjects(this.markersGroup.children, true);
      if (markerHits.length > 0) {
        let parentMarker = markerHits[0].object;
        while (parentMarker.parent && parentMarker.parent !== this.markersGroup) {
          parentMarker = parentMarker.parent;
        }
        const siteData = parentMarker.userData;
        if (siteData && siteData.lat !== undefined) {
          this.focusLocation(siteData.lat, siteData.lon, 680);
          const telemetry = this.queryScientificDataAt(siteData.lat, siteData.lon);
          telemetry.feature_name = siteData.name;
          telemetry.feature_type = siteData.type;
          telemetry.site_id = siteData.id;
          telemetry.site_data = siteData;
          telemetry.is_marker = true;
          this.selectedLocation = telemetry;

          if (this.onLocationSelectedCallback) {
            this.onLocationSelectedCallback(telemetry);
          }
          return;
        }
      }

      // Check Moon surface mesh
      if (this.moonMesh) {
        const hits = this.raycaster.intersectObject(this.moonMesh, true);
        if (hits.length > 0) {
          const hitPoint = hits[0].point;
          const coords = this.sphereToLatLon(hitPoint.x, hitPoint.y, hitPoint.z);
          const telemetry = this.queryScientificDataAt(coords.lat, coords.lon);
          this.selectedLocation = telemetry;

          // Focus smoothly towards selected point
          this.focusLocation(coords.lat, coords.lon, 720);

          if (this.onLocationSelectedCallback) {
            this.onLocationSelectedCallback(telemetry);
          }
        }
      }
    }

    /**
     * Animation and Render Loop.
     */
    animate() {
      requestAnimationFrame(() => this.animate());

      // Smooth camera transition interpolation
      if (this.animatingCamera) {
        const now = performance.now();
        const elapsed = now - this.camAnimStart;
        const progress = Math.min(1.0, elapsed / this.camAnimDuration);

        // Smooth cubic ease-in-out
        const t = progress < 0.5
          ? 4 * progress * progress * progress
          : 1 - Math.pow(-2 * progress + 2, 3) / 2;

        if (this.camPosStart && this.camPosTarget) {
          this.camera.position.lerpVectors(this.camPosStart, this.camPosTarget, t);
        }
        if (this.controls && this.camLookStart && this.camLookTarget) {
          this.controls.target.lerpVectors(this.camLookStart, this.camLookTarget, t);
          this.controls.update();
        }

        if (progress >= 1.0) {
          this.animatingCamera = false;
        }
      } else if (this.controls) {
        this.controls.update();
      }

      // Self-healing recovery if camera coordinates ever corrupt
      if (this.camera && (!Number.isFinite(this.camera.position.x) || !Number.isFinite(this.camera.position.y) || !Number.isFinite(this.camera.position.z))) {
        console.error('[LunarMoon] Camera matrix corrupted, restoring default overview position.');
        this.camera.position.copy(this.defaultCamPos);
        if (this.controls) {
          this.controls.target.copy(this.defaultLookAt);
          this.controls.update();
        }
        this.animatingCamera = false;
      }

      this.renderer.render(this.scene, this.camera);
    }
  }

  return new LunarMoonEngine();
});
