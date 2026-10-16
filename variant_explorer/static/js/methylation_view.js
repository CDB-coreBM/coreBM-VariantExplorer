// DNA Methylation Explorer Module with Methylartist Studio Integration
let methData = [];
let currentMethylartistSvg = '';

async function loadMethylationRegions() {
  if (!AppState.activeCaseId) {
    const tbody = document.getElementById('methTableBody');
    if (tbody) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 3rem;"><i class="fa-solid fa-folder-open" style="font-size: 2rem; margin-bottom: 0.75rem; color: #64748b; display: block;"></i>Please select a clinical case from the header dropdown or ingest a new sample.</td></tr>';
    }
    const container = document.getElementById('methylartistContainer');
    if (container) {
      container.innerHTML = '<div style="color: #94a3b8; text-align: center; padding: 4rem;"><i class="fa-solid fa-folder-open" style="font-size: 2rem; margin-bottom: 0.75rem; color: #64748b; display: block;"></i>Please select a clinical case to view authentic 5mC epigenetic plots.</div>';
    }
    return;
  }

  const gEl = document.getElementById('methGeneFilter');
  const tEl = document.getElementById('methTargetFilter');
  const mEl = document.getElementById('methMinPercentFilter');
  const aEl = document.getElementById('methAsmOnlyFilter');

  const gene = (gEl && gEl.value) || '';
  const target = (tEl && tEl.value) || '';
  const minPercent = (mEl && mEl.value) || '';
  const asmOnly = (aEl && aEl.checked) ? 'true' : 'false';

  const params = new URLSearchParams({
    case_id: AppState.activeCaseId,
    gene: gene || target,
    min_percent: minPercent,
    asm_only: asmOnly,
  });

  const tbody = document.getElementById('methTableBody');
  if (tbody) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 2rem;"><div class="spinner" style="margin: 0 auto 0.5rem auto;"></div>Loading DNA methylation data...</td></tr>';
  }

  try {
    const res = await fetch(`/api/methylation?${params.toString()}`);
    const result = await res.json();
    methData = result.regions || result.methylation_regions || [];

    renderMethTable(methData);
    updateMethStats(methData);

    // If methylartist is empty or newly loaded, load the first gene or preset
    if (methData.length > 0) {
      const gInputEl = document.getElementById('maGeneInput');
      const activeGene = gInputEl ? gInputEl.value.trim() : '';
      const matching = methData.find((m) => m.gene_symbol === activeGene) || methData[0];
      loadMethylartistPlot(matching.gene_symbol, matching.chrom, matching.start, matching.end);
    }
  } catch (err) {
    console.error('Error fetching methylation:', err);
    if (tbody) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: var(--badge-pathogenic); padding: 2rem;">Error loading methylation data</td></tr>';
    }
  }
}

function renderMethTable(regions) {
  const tbody = document.getElementById('methTableBody');
  if (!tbody) return;
  if (!regions || regions.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 2rem;">No methylation regions match the filter criteria.</td></tr>';
    return;
  }

  tbody.innerHTML = regions.map((r) => {
    const pctVal = r.percent_modified !== null && r.percent_modified !== undefined ? r.percent_modified : (r.mean_methylated_pct || 0);
    const methPercent = pctVal.toFixed(1);
    
    let methBadge = `<span class="badge badge-benign">${methPercent}% 5mC</span>`;
    if (pctVal >= 60.0) {
      methBadge = `<span class="badge badge-pathogenic">${methPercent}% Hypermethylated</span>`;
    } else if (pctVal >= 25.0) {
      methBadge = `<span class="badge badge-likely-path">${methPercent}% Intermediate</span>`;
    }

    const isAsm = r.is_asm === 1 || r.is_allele_specific;
    const asmBadge = isAsm 
      ? '<span class="badge badge-tier-2"><i class="fa-solid fa-code-branch"></i> ASM Confirmed</span>'
      : '<span style="color: #94a3b8;">Biallelic</span>';

    const covVal = r.n_valid_cov || r.mean_valid_coverage || 0;
    const nMod = r.n_mod || 0;
    const nCanon = r.n_canonical || 0;
    const totalSites = nMod + nCanon;

    return `
      <tr onclick="selectMethRegion('${r.gene_symbol}', '${r.chrom}', ${r.start}, ${r.end}, '${r.id}')" style="cursor: pointer;">
        <td><strong>${r.gene_symbol || r.name || '-'}</strong></td>
        <td><span style="font-family: monospace; font-size: 0.8rem;">${r.chrom}:${r.start.toLocaleString()}-${r.end.toLocaleString()}</span></td>
        <td><span class="badge badge-tier-4">${r.region_type || 'Promoter CpG'}</span></td>
        <td>${methBadge}</td>
        <td>${totalSites > 0 ? totalSites + ' CpGs' : '-'}</td>
        <td>${covVal ? covVal.toFixed(1) : 0}x</td>
        <td><span style="font-size: 0.82rem;">${r.clinical_significance || 'Epigenetic biomarker'}</span></td>
        <td>${asmBadge}</td>
        <td>
          <button class="btn btn-teal" style="padding: 0.2rem 0.45rem; font-size: 0.75rem;" onclick="event.stopPropagation(); selectMethRegion('${r.gene_symbol}', '${r.chrom}', ${r.start}, ${r.end}, '${r.id}')" title="Inspect in Methylartist Studio">
            <i class="fa-solid fa-paintbrush"></i> Studio
          </button>
          <button class="btn btn-secondary" style="padding: 0.2rem 0.45rem; font-size: 0.75rem;" onclick="event.stopPropagation(); inspectMethInLocusTrack('${r.chrom}', ${r.start}, ${r.end})" title="Inspect in Multi-Track Locus (IGV)">
            <i class="fa-solid fa-magnifying-glass-location"></i> IGV
          </button>
          ${(typeof isVariantInReport === 'function' && isVariantInReport(r))
            ? `<button class="btn btn-secondary" style="padding: 0.2rem 0.45rem; font-size: 0.75rem; opacity: 0.85; cursor: not-allowed; color: #10b981;" disabled title="Already included in clinical report"><i class="fa-solid fa-check"></i> Included</button>`
            : `<button class="btn btn-primary" style="padding: 0.2rem 0.45rem; font-size: 0.75rem;" onclick="event.stopPropagation(); addMethToReport('${r.id}')" title="Add to Clinical Report"><i class="fa-solid fa-file-circle-plus"></i> Add</button>`
          }
        </td>
      </tr>
    `;
  }).join('');
}

function switchMethViewMode(mode) {
  const tableSec = document.getElementById('methTableSection');
  const studioSec = document.getElementById('methStudioSection');
  const tableBtn = document.getElementById('methViewTableBtn');
  const studioBtn = document.getElementById('methViewStudioBtn');

  if (mode === 'studio') {
    if (studioSec) studioSec.style.display = 'block';
    if (tableSec) tableSec.style.display = 'none';
    if (studioBtn) studioBtn.className = 'btn btn-primary';
    if (tableBtn) tableBtn.className = 'btn btn-secondary';
  } else {
    if (studioSec) studioSec.style.display = 'none';
    if (tableSec) tableSec.style.display = 'block';
    if (studioBtn) studioBtn.className = 'btn btn-secondary';
    if (tableBtn) tableBtn.className = 'btn btn-primary';
  }
}

function selectMethRegion(gene, chrom, start, end, id) {
  switchMethViewMode('studio');
  loadMethylartistPlot(gene, chrom, start, end);
  const studio = document.getElementById('methylartistContainer');
  if (studio) {
    studio.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

function inspectMethInLocusTrack(chrom, start, end) {
  if (typeof switchView === 'function') {
    switchView('locus-view');
    const locInput = document.getElementById('locusSearchInput');
    if (locInput) {
      locInput.value = `${chrom}:${start}-${end}`;
    }
    if (typeof igvGoTo === 'function') {
      igvGoTo(`${chrom}:${start}-${end}`);
    }
  }
}

window.addMethToReport = function(regionId) {
  const r = methData.find(item => String(item.id) === String(regionId));
  if (!r) {
    if (typeof showToast === 'function') showToast('Methylation region not found', 'warning');
    return;
  }
  if (typeof addVariantToClinicalReport === 'function') {
    addVariantToClinicalReport(r);
    renderMethTable(methData);
  }
};

async function loadMethylartistPlot(gene, chrom, start, end) {
  const container = document.getElementById('methylartistContainer');
  if (!container) return;

  if (!AppState.activeCaseId) {
    container.innerHTML = '<div style="color: #94a3b8; text-align: center; padding: 3rem;">Please select an active clinical case to render methylation plots.</div>';
    return;
  }

  const gInput = document.getElementById('maGeneInput');
  const cInput = document.getElementById('maChromInput');
  const sInput = document.getElementById('maStartInput');
  const eInput = document.getElementById('maEndInput');

  if (gInput && gene !== undefined && gene !== null) gInput.value = gene;
  if (cInput && chrom !== undefined && chrom !== null) cInput.value = chrom;
  if (sInput && start !== undefined && start !== null) sInput.value = start;
  if (eInput && end !== undefined && end !== null) eInput.value = end;

  const currentGene = (gInput ? gInput.value.trim() : (gene || '')).trim();
  const currentChrom = (cInput ? cInput.value.trim() : (chrom || '')).trim();
  const currentStart = (sInput ? sInput.value.trim() : (start || '')).toString().trim();
  const currentEnd = (eInput ? eInput.value.trim() : (end || '')).toString().trim();

  if (!currentGene && !currentChrom) {
    container.innerHTML = '<div style="color: #94a3b8; text-align: center; padding: 3rem;">Please enter a gene symbol or chromosome coordinates to render epigenetic plot.</div>';
    return;
  }

  const displayTarget = currentGene || `${currentChrom}:${Number(currentStart).toLocaleString()}-${Number(currentEnd).toLocaleString()}`;
  container.innerHTML = `
    <div style="color: #94a3b8; text-align: center; padding: 3rem;">
      <div class="spinner" style="margin: 0 auto 0.75rem auto;"></div>
      Querying verified 5mC calls for <strong>${displayTarget}</strong>...
    </div>
  `;

  try {
    const params = new URLSearchParams({
      case_id: AppState.activeCaseId
    });
    if (currentGene) params.append('gene', currentGene);
    if (currentChrom) params.append('chrom', currentChrom);
    if (currentStart) params.append('start', currentStart);
    if (currentEnd) params.append('end', currentEnd);

    const res = await fetch(`/api/methylation/methylartist?${params.toString()}`);
    if (!res.ok) {
      let errText = 'No authentic methylation data found.';
      try {
        const errJson = await res.json();
        if (errJson && errJson.message) errText = errJson.message;
      } catch (_) {}
      throw new Error(errText);
    }
    const svgText = await res.text();
    currentMethylartistSvg = svgText;
    container.innerHTML = svgText;
  } catch (err) {
    console.warn('Methylartist plot rendering notice:', err);
    container.innerHTML = `
      <div style="background: #1e293b; border: 1px solid #ef4444; border-radius: 8px; padding: 2.5rem 1.5rem; text-align: center; color: #f8fafc; max-width: 650px; margin: 2rem auto; box-shadow: 0 10px 25px rgba(0,0,0,0.4);">
        <div style="width: 50px; height: 50px; line-height: 50px; border-radius: 50%; background: rgba(239, 68, 68, 0.15); color: #ef4444; font-size: 1.5rem; margin: 0 auto 1rem auto;">
          <i class="fa-solid fa-triangle-exclamation"></i>
        </div>
        <h4 style="margin: 0 0 0.5rem 0; font-size: 1.15rem; color: #fca5a5;">No Methylation Data for "${displayTarget}"</h4>
        <p style="font-size: 0.85rem; color: #cbd5e1; margin-bottom: 1.25rem; line-height: 1.5;">
          ${err.message || 'No authentic methylation records found.'}<br>
          <strong style="color: #94a3b8;">Zero Simulation Policy:</strong> This platform does not generate fabricated exon models or synthetic CpG calls. Only verified sequenced loci with Dorado / modkit bedMethyl calls are plotted.
        </p>
        <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 0.75rem;">Select an authentic sequenced clinical locus:</div>
        <div style="display: flex; gap: 0.5rem; justify-content: center; flex-wrap: wrap;">
          <button class="btn btn-secondary" onclick="loadMethylartistPreset('MLH1', 'chr3', 36993100, 36993600)">MLH1</button>
          <button class="btn btn-secondary" onclick="loadMethylartistPreset('TP53', 'chr17', 7676000, 7676600)">TP53</button>
          <button class="btn btn-secondary" onclick="loadMethylartistPreset('H19/IGF2', 'chr11', 1977700, 1982700)">H19/IGF2 (ASM)</button>
          <button class="btn btn-secondary" onclick="loadMethylartistPreset('MGMT', 'chr10', 129467200, 129467500)">MGMT</button>
          <button class="btn btn-secondary" onclick="loadMethylartistPreset('CYP2D6', 'chr22', 42125000, 42125800)">CYP2D6</button>
        </div>
      </div>
    `;
  }
}

function loadMethylartistPreset(gene, chrom, start, end) {
  switchMethViewMode('studio');
  loadMethylartistPlot(gene, chrom, start, end);
}

function downloadMethylartistSvg() {
  if (!currentMethylartistSvg) {
    showToast('No methylartist plot rendered yet to download', 'warning');
    return;
  }
  const maGInput = document.getElementById('maGeneInput');
  const gene = (maGInput && maGInput.value) || 'locus';
  const blob = new Blob([currentMethylartistSvg], { type: 'image/svg+xml' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `methylartist_${gene}_5mC_epigenetics.svg`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast(`Downloaded methylartist SVG for ${gene}`, 'success');
}

function zoomMethylartist(factor) {
  const sInput = document.getElementById('maStartInput');
  const eInput = document.getElementById('maEndInput');
  if (!sInput || !eInput) return;

  const start = parseInt(sInput.value);
  const end = parseInt(eInput.value);
  const mid = (start + end) / 2;
  const newSpan = Math.max(200, (end - start) * factor);
  sInput.value = Math.max(1, Math.round(mid - newSpan / 2));
  eInput.value = Math.round(mid + newSpan / 2);
  loadMethylartistPlot();
}

function updateMethStats(regions) {
  let hyper = 0, asm = 0, normal = 0;
  regions.forEach((r) => {
    const pctVal = r.percent_modified !== null && r.percent_modified !== undefined ? r.percent_modified : (r.mean_methylated_pct || 0);
    if (pctVal >= 60.0) hyper++;
    else normal++;
    if (r.is_asm === 1 || r.is_allele_specific) asm++;
  });

  const pHyper = document.getElementById('pillHypermethylated');
  const pAsm = document.getElementById('pillAsmCount');
  const pNorm = document.getElementById('pillNormalMeth');
  if (pHyper) pHyper.textContent = hyper;
  if (pAsm) pAsm.textContent = asm;
  if (pNorm) pNorm.textContent = normal;
}

function inspectMethDetail(methId) {
  const r = methData.find((item) => item.id == methId);
  if (!r) return;

  const pctVal = r.percent_modified !== null && r.percent_modified !== undefined ? r.percent_modified : (r.mean_methylated_pct || 0);
  const methPercent = pctVal.toFixed(1);
  const isAsm = r.is_asm === 1 || r.is_allele_specific;
  const covVal = r.n_valid_cov || r.mean_valid_coverage || 0;

  const html = `
    <div class="drawer-section">
      <h4 class="drawer-section-title">Epigenetic Diagnostic Target</h4>
      <div class="drawer-kv-grid">
        <span class="drawer-kv-label">Gene / Target:</span>
        <span class="drawer-kv-value"><strong>${r.gene_symbol || r.name || '-'}</strong></span>
        <span class="drawer-kv-label">Locus (GRCh38):</span>
        <span class="drawer-kv-value" style="font-family: monospace;">${r.chrom}:${r.start.toLocaleString()}-${r.end.toLocaleString()}</span>
        <span class="drawer-kv-label">Region Category:</span>
        <span class="drawer-kv-value">${r.region_type || 'Promoter CpG Island'}</span>
        <span class="drawer-kv-label">Clinical Role:</span>
        <span class="drawer-kv-value">${r.clinical_significance || '-'}</span>
      </div>
    </div>

    <div class="drawer-section">
      <h4 class="drawer-section-title">Direct Oxford Nanopore 5mC Quantification</h4>
      <div class="drawer-kv-grid">
        <span class="drawer-kv-label">Mean 5mC Level:</span>
        <span class="drawer-kv-value" style="font-size: 1.1rem; font-weight: 800; color: ${pctVal >= 60 ? '#d90429' : '#058c42'}">
          ${methPercent}%
        </span>
        <span class="drawer-kv-label">Valid Coverage:</span>
        <span class="drawer-kv-value">${covVal ? covVal.toFixed(1) : 0}x valid ONT reads</span>
        <span class="drawer-kv-label">Imprinting (ASM):</span>
        <span class="drawer-kv-value">${isAsm ? '<strong style="color: #0284c7;">Allele-Specific Methylation Confirmed</strong>' : 'Biallelic methylation'}</span>
        <span class="drawer-kv-label">Haplotype 1 / 2:</span>
        <span class="drawer-kv-value">HP1: ${r.hp1_percent ? r.hp1_percent.toFixed(1) : '0'}% | HP2: ${r.hp2_percent ? r.hp2_percent.toFixed(1) : '0'}%</span>
      </div>
    </div>

    <div style="margin-top: 1rem;">
      <button class="btn btn-teal" style="width: 100%;" onclick="selectMethRegion('${r.gene_symbol}', '${r.chrom}', ${r.start}, ${r.end}, '${r.id}'); closeDetailDrawer();">
        <i class="fa-solid fa-paintbrush"></i> Load in Methylartist Studio
      </button>
    </div>
  `;

  openDetailDrawer(
    `5mC Methylation: ${r.gene_symbol || r.name}`,
    `${r.chrom}:${r.start}-${r.end}`,
    html,
    r
  );
}

// Live Autocomplete for Methylation Gene Input and Table Filter
function setupMethylationGeneAutocomplete() {
  const maInput = document.getElementById('maGeneInput');
  const maDropdown = document.getElementById('maGeneDropdown');
  const cInput = document.getElementById('maChromInput');
  const sInput = document.getElementById('maStartInput');
  const eInput = document.getElementById('maEndInput');

  if (maInput && maDropdown) {
    let timer = null;
    maInput.addEventListener('input', (e) => {
      const q = e.target.value.trim();
      clearTimeout(timer);
      if (!q) {
        maDropdown.style.display = 'none';
        return;
      }
      timer = setTimeout(async () => {
        try {
          const res = await fetch(`/api/genes/search?q=${encodeURIComponent(q)}&limit=10`);
          if (!res.ok) return;
          const data = await res.json();
          const genes = data.genes || [];

          if (genes.length === 0) {
            maDropdown.innerHTML = '<div style="padding: 0.65rem 0.85rem; color: #94a3b8; font-size: 0.75rem;">No matching genes found.</div>';
            maDropdown.style.display = 'block';
            return;
          }

          maDropdown.innerHTML = genes.map((g) => `
            <div class="gene-suggest-item" style="padding: 0.5rem 0.85rem; cursor: pointer; border-bottom: 1px solid #1e293b;" 
                 data-symbol="${g.symbol}" data-chrom="${g.chrom}" data-start="${g.start}" data-end="${g.end}">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <strong style="color: #38bdf8; font-size: 0.82rem;">${g.symbol}</strong>
                <span style="font-family: monospace; font-size: 0.72rem; color: #94a3b8;">${g.chrom}:${g.start.toLocaleString()}-${g.end.toLocaleString()}</span>
              </div>
              <div style="font-size: 0.7rem; color: #64748b; margin-top: 2px;">${g.description || g.source}</div>
            </div>
          `).join('');
          maDropdown.style.display = 'block';

          maDropdown.querySelectorAll('.gene-suggest-item').forEach((item) => {
            item.addEventListener('mouseenter', () => { item.style.background = '#1e293b'; });
            item.addEventListener('mouseleave', () => { item.style.background = 'transparent'; });
            item.addEventListener('click', () => {
              const sym = item.getAttribute('data-symbol');
              const chrom = item.getAttribute('data-chrom');
              const gStart = parseInt(item.getAttribute('data-start'));
              const gEnd = parseInt(item.getAttribute('data-end'));

              maInput.value = sym;
              if (cInput) cInput.value = chrom;
              if (sInput) sInput.value = gStart;
              if (eInput) eInput.value = gEnd;
              maDropdown.style.display = 'none';

              loadMethylartistPlot(sym, chrom, gStart, gEnd);
              showToast(`Coordinates adjusted for ${sym} (${chrom}:${gStart.toLocaleString()}-${gEnd.toLocaleString()})`, 'info');
            });
          });
        } catch (err) {
          console.warn('Methylation gene search error:', err);
        }
      }, 200);
    });

    maInput.addEventListener('keydown', async (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const first = maDropdown.querySelector('.gene-suggest-item');
        if (first && maDropdown.style.display !== 'none') {
          first.click();
        } else {
          loadMethylartistPlot();
        }
      }
    });

    document.addEventListener('click', (e) => {
      if (!maInput.contains(e.target) && !maDropdown.contains(e.target)) {
        maDropdown.style.display = 'none';
      }
    });
  }

  // Table filter autocomplete
  const filterInput = document.getElementById('methGeneFilter');
  const filterDropdown = document.getElementById('methFilterDropdown');
  if (filterInput && filterDropdown) {
    let fTimer = null;
    filterInput.addEventListener('input', (e) => {
      const q = e.target.value.trim().toUpperCase();
      clearTimeout(fTimer);
      if (!q) {
        filterDropdown.style.display = 'none';
        loadMethylationRegions();
        return;
      }
      fTimer = setTimeout(() => {
        const matches = (methData || []).filter(m => (m.gene_symbol || '').toUpperCase().includes(q));
        if (matches.length === 0) {
          filterDropdown.innerHTML = '<div style="padding: 0.5rem 0.75rem; color: #94a3b8; font-size: 0.75rem;">No matching sequenced regions.</div>';
          filterDropdown.style.display = 'block';
          return;
        }
        filterDropdown.innerHTML = matches.map(m => `
          <div class="filter-suggest-item" style="padding: 0.45rem 0.75rem; cursor: pointer; border-bottom: 1px solid #1e293b;" data-symbol="${m.gene_symbol}">
            <strong style="color: #38bdf8; font-size: 0.8rem;">${m.gene_symbol}</strong>
            <span style="font-size: 0.72rem; color: #94a3b8; margin-left: 0.5rem;">${m.percent_modified || m.mean_methylated_pct}% 5mC</span>
          </div>
        `).join('');
        filterDropdown.style.display = 'block';

        filterDropdown.querySelectorAll('.filter-suggest-item').forEach(it => {
          it.addEventListener('click', () => {
            filterInput.value = it.getAttribute('data-symbol');
            filterDropdown.style.display = 'none';
            loadMethylationRegions();
          });
        });
      }, 150);
    });

    document.addEventListener('click', (e) => {
      if (!filterInput.contains(e.target) && !filterDropdown.contains(e.target)) {
        filterDropdown.style.display = 'none';
      }
    });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  setupMethylationGeneAutocomplete();
  switchMethViewMode('table');

  const applyBtn = document.getElementById('methApplyFilterBtn');
  if (applyBtn) applyBtn.addEventListener('click', loadMethylationRegions);

  const resetBtn = document.getElementById('methResetFilterBtn');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      const gF = document.getElementById('methGeneFilter');
      const tF = document.getElementById('methTargetFilter');
      const mF = document.getElementById('methMinPercentFilter');
      const aF = document.getElementById('methAsmOnlyFilter');
      if (gF) gF.value = '';
      if (tF) tF.value = '';
      if (mF) mF.value = '';
      if (aF) aF.checked = false;
      loadMethylationRegions();
    });
  }

  const renderBtn = document.getElementById('maRenderBtn');
  if (renderBtn) renderBtn.addEventListener('click', () => loadMethylartistPlot());

  const dlBtn = document.getElementById('maDownloadSvgBtn');
  if (dlBtn) dlBtn.addEventListener('click', downloadMethylartistSvg);

  const zInBtn = document.getElementById('maZoomInBtn');
  if (zInBtn) zInBtn.addEventListener('click', () => zoomMethylartist(0.6));

  const zOutBtn = document.getElementById('maZoomOutBtn');
  if (zOutBtn) zOutBtn.addEventListener('click', () => zoomMethylartist(1.6));
});

