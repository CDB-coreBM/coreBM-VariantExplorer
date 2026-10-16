// Tandem Repeat Expansions (TRGT / Straglr) Module
// Hospital Clínic de Barcelona - CoreBM Variant Explorer

let repeatsData = [];

async function loadRepeats(resetFilters = false) {
  const tbody = document.getElementById('repeatsTableBody');
  if (!AppState.activeCaseId) {
    if (tbody) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 3rem;"><i class="fa-solid fa-folder-open" style="font-size: 2rem; margin-bottom: 0.75rem; color: #64748b; display: block;"></i>Please select a clinical case from the header dropdown or ingest a new sample.</td></tr>';
    }
    return;
  }

  if (resetFilters) {
    const sInput = document.getElementById('repeatsSearchInput');
    const stSelect = document.getElementById('repeatsStatusFilter');
    if (sInput) sInput.value = '';
    if (stSelect) stSelect.value = '';
  }

  if (tbody) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 2rem;"><div class="spinner" style="margin: 0 auto 0.5rem auto;"></div>Loading tandem repeat expansions...</td></tr>';
  }

  try {
    const res = await fetch(`/api/repeats?case_id=${AppState.activeCaseId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch repeats`);
    const data = await res.json();
    repeatsData = data.repeat_expansions || [];

    updateRepeatsStats(repeatsData);
    filterAndRenderRepeats();
  } catch (err) {
    console.error('Error fetching repeats:', err);
    if (tbody) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: var(--badge-pathogenic); padding: 2rem;">Error loading tandem repeat expansions.</td></tr>';
    }
  }
}

function updateRepeatsStats(repeats) {
  const badge = document.getElementById('badgeRepeatsCount');
  const totalEl = document.getElementById('repeatsSummaryTotal');
  const statusEl = document.getElementById('repeatsSummaryStatus');
  const pathPill = document.getElementById('pillRepeatsPath');
  const premutPill = document.getElementById('pillRepeatsPremut');
  const normPill = document.getElementById('pillRepeatsNorm');

  const count = repeats.length;
  if (badge) badge.textContent = count;
  if (totalEl) totalEl.textContent = count;

  let pathCount = 0;
  let premutCount = 0;
  let normCount = 0;

  repeats.forEach((r) => {
    const s = r.status || '';
    if (s.includes('Pathogenic')) pathCount++;
    else if (s.includes('Premutation') || s.includes('Reduced')) premutCount++;
    else normCount++;
  });

  if (pathPill) pathPill.textContent = pathCount;
  if (premutPill) premutPill.textContent = premutCount;
  if (normPill) normPill.textContent = normCount;

  if (statusEl) {
    if (pathCount > 0) {
      statusEl.textContent = `${pathCount} Pathogenic Expansion Detected`;
      statusEl.style.color = '#ef4444';
    } else if (premutCount > 0) {
      statusEl.textContent = `${premutCount} Premutation Allele Detected`;
      statusEl.style.color = '#f59e0b';
    } else {
      statusEl.textContent = 'All Evaluated Loci Normal';
      statusEl.style.color = '#10b981';
    }
  }
}

function filterAndRenderRepeats() {
  const sInput = document.getElementById('repeatsSearchInput');
  const stSelect = document.getElementById('repeatsStatusFilter');

  const q = (sInput && sInput.value.trim().toUpperCase()) || '';
  const statusFilter = (stSelect && stSelect.value) || '';

  const filtered = repeatsData.filter((r) => {
    if (q) {
      const g = (r.gene_symbol || '').toUpperCase();
      const d = (r.disease || '').toUpperCase();
      const m = (r.motif || '').toUpperCase();
      if (!g.includes(q) && !d.includes(q) && !m.includes(q)) return false;
    }
    if (statusFilter) {
      const s = r.status || '';
      if (!s.toLowerCase().includes(statusFilter.toLowerCase())) return false;
    }
    return true;
  });

  renderRepeatsTable(filtered);
}

function renderRepeatsTable(repeats) {
  const tbody = document.getElementById('repeatsTableBody');
  if (!tbody) return;

  if (!repeats || repeats.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 2rem;">No tandem repeat expansions match current filters.</td></tr>';
    return;
  }

  tbody.innerHTML = repeats.map((r) => {
    const st = r.status || 'Normal Range';
    let badgeClass = 'badge-likely-benign';
    if (st.includes('Pathogenic')) badgeClass = 'badge-pathogenic';
    else if (st.includes('Premutation') || st.includes('Reduced')) badgeClass = 'badge-warning';
    else if (st.includes('Intermediate')) badgeClass = 'badge-tier-3';

    // Normal and pathogenic cutoffs
    let cutoffsStr = 'Norm: ≤26, Path: ≥40';
    if (r.gene_symbol === 'HTT') cutoffsStr = 'Norm: ≤26, Interm: 27-35, Path: ≥40';
    else if (r.gene_symbol === 'C9orf72' || r.gene_symbol === 'C9ORF72') cutoffsStr = 'Norm: ≤25, Path: ≥31';
    else if (r.gene_symbol === 'FMR1') cutoffsStr = 'Norm: ≤44, Premut: 55-200, Path: >200';
    else if (r.gene_symbol === 'FXN') cutoffsStr = 'Norm: ≤33, Path: ≥66';
    else if (r.gene_symbol === 'DMPK') cutoffsStr = 'Norm: ≤37, Path: ≥50';
    else if (r.gene_symbol === 'ATXN1') cutoffsStr = 'Norm: ≤35, Path: ≥44';
    else if (r.gene_symbol === 'ATXN2') cutoffsStr = 'Norm: ≤31, Path: ≥32';
    else if (r.gene_symbol === 'ATXN3') cutoffsStr = 'Norm: ≤44, Path: ≥60';

    const coords = (r.chrom && r.start && r.end) ? `${r.chrom}:${r.start}-${r.end}` : '';

    return `
      <tr>
        <td>
          <strong style="font-size: 0.9rem; color: #0b2545;">${r.gene_symbol}</strong>
          ${coords ? `<br><span style="font-family: monospace; font-size: 0.72rem; color: #64748b;">${coords}</span>` : ''}
        </td>
        <td><strong style="color: #334155;">${r.disease || '-'}</strong></td>
        <td><span class="badge badge-info" style="font-family: monospace; font-size: 0.78rem;">${r.motif || 'TR'}</span></td>
        <td><strong>${r.allele_1_count}</strong> repeats</td>
        <td><strong>${r.allele_2_count}</strong> repeats</td>
        <td><span style="font-size: 0.75rem; color: #64748b;">${cutoffsStr}</span></td>
        <td><span class="badge ${badgeClass}">${st}</span></td>
        <td style="font-size: 0.8rem; color: #334155; max-width: 280px;">${r.clinical_significance || '-'}</td>
        <td>
          <div style="display: flex; gap: 0.35rem;">
            ${coords ? `
              <button class="btn btn-secondary" style="padding: 0.2rem 0.45rem; font-size: 0.75rem;" onclick="inspectRepeatInLocus('${r.chrom}', ${r.start}, ${r.end})" title="Inspect in Multi-Track Locus (IGV)">
                <i class="fa-solid fa-magnifying-glass-location"></i> IGV
              </button>
            ` : ''}
            ${(typeof isVariantInReport === 'function' && isVariantInReport(r))
              ? `<button class="btn btn-secondary" style="padding: 0.2rem 0.45rem; font-size: 0.75rem; opacity: 0.85; cursor: not-allowed; color: #10b981;" disabled title="Already included in clinical report"><i class="fa-solid fa-check"></i> Included</button>`
              : `<button class="btn btn-primary" style="padding: 0.2rem 0.45rem; font-size: 0.75rem;" onclick="addRepeatToReport('${r.gene_symbol}')" title="Add to Clinical Report"><i class="fa-solid fa-file-circle-plus"></i> Add</button>`
            }
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function inspectRepeatInLocus(chrom, start, end) {
  if (typeof switchView === 'function') {
    switchView('locus-view');
    const locInput = document.getElementById('locusSearchInput');
    const pad = 2000;
    const s = Math.max(1, start - pad);
    const e = end + pad;
    if (locInput) locInput.value = `${chrom}:${s}-${e}`;
    if (typeof igvGoTo === 'function') igvGoTo(`${chrom}:${s}-${e}`);
  }
}

window.addRepeatToReport = function(geneSymbol) {
  const r = repeatsData.find(item => item.gene_symbol === geneSymbol);
  if (!r) {
    if (typeof showToast === 'function') showToast('Repeat locus not found', 'warning');
    return;
  }
  if (typeof addVariantToClinicalReport === 'function') {
    addVariantToClinicalReport(r);
    filterAndRenderRepeats();
  }
};

document.addEventListener('DOMContentLoaded', () => {
  const applyBtn = document.getElementById('repeatsApplyFilterBtn');
  if (applyBtn) applyBtn.addEventListener('click', filterAndRenderRepeats);

  const resetBtn = document.getElementById('repeatsResetFilterBtn');
  if (resetBtn) resetBtn.addEventListener('click', () => loadRepeats(true));

  const sInput = document.getElementById('repeatsSearchInput');
  if (sInput) {
    sInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        filterAndRenderRepeats();
      }
    });
  }

  const stSelect = document.getElementById('repeatsStatusFilter');
  if (stSelect) stSelect.addEventListener('change', filterAndRenderRepeats);
});
