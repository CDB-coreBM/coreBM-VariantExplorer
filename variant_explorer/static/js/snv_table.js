// SNV / Indel Explorer Module
let snvData = [];
let snvTotal = 0;

async function loadSnvVariants(resetPage = false) {
  if (!AppState.activeCaseId) return;
  if (resetPage) AppState.snvPage = 1;

  const pEl = document.getElementById('snvPanelFilter');
  const gEl = document.getElementById('snvGeneFilter');
  const aEl = document.getElementById('snvAcmgFilter');
  const cEl = document.getElementById('snvConsequenceFilter');
  const vEl = document.getElementById('snvMinVafFilter');
  const dEl = document.getElementById('snvMinDpFilter');
  const phEl = document.getElementById('snvPhasedOnlyFilter');

  const panel = (pEl && pEl.value) || '';
  const gene = (gEl && gEl.value) || '';
  const acmg = (aEl && aEl.value) || '';
  const consequence = (cEl && cEl.value) || '';
  const minVaf = (vEl && vEl.value) || '';
  const minDp = (dEl && dEl.value) || '';
  const phasedOnly = (phEl && phEl.checked) ? 'true' : 'false';

  const params = new URLSearchParams({
    case_id: AppState.activeCaseId,
    page: AppState.snvPage,
    limit: AppState.snvPageSize,
    gene,
    acmg_class: acmg,
    consequence,
    min_vaf: minVaf,
    min_dp: minDp,
    phased_only: phasedOnly,
  });
  if (panel) params.append('panel_id', panel);

  const tbody = document.getElementById('snvTableBody');
  tbody.innerHTML = '<tr><td colspan="11" style="text-align: center; color: var(--text-muted); padding: 2rem;"><div class="spinner" style="margin: 0 auto 0.5rem auto;"></div>Loading variants...</td></tr>';

  try {
    const res = await fetch(`/api/variants/snv?${params.toString()}`);
    const result = await res.json();
    snvData = result.variants || [];
    snvTotal = result.total_records || result.total || 0;

    renderSnvTable(snvData);
    updateSnvPagination(result);
    updateSnvStats(result.metrics || result);
  } catch (err) {
    console.error('Error fetching SNVs:', err);
    tbody.innerHTML = '<tr><td colspan="11" style="text-align: center; color: var(--badge-pathogenic); padding: 2rem;">Error loading variants</td></tr>';
  }
}

function renderSnvTable(variants) {
  const tbody = document.getElementById('snvTableBody');
  if (!variants || variants.length === 0) {
    tbody.innerHTML = '<tr><td colspan="11" style="text-align: center; color: var(--text-muted); padding: 2rem;">No variants matched filter criteria.</td></tr>';
    return;
  }

  tbody.innerHTML = variants.map((v) => {
    const acmgBadge = getAcmgBadgeHtml(v.acmg_class);
    const tierBadge = getSomaticTierBadgeHtml(v.somatic_tier);
    const phaseTag = v.phase_set ? `<span class="phase-tag phased" title="ONT Phase Block: ${v.phase_set}">PS:${v.phase_set}</span>` : '<span class="phase-tag">Unphased</span>';
    const vafVal = v.vaf !== null && v.vaf !== undefined ? v.vaf : 0;
    const vafDisplay = (vafVal * 100).toFixed(1) + '%';
    const dpDisplay = v.depth ? `(${v.depth}x)` : '';
    const hgvsC = v.hgvs_c || v.hgvsc || '-';
    let hgvsP = v.hgvs_p || v.hgvsp || '';
    let isSpecialConsequence = false;
    if (!hgvsP || hgvsP === 'p.?') {
      isSpecialConsequence = true;
      const c = (v.consequence || '').toLowerCase();
      if (c.includes('splice_donor')) hgvsP = 'Splice Donor (p.?)';
      else if (c.includes('splice_acceptor')) hgvsP = 'Splice Acceptor (p.?)';
      else if (c.includes('splice')) hgvsP = 'Splice Impact (p.?)';
      else if (c.includes('upstream') || c.includes('5_prime')) hgvsP = 'Promoter / 5\' UTR';
      else if (c.includes('synonymous')) hgvsP = 'p.(=) Synonymous';
      else hgvsP = formatConsequence(v.consequence);
    }

    let gnomadDisplay = '-';
    if (v.gnomad_af !== null && v.gnomad_af !== undefined) {
      const af = Number(v.gnomad_af);
      if (af > 0) {
        if (af < 0.001) {
          gnomadDisplay = `<strong>${af.toExponential(2)}</strong>`;
        } else {
          gnomadDisplay = `<strong>${(af * 100).toFixed(2)}%</strong>`;
        }
      } else {
        gnomadDisplay = '<span style="color: #64748b;" title="Unobserved in gnomAD / Novel (AF < 1e-5)">&lt; 1e-5 (Novel)</span>';
      }
    }

    return `
      <tr onclick="inspectSnvDetail('${v.id}')">
        <td class="col-gene" title="${v.gene_symbol || '-'}"><strong>${v.gene_symbol || '-'}</strong></td>
        <td class="col-pos" title="${v.chrom}:${v.pos} ${v.ref}>${v.alt}">
          <span class="pos-tag">${v.chrom}:${v.pos} ${v.ref}&gt;${v.alt}</span>
        </td>
        <td class="col-change" title="${hgvsP} (${hgvsC})">
          <div class="change-protein" style="${isSpecialConsequence ? 'color: #0284c7;' : ''}">${hgvsP}</div>
          <div class="change-cdna">${hgvsC}</div>
        </td>
        <td class="col-consequence" title="${formatConsequence(v.consequence)}">
          <span>${formatConsequence(v.consequence)}</span>
        </td>
        <td class="col-vaf"><strong>${vafDisplay}</strong> <span style="color: var(--text-muted); font-size: 0.72rem;">${dpDisplay}</span></td>
        <td class="col-gt"><span>${v.genotype || './.'}</span></td>
        <td class="col-ps">${phaseTag}</td>
        <td class="col-acmg">${acmgBadge}</td>
        <td class="col-tier">${tierBadge}</td>
        <td class="col-af">${gnomadDisplay}</td>
        <td class="col-actions">
          <button class="btn btn-secondary" style="padding: 0.2rem 0.45rem; font-size: 0.75rem;" onclick="event.stopPropagation(); inspectSnvDetail('${v.id}')" title="Inspect Full Evidence">
            <i class="fa-solid fa-microscope"></i>
          </button>
          ${(typeof isVariantInReport === 'function' && isVariantInReport(v))
            ? `<button class="btn btn-secondary" style="padding: 0.2rem 0.45rem; font-size: 0.75rem; opacity: 0.85; cursor: not-allowed; color: #10b981;" disabled title="Already included in clinical report"><i class="fa-solid fa-check"></i> Included</button>`
            : `<button class="btn btn-primary" style="padding: 0.2rem 0.45rem; font-size: 0.75rem;" onclick="event.stopPropagation(); addSnvToReportFromTable('${v.id}')" title="Add to Clinical Report"><i class="fa-solid fa-file-circle-plus"></i> Add</button>`
          }
        </td>
      </tr>
    `;
  }).join('');
}

window.addSnvToReportFromTable = function(snvId) {
  const snv = snvData.find(item => String(item.id) === String(snvId));
  if (!snv) {
    if (typeof showToast === 'function') showToast('Small variant not found', 'warning');
    return;
  }
  if (typeof addVariantToClinicalReport === 'function') {
    addVariantToClinicalReport(snv);
    renderSnvTable(snvData);
  }
};

function getAcmgBadgeHtml(acmgClass) {
  if (!acmgClass) return '-';
  const cls = acmgClass.toLowerCase().replace(/\s+/g, '-');
  if (cls === 'pathogenic') return '<span class="badge badge-pathogenic"><i class="fa-solid fa-triangle-exclamation"></i> Pathogenic</span>';
  if (cls === 'likely-pathogenic') return '<span class="badge badge-likely-path">Likely Pathogenic</span>';
  if (cls === 'vus') return '<span class="badge badge-vus">VUS</span>';
  if (cls === 'likely-benign') return '<span class="badge badge-likely-benign">Likely Benign</span>';
  if (cls === 'benign') return '<span class="badge badge-benign">Benign</span>';
  return `<span class="badge">${acmgClass}</span>`;
}

function getSomaticTierBadgeHtml(tier) {
  if (!tier) return '-';
  if (tier.startsWith('Tier I')) return '<span class="badge badge-tier-1">Tier I: Strong</span>';
  if (tier.startsWith('Tier II')) return '<span class="badge badge-tier-2">Tier II: Potential</span>';
  if (tier.startsWith('Tier III')) return '<span class="badge badge-tier-3">Tier III: VUS</span>';
  if (tier.startsWith('Tier IV')) return '<span class="badge badge-tier-4">Tier IV: Benign</span>';
  return `<span class="badge">${tier}</span>`;
}

function formatConsequence(c) {
  if (!c) return '-';
  return c.replace(/_/g, ' ');
}

function updateSnvPagination(result) {
  const page = result.page || 1;
  const limit = result.limit || 50;
  const total = result.total_records || result.total || 0;
  const pages = result.total_pages || result.pages || 1;
  const variants = result.variants || [];

  const start = (page - 1) * limit + (variants.length > 0 ? 1 : 0);
  const end = (page - 1) * limit + variants.length;
  
  document.getElementById('snvShowingStart').textContent = start;
  document.getElementById('snvShowingEnd').textContent = end;
  document.getElementById('snvTotalCount').textContent = total;
  document.getElementById('snvCurrentPage').textContent = page;
  document.getElementById('snvTotalPages').textContent = pages;

  const prevBtn = document.getElementById('snvPrevPageBtn');
  const nextBtn = document.getElementById('snvNextPageBtn');
  if (prevBtn) prevBtn.disabled = page <= 1;
  if (nextBtn) nextBtn.disabled = page >= pages;
}

function updateSnvStats(metricsOrVariants) {
  let pathCount = 0;
  let vusCount = 0;
  let phasedCount = 0;

  if (metricsOrVariants && typeof metricsOrVariants === 'object' && !Array.isArray(metricsOrVariants)) {
    pathCount = metricsOrVariants.pathogenic_count !== undefined ? metricsOrVariants.pathogenic_count : 0;
    vusCount = metricsOrVariants.vus_count !== undefined ? metricsOrVariants.vus_count : 0;
    phasedCount = metricsOrVariants.phased_count !== undefined ? metricsOrVariants.phased_count : 0;
  } else if (Array.isArray(metricsOrVariants)) {
    metricsOrVariants.forEach((v) => {
      if (v.acmg_class === 'Pathogenic' || v.acmg_class === 'Likely Pathogenic') pathCount++;
      if (v.acmg_class === 'VUS') vusCount++;
      if (v.phase_set) phasedCount++;
    });
  }

  const pPath = document.getElementById('pillPathogenicCount');
  const pVus = document.getElementById('pillVusCount');
  const pPhased = document.getElementById('pillPhasedCount');
  if (pPath) pPath.textContent = Number(pathCount).toLocaleString();
  if (pVus) pVus.textContent = Number(vusCount).toLocaleString();
  if (pPhased) pPhased.textContent = Number(phasedCount).toLocaleString();
}

async function inspectSnvDetail(variantId) {
  const v = snvData.find((item) => item.id == variantId);
  if (!v) return;

  // Fetch live Bayesian ACMG calculation from the backend
  let acmgDetails = null;
  try {
    const res = await fetch(`/api/variants/snv/${variantId}/acmg_evidence`);
    if (res.ok) {
      const data = await res.json();
      acmgDetails = data.acmg_details;
    }
  } catch (e) {
    console.warn('Could not fetch ACMG Bayesian details:', e);
  }

  const criteriaList = (acmgDetails && acmgDetails.codes_applied) || (v.acmg_criteria || '').split(',').map((c) => c.trim()).filter(Boolean);
  const criteriaHtml = criteriaList.length > 0 
    ? criteriaList.map((c) => `<span class="criteria-pill ${c.startsWith('P') ? 'strong' : 'benign'}">${c}</span>`).join(' ')
    : '<span style="color: var(--text-muted); font-size: 0.8rem;">No automated criteria triggered</span>';

  let evidenceDetailsHtml = '';
  if (acmgDetails && acmgDetails.evidence && acmgDetails.evidence.length > 0) {
    evidenceDetailsHtml = `
      <div style="margin-top: 0.5rem; background: #0f172a; padding: 0.65rem; border-radius: 6px; border: 1px solid #1e293b;">
        <div style="font-size: 0.75rem; color: #38bdf8; font-weight: 700; margin-bottom: 0.35rem;">
          Tavtigian Bayesian Scoring: Total Points = <span style="color:#f59e0b; font-size:0.9rem;">${acmgDetails.total_points > 0 ? '+' : ''}${acmgDetails.total_points}</span> | OddsPath = <span style="color:#10b981;">${acmgDetails.odds_pathogenicity}:1</span>
        </div>
        <ul style="margin: 0; padding-left: 1.1rem; font-size: 0.75rem; color: #cbd5e1; line-height: 1.4;">
          ${acmgDetails.evidence.map(e => `<li><strong>${e.code}</strong> (${e.points > 0 ? '+' : ''}${e.points} pts): ${e.desc}</li>`).join('')}
        </ul>
      </div>
    `;
  }

  const hgvsP = v.hgvs_p || v.hgvsp || '-';
  const hgvsC = v.hgvs_c || v.hgvsc || '-';
  const vafVal = v.vaf !== null && v.vaf !== undefined ? v.vaf : 0;

  const html = `
    <div class="drawer-section">
      <h4 class="drawer-section-title">Gene & Clinical Classification</h4>
      <div class="drawer-kv-grid">
        <span class="drawer-kv-label">Gene Symbol:</span>
        <span class="drawer-kv-value"><strong>${v.gene_symbol || '-'}</strong> (${v.transcript_id || v.transcript || '-'})</span>
        <span class="drawer-kv-label">HGVS Protein:</span>
        <span class="drawer-kv-value" style="font-weight: 700; color: var(--clinical-blue);">${hgvsP}</span>
        <span class="drawer-kv-label">HGVS cDNA:</span>
        <span class="drawer-kv-value" style="font-family: monospace;">${hgvsC}</span>
        <span class="drawer-kv-label">ACMG 5-Tier:</span>
        <span class="drawer-kv-value">${getAcmgBadgeHtml((acmgDetails && acmgDetails.classification) || v.acmg_class)}</span>
        <span class="drawer-kv-label">Somatic Tier:</span>
        <span class="drawer-kv-value">${getSomaticTierBadgeHtml(v.somatic_tier)}</span>
        <span class="drawer-kv-label">ClinVar:</span>
        <span class="drawer-kv-value">${v.clinvar_sig || v.clinvar_significance || 'Not reported'}</span>
      </div>
    </div>

    <div class="drawer-section">
      <h4 class="drawer-section-title">ACMG / ClinGen Bayesian Evidence</h4>
      <div class="criteria-pill-list" style="margin-bottom: 0.5rem;">
        ${criteriaHtml}
      </div>
      ${evidenceDetailsHtml || `
      <p style="font-size: 0.8rem; color: #475569; line-height: 1.5; background: #f8fafc; padding: 0.5rem; border-radius: 4px; border: 1px solid #e2e8f0;">
        ${v.acmg_explanation || `Automated ACMG rules triggered: ${v.acmg_criteria || 'None'}. Bayesian Score: ${v.acmg_score || 0}.`}
      </p>
      `}
    </div>

    <div class="drawer-section">
      <h4 class="drawer-section-title">Nanopore Phasing & Sequencing Metrics</h4>
      <div class="drawer-kv-grid">
        <span class="drawer-kv-label">Position (GRCh38):</span>
        <span class="drawer-kv-value" style="font-family: monospace;">${v.chrom}:${v.pos} ${v.ref}>${v.alt}</span>
        <span class="drawer-kv-label">ONT Phase Block (PS):</span>
        <span class="drawer-kv-value">${v.phase_set ? `<span class="phase-tag phased">Block ${v.phase_set}</span>` : 'Unphased'}</span>
        <span class="drawer-kv-label">Genotype:</span>
        <span class="drawer-kv-value" style="font-family: monospace;">${v.genotype || './.'}</span>
        <span class="drawer-kv-label">VAF / Allele Balance:</span>
        <span class="drawer-kv-value"><strong>${(vafVal * 100).toFixed(1)}%</strong></span>
        <span class="drawer-kv-label">Read Depth (DP):</span>
        <span class="drawer-kv-value">${v.depth || 0} reads (Alt reads: ${v.alt_depth || v.alt_count || 0})</span>
        <span class="drawer-kv-label">Phred Quality:</span>
        <span class="drawer-kv-value">${v.qual || '-'}</span>
      </div>
    </div>

    <div class="drawer-section">
      <h4 class="drawer-section-title">In-silico & Population Allele Frequencies</h4>
      <div class="drawer-kv-grid">
        <span class="drawer-kv-label">gnomAD Population AF:</span>
        <span class="drawer-kv-value">${v.gnomad_af && Number(v.gnomad_af) > 0 ? (Number(v.gnomad_af) < 0.001 ? Number(v.gnomad_af).toExponential(3) : (Number(v.gnomad_af) * 100).toFixed(2) + '% (' + v.gnomad_af + ')') : '<span style="color: #64748b;">&lt; 1e-5 (Unobserved / Novel)</span>'}</span>
        <span class="drawer-kv-label">REVEL Score:</span>
        <span class="drawer-kv-value">${v.revel !== null && v.revel !== undefined ? v.revel : (v.revel_score || '-')}</span>
        <span class="drawer-kv-label">CADD Phred:</span>
        <span class="drawer-kv-value">${v.cadd_phred !== null && v.cadd_phred !== undefined ? v.cadd_phred : '-'}</span>
      </div>
    </div>
  `;

  openDetailDrawer(
    `${v.gene_symbol} ${hgvsP}`,
    `${v.chrom}:${v.pos} ${v.ref}>${v.alt}`,
    html,
    v
  );
}

document.addEventListener('DOMContentLoaded', () => {
  const applyBtn = document.getElementById('snvApplyFilterBtn');
  if (applyBtn) applyBtn.addEventListener('click', () => loadSnvVariants(true));

  const panelSelect = document.getElementById('snvPanelFilter');
  if (panelSelect) panelSelect.addEventListener('change', () => loadSnvVariants(true));

  const resetBtn = document.getElementById('snvResetFilterBtn');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      if (document.getElementById('snvPanelFilter')) document.getElementById('snvPanelFilter').value = '';
      if (document.getElementById('snvGeneFilter')) document.getElementById('snvGeneFilter').value = '';
      if (document.getElementById('snvAcmgFilter')) document.getElementById('snvAcmgFilter').value = '';
      if (document.getElementById('snvConsequenceFilter')) document.getElementById('snvConsequenceFilter').value = '';
      if (document.getElementById('snvMinVafFilter')) document.getElementById('snvMinVafFilter').value = '';
      if (document.getElementById('snvMinDpFilter')) document.getElementById('snvMinDpFilter').value = '';
      if (document.getElementById('snvPhasedOnlyFilter')) document.getElementById('snvPhasedOnlyFilter').checked = false;
      loadSnvVariants(true);
    });
  }

  const prevBtn = document.getElementById('snvPrevPageBtn');
  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      if (AppState.snvPage > 1) {
        AppState.snvPage--;
        loadSnvVariants(false);
      }
    });
  }

  const nextBtn = document.getElementById('snvNextPageBtn');
  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      AppState.snvPage++;
      loadSnvVariants(false);
    });
  }
});
