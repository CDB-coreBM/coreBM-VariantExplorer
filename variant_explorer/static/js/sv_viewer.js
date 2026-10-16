// Structural Variant Explorer Module with Interactive Circos Fusion Viewer
let svData = [];
let svTotal = 0;
let allCaseSVs = [];

async function loadSvVariants(resetPage = false) {
  if (!AppState.activeCaseId) {
    const tbody = document.getElementById('svTableBody');
    if (tbody) {
      tbody.innerHTML = '<tr><td colspan="10" style="text-align: center; color: var(--text-muted); padding: 3rem;"><i class="fa-solid fa-folder-open" style="font-size: 2rem; margin-bottom: 0.75rem; color: #64748b; display: block;"></i>Please select a clinical case from the header dropdown or ingest a new sample.</td></tr>';
    }
    return;
  }
  if (resetPage) AppState.svPage = 1;

  const pEl = document.getElementById('svPanelFilter');
  const gEl = document.getElementById('svGeneFilter');
  const tEl = document.getElementById('svTypeFilter');
  const minLEl = document.getElementById('svMinLenFilter');
  const maxLEl = document.getElementById('svMaxLenFilter');
  const sEl = document.getElementById('svMinSupportFilter');

  const panel = (pEl && pEl.value) || '';
  const gene = (gEl && gEl.value) || '';
  const svType = (tEl && tEl.value) || '';
  const minLen = (minLEl && minLEl.value) || '';
  const maxLen = (maxLEl && maxLEl.value) || '';
  const minSupport = (sEl && sEl.value) || '';

  const params = new URLSearchParams({
    case_id: AppState.activeCaseId,
    page: AppState.svPage,
    limit: AppState.svPageSize,
    gene,
    sv_type: svType,
    min_len: minLen,
    min_length: minLen,
    max_len: maxLen,
    max_length: maxLen,
    min_support: minSupport,
  });
  if (panel) params.append('panel_id', panel);

  const tbody = document.getElementById('svTableBody');
  if (tbody) {
    tbody.innerHTML = '<tr><td colspan="10" style="text-align: center; color: var(--text-muted); padding: 2rem;"><div class="spinner" style="margin: 0 auto 0.5rem auto;"></div>Loading structural variants...</td></tr>';
  }

  // 1. Fetch and render paginated SV table
  try {
    const res = await fetch(`/api/variants/sv?${params.toString()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch SVs`);
    const result = await res.json();
    svData = result.structural_variants || [];
    svTotal = result.total_records || result.total || 0;

    renderSvTable(svData);
    updateSvPagination(result);
    updateSvStats(result.metrics || result);
  } catch (tableErr) {
    console.error('Error fetching SV table data:', tableErr);
    if (tbody) {
      tbody.innerHTML = '<tr><td colspan="10" style="text-align: center; color: var(--badge-pathogenic); padding: 2rem;"><i class="fa-solid fa-triangle-exclamation" style="margin-right: 0.5rem;"></i>Error loading structural variants. Please refresh case data.</td></tr>';
    }
  }

  // 2. Fetch full cohort SVs for interactive Circos plot (isolated try/catch)
  try {
    const circosRes = await fetch(`/api/variants/sv/circos?case_id=${AppState.activeCaseId}`);
    if (circosRes.ok) {
      const circosJson = await circosRes.json();
      allCaseSVs = circosJson.structural_variants || [];
      if (typeof renderCircosPlot === 'function') {
        renderCircosPlot(allCaseSVs);
      }
    }
  } catch (circosErr) {
    console.warn('Circos plot rendering notice:', circosErr);
    const circosContainer = document.getElementById('circosSvgContainer');
    if (circosContainer && (!allCaseSVs || allCaseSVs.length === 0)) {
      circosContainer.innerHTML = '<div style="color: #94a3b8; text-align: center; padding: 2rem;"><i class="fa-solid fa-circle-exclamation fa-2x" style="color:#f59e0b; margin-bottom: 0.5rem;"></i><br>Circos plot standing by for complex rearrangements.</div>';
    }
  }
}

function switchSvViewMode(mode) {
  const circosSec = document.getElementById('svCircosSection');
  const tableSec = document.getElementById('svTableSection');
  const circosBtn = document.getElementById('svViewCircosBtn');
  const tableBtn = document.getElementById('svViewTableBtn');

  if (mode === 'circos') {
    if (circosSec) circosSec.style.display = 'block';
    if (tableSec) tableSec.style.display = 'none';
    if (circosBtn) { circosBtn.className = 'btn btn-primary'; }
    if (tableBtn) { tableBtn.className = 'btn btn-secondary'; }
  } else {
    if (circosSec) circosSec.style.display = 'none';
    if (tableSec) tableSec.style.display = 'block';
    if (circosBtn) { circosBtn.className = 'btn btn-secondary'; }
    if (tableBtn) { tableBtn.className = 'btn btn-primary'; }
  }
}

function renderSvTable(svs) {
  const tbody = document.getElementById('svTableBody');
  if (!tbody) return;
  if (!svs || svs.length === 0) {
    tbody.innerHTML = '<tr><td colspan="10" style="text-align: center; color: var(--text-muted); padding: 2rem;">No structural variants match the current filters.</td></tr>';
    return;
  }

  tbody.innerHTML = svs.map((sv) => {
    const badgeType = getSvBadgeHtml(sv.sv_type);
    const sizeStr = sv.sv_len ? formatBp(Math.abs(sv.sv_len)) : '-';
    const isTr = sv.tandem_repeat || sv.is_tandem_repeat;
    const trBadge = isTr ? '<span class="badge badge-likely-path">Repeat TR</span>' : '<span style="color: #94a3b8;">No</span>';
    const vafStr = sv.vaf ? (sv.vaf * 100).toFixed(1) + '%' : '-';
    const geneDisplay = sv.genes_affected || sv.genes_overlapped || '-';
    const endChr = sv.chr2 || sv.end_chrom || sv.chrom;
    const startNum = sv.start !== undefined && sv.start !== null ? Number(sv.start) : 0;
    const endPos = sv.pos2 !== undefined && sv.pos2 !== null ? sv.pos2 : (sv.end !== undefined && sv.end !== null ? sv.end : startNum);
    const endNum = Number(endPos);
    const depthVal = sv.total_depth || sv.depth || 0;

    return `
      <tr onclick="inspectSvDetail('${sv.id}')">
        <td>${badgeType}</td>
        <td><strong>${geneDisplay}</strong></td>
        <td><span style="font-family: monospace; font-size: 0.8rem;">${sv.chrom}:${startNum.toLocaleString()}</span></td>
        <td><span style="font-family: monospace; font-size: 0.8rem;">${endChr}:${endNum.toLocaleString()}</span></td>
        <td><strong>${sizeStr}</strong></td>
        <td>${sv.support_reads || 0} / ${depthVal}</td>
        <td><strong>${vafStr}</strong></td>
        <td><span style="font-family: monospace;">${sv.genotype || './.'}</span></td>
        <td>${trBadge}</td>
        <td>
          <button class="btn btn-secondary" style="padding: 0.2rem 0.45rem; font-size: 0.75rem;" onclick="event.stopPropagation(); inspectSvDetail('${sv.id}')" title="Inspect Breakpoint Detail">
            <i class="fa-solid fa-magnifying-glass-chart"></i>
          </button>
          <button class="btn btn-teal" style="padding: 0.2rem 0.45rem; font-size: 0.75rem;" onclick="event.stopPropagation(); highlightInCircos('${sv.id}')" title="View in Circos Plot">
            <i class="fa-solid fa-circle-notch"></i>
          </button>
          ${(typeof isVariantInReport === 'function' && isVariantInReport(sv))
            ? `<button class="btn btn-secondary" style="padding: 0.2rem 0.45rem; font-size: 0.75rem; opacity: 0.85; cursor: not-allowed; color: #10b981;" disabled title="Already included in clinical report"><i class="fa-solid fa-check"></i> Included</button>`
            : `<button class="btn btn-primary" style="padding: 0.2rem 0.45rem; font-size: 0.75rem;" onclick="event.stopPropagation(); addSvToReportFromTable('${sv.id}')" title="Add to Clinical Report"><i class="fa-solid fa-file-circle-plus"></i> Add</button>`
          }
        </td>
      </tr>
    `;
  }).join('');
}

window.addSvToReportFromTable = function(svId) {
  const sv = svData.find(item => String(item.id) === String(svId)) || allCaseSVs.find(item => String(item.id) === String(svId));
  if (!sv) {
    if (typeof showToast === 'function') showToast('Structural variant not found', 'warning');
    return;
  }
  if (typeof addVariantToClinicalReport === 'function') {
    addVariantToClinicalReport(sv);
    renderSvTable(svData);
  }
};

function highlightInCircos(svId) {
  switchSvViewMode('circos');
  if (typeof handleCircosChordClick === 'function') {
    handleCircosChordClick(svId);
  }
}

function getSvBadgeHtml(type) {
  if (!type) return '-';
  const t = type.toUpperCase();
  if (t === 'DEL') return '<span class="badge badge-sv-del"><i class="fa-solid fa-minus"></i> DEL</span>';
  if (t === 'DUP') return '<span class="badge badge-sv-dup"><i class="fa-solid fa-plus"></i> DUP</span>';
  if (t === 'INS') return '<span class="badge badge-sv-ins"><i class="fa-solid fa-arrow-down"></i> INS</span>';
  if (t === 'INV') return '<span class="badge badge-sv-inv"><i class="fa-solid fa-arrows-rotate"></i> INV</span>';
  if (t === 'BND' || t === 'TRA') return '<span class="badge badge-sv-bnd"><i class="fa-solid fa-shuffle"></i> BND / Fusion</span>';
  return `<span class="badge">${type}</span>`;
}

function formatBp(len) {
  if (len >= 1000000) return (len / 1000000).toFixed(2) + ' Mb';
  if (len >= 1000) return (len / 1000).toFixed(1) + ' kb';
  return len.toLocaleString() + ' bp';
}

function updateSvPagination(result) {
  const page = result.page || 1;
  const limit = result.limit || 50;
  const total = result.total_records || result.total || 0;
  const pages = result.total_pages || result.pages || 1;
  const svs = result.structural_variants || [];

  const start = (page - 1) * limit + (svs.length > 0 ? 1 : 0);
  const end = (page - 1) * limit + svs.length;

  const sStart = document.getElementById('svShowingStart');
  const sEnd = document.getElementById('svShowingEnd');
  const sTotal = document.getElementById('svTotalCount');
  const sPage = document.getElementById('svCurrentPage');
  const sPages = document.getElementById('svTotalPages');

  if (sStart) sStart.textContent = start;
  if (sEnd) sEnd.textContent = end;
  if (sTotal) sTotal.textContent = total;
  if (sPage) sPage.textContent = page;
  if (sPages) sPages.textContent = pages;

  const prevBtn = document.getElementById('svPrevPageBtn');
  const nextBtn = document.getElementById('svNextPageBtn');
  if (prevBtn) prevBtn.disabled = page <= 1;
  if (nextBtn) nextBtn.disabled = page >= pages;
}

function updateSvStats(metricsOrSvs) {
  let del = 0, dup = 0, ins = 0, bnd = 0;

  if (metricsOrSvs && typeof metricsOrSvs === 'object' && !Array.isArray(metricsOrSvs)) {
    del = metricsOrSvs.del_count !== undefined ? metricsOrSvs.del_count : 0;
    dup = metricsOrSvs.dup_count !== undefined ? metricsOrSvs.dup_count : 0;
    ins = metricsOrSvs.ins_count !== undefined ? metricsOrSvs.ins_count : 0;
    bnd = metricsOrSvs.bnd_count !== undefined ? metricsOrSvs.bnd_count : 0;
  } else if (Array.isArray(metricsOrSvs)) {
    metricsOrSvs.forEach((s) => {
      const t = (s.sv_type || '').toUpperCase();
      if (t === 'DEL') del++;
      else if (t === 'DUP') dup++;
      else if (t === 'INS') ins++;
      else if (t === 'BND' || t === 'TRA') bnd++;
    });
  }

  const pDel = document.getElementById('pillDelCount');
  const pDup = document.getElementById('pillDupCount');
  const pIns = document.getElementById('pillInsCount');
  const pBnd = document.getElementById('pillBndCount');
  if (pDel) pDel.textContent = Number(del).toLocaleString();
  if (pDup) pDup.textContent = Number(dup).toLocaleString();
  if (pIns) pIns.textContent = Number(ins).toLocaleString();
  if (pBnd) pBnd.textContent = Number(bnd).toLocaleString();
}

function inspectSvDetail(svId) {
  const sv = svData.find((item) => item.id == svId) || allCaseSVs.find((item) => item.id == svId);
  if (!sv) return;

  const sizeStr = sv.sv_len ? formatBp(Math.abs(sv.sv_len)) : 'Complex Breakend';
  const geneDisplay = sv.genes_affected || sv.genes_overlapped || 'Intergenic';
  const endChr = sv.chr2 || sv.end_chrom || sv.chrom;
  const endPos = sv.pos2 || sv.end;
  const depthVal = sv.total_depth || sv.depth || 0;
  const impactVal = sv.clinical_impact || sv.impact || 'Exon disruption / copy number alteration';

  const html = `
    <div class="drawer-section">
      <h4 class="drawer-section-title">Structural Variant Classification</h4>
      <div class="drawer-kv-grid">
        <span class="drawer-kv-label">SV Type:</span>
        <span class="drawer-kv-value">${getSvBadgeHtml(sv.sv_type)}</span>
        <span class="drawer-kv-label">Overlapping Gene(s):</span>
        <span class="drawer-kv-value"><strong>${geneDisplay}</strong></span>
        <span class="drawer-kv-label">SV Span / Size:</span>
        <span class="drawer-kv-value"><strong>${sizeStr}</strong></span>
        <span class="drawer-kv-label">Clinical Impact:</span>
        <span class="drawer-kv-value">${impactVal}</span>
      </div>
    </div>

    <div class="drawer-section">
      <h4 class="drawer-section-title">Breakpoints & Coordinates (GRCh38)</h4>
      <div class="drawer-kv-grid">
        <span class="drawer-kv-label">Breakpoint 1 (Start):</span>
        <span class="drawer-kv-value" style="font-family: monospace;">${sv.chrom}:${sv.start.toLocaleString()}</span>
        <span class="drawer-kv-label">Breakpoint 2 (End):</span>
        <span class="drawer-kv-value" style="font-family: monospace;">${endChr}:${endPos.toLocaleString()}</span>
        <span class="drawer-kv-label">Tandem Repeat (TR):</span>
        <span class="drawer-kv-value">${sv.tandem_repeat || sv.is_tandem_repeat ? 'Yes (Tandem Repeat region)' : 'Non-repetitive single-copy locus'}</span>
        <span class="drawer-kv-label">Genotype:</span>
        <span class="drawer-kv-value" style="font-family: monospace;">${sv.genotype || './.'}</span>
      </div>
    </div>

    <div class="drawer-section">
      <h4 class="drawer-section-title">Nanopore Read Evidence & Support</h4>
      <div class="drawer-kv-grid">
        <span class="drawer-kv-label">Supporting Reads:</span>
        <span class="drawer-kv-value"><strong>${sv.support_reads || 0}</strong> spanning reads</span>
        <span class="drawer-kv-label">Total Depth:</span>
        <span class="drawer-kv-value">${depthVal}x</span>
        <span class="drawer-kv-label">Variant Fraction:</span>
        <span class="drawer-kv-value">${sv.vaf ? (sv.vaf * 100).toFixed(1) + '%' : '-'}</span>
      </div>
    </div>

    <div style="margin-top: 1rem; display: flex; gap: 0.5rem;">
      <button class="btn btn-teal" style="flex: 1;" onclick="highlightInCircos('${sv.id}'); closeDetailDrawer();">
        <i class="fa-solid fa-circle-notch"></i> Explore in Circos
      </button>
    </div>
  `;

  openDetailDrawer(
    `${sv.sv_type} in ${geneDisplay}`,
    `${sv.chrom}:${sv.start.toLocaleString()}-${endPos.toLocaleString()} (${sizeStr})`,
    html,
    sv
  );
}

document.addEventListener('DOMContentLoaded', () => {
  const applyBtn = document.getElementById('svApplyFilterBtn');
  if (applyBtn) applyBtn.addEventListener('click', () => loadSvVariants(true));

  const panelSelect = document.getElementById('svPanelFilter');
  if (panelSelect) panelSelect.addEventListener('change', () => loadSvVariants(true));

  // Ensure default view mode is Structural Variant Callset Table
  switchSvViewMode('table');

  const resetBtn = document.getElementById('svResetFilterBtn');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      if (document.getElementById('svPanelFilter')) document.getElementById('svPanelFilter').value = '';
      if (document.getElementById('svGeneFilter')) document.getElementById('svGeneFilter').value = '';
      if (document.getElementById('svTypeFilter')) document.getElementById('svTypeFilter').value = '';
      if (document.getElementById('svMinLenFilter')) document.getElementById('svMinLenFilter').value = '';
      if (document.getElementById('svMaxLenFilter')) document.getElementById('svMaxLenFilter').value = '';
      if (document.getElementById('svMinSupportFilter')) document.getElementById('svMinSupportFilter').value = '';
      loadSvVariants(true);
    });
  }

  const prevBtn = document.getElementById('svPrevPageBtn');
  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      if (AppState.svPage > 1) {
        AppState.svPage--;
        loadSvVariants(false);
      }
    });
  }

  const nextBtn = document.getElementById('svNextPageBtn');
  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      AppState.svPage++;
      loadSvVariants(false);
    });
  }
});
