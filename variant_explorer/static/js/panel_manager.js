// Clinical Gene Panel Manager & Versioning Module
// Hospital Clínic de Barcelona - CoreBM Variant Explorer

let allPanelsCache = [];
let activePanelData = null;
let currentWorkingGenes = [];
let isVersionHistoryVisible = false;

async function loadGenePanelsDropdown() {
  try {
    const res = await fetch('/api/panels');
    if (!res.ok) return;
    const data = await res.json();
    allPanelsCache = data.panels || [];

    const snvSelect = document.getElementById('snvPanelFilter');
    const svSelect = document.getElementById('svPanelFilter');

    const optionsHtml = ['<option value="">All Genes (Genome-wide)</option>'].concat(
      allPanelsCache.map((p) => {
        return `<option value="${p.id}">${p.name} (${p.version_str || 'v1.0'} - ${p.gene_count || 0} genes)</option>`;
      })
    ).join('');

    if (snvSelect) {
      const currentVal = snvSelect.value;
      snvSelect.innerHTML = optionsHtml;
      if (currentVal) snvSelect.value = currentVal;
    }
    if (svSelect) {
      const currentVal = svSelect.value;
      svSelect.innerHTML = optionsHtml;
      if (currentVal) svSelect.value = currentVal;
    }
  } catch (err) {
    console.error('Error loading gene panels dropdown:', err);
  }
}

function openGenePanelModal() {
  const modal = document.getElementById('genePanelModal');
  if (modal) modal.style.display = 'flex';
  renderPanelList();
  if (allPanelsCache.length > 0) {
    selectPanelInModal(allPanelsCache[0].id);
  } else {
    loadGenePanelsDropdown().then(() => {
      renderPanelList();
      if (allPanelsCache.length > 0) selectPanelInModal(allPanelsCache[0].id);
    });
  }
}

function closeGenePanelModal() {
  const modal = document.getElementById('genePanelModal');
  if (modal) modal.style.display = 'none';
  hideNewPanelForm();
}

function renderPanelList() {
  const container = document.getElementById('panelListContainer');
  if (!container) return;

  if (allPanelsCache.length === 0) {
    container.innerHTML = '<div style="color: #64748b; font-size: 0.8rem; text-align: center; padding: 1.5rem 0;">No panels defined.</div>';
    return;
  }

  container.innerHTML = allPanelsCache.map((p) => {
    const isSelected = activePanelData && activePanelData.id === p.id;
    return `
      <div onclick="selectPanelInModal(${p.id})" 
           style="background: ${isSelected ? '#1e293b' : '#0b1329'}; border: 1px solid ${isSelected ? '#38bdf8' : '#334155'}; border-radius: 6px; padding: 0.6rem 0.75rem; cursor: pointer; transition: all 0.15s ease;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
          <strong style="font-size: 0.82rem; color: ${isSelected ? '#38bdf8' : '#f8fafc'};">${p.name}</strong>
        </div>
        <div style="display: flex; gap: 0.4rem; align-items: center; flex-wrap: wrap;">
          <span class="badge" style="background: #334155; font-size: 0.7rem; color: #94a3b8;">${p.code}</span>
          <span class="badge" style="background: #0284c7; font-size: 0.7rem; color: white;">${p.version_str || 'v1.0'}</span>
          <span style="font-size: 0.72rem; color: #94a3b8; margin-left: auto;">${p.gene_count || 0} genes</span>
        </div>
      </div>
    `;
  }).join('');
}

async function selectPanelInModal(panelId) {
  hideNewPanelForm();
  try {
    const res = await fetch(`/api/panels/${panelId}`);
    if (!res.ok) throw new Error('Failed to fetch panel details');
    const data = await res.json();
    activePanelData = data.panel || {};
    currentWorkingGenes = [...(activePanelData.active_genes || [])];

    // Update panel header
    document.getElementById('panelDetailName').textContent = activePanelData.name || 'Gene Panel';
    document.getElementById('panelDetailCode').textContent = activePanelData.code || '-';
    document.getElementById('panelDetailCategory').textContent = activePanelData.category || 'Clinical';
    document.getElementById('panelDetailDesc').textContent = activePanelData.description || 'No description provided.';
    
    const vers = activePanelData.versions || [];
    const activeVer = vers.find((v) => v.is_active) || (vers.length > 0 ? vers[0] : {});
    document.getElementById('panelActiveVersionBadge').textContent = `${activeVer.version_str || 'v1.0'} Active`;
    document.getElementById('panelActiveGeneCount').textContent = `${currentWorkingGenes.length} Curated Genes`;

    // Next version suggestion
    suggestNextVersion(activeVer.version_str || 'v1.0');

    // Render Working Chips
    renderWorkingGeneChips();

    // Populate Version History
    renderVersionHistory(activePanelData.versions || []);

    // Re-render panel list to update active highlight
    renderPanelList();
  } catch (err) {
    console.error('Error selecting panel:', err);
    showToast('Failed to load panel details', 'error');
  }
}

function suggestNextVersion(currentVer) {
  let nextVer = 'v1.1';
  const match = currentVer.match(/v?(\d+)\.(\d+)/);
  if (match) {
    const major = parseInt(match[1]);
    const minor = parseInt(match[2]) + 1;
    nextVer = `v${major}.${minor}`;
  }
  const verInput = document.getElementById('bumpVersionStr');
  if (verInput) verInput.value = nextVer;
  const changelogInput = document.getElementById('bumpChangelog');
  if (changelogInput) changelogInput.value = '';
}

function renderWorkingGeneChips(filterText = '') {
  const container = document.getElementById('geneChipsContainer');
  const countBadge = document.getElementById('workingGeneCountBadge');
  if (!container) return;

  const f = filterText.trim().toUpperCase();
  const filtered = f ? currentWorkingGenes.filter((g) => g.includes(f)) : currentWorkingGenes;

  if (countBadge) countBadge.textContent = currentWorkingGenes.length;

  if (filtered.length === 0) {
    container.innerHTML = `<div style="color: #64748b; font-size: 0.78rem; padding: 0.5rem;">${f ? 'No genes matched search filter.' : 'No genes in panel.'}</div>`;
    return;
  }

  container.innerHTML = filtered.map((gene) => {
    return `
      <span style="display: inline-flex; align-items: center; gap: 0.35rem; background: #1e293b; border: 1px solid #475569; color: #f8fafc; font-size: 0.78rem; font-weight: 600; padding: 0.2rem 0.5rem; border-radius: 4px;">
        ${gene}
        <i class="fa-solid fa-xmark" style="cursor: pointer; color: #94a3b8; font-size: 0.75rem; transition: color 0.15s;" 
           onmouseover="this.style.color='#ef4444'" onmouseout="this.style.color='#94a3b8'"
           onclick="removeGeneFromWorkingSet('${gene}')" title="Remove ${gene}"></i>
      </span>
    `;
  }).join('');
}

async function validateGenesApi(genes) {
  try {
    const res = await fetch('/api/genes/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ genes })
    });
    if (!res.ok) return null;
    const json = await res.json();
    return json.data || null;
  } catch (e) {
    console.error('Validation request failed:', e);
    return null;
  }
}

async function addGenesToCurrentPanel() {
  const input = document.getElementById('addGeneInput');
  const feedbackEl = document.getElementById('addGeneValidationFeedback');
  if (!input) return;
  const raw = input.value.trim().toUpperCase();
  if (!raw) return;

  const toAdd = raw.replace(/,/g, ' ').replace(/;/g, ' ').split(/\s+/).filter((g) => g.length > 0);
  
  // Validate symbols against catalog
  const valResult = await validateGenesApi(toAdd);
  if (valResult && valResult.invalid_count > 0 && feedbackEl) {
    const invNames = valResult.invalid_genes.map((ig) => ig.symbol).join(', ');
    feedbackEl.style.display = 'block';
    feedbackEl.style.background = 'rgba(239, 68, 68, 0.15)';
    feedbackEl.style.border = '1px solid #ef4444';
    feedbackEl.style.color = '#fca5a5';
    feedbackEl.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> Warning: Unrecognized gene symbol(s): <strong>${invNames}</strong>.`;
  } else if (feedbackEl) {
    feedbackEl.style.display = 'none';
  }

  let addedCount = 0;
  toAdd.forEach((g) => {
    if (!currentWorkingGenes.includes(g)) {
      currentWorkingGenes.push(g);
      addedCount++;
    }
  });

  currentWorkingGenes.sort();
  input.value = '';
  const searchEl = document.getElementById('geneChipSearchInput');
  renderWorkingGeneChips((searchEl && searchEl.value) || '');

  if (addedCount > 0) {
    showToast(`Added ${addedCount} gene(s) to working panel. Publish version bump to save changes.`, 'info');
    const changelogInput = document.getElementById('bumpChangelog');
    if (changelogInput && !changelogInput.value) {
      changelogInput.value = `Added ${toAdd.slice(0, 3).join(', ')}${toAdd.length > 3 ? ` and ${toAdd.length - 3} more` : ''}`;
    }
  } else {
    showToast('Entered genes are already present in this panel', 'warning');
  }
}

function removeGeneFromWorkingSet(gene) {
  currentWorkingGenes = currentWorkingGenes.filter((g) => g !== gene);
  const searchEl = document.getElementById('geneChipSearchInput');
  renderWorkingGeneChips((searchEl && searchEl.value) || '');
  const changelogInput = document.getElementById('bumpChangelog');
  if (changelogInput && !changelogInput.value) {
    changelogInput.value = `Removed ${gene}`;
  }
}

async function publishPanelVersionBump() {
  if (!activePanelData || !activePanelData.id) return;
  const verInput = document.getElementById('bumpVersionStr');
  const changelogInput = document.getElementById('bumpChangelog');
  const authorInput = document.getElementById('bumpAuthor');

  const version = (verInput && verInput.value.trim()) || 'v1.1';
  const changelog = (changelogInput && changelogInput.value.trim()) || `Updated gene set (${currentWorkingGenes.length} genes)`;
  const author = (authorInput && authorInput.value.trim()) || 'Clinical Geneticist';

  if (!version) {
    showToast('Version number is required (e.g. v1.1)', 'warning');
    return;
  }

  try {
    const res = await fetch(`/api/panels/${activePanelData.id}/versions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        version,
        changelog,
        author,
        genes: currentWorkingGenes
      })
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.message || 'Failed to publish new version');
    }

    const data = await res.json();
    showToast(data.message || `Version ${version} published successfully!`, 'success');

    // Reload panels cache & reselect current panel
    await loadGenePanelsDropdown();
    await selectPanelInModal(activePanelData.id);

    // If active view is snv-view or sv-view, and current filter matches this panel, reload
    const snvPanelEl = document.getElementById('snvPanelFilter');
    const snvPanelVal = snvPanelEl ? snvPanelEl.value : null;
    if (snvPanelVal == activePanelData.id && typeof loadSnvVariants === 'function') {
      loadSnvVariants(false);
    }
    const svPanelEl = document.getElementById('svPanelFilter');
    const svPanelVal = svPanelEl ? svPanelEl.value : null;
    if (svPanelVal == activePanelData.id && typeof loadSvVariants === 'function') {
      loadSvVariants(false);
    }
  } catch (err) {
    console.error('Error publishing version bump:', err);
    showToast(`Error publishing version: ${err.message}`, 'error');
  }
}

function renderVersionHistory(versions) {
  const tbody = document.getElementById('versionHistoryTbody');
  if (!tbody) return;

  if (!versions || versions.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #64748b; padding: 1rem;">No prior versions recorded.</td></tr>';
    return;
  }

  tbody.innerHTML = versions.map((v) => {
    const dateStr = v.created_at ? v.created_at.split(' ')[0] : '-';
    const statusTag = v.is_active 
      ? '<span class="badge" style="background:#0284c7; color:white; font-size:0.68rem;">Active</span>' 
      : '<span class="badge" style="background:#334155; color:#94a3b8; font-size:0.68rem;">Archived</span>';
    return `
      <tr style="border-bottom: 1px solid #1e293b;">
        <td style="padding: 0.35rem; font-weight: 700; color: #38bdf8;">${v.version_str}</td>
        <td style="padding: 0.35rem;">${v.gene_count} genes</td>
        <td style="padding: 0.35rem; color: #cbd5e1;">${v.changelog || '-'}</td>
        <td style="padding: 0.35rem; color: #94a3b8;">${v.author || '-'} (${dateStr})</td>
        <td style="padding: 0.35rem;">${statusTag}</td>
      </tr>
    `;
  }).join('');
}

function toggleVersionHistory() {
  const container = document.getElementById('versionHistoryContainer');
  const text = document.getElementById('historyToggleText');
  if (!container) return;

  isVersionHistoryVisible = !isVersionHistoryVisible;
  container.style.display = isVersionHistoryVisible ? 'block' : 'none';
  if (text) text.textContent = isVersionHistoryVisible ? 'Hide Version History' : 'View Version History';
}

function showNewPanelForm() {
  const detail = document.getElementById('panelDetailContainer');
  const form = document.getElementById('newPanelFormContainer');
  if (detail) detail.style.display = 'none';
  if (form) form.style.display = 'flex';
}

function hideNewPanelForm() {
  const detail = document.getElementById('panelDetailContainer');
  const form = document.getElementById('newPanelFormContainer');
  if (detail) detail.style.display = 'flex';
  if (form) form.style.display = 'none';
}

let newPanelValidationTimeout = null;

function debounceValidateNewPanelGenes() {
  clearTimeout(newPanelValidationTimeout);
  newPanelValidationTimeout = setTimeout(() => {
    validateNewPanelGenes();
  }, 450);
}

function replacePanelGeneSymbol(oldSymbol, newSymbol) {
  const genesEl = document.getElementById('newPanelGenes');
  if (!genesEl) return;
  const regex = new RegExp(`\\b${oldSymbol}\\b`, 'gi');
  genesEl.value = genesEl.value.replace(regex, newSymbol);
  validateNewPanelGenes();
}

async function validateNewPanelGenes() {
  const genesEl = document.getElementById('newPanelGenes');
  const statusEl = document.getElementById('newPanelGeneValidationStatus');
  if (!genesEl || !statusEl) return null;

  const raw = genesEl.value.trim().toUpperCase();
  if (!raw) {
    statusEl.style.display = 'none';
    statusEl.innerHTML = '';
    return null;
  }

  const symbols = raw.replace(/,/g, ' ').replace(/;/g, ' ').split(/\s+/).filter((s) => s.length > 0);
  if (symbols.length === 0) {
    statusEl.style.display = 'none';
    return null;
  }

  statusEl.style.display = 'block';
  statusEl.style.background = '#0f172a';
  statusEl.style.border = '1px solid #334155';
  statusEl.style.color = '#94a3b8';
  statusEl.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Validating gene symbols against HGNC catalog...';

  const valData = await validateGenesApi(symbols);
  if (!valData) {
    statusEl.style.display = 'none';
    return null;
  }

  if (valData.invalid_count === 0) {
    statusEl.style.background = 'rgba(34, 197, 94, 0.12)';
    statusEl.style.border = '1px solid #16a34a';
    statusEl.style.color = '#86efac';
    statusEl.innerHTML = `
      <div style="display: flex; align-items: center; gap: 0.5rem;">
        <i class="fa-solid fa-circle-check" style="color: #22c55e; font-size: 1rem;"></i>
        <div>
          <strong>Validation Passed:</strong> All ${valData.valid_count} gene symbol(s) are approved in the clinical catalog.
        </div>
      </div>
    `;
  } else {
    statusEl.style.background = 'rgba(239, 68, 68, 0.12)';
    statusEl.style.border = '1px solid #dc2626';
    statusEl.style.color = '#fca5a5';

    const invalidItemsHtml = valData.invalid_genes.map((inv) => {
      let suggHtml = '';
      if (inv.suggestions && inv.suggestions.length > 0) {
        suggHtml = inv.suggestions.map((s) => 
          `<button type="button" class="btn btn-secondary" style="padding: 0.1rem 0.4rem; font-size: 0.72rem; color: #38bdf8; margin-left: 0.25rem;" onclick="replacePanelGeneSymbol('${inv.symbol}', '${s}')">Use ${s}</button>`
        ).join('');
      }
      return `<li style="margin-top: 0.25rem;"><span class="badge" style="background: #ef4444; color: white;">${inv.symbol}</span> ${suggHtml ? `&rarr; Suggested: ${suggHtml}` : '<span style="color: #94a3b8; font-size: 0.72rem;">(No close match found)</span>'}</li>`;
    }).join('');

    statusEl.innerHTML = `
      <div>
        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem;">
          <i class="fa-solid fa-triangle-exclamation" style="color: #ef4444; font-size: 1rem;"></i>
          <strong>Unrecognized Gene Symbols Detected (${valData.invalid_count}):</strong>
        </div>
        <ul style="margin: 0 0 0.5rem 1rem; padding: 0;">
          ${invalidItemsHtml}
        </ul>
        <div style="font-size: 0.73rem; color: #cbd5e1;">
          ${valData.valid_count} valid symbol(s) confirmed. Please correct or verify the flagged symbols.
        </div>
      </div>
    `;
  }

  return valData;
}

async function submitCreateNewPanel() {
  const nameEl = document.getElementById('newPanelName');
  const codeEl = document.getElementById('newPanelCode');
  const catEl = document.getElementById('newPanelCategory');
  const verEl = document.getElementById('newPanelVersion');
  const descEl = document.getElementById('newPanelDesc');
  const genesEl = document.getElementById('newPanelGenes');

  const name = nameEl ? nameEl.value.trim() : '';
  const code = codeEl ? codeEl.value.trim() : '';
  const category = catEl ? catEl.value : 'Clinical';
  const version = (verEl && verEl.value.trim()) || 'v1.0';
  const description = descEl ? descEl.value.trim() : '';
  const rawGenes = genesEl ? genesEl.value.trim() : '';

  if (!name || !code) {
    showToast('Panel Name and Unique Code are required', 'warning');
    return;
  }
  if (!rawGenes) {
    showToast('Please provide at least one gene for the initial panel', 'warning');
    return;
  }

  // Validate gene symbols before submission
  const valResult = await validateNewPanelGenes();
  if (valResult && valResult.invalid_count > 0) {
    const invNames = valResult.invalid_genes.map((g) => g.symbol).join(', ');
    const proceed = confirm(`Warning: ${valResult.invalid_count} unrecognized gene symbol(s) detected: ${invNames}.\n\nDo you want to proceed anyway?`);
    if (!proceed) return;
  }

  try {
    const res = await fetch('/api/panels', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        code,
        category,
        version,
        description,
        genes: rawGenes,
        changelog: 'Initial clinical panel creation.',
        author: 'Clinical Molecular Geneticist'
      })
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.message || 'Failed to create panel');
    }

    const data = await res.json();
    showToast(data.message || 'Panel created successfully', 'success');

    // Reset form inputs
    document.getElementById('newPanelName').value = '';
    document.getElementById('newPanelCode').value = '';
    document.getElementById('newPanelDesc').value = '';
    document.getElementById('newPanelGenes').value = '';
    const statusEl = document.getElementById('newPanelGeneValidationStatus');
    if (statusEl) {
      statusEl.style.display = 'none';
      statusEl.innerHTML = '';
    }

    await loadGenePanelsDropdown();
    if (data.panel_id) {
      await selectPanelInModal(data.panel_id);
    }
  } catch (err) {
    console.error('Error creating panel:', err);
    showToast(`Error: ${err.message}`, 'error');
  }
}

// Global Initialization
document.addEventListener('DOMContentLoaded', () => {
  loadGenePanelsDropdown();

  // Bind Open Panel Modal buttons across views
  document.querySelectorAll('.openGenePanelModalBtn').forEach((btn) => {
    btn.addEventListener('click', openGenePanelModal);
  });

  // Filter chips live search
  const chipSearch = document.getElementById('geneChipSearchInput');
  if (chipSearch) {
    chipSearch.addEventListener('input', (e) => {
      renderWorkingGeneChips(e.target.value);
    });
  }

  // Enter key in add gene input
  const addInput = document.getElementById('addGeneInput');
  if (addInput) {
    addInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        addGenesToCurrentPanel();
      }
    });
  }
});
