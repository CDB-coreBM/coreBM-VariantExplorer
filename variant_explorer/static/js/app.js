// CoreBM Variant Explorer - Global App Controller
const AppState = {
  activeCaseId: null,
  activeCaseData: null,
  currentView: 'qc-view',
  snvPage: 1,
  snvPageSize: 50,
  svPage: 1,
  svPageSize: 50,
  selectedVariant: null,
};

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  let icon = 'fa-circle-info';
  if (type === 'success') icon = 'fa-circle-check';
  if (type === 'error') icon = 'fa-circle-xmark';
  if (type === 'warning') icon = 'fa-triangle-exclamation';

  toast.innerHTML = `
    <div style="display: flex; align-items: center; gap: 0.5rem;">
      <i class="fa-solid ${icon}"></i>
      <span>${message}</span>
    </div>
    <button style="background: transparent; border: none; cursor: pointer; color: #94a3b8; font-size: 1.1rem;" onclick="this.parentElement.remove()">&times;</button>
  `;
  container.appendChild(toast);
  setTimeout(() => { if (toast.parentElement) toast.remove(); }, 4000);
}

async function loadCases() {
  try {
    const res = await fetch('/api/cases');
    const data = await res.json();
    const select = document.getElementById('activeCaseSelect');
    select.innerHTML = '';
    
    const cases = data.cases || [];
    if (cases.length === 0) {
      select.innerHTML = '<option value="">No cases ingested</option>';
      return;
    }
    
    cases.forEach((c) => {
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = `${c.sample_name || c.case_id} (${c.platform || c.instrument || 'ONT'})`;
      select.appendChild(opt);
    });

    if (!AppState.activeCaseId && cases.length > 0) {
      AppState.activeCaseId = cases[0].id;
    }
    select.value = AppState.activeCaseId;
    await fetchActiveCaseDetails();
  } catch (err) {
    console.error('Failed to load cases:', err);
    showToast('Failed to load clinical cases', 'error');
  }
}

async function fetchActiveCaseDetails() {
  if (!AppState.activeCaseId) return;
  try {
    const res = await fetch(`/api/cases/${AppState.activeCaseId}`);
    const data = await res.json();
    const caseData = data.data || data;
    if (data.status === 'error') {
      showToast(data.message || 'Error fetching case', 'error');
      return;
    }
    AppState.activeCaseData = caseData;
    updateHeaderBadges(caseData);
    updateQcView(caseData);
    
    if (AppState.currentView === 'qc-view') loadCaseQcAndPhasing();
    else if (AppState.currentView === 'snv-view') loadSnvVariants(true);
    else if (AppState.currentView === 'sv-view') loadSvVariants(true);
    else if (AppState.currentView === 'methylation-view') loadMethylationRegions();
    else if (AppState.currentView === 'locus-view') { if (typeof initIgvBrowser === 'function') initIgvBrowser(); }
    else if (AppState.currentView === 'report-view') updateClinicalReport(caseData);
  } catch (err) {
    console.error('Error fetching case details:', err);
  }
}

function switchView(viewId) {
  document.querySelectorAll('.sidebar-item').forEach((i) => i.classList.remove('active'));
  document.querySelectorAll('.view-section').forEach((v) => v.classList.remove('active'));

  const navItem = document.querySelector(`.sidebar-item[data-view="${viewId}"]`);
  if (navItem) navItem.classList.add('active');

  const targetView = document.getElementById(viewId);
  if (targetView) targetView.classList.add('active');

  AppState.currentView = viewId;

  if (viewId === 'qc-view') loadCaseQcAndPhasing();
  else if (viewId === 'snv-view') loadSnvVariants(false);
  else if (viewId === 'sv-view') loadSvVariants(false);
  else if (viewId === 'methylation-view') loadMethylationRegions();
  else if (viewId === 'locus-view') { if (typeof initIgvBrowser === 'function') initIgvBrowser(); }
  else if (viewId === 'report-view') updateClinicalReport(AppState.activeCaseData);
}

function updateHeaderBadges(caseData) {
  const c = caseData.case || {};
  const snvM = caseData.snv_metrics || {};
  const svM = caseData.sv_metrics || {};
  const methM = caseData.methylation_metrics || {};
  
  const bSnv = document.getElementById('badgeSnvCount');
  const bSv = document.getElementById('badgeSvCount');
  const bMeth = document.getElementById('badgeMethCount');
  if (bSnv) {
    bSnv.textContent = (snvM.total_snv || 0).toLocaleString();
    if (c.case_id === 'HG002-GIAB-ONT-R10') {
      bSnv.title = '27,939 GIAB CMRG Medical Gene calls + 3,923,548 WGS Truth Set Small Variants';
    }
  }
  if (bSv) {
    bSv.textContent = (svM.total_sv || 0).toLocaleString();
    if (c.case_id === 'HG002-GIAB-ONT-R10') {
      bSv.title = '250 GIAB CMRG Medical Gene SVs + 74,012 WGS Tier 1 SVs';
    }
  }
  if (bMeth) bMeth.textContent = (methM.total_regions || 0).toLocaleString();

  const sSample = document.getElementById('snvSummarySample');
  const sDepth = document.getElementById('snvSummaryDepth');
  const sTitv = document.getElementById('snvSummaryTitv');
  if (sSample) sSample.textContent = c.sample_name || c.case_id || '-';
  if (sDepth) sDepth.textContent = `${c.mean_depth ? c.mean_depth.toFixed(1) : 0}x`;
  if (sTitv) sTitv.textContent = c.ti_tv_ratio ? c.ti_tv_ratio.toFixed(2) : '-';

  const svTotal = document.getElementById('svSummaryTotal');
  if (svTotal) svTotal.textContent = svM.total_sv || 0;

  const methTotal = document.getElementById('methSummaryTotal');
  if (methTotal) methTotal.textContent = methM.total_regions || 0;
}

function openDetailDrawer(title, subtitle, htmlContent, variantData = null) {
  const drawer = document.getElementById('detailDrawer');
  const dTitle = document.getElementById('drawerTitle');
  const dSubtitle = document.getElementById('drawerSubtitle');
  const dContent = document.getElementById('drawerContent');
  
  if (dTitle) dTitle.textContent = title;
  if (dSubtitle) dSubtitle.textContent = subtitle;
  if (dContent) dContent.innerHTML = htmlContent;
  
  AppState.selectedVariant = variantData;
  if (typeof updateDrawerReportButtonState === 'function') {
    updateDrawerReportButtonState();
  }
  if (drawer) drawer.classList.add('open');
}

function closeDetailDrawer() {
  const drawer = document.getElementById('detailDrawer');
  if (drawer) drawer.classList.remove('open');
  AppState.selectedVariant = null;
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.sidebar-item').forEach((item) => {
    item.addEventListener('click', () => {
      const viewId = item.getAttribute('data-view');
      switchView(viewId);
    });
  });

  const caseSelect = document.getElementById('activeCaseSelect');
  if (caseSelect) {
    caseSelect.addEventListener('change', (e) => {
      AppState.activeCaseId = e.target.value;
      // Per clinical workflow: Once a case is selected by default it goes to the Case QC & Phasing tab
      switchView('qc-view');
      fetchActiveCaseDetails();
    });
  }

  const refreshBtn = document.getElementById('refreshCaseBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      fetchActiveCaseDetails();
      showToast('Refreshed case data', 'success');
    });
  }

  const closeDrawerBtn = document.getElementById('closeDrawerBtn');
  if (closeDrawerBtn) closeDrawerBtn.addEventListener('click', closeDetailDrawer);

  const drawerInspectBtn = document.getElementById('drawerInspectLocusBtn');
  if (drawerInspectBtn) {
    drawerInspectBtn.addEventListener('click', () => {
      if (AppState.selectedVariant) {
        const v = AppState.selectedVariant;
        const chrom = v.chrom;
        const pos = Number(v.pos || v.start || 1);
        const gene = v.gene_symbol || v.genes_affected || v.gene || chrom;
        closeDetailDrawer();

        if (typeof window.jumpToLocus === 'function') {
          window.jumpToLocus(chrom, pos);
          showToast(`Navigated to ${gene}:${pos.toLocaleString()}`, 'info');
        } else {
          // Direct fallback: switch to locus tab and update coordinates
          document.querySelectorAll('.sidebar-item').forEach((i) => i.classList.remove('active'));
          document.querySelectorAll('.view-section').forEach((view) => view.classList.remove('active'));
          const locusNav = document.querySelector('.sidebar-item[data-view="locus-view"]');
          if (locusNav) locusNav.classList.add('active');
          const locusView = document.getElementById('locus-view');
          if (locusView) locusView.classList.add('active');
          AppState.currentView = 'locus-view';

          const cInput = document.getElementById('locusChromInput');
          const sInput = document.getElementById('locusStartInput');
          const eInput = document.getElementById('locusEndInput');
          if (cInput) cInput.value = chrom;
          if (sInput) sInput.value = Math.max(1, pos - 10000);
          if (eInput) eInput.value = pos + 10000;

          if (typeof initNativeIgv === 'function') {
            initNativeIgv();
          }
          showToast(`Navigated to ${gene}:${pos.toLocaleString()}`, 'info');
        }
      } else {
        showToast('No variant selected to inspect', 'warning');
      }
    });
  }

  const drawerAddToReportBtn = document.getElementById('drawerAddToReportBtn');
  if (drawerAddToReportBtn) {
    drawerAddToReportBtn.addEventListener('click', () => {
      if (AppState.selectedVariant) {
        if (typeof addVariantToClinicalReport === 'function') {
          addVariantToClinicalReport(AppState.selectedVariant);
        } else {
          showToast('Report builder module not ready', 'warning');
        }
      } else {
        showToast('No variant selected to add to report', 'warning');
      }
    });
  }

  loadCases();
});

async function loadCaseQcAndPhasing() {
  const caseId = AppState.activeCaseId || 1;
  const hetContainer = document.getElementById('compoundHetTableContainer');
  const repContainer = document.getElementById('repeatsTableContainer');

  // 1. Fetch Compound Heterozygosity
  if (hetContainer) {
    try {
      const res = await fetch(`/api/phasing/compound_het?case_id=${caseId}`);
      if (res.ok) {
        const data = await res.json();
        const pairs = data.compound_heterozygous_pairs || [];
        if (pairs.length === 0) {
          hetContainer.innerHTML = '<div style="color: #64748b; font-size: 0.85rem; padding: 0.5rem 0;">No multi-variant compound heterozygous pairs detected in evaluated recessive disease genes.</div>';
        } else {
          hetContainer.innerHTML = `
            <table class="clinic-table" style="font-size: 0.85rem;">
              <thead>
                <tr>
                  <th>Gene</th>
                  <th>Variant 1</th>
                  <th>Variant 2</th>
                  <th>Haplotype Phasing</th>
                  <th>Clinical Diagnostic Interpretation</th>
                </tr>
              </thead>
              <tbody>
                ${pairs.map(p => `
                  <tr>
                    <td><strong>${p.gene_symbol}</strong></td>
                    <td><code>${p.variant_1}</code></td>
                    <td><code>${p.variant_2}</code></td>
                    <td><span class="badge ${p.phase_configuration.includes('In-Trans') ? 'badge-pathogenic' : 'badge-warning'}">${p.phase_configuration}</span></td>
                    <td style="font-size: 0.8rem; line-height: 1.4;">${p.clinical_interpretation}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          `;
        }
      }
    } catch (e) {
      console.warn('Error loading compound het:', e);
    }
  }

  // 2. Fetch Tandem Repeat Expansions
  if (repContainer) {
    try {
      const res = await fetch(`/api/repeats?case_id=${caseId}`);
      if (res.ok) {
        const data = await res.json();
        const repeats = data.repeat_expansions || [];
        repContainer.innerHTML = `
          <table class="clinic-table" style="font-size: 0.85rem;">
            <thead>
              <tr>
                <th>Locus / Disease</th>
                <th>Repeat Motif</th>
                <th>Allele 1 Size</th>
                <th>Allele 2 Size</th>
                <th>Expansion Status</th>
                <th>Clinical Assessment</th>
              </tr>
            </thead>
            <tbody>
              ${repeats.map(r => `
                <tr>
                  <td><strong>${r.gene_symbol}</strong> <span style="font-size: 0.75rem; color: #64748b;">(${r.disease})</span></td>
                  <td><span class="badge badge-info" style="font-family: monospace;">${r.motif}</span></td>
                  <td><strong>${r.allele_1_count}</strong> repeats</td>
                  <td><strong>${r.allele_2_count}</strong> repeats</td>
                  <td><span class="badge ${r.status.includes('Pathogenic') ? 'badge-pathogenic' : 'badge-likely-benign'}">${r.status}</span></td>
                  <td style="font-size: 0.8rem;">${r.clinical_significance}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        `;
      }
    } catch (e) {
      console.warn('Error loading repeats:', e);
    }
  }
}

function openUploadModal() {
  const modal = document.getElementById('uploadModal');
  if (modal) modal.classList.add('open');
}

function closeUploadModal() {
  const modal = document.getElementById('uploadModal');
  if (modal) modal.classList.remove('open');
}

const uploadBtn = document.getElementById('openUploadModalBtn');
if (uploadBtn) uploadBtn.addEventListener('click', openUploadModal);
