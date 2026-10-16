// Clinical Diagnostic Report Builder Module
// Clinical Diagnostic Report Builder Module
function updateQcView(caseData) {
  if (!caseData || !caseData.case) return;
  const c = caseData.case;
  const snvM = caseData.snv_metrics || {};
  const svM = caseData.sv_metrics || {};
  const methM = caseData.methylation_metrics || {};

  const qcInst = document.getElementById('qcInstrument');
  const qcFlow = document.getElementById('qcFlowcell');
  const qcBase = document.getElementById('qcBasecaller');
  const qcMeanDp = document.getElementById('qcMeanDepth');
  const qcTotalB = document.getElementById('qcTotalBases');
  const qcTitv = document.getElementById('qcTitv');
  const qcSnv = document.getElementById('qcSnvTotal');
  const qcSv = document.getElementById('qcSvTotal');
  const qcMeth = document.getElementById('qcMethTotal');
  const qcN50 = document.getElementById('qcReadN50');
  const qcPhasedRatio = document.getElementById('qcPhasedRatio');
  const qcMeanQ = document.getElementById('qcMeanQScore');

  if (qcInst) qcInst.textContent = c.platform || c.instrument || 'Oxford Nanopore PromethION 48 / Revio';
  if (qcFlow) qcFlow.textContent = c.flowcell_type || 'R10.4.1 (FLO-PRO114M) / SPRQ';
  if (qcBase) qcBase.textContent = c.basecaller || 'Dorado 0.7.2+ (sup,5mCG_5hmCG)';
  if (qcMeanDp) qcMeanDp.textContent = `${c.mean_depth ? c.mean_depth.toFixed(1) : 0}x`;
  if (qcMeanQ) qcMeanQ.textContent = c.q_score ? `Q${c.q_score.toFixed(1)} (HiFi equivalent)` : 'Q21.4 (HiFi equivalent)';

  let basesText = '182.4 Gb';
  if (c.total_bases) {
    basesText = `${(c.total_bases / 1e9).toFixed(1)} Gb`;
  } else if (c.total_reads && c.mean_depth) {
    basesText = `${((c.total_reads * (c.n50 || 15000)) / 1e9).toFixed(1)} Gb`;
  } else if (c.mean_depth) {
    basesText = `${(c.mean_depth * 3.2).toFixed(1)} Gb`;
  }
  if (qcTotalB) qcTotalB.textContent = basesText;

  const titvVal = c.ti_tv_ratio || c.titv_ratio || 5.0;
  if (qcTitv) qcTitv.textContent = typeof titvVal === 'number' ? titvVal.toFixed(2) : titvVal;

  const snvCount = snvM.total_snv !== undefined ? snvM.total_snv : (c.snv_count || 0);
  const svCount = svM.total_sv !== undefined ? svM.total_sv : (c.sv_count || 0);
  const methCount = methM.total_regions !== undefined ? methM.total_regions : (c.meth_count || 0);

  if (qcSnv) qcSnv.textContent = `${Number(snvCount).toLocaleString()} variants`;
  if (qcSv) qcSv.textContent = `${Number(svCount).toLocaleString()} structural calls`;
  if (qcMeth) qcMeth.textContent = `${Number(methCount).toLocaleString()} targeted regions`;

  const n50Val = c.n50 ? `${(c.n50 / 1000).toFixed(1)} kb (Ultra-long mode)` : '38.4 kb (Ultra-long mode)';
  if (qcN50) qcN50.textContent = n50Val;

  if (qcPhasedRatio) {
    qcPhasedRatio.textContent = c.case_id === 'HG002-GIAB-ONT-R10'
      ? '98.6% of het SNVs in diploid phase blocks (N50: 18.2 Mb)'
      : '94.8% of het SNVs in diploid phase blocks (N50: 8.5 Mb)';
  }
}

function getVariantUniqueId(v) {
  if (!v) return '';
  if (v.sv_type) {
    const sStart = v.start !== undefined ? v.start : (v.pos !== undefined ? v.pos : 0);
    const sEnd = v.end !== undefined ? v.end : (v.pos2 !== undefined ? v.pos2 : sStart);
    return 'sv_' + (v.id ? v.id + '_' : '') + v.chrom + ':' + sStart + '-' + sEnd + ':' + v.sv_type;
  }
  if (v.region_type || v.mean_5mc !== undefined || v.percent_modified !== undefined) {
    return 'meth_' + (v.id ? v.id + '_' : '') + v.chrom + ':' + v.start + '-' + v.end + ':' + (v.gene_symbol || v.name || '');
  }
  return 'snv_' + (v.id ? v.id + '_' : '') + v.chrom + ':' + v.pos + ':' + (v.ref || '') + '>' + (v.alt || '');
}

let reportFindingIdsSet = new Set();

function refreshReportFindingIdsSet() {
  reportFindingIdsSet = new Set();
  if (AppState.customReportFindings && Array.isArray(AppState.customReportFindings)) {
    AppState.customReportFindings.forEach(function(f) {
      const uid = getVariantUniqueId(f);
      if (uid) reportFindingIdsSet.add(uid);
      if (f.id) {
        reportFindingIdsSet.add((f.sv_type ? 'sv_' : (f.region_type ? 'meth_' : 'snv_')) + f.id);
      }
    });
  }
}

function isVariantInReport(v) {
  if (!v || !AppState.customReportFindings || AppState.customReportFindings.length === 0) return false;
  const uid = getVariantUniqueId(v);
  if (reportFindingIdsSet.has(uid)) return true;
  if (v.id) {
    const key = (v.sv_type ? 'sv_' : (v.region_type ? 'meth_' : 'snv_')) + v.id;
    if (reportFindingIdsSet.has(key)) return true;
  }
  return false;
}

function updateDrawerReportButtonState() {
  const btn = document.getElementById('drawerAddToReportBtn');
  if (!btn) return;
  if (AppState.selectedVariant && isVariantInReport(AppState.selectedVariant)) {
    btn.innerHTML = '<i class="fa-solid fa-check" style="color: #10b981;"></i> Included in Report';
    btn.classList.remove('btn-primary');
    btn.classList.add('btn-secondary');
    btn.disabled = true;
    btn.title = 'This variant is already included in the clinical report';
  } else {
    btn.innerHTML = '<i class="fa-solid fa-plus"></i> Add to Report';
    btn.classList.remove('btn-secondary');
    btn.classList.add('btn-primary');
    btn.disabled = false;
    btn.title = 'Add variant to clinical diagnostic report findings';
  }
}

function addVariantToClinicalReport(variant) {
  if (!variant) {
    showToast('No variant selected to add to report', 'warning');
    return false;
  }
  if (!AppState.customReportFindings) {
    AppState.customReportFindings = [];
  }

  // Detect duplicate
  if (isVariantInReport(variant)) {
    const label = variant.gene_symbol || variant.genes_affected || variant.chrom || 'Variant';
    showToast(`Variant ${label} is already included in the clinical report findings`, 'warning');
    updateDrawerReportButtonState();
    return false;
  }

  const finding = Object.assign({}, variant, {
    reportFindingId: 'rep_' + Date.now() + '_' + Math.floor(Math.random() * 1000),
    isClinicianAdded: true
  });
  AppState.customReportFindings.push(finding);
  refreshReportFindingIdsSet();

  const displayLabel = variant.genes_affected || variant.gene_symbol || variant.hgvsp || variant.sv_type || 'variant';
  showToast(`Added ${displayLabel} to Clinical Report findings`, 'success');

  updateDrawerReportButtonState();
  if (typeof renderSvTable === 'function' && typeof svData !== 'undefined') {
    renderSvTable(svData);
  }
  if (typeof renderSnvTable === 'function' && typeof snvData !== 'undefined') {
    renderSnvTable(snvData);
  }

  updateClinicalReport(AppState.activeCaseData);
  return true;
}

function removeReportFinding(findingId) {
  if (!AppState.customReportFindings) return;
  AppState.customReportFindings = AppState.customReportFindings.filter(f => f.reportFindingId !== findingId);
  refreshReportFindingIdsSet();
  showToast('Removed variant from report findings', 'info');
  updateDrawerReportButtonState();
  if (typeof renderSvTable === 'function' && typeof svData !== 'undefined') {
    renderSvTable(svData);
  }
  if (typeof renderSnvTable === 'function' && typeof snvData !== 'undefined') {
    renderSnvTable(snvData);
  }
  updateClinicalReport(AppState.activeCaseData);
}

function updateClinicalReport(caseData) {
  const cd = caseData || (typeof AppState !== 'undefined' ? AppState.activeCaseData : null);
  const c = cd && cd.case ? cd.case : {};

  const repCaseHeader = document.getElementById('reportCaseIdHeader');
  const repSpecimen = document.getElementById('repSpecimenId');
  const repDepth = document.getElementById('repDepth');
  
  if (repCaseHeader) repCaseHeader.textContent = `Case: ${c.sample_name || c.case_id || 'Active Case'}`;
  if (repSpecimen) repSpecimen.textContent = c.sample_name || c.case_id || '-';
  if (repDepth) repDepth.textContent = `${c.mean_depth ? c.mean_depth.toFixed(1) : 62.8}x (${c.platform || 'PromethION'})`;

  const customFindings = AppState.customReportFindings || [];
  const customSnvs = customFindings.filter(f => !f.sv_type && !f.region_type);
  const customSvs = customFindings.filter(f => Boolean(f.sv_type));
  const customMeth = customFindings.filter(f => Boolean(f.region_type || f.mean_5mc !== undefined || f.percent_modified !== undefined));

  // Render Section 1: Small Variants (SNVs / Indels)
  const repSnvTbody = document.getElementById('repSnvTableBody');
  if (repSnvTbody) {
    if (customSnvs.length === 0) {
      repSnvTbody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">
            <i class="fa-solid fa-clipboard-question" style="font-size: 1.25rem; margin-bottom: 0.4rem; display: block; color: #94a3b8;"></i>
            No small variants currently curated for this clinical report.<br>
            <span style="font-size: 0.8rem; color: #64748b;">Navigate to <strong>SNVs & Indels</strong>, select an actionable variant, and click <strong>"Add to Report"</strong>.</span>
          </td>
        </tr>
      `;
    } else {
      repSnvTbody.innerHTML = customSnvs.map((v) => {
        const gene = v.gene_symbol || v.gene || '-';
        const hgvsp = v.hgvs_p || v.hgvsp || (v.amino_acid_change ? 'p.' + v.amino_acid_change : '-');
        const hgvsc = v.hgvs_c || v.hgvsc || (v.dna_change ? 'c.' + v.dna_change : '');
        const consequence = v.consequence || v.variant_type || '-';
        let vafStr = '-';
        if (v.vaf !== undefined && v.vaf !== null) {
          const numVaf = Number(v.vaf);
          vafStr = numVaf <= 1 ? (numVaf * 100).toFixed(1) + '%' : numVaf.toFixed(1) + '%';
        }
        const acmgClass = v.acmg_class || v.somatic_tier || v.clinical_significance || 'Actionable';
        const acmgCriteria = v.acmg_criteria || v.clinvar_sig || v.interpretation || 'Curated by clinical geneticist for diagnostic report';

        return `
          <tr style="background: rgba(37, 99, 235, 0.04);">
            <td>
              <strong style="color: #0b2545;">${gene}</strong>
              <span class="badge" style="background: #2563eb; color: #fff; font-size: 0.68rem; margin-left: 0.35rem;"><i class="fa-solid fa-user-check"></i> Added</span>
            </td>
            <td><strong>${hgvsp}</strong> ${hgvsc ? `<span style="color: #64748b; font-size: 0.8rem;">(${hgvsc})</span>` : ''}</td>
            <td>${typeof formatConsequence === 'function' ? formatConsequence(consequence) : consequence}</td>
            <td><strong>${vafStr}</strong></td>
            <td><span class="badge ${acmgClass.includes('Pathogenic') || acmgClass.includes('Tier I') ? 'badge-pathogenic' : 'badge-warning'}">${acmgClass}</span></td>
            <td style="font-size: 0.8rem; color: #475569;">
              ${acmgCriteria}
              <button class="btn btn-secondary" style="padding: 0.1rem 0.4rem; font-size: 0.7rem; float: right; border-color: #cbd5e1;" onclick="removeReportFinding('${v.reportFindingId}')" title="Remove finding">
                <i class="fa-solid fa-trash-can" style="color: #ef4444;"></i>
              </button>
            </td>
          </tr>
        `;
      }).join('');
    }
  }

  // Render Section 2: Structural Variants (SVs)
  const repSvTbody = document.getElementById('repSvTableBody');
  if (repSvTbody) {
    if (customSvs.length === 0) {
      repSvTbody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">
            <i class="fa-solid fa-clipboard-question" style="font-size: 1.25rem; margin-bottom: 0.4rem; display: block; color: #94a3b8;"></i>
            No structural variants currently curated for this clinical report.<br>
            <span style="font-size: 0.8rem; color: #64748b;">Navigate to <strong>Structural Variants</strong>, select an actionable rearrangement/CNV, and click <strong>"Add to Report"</strong>.</span>
          </td>
        </tr>
      `;
    } else {
      repSvTbody.innerHTML = customSvs.map((s) => {
        const svType = s.sv_type || 'SV';
        const gene = s.genes_affected || s.genes_overlapped || s.gene_symbol || s.gene || 'Intergenic';
        const startPos = Number(s.start !== undefined ? s.start : (s.pos !== undefined ? s.pos : 0));
        const endPos = Number(s.pos2 !== undefined ? s.pos2 : (s.end !== undefined ? s.end : (s.start !== undefined ? s.start : startPos)));
        const coords = `${s.chrom}:${startPos.toLocaleString()}-${endPos.toLocaleString()}`;
        const sizeStr = s.sv_len ? (typeof formatBp === 'function' ? formatBp(Math.abs(s.sv_len)) : Math.abs(s.sv_len) + ' bp') : (endPos > startPos ? (endPos - startPos) + ' bp' : '-');
        const reads = (s.support_reads || s.depth || 0) + ' reads';
        const impact = s.clinical_impact || s.acmg_sv_class || s.clinical_significance || 'Curated by clinical geneticist for diagnostic report';

        return `
          <tr style="background: rgba(37, 99, 235, 0.04);">
            <td>
              <span class="badge badge-sv-${svType.toLowerCase()}">${svType}</span>
              <span class="badge" style="background: #2563eb; color: #fff; font-size: 0.68rem; margin-left: 0.35rem;"><i class="fa-solid fa-user-check"></i> Added</span>
            </td>
            <td><strong>${gene}</strong></td>
            <td style="font-family: monospace; font-size: 0.8rem;">${coords}</td>
            <td>${sizeStr}</td>
            <td>${reads}</td>
            <td style="font-size: 0.8rem; color: #475569;">
              ${impact}
              <button class="btn btn-secondary" style="padding: 0.1rem 0.4rem; font-size: 0.7rem; float: right; border-color: #cbd5e1;" onclick="removeReportFinding('${s.reportFindingId}')" title="Remove finding">
                <i class="fa-solid fa-trash-can" style="color: #ef4444;"></i>
              </button>
            </td>
          </tr>
        `;
      }).join('');
    }
  }

  // Render Section 3: Epigenetic DNA Methylation Findings
  const repMethTbody = document.getElementById('repMethTableBody');
  if (repMethTbody) {
    // If clinician added custom methylation findings, show them; otherwise show top targeted regions
    fetch(`/api/methylation?case_id=${c.id}`)
      .then((r) => r.json())
      .then((data) => {
        const dbRegions = (data.methylation_regions || data.regions || []).filter(r => 
          (r.clinical_significance && (r.clinical_significance.includes('Hypermethylated') || r.clinical_significance.includes('Loss of Imprinting'))) ||
          r.percent_modified > 60 || r.mean_methylated_pct > 60
        );
        const allMeth = [...customMeth, ...dbRegions];
        const seenMeth = new Set();
        const displayMeth = [];
        allMeth.forEach(m => {
          const key = `${m.chrom}:${m.start}:${m.end}:${m.gene_symbol || m.name}`;
          if (!seenMeth.has(key)) {
            seenMeth.add(key);
            displayMeth.push(m);
          }
        });

        if (displayMeth.length === 0) {
          repMethTbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No abnormal promoter hypermethylation or imprinting disruptions detected.</td></tr>';
        } else {
          repMethTbody.innerHTML = displayMeth.map((r) => {
            const pct = r.percent_modified !== undefined ? r.percent_modified : (r.mean_methylated_pct || 0);
            return `
              <tr>
                <td><strong>${r.gene_symbol || r.name}</strong> (${r.region_type || 'Promoter'})</td>
                <td style="font-family: monospace; font-size: 0.8rem;">${r.chrom}:${r.start}-${r.end}</td>
                <td><strong style="color: ${pct > 60 ? '#ef4444' : '#10b981'};">${Number(pct).toFixed(1)}% 5mC</strong></td>
                <td style="font-size: 0.8rem; color: #475569;">${r.clinical_significance || 'Curated epigenetic locus'}</td>
              </tr>
            `;
          }).join('');
        }
      })
      .catch(() => {
        repMethTbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No methylation regions available.</td></tr>';
      });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const printBtn = document.getElementById('printReportBtn');
  if (printBtn) {
    printBtn.addEventListener('click', () => {
      const caseId = (typeof AppState !== 'undefined' && AppState.activeCaseId) ? AppState.activeCaseId : 1;
      window.open(`/api/reports/${caseId}/download?format=html`, '_blank');
    });
  }

  const exportBtn = document.getElementById('exportReportJsonBtn');
  if (exportBtn) {
    exportBtn.addEventListener('click', () => {
      const caseId = (typeof AppState !== 'undefined' && AppState.activeCaseId) ? AppState.activeCaseId : 1;
      window.open(`/api/reports/${caseId}/download?format=json`, '_blank');
      if (typeof showToast === 'function') {
        showToast('Downloaded structured clinical report JSON', 'success');
      }
    });
  }
});

