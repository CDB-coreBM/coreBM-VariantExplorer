// Tandem Repeat Expansions (TRGT / Straglr) Module
// Hospital Clínic de Barcelona - CoreBM Variant Explorer

let repeatsData = [];
let referenceDistribution = {};
let clinicalLociDefs = {};
let currentRepeatsUnit = 'bp'; // 'bp' or 'copies'
let currentRepeatsMode = 'plot'; // 'plot' or 'table'

/**
 * Loads tandem repeat data, reference distributions, and clinical cutoffs.
 */
async function loadRepeats(resetFilters = false) {
  const tbody = document.getElementById('repeatsTableBody');
  const plotContainer = document.getElementById('repeatsSvgContainer');
  const activeSampleSpan = document.getElementById('repeatsPlotActiveSample');

  if (!AppState.activeCaseId) {
    if (tbody) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 3rem;"><i class="fa-solid fa-folder-open" style="font-size: 2rem; margin-bottom: 0.75rem; color: #64748b; display: block;"></i>Please select a clinical case from the header dropdown or ingest a new sample.</td></tr>';
    }
    if (plotContainer) {
      plotContainer.innerHTML = '<div style="text-align: center; padding: 4rem 1rem; color: #64748b;"><i class="fa-solid fa-folder-open" style="font-size: 2.5rem; margin-bottom: 1rem; color: #94a3b8; display: block;"></i>Please select a clinical case to visualize repeat expansion sizing distribution.</div>';
    }
    if (activeSampleSpan) activeSampleSpan.textContent = 'None';
    return;
  }

  if (activeSampleSpan) {
    activeSampleSpan.textContent = AppState.activeCaseId;
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
    const res = await fetch(`/api/repeats?case_id=${encodeURIComponent(AppState.activeCaseId)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch repeats`);
    const data = await res.json();
    repeatsData = data.repeat_expansions || data.repeats || [];
    referenceDistribution = data.reference_distribution || {};
    clinicalLociDefs = data.clinical_loci_definitions || {};

    updateRepeatsStats(repeatsData);
    filterAndRenderRepeats();
    renderRepeatsDistributionPlot();
  } catch (err) {
    console.error('Error fetching repeats:', err);
    if (tbody) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: var(--badge-pathogenic); padding: 2rem;">Error loading tandem repeat expansions.</td></tr>';
    }
    if (plotContainer) {
      plotContainer.innerHTML = `<div style="text-align: center; padding: 3rem; color: #ef4444;"><i class="fa-solid fa-triangle-exclamation" style="font-size: 2rem; margin-bottom: 0.5rem; display: block;"></i>Failed to load sizing distribution: ${err.message}</div>`;
    }
  }
}

/**
 * Switch view mode between Plot and Table
 */
window.switchRepeatsViewMode = function(mode) {
  currentRepeatsMode = mode;
  const plotSec = document.getElementById('repeatsPlotSection');
  const tableSec = document.getElementById('repeatsTableSection');
  const plotBtn = document.getElementById('repeatsViewPlotBtn');
  const tableBtn = document.getElementById('repeatsViewTableBtn');

  if (mode === 'plot') {
    if (plotSec) plotSec.style.display = 'block';
    if (tableSec) tableSec.style.display = 'none';
    if (plotBtn) {
      plotBtn.className = 'btn btn-primary';
    }
    if (tableBtn) {
      tableBtn.className = 'btn btn-secondary';
    }
    renderRepeatsDistributionPlot();
  } else {
    if (plotSec) plotSec.style.display = 'none';
    if (tableSec) tableSec.style.display = 'block';
    if (plotBtn) {
      plotBtn.className = 'btn btn-secondary';
    }
    if (tableBtn) {
      tableBtn.className = 'btn btn-primary';
    }
  }
};

/**
 * Toggle unit between Base Pairs (bp) and Repeat Copies
 */
window.setRepeatsUnit = function(unit) {
  currentRepeatsUnit = unit;
  const bpBtn = document.getElementById('repeatsUnitBpBtn');
  const copiesBtn = document.getElementById('repeatsUnitCopiesBtn');

  if (unit === 'bp') {
    if (bpBtn) bpBtn.className = 'btn btn-primary';
    if (copiesBtn) copiesBtn.className = 'btn btn-secondary';
  } else {
    if (bpBtn) bpBtn.className = 'btn btn-secondary';
    if (copiesBtn) copiesBtn.className = 'btn btn-primary';
  }

  renderRepeatsDistributionPlot();
};

/**
 * Updates summary KPIs and badges.
 */
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

/**
 * Filters and renders the tabular callset view.
 */
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

    const mLen = r.motif_len || (r.motif ? r.motif.length : 3);
    const normMax = r.normal_max || 30;
    const pathMin = r.pathogenic_min || 50;
    const interMax = r.intermediate_max;

    let cutoffsStr = `Norm: ≤${normMax}, Path: ≥${pathMin}`;
    if (interMax && interMax !== normMax) {
      cutoffsStr = `Norm: ≤${normMax}, Risk: ${normMax + 1}-${pathMin - 1}, Path: ≥${pathMin}`;
    }

    const coords = (r.chrom && r.start && r.end) ? `${r.chrom}:${r.start}-${r.end}` : '';

    return `
      <tr>
        <td>
          <strong style="font-size: 0.9rem; color: #0b2545;">${r.gene_symbol}</strong>
          ${coords ? `<br><span style="font-family: monospace; font-size: 0.72rem; color: #64748b;">${coords}</span>` : ''}
        </td>
        <td><strong style="color: #334155;">${r.disease || '-'}</strong></td>
        <td><span class="badge badge-info" style="font-family: monospace; font-size: 0.78rem;">${r.motif || 'TR'}</span></td>
        <td><strong>${r.allele_1_count}</strong> rpts (${r.allele_1_bp || r.allele_1_count * mLen} bp)</td>
        <td><strong>${r.allele_2_count}</strong> rpts (${r.allele_2_bp || r.allele_2_count * mLen} bp)</td>
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

/**
 * Main SVG Rendering Engine for Tandem Repeat Allele Sizing Distribution.
 * Matches ExpansionHunter / TRGT horizontal lane strip-plot with shaded clinical ranges.
 */
function renderRepeatsDistributionPlot() {
  const container = document.getElementById('repeatsSvgContainer');
  if (!container) return;

  if (!repeatsData || repeatsData.length === 0) {
    container.innerHTML = '<div style="text-align: center; padding: 4rem; color: #64748b;">No repeat expansion data available for active case.</div>';
    return;
  }

  const isBp = (currentRepeatsUnit === 'bp');

  // Order of genes to display:
  // Prefer the order in repeatsData (which reflects external catalog display_order)
  const geneOrder = repeatsData.map(r => r.gene_symbol);
  const lociCount = geneOrder.length;

  // Chart Dimensions & Margins
  const margin = { top: 45, right: 35, bottom: 60, left: 130 };
  const laneHeight = 44;
  const plotWidth = 980;
  const innerWidth = plotWidth - margin.left - margin.right;
  const innerHeight = lociCount * laneHeight;
  const totalHeight = innerHeight + margin.top + margin.bottom;

  // Determine X-axis maximum domain
  // In bp mode, screenshot reaches ~650 bp. Let's make sure it covers all loci.
  let maxXDomain = isBp ? 650 : 220;

  repeatsData.forEach(r => {
    const mLen = r.motif_len || (r.motif ? r.motif.length : 3);
    const pathMin = r.pathogenic_min || 50;
    const longAllele = r.max_repeat_count || Math.max(r.allele_1_count || 0, r.allele_2_count || 0);

    const valPath = isBp ? (pathMin * mLen) : pathMin;
    const valPatient = isBp ? (longAllele * mLen) : longAllele;

    if (valPath * 1.25 > maxXDomain) maxXDomain = Math.ceil((valPath * 1.25) / 50) * 50;
    if (valPatient * 1.2 > maxXDomain) maxXDomain = Math.ceil((valPatient * 1.2) / 50) * 50;
  });

  // Check reference points to ensure they fit in domain
  Object.values(referenceDistribution).forEach(pts => {
    pts.forEach(p => {
      const pVal = isBp ? p.bp : p.repeats;
      if (pVal * 1.1 > maxXDomain) {
        maxXDomain = Math.ceil((pVal * 1.1) / 50) * 50;
      }
    });
  });

  const scaleX = (val) => {
    const clamped = Math.max(0, Math.min(val, maxXDomain));
    return margin.left + (clamped / maxXDomain) * innerWidth;
  };

  // Color Palette matching ExpansionHunter screenshot
  const colors = {
    normalBg: '#e0f2fe',       // Soft Sky Blue
    normalBorder: '#bae6fd',
    riskBg: '#fef3c7',         // Soft Cream / Light Amber
    riskBorder: '#fde68a',
    diseaseBg: '#fed7aa',      // Soft Peach / Coral
    diseaseBorder: '#fdba74',
    dotNormal: '#0284c7',      // Primary Blue
    dotPremutation: '#f59e0b', // Amber / Orange
    dotExpansion: '#b91c1c',   // Crimson / Dark Red
    laneLine: '#94a3b8',
    axisLine: '#334155',
    textMain: '#0f172a',
    patientGlow: '#00f5d4'
  };

  let svgHtml = `
    <svg id="repeatsDistributionSvg" viewBox="0 0 ${plotWidth} ${totalHeight}" width="100%" height="${totalHeight}" 
         style="background: #ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: block; user-select: none;">
      <defs>
        <!-- Glow filter for Active Patient Sample Marker -->
        <filter id="patientSampleGlow" x="-30%" y="-30%" width="160%" height="160%">
          <feDropShadow dx="0" dy="1" stdDeviation="3" flood-color="#000000" flood-opacity="0.35"/>
          <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="#0284c7" flood-opacity="0.8"/>
        </filter>
        <filter id="patientSampleGlowPath" x="-30%" y="-30%" width="160%" height="160%">
          <feDropShadow dx="0" dy="1" stdDeviation="3" flood-color="#000000" flood-opacity="0.35"/>
          <feDropShadow dx="0" dy="0" stdDeviation="5" flood-color="#ef4444" flood-opacity="0.9"/>
        </filter>
        <filter id="patientSampleGlowPremut" x="-30%" y="-30%" width="160%" height="160%">
          <feDropShadow dx="0" dy="1" stdDeviation="3" flood-color="#000000" flood-opacity="0.35"/>
          <feDropShadow dx="0" dy="0" stdDeviation="5" flood-color="#f59e0b" flood-opacity="0.9"/>
        </filter>
      </defs>

      <!-- Plot Title matching ExpansionHunter banner -->
      <text x="${plotWidth / 2}" y="26" text-anchor="middle" font-size="16" font-weight="700" fill="#0f172a" letter-spacing="0.5">
        Expansion Hunter
      </text>

      <!-- Left Vertical Axis Label: 'Gene containing the repeat' -->
      <g transform="translate(24, ${margin.top + innerHeight / 2}) rotate(-90)">
        <text text-anchor="middle" font-size="13" font-weight="600" fill="#334155" letter-spacing="0.3">
          Gene containing the repeat
        </text>
      </g>
  `;

  // Draw Gene Lanes
  geneOrder.forEach((gene, idx) => {
    const laneY = margin.top + idx * laneHeight;
    const laneCenterY = laneY + laneHeight / 2;

    const patientRecord = repeatsData.find(r => r.gene_symbol === gene) || {};
    const locusDef = clinicalLociDefs[gene] || {};
    const motif = patientRecord.motif || locusDef.motif || 'CAG';
    const mLen = patientRecord.motif_len || motif.length || 3;

    const normMax = patientRecord.normal_max || locusDef.normal_max || 30;
    const pathMin = patientRecord.pathogenic_min || locusDef.pathogenic_min || 50;

    const normCutoff = isBp ? (normMax * mLen) : normMax;
    const pathCutoff = isBp ? (pathMin * mLen) : pathMin;

    const x0 = scaleX(0);
    const xNorm = scaleX(normCutoff);
    const xPath = scaleX(pathCutoff);
    const xMax = scaleX(maxXDomain);

    // 1. Shaded Background Bands for Clinical Repeat Ranges
    // Normal Range (Sky Blue)
    svgHtml += `
      <rect x="${x0}" y="${laneY}" width="${Math.max(0, xNorm - x0)}" height="${laneHeight}" 
            fill="${colors.normalBg}" stroke="${colors.normalBorder}" stroke-width="0.5" />
    `;

    // Risk / Intermediate / Premutation Range (Cream / Light Amber)
    if (xPath > xNorm) {
      svgHtml += `
        <rect x="${xNorm}" y="${laneY}" width="${Math.max(0, xPath - xNorm)}" height="${laneHeight}" 
              fill="${colors.riskBg}" stroke="${colors.riskBorder}" stroke-width="0.5" />
      `;
    }

    // Disease / Full Expansion Range (Peach / Coral)
    if (xMax > xPath) {
      svgHtml += `
        <rect x="${xPath}" y="${laneY}" width="${Math.max(0, xMax - xPath)}" height="${laneHeight}" 
              fill="${colors.diseaseBg}" stroke="${colors.diseaseBorder}" stroke-width="0.5" />
      `;
    }

    // Lane Divider Lines
    svgHtml += `
      <line x1="${x0}" y1="${laneY}" x2="${xMax}" y2="${laneY}" stroke="${colors.laneLine}" stroke-width="0.75" />
    `;
    if (idx === lociCount - 1) {
      svgHtml += `
        <line x1="${x0}" y1="${laneY + laneHeight}" x2="${xMax}" y2="${laneY + laneHeight}" stroke="${colors.laneLine}" stroke-width="0.75" />
      `;
    }

    // Gene Label on Left
    svgHtml += `
      <text x="${margin.left - 12}" y="${laneCenterY + 4.5}" text-anchor="end" font-size="12" font-weight="700" fill="${colors.textMain}">
        ${gene}
      </text>
    `;

    // 2. Population Reference Swarm Points
    const refPoints = referenceDistribution[gene] || [];
    refPoints.forEach((pt) => {
      const ptVal = isBp ? pt.bp : pt.repeats;
      const ptX = scaleX(ptVal);
      // Jitter range +- 12px within lane
      const ptY = laneCenterY + (pt.jitter_y * (laneHeight * 0.38));

      let dotColor = colors.dotNormal;
      if (pt.status === 'premutation') dotColor = colors.dotPremutation;
      else if (pt.status === 'expansion') dotColor = colors.dotExpansion;

      const safeSample = escapeSvg(pt.sample_id || 'Ref Cohort');
      const safeLabel = escapeSvg(pt.status_label || pt.status);

      svgHtml += `
        <circle cx="${ptX}" cy="${ptY}" r="3.2" fill="${dotColor}" fill-opacity="0.8" stroke="#ffffff" stroke-width="0.5"
                class="ref-dot"
                onmouseover="showRepeatPointTooltip(event, '${gene}', '${safeSample}', ${pt.repeats}, ${pt.bp}, '${safeLabel}', false)"
                onmouseout="hideRepeatTooltip()" 
                style="cursor: pointer; transition: transform 0.15s ease;" />
      `;
    });

    // 3. Current Active Patient Sample Marker (Long Allele & Short Allele)
    if (patientRecord.max_repeat_count !== undefined || patientRecord.allele_1_count !== undefined) {
      const a1 = patientRecord.allele_1_count || 0;
      const a2 = patientRecord.allele_2_count || 0;
      const longCount = Math.max(a1, a2);
      const shortCount = Math.min(a1, a2);

      const longBp = patientRecord.long_allele_bp || (longCount * mLen);
      const shortBp = patientRecord.short_allele_bp || (shortCount * mLen);

      const patientLongVal = isBp ? longBp : longCount;
      const patientShortVal = isBp ? shortBp : shortCount;

      const pXLong = scaleX(patientLongVal);
      const pXShort = scaleX(patientShortVal);
      const pY = laneCenterY;

      const pStatus = patientRecord.status || 'Normal Range';
      let patientColor = '#0284c7';
      let filterTag = 'patientSampleGlow';
      if (pStatus.includes('Pathogenic')) {
        patientColor = '#ef4444';
        filterTag = 'patientSampleGlowPath';
      } else if (pStatus.includes('Premutation') || pStatus.includes('Reduced')) {
        patientColor = '#f59e0b';
        filterTag = 'patientSampleGlowPremut';
      }

      const caseLabel = escapeSvg(AppState.activeCaseId || 'Patient Sample');
      const safeStatus = escapeSvg(pStatus);
      const safeDisease = escapeSvg(patientRecord.disease || '');

      // Short allele (smaller marker if heterozygous)
      if (longCount !== shortCount) {
        svgHtml += `
          <circle cx="${pXShort}" cy="${pY}" r="5" fill="#ffffff" stroke="${patientColor}" stroke-width="2.5" 
                  onmouseover="showRepeatPointTooltip(event, '${gene}', '${caseLabel} (Allele 1)', ${shortCount}, ${shortBp}, '${safeStatus}', true, '${safeDisease}')"
                  onmouseout="hideRepeatTooltip()"
                  style="cursor: pointer;" />
        `;
      }

      // Long allele (prominent, glowing diamond)
      const dSize = 7.5;
      svgHtml += `
        <g transform="translate(${pXLong}, ${pY})" filter="url(#${filterTag})" style="cursor: pointer;"
           onmouseover="showRepeatPointTooltip(event, '${gene}', '${caseLabel} (Long Allele)', ${longCount}, ${longBp}, '${safeStatus}', true, '${safeDisease}', '${patientRecord.chrom}', ${patientRecord.start}, ${patientRecord.end})"
           onmouseout="hideRepeatTooltip()">
          <!-- Diamond Marker -->
          <polygon points="0,-${dSize} ${dSize},0 0,${dSize} -${dSize},0" 
                   fill="${patientColor}" stroke="#ffffff" stroke-width="2.5" />
          <circle cx="0" cy="0" r="2.2" fill="#ffffff" />
        </g>
      `;
    }
  });

  // 4. Bottom X-Axis Ticks & Labels
  const axisY = margin.top + innerHeight;
  const x0 = scaleX(0);
  const xMax = scaleX(maxXDomain);

  svgHtml += `
    <!-- Axis Main Line -->
    <line x1="${x0}" y1="${axisY}" x2="${xMax}" y2="${axisY}" stroke="${colors.axisLine}" stroke-width="1.2" />
  `;

  // Compute nice tick step (e.g. 100 for bp, 25 or 50 for copies)
  const tickStep = isBp ? 100 : (maxXDomain > 150 ? 50 : 25);
  for (let val = 0; val <= maxXDomain; val += tickStep) {
    const tickX = scaleX(val);
    svgHtml += `
      <line x1="${tickX}" y1="${axisY}" x2="${tickX}" y2="${axisY + 6}" stroke="${colors.axisLine}" stroke-width="1" />
      <text x="${tickX}" y="${axisY + 20}" text-anchor="middle" font-size="11.5" font-weight="500" fill="#334155">
        ${val}
      </text>
    `;
  }

  // Bottom Axis Title matching screenshot
  const axisLabel = isBp ? 'Estimate of the long allele size (bp)' : 'Repeat copies (units)';
  svgHtml += `
    <text x="${margin.left + innerWidth / 2}" y="${axisY + 44}" text-anchor="middle" font-size="13" font-weight="600" fill="#0f172a" letter-spacing="0.3">
      ${axisLabel}
    </text>
  `;

  // 5. Legend Box (Matching Screenshot Box on Bottom Right)
  const legendWidth = 230;
  const legendHeight = 110;
  const legendX = plotWidth - margin.right - legendWidth - 5;
  const legendY = totalHeight - margin.bottom - legendHeight + 15;

  svgHtml += `
    <g transform="translate(${legendX}, ${legendY})">
      <!-- Legend Background Card -->
      <rect x="0" y="0" width="${legendWidth}" height="${legendHeight}" rx="4" ry="4" 
            fill="#ffffff" stroke="#cbd5e1" stroke-width="1" opacity="0.95" />
      
      <!-- Legend Header -->
      <text x="14" y="20" font-size="11.5" font-weight="700" fill="#0f172a">Experimental status</text>

      <!-- Legend Item 1: Normal or unknown -->
      <circle cx="22" cy="38" r="4.5" fill="${colors.dotNormal}" stroke="#ffffff" stroke-width="0.5" />
      <text x="36" y="42" font-size="11" font-weight="500" fill="#334155">Normal or unknown</text>

      <!-- Legend Item 2: Premutation -->
      <circle cx="22" cy="58" r="4.5" fill="${colors.dotPremutation}" stroke="#ffffff" stroke-width="0.5" />
      <text x="36" y="62" font-size="11" font-weight="500" fill="#334155">Premutation</text>

      <!-- Legend Item 3: Full expansion -->
      <circle cx="22" cy="78" r="4.5" fill="${colors.dotExpansion}" stroke="#ffffff" stroke-width="0.5" />
      <text x="36" y="82" font-size="11" font-weight="500" fill="#334155">Full expansion</text>

      <!-- Legend Item 4: Active Patient Sample -->
      <g transform="translate(22, 97)">
        <polygon points="0,-5 5,0 0,5 -5,0" fill="#0284c7" stroke="#00f5d4" stroke-width="1.5" />
      </g>
      <text x="36" y="100" font-size="11" font-weight="700" fill="#0f172a">Current Patient Sample</text>
    </g>
  `;

  svgHtml += `</svg>`;
  container.innerHTML = svgHtml;
}

/**
 * Escapes strings for safe inclusion in SVG attributes
 */
function escapeSvg(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * Interactive Tooltip Display for Data Points on the Strip Plot
 */
window.showRepeatPointTooltip = function(event, gene, sampleId, repeats, bp, statusLabel, isPatient = false, disease = '', chrom = '', start = 0, end = 0) {
  const tooltip = document.getElementById('repeatsPlotTooltip');
  if (!tooltip) return;

  let badgeColor = '#0284c7';
  if (statusLabel.includes('Pathogenic') || statusLabel.includes('Full expansion')) badgeColor = '#ef4444';
  else if (statusLabel.includes('Premutation') || statusLabel.includes('Reduced')) badgeColor = '#f59e0b';
  else if (statusLabel.includes('Intermediate')) badgeColor = '#8b5cf6';

  let html = `
    <div style="font-weight: 700; font-size: 0.95rem; margin-bottom: 0.25rem; display: flex; justify-content: space-between; align-items: center;">
      <span>${gene}</span>
      <span style="font-size: 0.7rem; background: ${badgeColor}; padding: 0.15rem 0.45rem; border-radius: 4px; color: #fff;">${statusLabel}</span>
    </div>
    ${disease ? `<div style="font-size: 0.74rem; color: #94a3b8; margin-bottom: 0.4rem;">${disease}</div>` : ''}
    <div style="font-size: 0.8rem; margin-bottom: 0.2rem;">
      <span style="color: #cbd5e1;">Sample:</span> <strong>${sampleId}</strong>
    </div>
    <div style="font-size: 0.8rem; margin-bottom: 0.2rem;">
      <span style="color: #cbd5e1;">Allele Sizing:</span> <strong>${bp} bp</strong> (${repeats} repeats)
    </div>
  `;

  if (isPatient) {
    html += `
      <div style="margin-top: 0.6rem; padding-top: 0.5rem; border-top: 1px solid #334155; display: flex; gap: 0.4rem;">
        ${(chrom && start && end) ? `
          <button class="btn btn-secondary" style="padding: 0.15rem 0.45rem; font-size: 0.72rem;" onclick="inspectRepeatInLocus('${chrom}', ${start}, ${end})">
            <i class="fa-solid fa-magnifying-glass-location"></i> IGV
          </button>
        ` : ''}
        <button class="btn btn-primary" style="padding: 0.15rem 0.45rem; font-size: 0.72rem;" onclick="addRepeatToReport('${gene}')">
          <i class="fa-solid fa-file-circle-plus"></i> Report
        </button>
      </div>
    `;
  }

  tooltip.innerHTML = html;
  tooltip.style.display = 'block';

  // Position tooltip relative to container
  const container = document.getElementById('repeatsSvgWrapper');
  const containerRect = container.getBoundingClientRect();
  const left = event.clientX - containerRect.left + 15;
  const top = event.clientY - containerRect.top + 15;

  tooltip.style.left = `${Math.max(10, Math.min(left, containerRect.width - 300))}px`;
  tooltip.style.top = `${Math.max(10, top)}px`;
};

window.hideRepeatTooltip = function() {
  const tooltip = document.getElementById('repeatsPlotTooltip');
  if (tooltip) {
    tooltip.style.display = 'none';
  }
};

/**
 * Navigation to multi-track IGV viewer
 */
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

/**
 * Add repeat finding to persistent clinical report
 */
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

// Event Listeners Initialization
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
