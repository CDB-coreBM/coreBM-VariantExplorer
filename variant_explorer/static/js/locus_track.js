// Broad Native IGV.js Multi-Track Genomic Browser Module
// Hospital Clínic de Barcelona - CoreBM Variant Explorer

let igvBrowserInstance = null;
let isIgvInitializing = false;
let igvCachedTracks = {
  refseq: null,
  cmrg: null,
  coverage: null,
  bam: null,
  sv: null,
  snvCmrg: null,
  snvGiab: null,
  meth: null
};

const IGV_PRESETS = {
  'TP53': { locus: 'chr17:7,668,000-7,688,000', chrom: 'chr17', start: 7668000, end: 7688000, label: 'TP53 (Guardian of the Genome)' },
  'BRCA1': { locus: 'chr17:43,040,000-43,130,000', chrom: 'chr17', start: 43040000, end: 43130000, label: 'BRCA1 (DNA Repair)' },
  'BRCA2': { locus: 'chr13:32,315,000-32,400,000', chrom: 'chr13', start: 32315000, end: 32400000, label: 'BRCA2 (Homologous Recombination)' },
  'MLH1': { locus: 'chr3:36,990,000-37,055,000', chrom: 'chr3', start: 36990000, end: 37055000, label: 'MLH1 (Lynch Syndrome / Promoter 5mC)' },
  'MSH2': { locus: 'chr2:47,400,000-47,710,000', chrom: 'chr2', start: 47400000, end: 47710000, label: 'MSH2 (MMR-D / 14kb Deletion Locus)' },
  'CYP2D6': { locus: 'chr22:42,125,000-42,135,000', chrom: 'chr22', start: 42125000, end: 42135000, label: 'CYP2D6 (Pharmacogenomics)' },
  'EGFR': { locus: 'chr7:55,015,000-55,215,000', chrom: 'chr7', start: 55015000, end: 55215000, label: 'EGFR (L858R / Exon 19 del Locus)' },
  'KRAS': { locus: 'chr12:25,200,000-25,255,000', chrom: 'chr12', start: 25200000, end: 25255000, label: 'KRAS (Codon 12/13 Hotspots)' },
  'HBA': { locus: 'chr16:170,000-185,000', chrom: 'chr16', start: 170000, end: 185000, label: 'HBA1/HBA2 (Alpha-Thalassemia Locus)' },
  'BCR-ABL1': { locus: 'chr9:130,710,000-130,890,000', chrom: 'chr9', start: 130710000, end: 130890000, label: 'BCR::ABL1 Translocation Breakpoint' },
  '8p23.1-INV': { locus: 'chr8:8,000,000-12,500,000', chrom: 'chr8', start: 8000000, end: 12500000, label: '8p23.1 Recurrent Inversion (3.85 Mb)' },
  'H19-ASM': { locus: 'chr11:1,975,000-1,985,000', chrom: 'chr11', start: 1975000, end: 1985000, label: 'H19/IGF2 Imprinting ICR1 ASM' }
};

// -------------------------------------------------------------
// Global Entry Points (Immediately available on window)
// -------------------------------------------------------------
window.jumpToLocus = function(chrom, pos) {
  const c = chrom || 'chr17';
  const p = Number(pos) || 7668000;
  const start = Math.max(1, p - 10000);
  const end = p + 10000;
  const target = `${c}:${start}-${end}`;

  // Update form inputs
  const cInput = document.getElementById('locusChromInput');
  const sInput = document.getElementById('locusStartInput');
  const eInput = document.getElementById('locusEndInput');
  if (cInput) cInput.value = c;
  if (sInput) sInput.value = start;
  if (eInput) eInput.value = end;

  // Switch to locus view tab if not active
  document.querySelectorAll('.sidebar-item').forEach((i) => i.classList.remove('active'));
  document.querySelectorAll('.view-section').forEach((v) => v.classList.remove('active'));
  const navItem = document.querySelector('.sidebar-item[data-view="locus-view"]');
  if (navItem) navItem.classList.add('active');
  const locusView = document.getElementById('locus-view');
  if (locusView) locusView.classList.add('active');
  if (typeof AppState !== 'undefined') AppState.currentView = 'locus-view';

  if (igvBrowserInstance) {
    igvBrowserInstance.search(target).catch(err => {
      console.warn("IGV search failed, reinitializing:", err);
      initNativeIgv(target);
    });
  } else {
    initNativeIgv(target);
  }
};

window.jumpToIgvPreset = function(gene) {
  const preset = IGV_PRESETS[gene];
  if (!preset) return;

  const cInput = document.getElementById('locusChromInput');
  const sInput = document.getElementById('locusStartInput');
  const eInput = document.getElementById('locusEndInput');
  if (cInput) cInput.value = preset.chrom;
  if (sInput) sInput.value = preset.start;
  if (eInput) eInput.value = preset.end;

  if (igvBrowserInstance) {
    igvBrowserInstance.search(preset.locus).catch(() => initNativeIgv(preset.locus));
  } else {
    initNativeIgv(preset.locus);
  }

  if (typeof showToast === 'function') {
    showToast(`Loaded ${preset.label}`, 'info');
  }
};

// Aliases for compatibility
window.initIgvBrowser = function(chrom, start, end) {
  let locus = null;
  if (chrom && start && end) {
    locus = `${chrom}:${start}-${end}`;
  }
  return initNativeIgv(locus);
};

// -------------------------------------------------------------
// Native Broad IGV.js Initializer
// -------------------------------------------------------------
async function initNativeIgv(targetLocus = null) {
  if (isIgvInitializing) return;

  const container = document.getElementById('igvBrowserContainer');
  if (!container) return;

  const cInput = document.getElementById('locusChromInput');
  const sInput = document.getElementById('locusStartInput');
  const eInput = document.getElementById('locusEndInput');

  let chrom = (cInput && cInput.value.trim()) || 'chr17';
  let start = (sInput && parseInt(sInput.value.trim())) || 7668000;
  let end = (eInput && parseInt(eInput.value.trim())) || 7688000;
  if (start >= end) end = start + 20000;

  const locus = targetLocus || `${chrom}:${start}-${end}`;

  // If browser already exists, just search the new locus
  if (igvBrowserInstance) {
    try {
      await igvBrowserInstance.search(locus);
      updateStatusIndicator(locus);
      return;
    } catch (err) {
      console.warn("IGV navigate failed, recreating browser instance...", err);
      igvBrowserInstance = null;
    }
  }

  isIgvInitializing = true;
  container.innerHTML = `
    <div style="text-align: center; color: #94a3b8; padding: 6rem 1rem;">
      <div class="spinner" style="margin: 0 auto 0.75rem auto;"></div>
      <div>Loading Broad IGV.js multi-track browser with Phased Long Reads & VCF tracks...</div>
    </div>
  `;

  try {
  if (!AppState.activeCaseId) {
    container.innerHTML = `
      <div style="text-align: center; color: #94a3b8; padding: 6rem 1rem;">
        <i class="fa-solid fa-folder-open" style="font-size: 2.5rem; margin-bottom: 0.85rem; color: #64748b; display: block;"></i>
        <div style="font-size: 1.1rem; font-weight: 700; color: #ffffff; margin-bottom: 0.5rem;">No Clinical Case Selected</div>
        <div style="font-size: 0.85rem; color: #94a3b8; max-width: 480px; margin: 0 auto 1.25rem auto;">
          Please select an active clinical case from the header dropdown to initialize Broad IGV.js with patient-specific phased long-read alignments and variant tracks.
        </div>
      </div>
    `;
    return;
  }

  const caseId = AppState.activeCaseId;
  const res = await fetch(`/api/igv/config?case_id=${caseId}&locus=${encodeURIComponent(locus)}`);
  const data = await res.json();
  const config = data.config || {};

  // Cache track configurations from backend
  const tracks = config.tracks || [];
  tracks.forEach(t => {
    const name = t.name || '';
    if (t.format === 'bam' || t.type === 'alignment') igvCachedTracks.bam = t;
    else if (name.includes('Coverage') || t.format === 'bedgraph' || t.type === 'wig') igvCachedTracks.coverage = t;
    else if (t.format === 'refgene' || name === 'NCBI RefSeq Genes') igvCachedTracks.refseq = t;
    else if (name.includes('CMRG') && t.format === 'bed') igvCachedTracks.cmrg = t;
    else if (name.includes('CMRG SNVs')) igvCachedTracks.snvCmrg = t;
    else if (name.includes('Small Variants') || name.includes('GIAB')) igvCachedTracks.snvGiab = t;
    else if (name.includes('SV Benchmark') || name.includes('SV')) igvCachedTracks.sv = t;
    else if (name.includes('Methylation') || name.includes('5mC')) igvCachedTracks.meth = t;
  });

  // Check toggle states: BAM is NOT loaded by default to prevent overcomputing
  const bamCb = document.getElementById('trackToggleBam');
  const genesCb = document.getElementById('trackToggleGenes');
  const covCb = document.getElementById('trackToggleCoverage');
  const snvCb = document.getElementById('trackToggleSnv');
  const svCb = document.getElementById('trackToggleSv');
  const methCb = document.getElementById('trackToggleMeth');

  const shouldLoadBam = bamCb ? bamCb.checked : false; // Default: false
  const shouldLoadGenes = genesCb ? genesCb.checked : true;
  const shouldLoadCov = covCb ? covCb.checked : true;
  const shouldLoadSnv = snvCb ? snvCb.checked : true;
  const shouldLoadSv = svCb ? svCb.checked : true;
  const shouldLoadMeth = methCb ? methCb.checked : true;

  const initialTracks = [];
  if (shouldLoadGenes) {
    if (igvCachedTracks.refseq) initialTracks.push(igvCachedTracks.refseq);
    if (igvCachedTracks.cmrg) initialTracks.push(igvCachedTracks.cmrg);
  }
  if (shouldLoadCov && igvCachedTracks.coverage) initialTracks.push(igvCachedTracks.coverage);
  if (shouldLoadBam && igvCachedTracks.bam) initialTracks.push(igvCachedTracks.bam);
  if (shouldLoadSv && igvCachedTracks.sv) initialTracks.push(igvCachedTracks.sv);
  if (shouldLoadSnv) {
    if (igvCachedTracks.snvCmrg) initialTracks.push(igvCachedTracks.snvCmrg);
    if (igvCachedTracks.snvGiab) initialTracks.push(igvCachedTracks.snvGiab);
  }
  if (shouldLoadMeth && igvCachedTracks.meth) initialTracks.push(igvCachedTracks.meth);

  const activeConfig = Object.assign({}, config, { tracks: initialTracks });

    // Override container and ensure native configuration
    container.innerHTML = '';
    
    if (window.igv && typeof window.igv.createBrowser === 'function') {
      try {
        const igvPromise = window.igv.createBrowser(container, activeConfig);
        const timeoutPromise = new Promise(function(_, reject) {
          setTimeout(function() { reject(new Error("Reference loading timeout")); }, 3500);
        });
        igvBrowserInstance = await Promise.race([igvPromise, timeoutPromise]);
      } catch (refErr) {
        console.warn("Standard reference loading failed/timed out, falling back to local offline chromsizes:", refErr);
        container.innerHTML = '';
        const fallbackConfig = Object.assign({}, activeConfig, {
          reference: {
            id: "hg38",
            name: "Human (GRCh38 / hg38)",
            cytobandURL: "/static/vendor/cytoBand.txt",
            aliasURL: "/static/vendor/hg38_alias.tab",
            format: "chromsizes",
            fastaURL: "/static/vendor/hg38_chromsizes.txt"
          }
        });
        igvBrowserInstance = await window.igv.createBrowser(container, fallbackConfig);
      }
      updateStatusIndicator(locus);

      // Listen for feature clicks to display in inspector panel
      if (igvBrowserInstance && typeof igvBrowserInstance.on === 'function') {
        igvBrowserInstance.on('trackclick', function(track, popoverData) {
          renderFeatureInspector(track, popoverData);
        });
      }
    } else {
      container.innerHTML = `
        <div style="padding: 2rem; color: #ef4444; text-align: center;">
          <i class="fa-solid fa-triangle-exclamation" style="font-size: 2rem; margin-bottom: 0.5rem;"></i>
          <div>IGV.js library could not be loaded from local vendor scripts.</div>
        </div>
      `;
    }
  } catch (err) {
    console.error("Failed to initialize Broad IGV.js:", err);
    container.innerHTML = `
      <div style="padding: 2rem; color: #f59e0b; text-align: center; background: #0f172a; border-radius: 8px; margin: 1rem;">
        <i class="fa-solid fa-circle-exclamation" style="font-size: 2rem; margin-bottom: 0.5rem;"></i>
        <div style="font-weight: 700; margin-bottom: 0.5rem;">IGV.js Track Initialization Note</div>
        <div style="font-size: 0.85rem; color: #94a3b8; max-width: 600px; margin: 0 auto 1rem auto;">
          ${err.message || 'Error configuring genomic streaming tracks.'}
        </div>
        <button class="btn btn-teal" onclick="initNativeIgv()">
          <i class="fa-solid fa-arrows-rotate"></i> Retry Initializing IGV
        </button>
      </div>
    `;
  } finally {
    isIgvInitializing = false;
  }
}

function updateStatusIndicator(locus) {
  const indicator = document.getElementById('igvStatusIndicator');
  if (indicator) {
    indicator.innerHTML = `<i class="fa-solid fa-circle-check"></i> Broad IGV.js Active: <strong>${locus}</strong>`;
    indicator.style.color = '#10b981';
  }
}

function renderFeatureInspector(track, popoverData) {
  const panel = document.getElementById('igvVariantInspector');
  if (!panel) return;

  if (!popoverData || popoverData.length === 0) {
    panel.style.display = 'none';
    return;
  }

  const trackName = track ? (track.name || track.id || 'Genomic Feature') : 'Genomic Feature';
  let rowsHtml = popoverData.map(item => `
    <div style="display: flex; gap: 0.5rem; font-size: 0.8rem; padding: 0.2rem 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
      <span style="color: #94a3b8; min-width: 120px; font-weight: 600;">${item.name || ''}:</span>
      <span style="color: #ffffff; font-family: monospace;">${item.value !== undefined ? item.value : (item.html || '')}</span>
    </div>
  `).join('');

  panel.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; border-bottom: 1px solid #334155; padding-bottom: 0.35rem;">
      <span style="font-size: 0.85rem; font-weight: 700; color: #38bdf8;">
        <i class="fa-solid fa-crosshairs"></i> Selected Feature: ${trackName}
      </span>
      <button class="btn btn-secondary" style="padding: 0.1rem 0.4rem; font-size: 0.7rem;" onclick="document.getElementById('igvVariantInspector').style.display='none'">
        <i class="fa-solid fa-xmark"></i> Close
      </button>
    </div>
    <div style="max-height: 180px; overflow-y: auto;">
      ${rowsHtml}
    </div>
  `;
  panel.style.display = 'block';
}

// -------------------------------------------------------------
// Live Dynamic Gene Search with Autocomplete
// -------------------------------------------------------------
function setupLocusGeneSearch() {
  const input = document.getElementById('locusGeneSearchInput');
  const dropdown = document.getElementById('locusGeneDropdown');
  if (!input || !dropdown) return;

  let debounceTimer = null;

  input.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const q = input.value.trim();
    if (q.length === 0) {
      dropdown.style.display = 'none';
      dropdown.innerHTML = '';
      return;
    }

    debounceTimer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/genes/search?q=${encodeURIComponent(q)}&limit=12`);
        const data = await res.json();
        const genes = data.genes || [];

        if (genes.length === 0) {
          dropdown.innerHTML = `
            <div style="padding: 0.6rem 0.8rem; font-size: 0.78rem; color: #94a3b8;">
              <i class="fa-solid fa-circle-question" style="color: #f59e0b;"></i> No verified gene found for "<strong>${q}</strong>"
            </div>
          `;
          dropdown.style.display = 'block';
          return;
        }

        dropdown.innerHTML = genes.map(g => `
          <div class="locus-gene-suggestion" data-chrom="${g.chrom}" data-start="${g.start}" data-end="${g.end}" data-symbol="${g.symbol}"
               style="padding: 0.5rem 0.8rem; border-bottom: 1px solid #1e293b; cursor: pointer; display: flex; justify-content: space-between; align-items: center;"
               onmouseover="this.style.background='#1e293b'" onmouseout="this.style.background='transparent'">
            <div>
              <strong style="color: #38bdf8; font-size: 0.82rem;">${g.symbol}</strong>
              <span style="font-size: 0.72rem; color: #94a3b8; margin-left: 0.4rem;">${g.description || ''}</span>
            </div>
            <span style="font-family: monospace; font-size: 0.72rem; color: #64748b;">${g.chrom}:${Number(g.start).toLocaleString()}-${Number(g.end).toLocaleString()}</span>
          </div>
        `).join('');

        dropdown.querySelectorAll('.locus-gene-suggestion').forEach(item => {
          item.addEventListener('click', () => {
            const chrom = item.getAttribute('data-chrom');
            const start = parseInt(item.getAttribute('data-start'));
            const end = parseInt(item.getAttribute('data-end'));
            const symbol = item.getAttribute('data-symbol');

            input.value = symbol;
            dropdown.style.display = 'none';

            // Add 5kb boundary padding around gene
            const padStart = Math.max(1, start - 5000);
            const padEnd = end + 5000;

            const cInput = document.getElementById('locusChromInput');
            const sInput = document.getElementById('locusStartInput');
            const eInput = document.getElementById('locusEndInput');
            if (cInput) cInput.value = chrom;
            if (sInput) sInput.value = padStart;
            if (eInput) eInput.value = padEnd;

            const target = `${chrom}:${padStart}-${padEnd}`;
            if (igvBrowserInstance) {
              igvBrowserInstance.search(target).catch(() => initNativeIgv(target));
            } else {
              initNativeIgv(target);
            }

            if (typeof showToast === 'function') {
              showToast(`Navigated to ${symbol} (${chrom}:${padStart.toLocaleString()}-${padEnd.toLocaleString()})`, 'info');
            }
          });
        });

        dropdown.style.display = 'block';
      } catch (err) {
        console.error("Gene search error:", err);
      }
    }, 200);
  });

  // Close dropdown on outside click
  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.style.display = 'none';
    }
  });
}

// -------------------------------------------------------------
// Toolbar Pan, Zoom & Track Toggle Handlers
// -------------------------------------------------------------
function setupLocusControls() {
  // Jump Button
  const renderBtn = document.getElementById('locusRenderBtn');
  if (renderBtn) {
    renderBtn.addEventListener('click', () => {
      const cEl = document.getElementById('locusChromInput');
      const sEl = document.getElementById('locusStartInput');
      const eEl = document.getElementById('locusEndInput');
      const c = (cEl && cEl.value.trim()) || 'chr17';
      const s = (sEl && parseInt(sEl.value.trim())) || 7668000;
      let e = (eEl && parseInt(eEl.value.trim())) || 7688000;
      if (s >= e) e = s + 20000;
      const target = `${c}:${s}-${e}`;

      if (igvBrowserInstance) {
        igvBrowserInstance.search(target).catch(() => initNativeIgv(target));
      } else {
        initNativeIgv(target);
      }
    });
  }

  // Pan Left (25%)
  const panLeftBtn = document.getElementById('locusPanLeftBtn');
  if (panLeftBtn) {
    panLeftBtn.addEventListener('click', () => {
      if (!igvBrowserInstance) return;
      const cInput = document.getElementById('locusChromInput');
      const sInput = document.getElementById('locusStartInput');
      const eInput = document.getElementById('locusEndInput');
      const chrom = cInput ? cInput.value.trim() : 'chr17';
      const start = sInput ? parseInt(sInput.value.trim()) : 7668000;
      const end = eInput ? parseInt(eInput.value.trim()) : 7688000;
      const span = end - start;
      const shift = Math.round(span * 0.25);
      const newStart = Math.max(1, start - shift);
      const newEnd = end - shift;

      if (sInput) sInput.value = newStart;
      if (eInput) eInput.value = newEnd;
      igvBrowserInstance.search(`${chrom}:${newStart}-${newEnd}`);
    });
  }

  // Pan Right (25%)
  const panRightBtn = document.getElementById('locusPanRightBtn');
  if (panRightBtn) {
    panRightBtn.addEventListener('click', () => {
      if (!igvBrowserInstance) return;
      const cInput = document.getElementById('locusChromInput');
      const sInput = document.getElementById('locusStartInput');
      const eInput = document.getElementById('locusEndInput');
      const chrom = cInput ? cInput.value.trim() : 'chr17';
      const start = sInput ? parseInt(sInput.value.trim()) : 7668000;
      const end = eInput ? parseInt(eInput.value.trim()) : 7688000;
      const span = end - start;
      const shift = Math.round(span * 0.25);
      const newStart = start + shift;
      const newEnd = end + shift;

      if (sInput) sInput.value = newStart;
      if (eInput) eInput.value = newEnd;
      igvBrowserInstance.search(`${chrom}:${newStart}-${newEnd}`);
    });
  }

  // Zoom In (+50%)
  const zoomInBtn = document.getElementById('locusZoomInBtn');
  if (zoomInBtn) {
    zoomInBtn.addEventListener('click', () => {
      if (igvBrowserInstance && typeof igvBrowserInstance.zoomIn === 'function') {
        igvBrowserInstance.zoomIn();
      }
    });
  }

  // Zoom Out (-50%)
  const zoomOutBtn = document.getElementById('locusZoomOutBtn');
  if (zoomOutBtn) {
    zoomOutBtn.addEventListener('click', () => {
      if (igvBrowserInstance && typeof igvBrowserInstance.zoomOut === 'function') {
        igvBrowserInstance.zoomOut();
      }
    });
  }

  // Reset View
  const resetBtn = document.getElementById('locusResetViewBtn');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      window.jumpToIgvPreset('TP53');
    });
  }

  // Reload Tracks
  const reloadBtn = document.getElementById('locusReloadIgvBtn');
  if (reloadBtn) {
    reloadBtn.addEventListener('click', () => {
      igvBrowserInstance = null;
      initNativeIgv();
      if (typeof showToast === 'function') {
        showToast('Reloading native IGV.js tracks', 'info');
      }
    });
  }

  // Track Checkbox Toggles - dynamically controls what appears in IGV viewer
  // 1. Phased BAM Toggle (On Demand - Prevents overcomputing)
  const bamCb = document.getElementById('trackToggleBam');
  if (bamCb) {
    bamCb.addEventListener('change', async () => {
      if (!igvBrowserInstance) return;
      if (bamCb.checked) {
        if (!igvCachedTracks.bam) {
          if (typeof showToast === 'function') showToast('BAM track config not found', 'warning');
          return;
        }
        if (typeof showToast === 'function') showToast('Loading phased ONT read alignments (HP1/HP2)...', 'info');
        try {
          await igvBrowserInstance.loadTrack(igvCachedTracks.bam);
          if (typeof showToast === 'function') showToast('Phased BAM track loaded', 'success');
        } catch (e) {
          console.warn('Error loading BAM track:', e);
        }
      } else {
        if (igvCachedTracks.bam) {
          igvBrowserInstance.removeTrackByName(igvCachedTracks.bam.name);
          if (typeof showToast === 'function') showToast('Phased BAM track unloaded', 'info');
        }
      }
    });
  }

  // 2. RefSeq Genes Toggle
  const genesCb = document.getElementById('trackToggleGenes');
  if (genesCb) {
    genesCb.addEventListener('change', async () => {
      if (!igvBrowserInstance) return;
      if (genesCb.checked) {
        if (igvCachedTracks.refseq) await igvBrowserInstance.loadTrack(igvCachedTracks.refseq);
        if (igvCachedTracks.cmrg) await igvBrowserInstance.loadTrack(igvCachedTracks.cmrg);
      } else {
        if (igvCachedTracks.refseq) igvBrowserInstance.removeTrackByName(igvCachedTracks.refseq.name);
        if (igvCachedTracks.cmrg) igvBrowserInstance.removeTrackByName(igvCachedTracks.cmrg.name);
      }
    });
  }

  // 3. ONT Depth Coverage Toggle
  const covCb = document.getElementById('trackToggleCoverage');
  if (covCb) {
    covCb.addEventListener('change', async () => {
      if (!igvBrowserInstance || !igvCachedTracks.coverage) return;
      if (covCb.checked) {
        await igvBrowserInstance.loadTrack(igvCachedTracks.coverage);
      } else {
        igvBrowserInstance.removeTrackByName(igvCachedTracks.coverage.name);
      }
    });
  }

  // 4. Small Variants (SNVs) Toggle
  const snvCb = document.getElementById('trackToggleSnv');
  if (snvCb) {
    snvCb.addEventListener('change', async () => {
      if (!igvBrowserInstance) return;
      if (snvCb.checked) {
        if (igvCachedTracks.snvCmrg) await igvBrowserInstance.loadTrack(igvCachedTracks.snvCmrg);
        if (igvCachedTracks.snvGiab) await igvBrowserInstance.loadTrack(igvCachedTracks.snvGiab);
      } else {
        if (igvCachedTracks.snvCmrg) igvBrowserInstance.removeTrackByName(igvCachedTracks.snvCmrg.name);
        if (igvCachedTracks.snvGiab) igvBrowserInstance.removeTrackByName(igvCachedTracks.snvGiab.name);
      }
    });
  }

  // 5. Structural Variants (SVs) Toggle
  const svCb = document.getElementById('trackToggleSv');
  if (svCb) {
    svCb.addEventListener('change', async () => {
      if (!igvBrowserInstance || !igvCachedTracks.sv) return;
      if (svCb.checked) {
        await igvBrowserInstance.loadTrack(igvCachedTracks.sv);
      } else {
        igvBrowserInstance.removeTrackByName(igvCachedTracks.sv.name);
      }
    });
  }

  // 6. DNA Methylation (5mC) Toggle
  const methCb = document.getElementById('trackToggleMeth');
  if (methCb) {
    methCb.addEventListener('change', async () => {
      if (!igvBrowserInstance || !igvCachedTracks.meth) return;
      if (methCb.checked) {
        await igvBrowserInstance.loadTrack(igvCachedTracks.meth);
      } else {
        igvBrowserInstance.removeTrackByName(igvCachedTracks.meth.name);
      }
    });
  }
}

// -------------------------------------------------------------
// DOM Ready Lifecycle Initialization
// -------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  setupLocusGeneSearch();
  setupLocusControls();

  // If initial active section is locus-view, initialize IGV
  const locusSection = document.getElementById('locus-view');
  if (locusSection && locusSection.classList.contains('active')) {
    initNativeIgv();
  }
});
