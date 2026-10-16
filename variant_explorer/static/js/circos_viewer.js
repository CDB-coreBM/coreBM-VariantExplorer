// Interactive Circos Plot for Complex Structural Variants & Fusions
// Hospital Clínic de Barcelona - CoreBM Oxford Nanopore Variant Explorer

const CIRCOS_CONFIG = {
  chromosomes: [
    { name: 'chr1', length: 248956422, color: '#3b82f6' },
    { name: 'chr2', length: 242193529, color: '#06b6d4' },
    { name: 'chr3', length: 198295559, color: '#10b981' },
    { name: 'chr4', length: 190214555, color: '#84cc16' },
    { name: 'chr5', length: 181538259, color: '#eab308' },
    { name: 'chr6', length: 170805979, color: '#f97316' },
    { name: 'chr7', length: 159345973, color: '#ef4444' },
    { name: 'chr8', length: 145138636, color: '#ec4899' },
    { name: 'chr9', length: 138394717, color: '#d946ef' },
    { name: 'chr10', length: 133797422, color: '#a855f7' },
    { name: 'chr11', length: 135086622, color: '#8b5cf6' },
    { name: 'chr12', length: 133275309, color: '#6366f1' },
    { name: 'chr13', length: 114364328, color: '#3b82f6' },
    { name: 'chr14', length: 107043718, color: '#0ea5e9' },
    { name: 'chr15', length: 101991189, color: '#14b8a6' },
    { name: 'chr16', length: 90338345, color: '#22c55e' },
    { name: 'chr17', length: 83257441, color: '#eab308' },
    { name: 'chr18', length: 80373285, color: '#f97316' },
    { name: 'chr19', length: 58617616, color: '#f43f5e' },
    { name: 'chr20', length: 64444167, color: '#ec4899' },
    { name: 'chr21', length: 46709983, color: '#a855f7' },
    { name: 'chr22', length: 50818468, color: '#8b5cf6' },
    { name: 'chrX', length: 156040895, color: '#0284c7' },
    { name: 'chrY', length: 57227415, color: '#64748b' },
  ],
  gapAngleDeg: 1.5,
  innerRadius: 210,
  outerRadius: 232,
  labelRadius: 248,
  center: 280,
  size: 560
};

let currentCircosSVs = [];
let selectedCircosSV = null;

function initCircosLayout() {
  const totalLength = CIRCOS_CONFIG.chromosomes.reduce((acc, c) => acc + c.length, 0);
  const totalGapDeg = CIRCOS_CONFIG.chromosomes.length * CIRCOS_CONFIG.gapAngleDeg;
  const availableDeg = 360 - totalGapDeg;

  let currentAngle = 0;
  CIRCOS_CONFIG.chromosomes.forEach((chrom) => {
    chrom.fraction = chrom.length / totalLength;
    chrom.spanDeg = chrom.fraction * availableDeg;
    chrom.startDeg = currentAngle;
    chrom.endDeg = currentAngle + chrom.spanDeg;
    currentAngle += chrom.spanDeg + CIRCOS_CONFIG.gapAngleDeg;
  });
}

function getCircosCoords(chromName, pos, radius) {
  if (!chromName) return { x: CIRCOS_CONFIG.center, y: CIRCOS_CONFIG.center, angleRad: 0 };
  const normName = chromName.toLowerCase().startsWith('chr') ? chromName.toLowerCase() : 'chr' + chromName.toLowerCase();
  const chrom = CIRCOS_CONFIG.chromosomes.find((c) => c.name.toLowerCase() === normName);
  if (!chrom) return { x: CIRCOS_CONFIG.center, y: CIRCOS_CONFIG.center, angleRad: 0 };

  const numPos = typeof pos === 'number' && !isNaN(pos) ? pos : Number(pos || 0);
  const frac = Math.max(0, Math.min(1, numPos / chrom.length));
  const angleDeg = chrom.startDeg + (frac * chrom.spanDeg) - 90; // 0 deg at top
  const angleRad = (angleDeg * Math.PI) / 180;

  return {
    x: CIRCOS_CONFIG.center + radius * Math.cos(angleRad),
    y: CIRCOS_CONFIG.center + radius * Math.sin(angleRad),
    angleDeg,
    angleRad
  };
}

function renderCircosPlot(svList) {
  currentCircosSVs = svList || [];
  const svgContainer = document.getElementById('circosSvgContainer');
  if (!svgContainer) return;

  initCircosLayout();

  const cx = CIRCOS_CONFIG.center;
  const cy = CIRCOS_CONFIG.center;
  const rIn = CIRCOS_CONFIG.innerRadius;
  const rOut = CIRCOS_CONFIG.outerRadius;
  const rLabel = CIRCOS_CONFIG.labelRadius;

  let svg = `
    <svg id="circosSvg" viewBox="0 0 ${CIRCOS_CONFIG.size} ${CIRCOS_CONFIG.size}" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" style="font-family:Inter, system-ui, sans-serif; background:#0b1329; border-radius:12px; user-select:none;">
      <defs>
        <filter id="circosGlow">
          <feGaussianBlur stdDeviation="3" result="blur"/>
          <feMerge>
            <feMergeNode in="blur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
        <radialGradient id="circosCenterGrad" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#0f172a" stop-opacity="0.9"/>
          <stop offset="85%" stop-color="#0b1329" stop-opacity="1"/>
        </radialGradient>
      </defs>

      <!-- Center background -->
      <circle cx="${cx}" cy="${cy}" r="${rIn - 2}" fill="url(#circosCenterGrad)"/>
      <circle cx="${cx}" cy="${cy}" r="${rIn - 2}" fill="none" stroke="#1e293b" stroke-width="1"/>
  `;

  // Draw Chromosome Ideogram Bands
  CIRCOS_CONFIG.chromosomes.forEach((chrom) => {
    const startRad = ((chrom.startDeg - 90) * Math.PI) / 180;
    const endRad = ((chrom.endDeg - 90) * Math.PI) / 180;
    const largeArc = chrom.spanDeg > 180 ? 1 : 0;

    const x1Out = cx + rOut * Math.cos(startRad);
    const y1Out = cy + rOut * Math.sin(startRad);
    const x2Out = cx + rOut * Math.cos(endRad);
    const y2Out = cy + rOut * Math.sin(endRad);

    const x1In = cx + rIn * Math.cos(endRad);
    const y1In = cy + rIn * Math.sin(endRad);
    const x2In = cx + rIn * Math.cos(startRad);
    const y2In = cy + rIn * Math.sin(startRad);

    const pathData = `
      M ${x1Out} ${y1Out}
      A ${rOut} ${rOut} 0 ${largeArc} 1 ${x2Out} ${y2Out}
      L ${x1In} ${y1In}
      A ${rIn} ${rIn} 0 ${largeArc} 0 ${x2In} ${y2In}
      Z
    `;

    // Chromosome band
    svg += `
      <path d="${pathData}" fill="${chrom.color}" opacity="0.85" stroke="#0f172a" stroke-width="1.5" class="circos-chrom-band" data-chrom="${chrom.name}">
        <title>${chrom.name} (${(chrom.length / 1000000).toFixed(1)} Mb)</title>
      </path>
    `;

    // Chromosome Label
    const midAngleRad = ((chrom.startDeg + chrom.spanDeg / 2 - 90) * Math.PI) / 180;
    const lx = cx + rLabel * Math.cos(midAngleRad);
    const ly = cy + rLabel * Math.sin(midAngleRad);
    const shortLabel = chrom.name.replace('chr', '');

    svg += `
      <text x="${lx}" y="${ly}" fill="#cbd5e1" font-size="9" font-weight="700" text-anchor="middle" dominant-baseline="central">
        ${shortLabel}
      </text>
    `;
  });

  // Draw SV Connections & Translocation Chords
  const typeFilterEl = document.getElementById('circosTypeFilter');
  const filterType = (typeFilterEl && typeFilterEl.value) || '';

  currentCircosSVs.forEach((sv, idx) => {
    const t = (sv.sv_type || '').toUpperCase();
    if (filterType && t !== filterType) {
      if (filterType === 'FUSION' && t !== 'BND' && !isGeneFusion(sv)) return;
      if (filterType !== 'FUSION') return;
    }

    const chr1 = sv.chrom || 'chr1';
    const pos1 = sv.start !== undefined && sv.start !== null ? Number(sv.start) : 0;
    const chr2 = sv.chr2 || sv.end_chrom || sv.chrom || 'chr1';
    const pos2 = sv.pos2 !== undefined && sv.pos2 !== null ? Number(sv.pos2) : (sv.end !== undefined && sv.end !== null ? Number(sv.end) : pos1);

    const p1 = getCircosCoords(chr1, pos1, rIn - 4);
    const p2 = getCircosCoords(chr2, pos2, rIn - 4);

    const isSelected = selectedCircosSV && selectedCircosSV.id === sv.id;
    const isTransloc = t === 'BND' || chr1.toLowerCase() !== chr2.toLowerCase();
    const isInv = t === 'INV';
    const isDup = t === 'DUP';

    // Chord color scheme
    let strokeColor = '#f43f5e'; // DEL default
    if (isTransloc) strokeColor = '#ef4444'; // Translocation / Fusion
    else if (isInv) strokeColor = '#a855f7'; // Inversion
    else if (isDup) strokeColor = '#0284c7'; // Duplication
    else if (t === 'INS') strokeColor = '#10b981'; // Insertion

    const strokeWidth = isSelected ? 4.5 : isTransloc ? 3.0 : 2.0;
    const strokeOpacity = isSelected ? 1.0 : isTransloc ? 0.85 : 0.65;
    const chordGlow = isSelected ? 'filter="url(#circosGlow)"' : '';

    // Quadratic / Cubic curve bending towards center
    const controlX = cx;
    const controlY = cy;

    const pathData = `M ${p1.x} ${p1.y} Q ${controlX} ${controlY} ${p2.x} ${p2.y}`;

    svg += `
      <path d="${pathData}" fill="none" stroke="${strokeColor}" stroke-width="${strokeWidth}" 
            stroke-linecap="round" opacity="${strokeOpacity}" class="circos-sv-chord ${isSelected ? 'active' : ''}" 
            id="chord-sv-${sv.id}" data-id="${sv.id}" ${chordGlow}
            onclick="handleCircosChordClick(${sv.id})"
            onmouseenter="handleCircosChordHover(${sv.id}, true)"
            onmouseleave="handleCircosChordHover(${sv.id}, false)">
        <title>${sv.sv_type}: ${sv.genes_affected || 'Intergenic'} (${chr1}:${pos1} <-> ${chr2}:${pos2})</title>
      </path>
    `;

    // Breakpoint anchor circles
    svg += `
      <circle cx="${p1.x}" cy="${p1.y}" r="${isSelected ? 5 : 3.5}" fill="${strokeColor}" stroke="#ffffff" stroke-width="1" class="circos-bp-dot"/>
      <circle cx="${p2.x}" cy="${p2.y}" r="${isSelected ? 5 : 3.5}" fill="${strokeColor}" stroke="#ffffff" stroke-width="1" class="circos-bp-dot"/>
    `;
  });

  // Center legend / instructions if no variant selected
  if (!selectedCircosSV) {
    svg += `
      <g transform="translate(${cx}, ${cy})">
        <text y="-10" fill="#00a896" font-size="12" font-weight="800" text-anchor="middle" letter-spacing="0.5">COMPLEX SV & FUSIONS</text>
        <text y="8" fill="#94a3b8" font-size="9" text-anchor="middle">Click any chord to explore</text>
        <text y="24" fill="#64748b" font-size="8" text-anchor="middle">${currentCircosSVs.length} structural variants loaded</text>
      </g>
    `;
  }

  svg += '</svg>';
  svgContainer.innerHTML = svg;

  // Auto-select first fusion or complex SV if none selected
  if (!selectedCircosSV && currentCircosSVs.length > 0) {
    const firstFusion = currentCircosSVs.find((s) => s.sv_type === 'BND' || (s.genes_affected && s.genes_affected.includes(','))) || currentCircosSVs[0];
    if (firstFusion) {
      handleCircosChordClick(firstFusion.id, false);
    }
  }
}

function isGeneFusion(sv) {
  if (sv.sv_type === 'BND') return true;
  if (sv.genes_affected && sv.genes_affected.includes(',')) return true;
  return false;
}

function handleCircosChordClick(svId, reRender = true) {
  const sv = currentCircosSVs.find((s) => s.id == svId);
  if (!sv) return;

  selectedCircosSV = sv;
  renderComplexVariantInspector(sv);

  // Update styles of chords
  document.querySelectorAll('.circos-sv-chord').forEach((el) => {
    el.classList.remove('active');
    el.setAttribute('opacity', '0.3');
  });

  const activeChord = document.getElementById(`chord-sv-${sv.id}`);
  if (activeChord) {
    activeChord.classList.add('active');
    activeChord.setAttribute('opacity', '1.0');
    activeChord.setAttribute('stroke-width', '4.5');
  }
}

function handleCircosChordHover(svId, isHover) {
  if (selectedCircosSV && selectedCircosSV.id == svId) return;
  const chord = document.getElementById(`chord-sv-${svId}`);
  if (chord) {
    chord.setAttribute('opacity', isHover ? '1.0' : '0.65');
    chord.setAttribute('stroke-width', isHover ? '4' : '2.5');
  }
}

function renderComplexVariantInspector(sv) {
  const panel = document.getElementById('complexSvInspectorPanel');
  if (!panel) return;

  const t = (sv.sv_type || '').toUpperCase();
  const chr1 = sv.chrom || 'chr1';
  const pos1 = sv.start !== undefined && sv.start !== null ? Number(sv.start) : 0;
  const chr2 = sv.chr2 || sv.end_chrom || sv.chrom || 'chr1';
  const pos2 = sv.pos2 !== undefined && sv.pos2 !== null ? Number(sv.pos2) : (sv.end !== undefined && sv.end !== null ? Number(sv.end) : pos1);
  const isTransloc = t === 'BND' || chr1.toLowerCase() !== chr2.toLowerCase();

  const genes = (sv.genes_affected || 'Intergenic').split(',').map((g) => g.trim());
  const geneTitle = genes.length > 1 ? `${genes[0]} :: ${genes[1]} Gene Fusion` : genes[0];

  let actionabilityHtml = '';
  let therapyBadge = '';

  if (genes.includes('BCR') && genes.includes('ABL1')) {
    actionabilityHtml = `
      <div class="clinical-callout success">
        <div style="font-weight: 700; color: #10b981; margin-bottom: 0.25rem;">
          <i class="fa-solid fa-capsules"></i> Targeted Therapy Indicated (Tier I Actionable)
        </div>
        <p style="font-size: 0.8rem; margin: 0; color: #cbd5e1;">
          Constitutive BCR-ABL1 kinase activation (Philadelphia chromosome). Sensitive to Tyrosine Kinase Inhibitors (TKIs): <strong>Imatinib</strong>, <strong>Dasatinib</strong>, <strong>Nilotinib</strong>, <strong>Bosutinib</strong>, <strong>Ponatinib</strong>.
        </p>
      </div>
    `;
    therapyBadge = '<span class="badge badge-pathogenic" style="font-size: 0.75rem;"><i class="fa-solid fa-star"></i> Tier I Actionable Fusion</span>';
  } else if (genes.includes('KMT2A') || genes.includes('AFF1')) {
    actionabilityHtml = `
      <div class="clinical-callout info">
        <div style="font-weight: 700; color: #38bdf8; margin-bottom: 0.25rem;">
          <i class="fa-solid fa-dna"></i> KMT2A (MLL) Rearrangement Detected
        </div>
        <p style="font-size: 0.8rem; margin: 0; color: #cbd5e1;">
          t(4;11)(q21;q23) causing KMT2A-AFF1 in acute lymphoblastic leukemia. Eligible for clinical trials investigating <strong>Menin-KMT2A inhibitors (Revumenib)</strong>.
        </p>
      </div>
    `;
    therapyBadge = '<span class="badge badge-likely-path">KMT2A Rearrangement</span>';
  } else if (genes.includes('ALK') || genes.includes('EML4')) {
    actionabilityHtml = `
      <div class="clinical-callout success">
        <div style="font-weight: 700; color: #10b981; margin-bottom: 0.25rem;">
          <i class="fa-solid fa-capsules"></i> EML4-ALK Inversion Fusion
        </div>
        <p style="font-size: 0.8rem; margin: 0; color: #cbd5e1;">
          inv(2)(p21p23) generates oncogenic ALK fusion protein. Sensitive to ALK inhibitors: <strong>Alectinib</strong>, <strong>Lorlatinib</strong>, <strong>Brigatinib</strong>, <strong>Crizotinib</strong>.
        </p>
      </div>
    `;
    therapyBadge = '<span class="badge badge-pathogenic">ALK Inhibitor Sensitive</span>';
  } else if (genes.includes('MYC') || genes.includes('IGH')) {
    actionabilityHtml = `
      <div class="clinical-callout warning">
        <div style="font-weight: 700; color: #f59e0b; margin-bottom: 0.25rem;">
          <i class="fa-solid fa-bolt"></i> MYC-IGH Translocation t(8;14)
        </div>
        <p style="font-size: 0.8rem; margin: 0; color: #cbd5e1;">
          Overexpression of MYC oncogene driven by IGH enhancer. Hallmark of Burkitt lymphoma and aggressive B-cell non-Hodgkin lymphomas.
        </p>
      </div>
    `;
    therapyBadge = '<span class="badge badge-tier-2">MYC Overexpression</span>';
  } else if (genes.includes('MSH2')) {
    actionabilityHtml = `
      <div class="clinical-callout danger">
        <div style="font-weight: 700; color: #ef4444; margin-bottom: 0.25rem;">
          <i class="fa-solid fa-shield-virus"></i> MSH2 Large Deletion (Lynch Syndrome)
        </div>
        <p style="font-size: 0.8rem; margin: 0; color: #cbd5e1;">
          High-impact structural deletion disrupting canonical reading frame of MSH2. Predicts MMR deficiency (MSI-H) and eligibility for Anti-PD-1 immunotherapy (Pembrolizumab).
        </p>
      </div>
    `;
    therapyBadge = '<span class="badge badge-pathogenic">MMR-D / MSI-H</span>';
  } else if (genes.includes('PML') || genes.includes('RARA')) {
    actionabilityHtml = `
      <div class="clinical-callout success">
        <div style="font-weight: 700; color: #10b981; margin-bottom: 0.25rem;">
          <i class="fa-solid fa-pills"></i> PML-RARA t(15;17) APL Fusion (Tier I Actionable)
        </div>
        <p style="font-size: 0.8rem; margin: 0; color: #cbd5e1;">
          Diagnostic translocation for Acute Promyelocytic Leukemia (APL). Highly sensitive to dual differentiation therapy: <strong>All-Trans Retinoic Acid (ATRA)</strong> + <strong>Arsenic Trioxide (ATO)</strong> (>95% cure rate).
        </p>
      </div>
    `;
    therapyBadge = '<span class="badge badge-pathogenic">Tier I ATRA/ATO Actionable</span>';
  } else if (genes.includes('CYP2D6') || genes.includes('CYP2D7')) {
    actionabilityHtml = `
      <div class="clinical-callout warning">
        <div style="font-weight: 700; color: #f59e0b; margin-bottom: 0.25rem;">
          <i class="fa-solid fa-prescription-bottle-medical"></i> CYP2D6/CYP2D7 Complex Pharmacogenomic Rearrangement
        </div>
        <p style="font-size: 0.8rem; margin: 0; color: #cbd5e1;">
          12.8 kb structural deletion & hybrid conversion (*4/*10 alleles). CPIC Level 1A actionable: governs altered metabolism for <strong>Tamoxifen</strong>, <strong>Codeine</strong>, <strong>Tramadol</strong>, <strong>Fluoxetine</strong>, and <strong>Metoprolol</strong>.
        </p>
      </div>
    `;
    therapyBadge = '<span class="badge badge-likely-path">CPIC 1A Pharmacogene</span>';
  } else if (genes.includes('SMN1') || genes.includes('SMN2')) {
    actionabilityHtml = `
      <div class="clinical-callout info">
        <div style="font-weight: 700; color: #38bdf8; margin-bottom: 0.25rem;">
          <i class="fa-solid fa-child"></i> SMN1/SMN2 Spinal Muscular Atrophy (SMA) Locus
        </div>
        <p style="font-size: 0.8rem; margin: 0; color: #cbd5e1;">
          28.5 kb paralogous copy deletion/conversion. Critical for SMA molecular diagnosis; indicates eligibility for SMN restoration therapy: <strong>Nusinersen (Spinraza)</strong>, <strong>Risdiplam (Evrysdi)</strong>, or <strong>Onasemnogene abeparvovec (Zolgensma)</strong>.
        </p>
      </div>
    `;
    therapyBadge = '<span class="badge badge-pathogenic">SMA Therapeutic Target</span>';
  } else if (genes.includes('DEFB4A') || (chr1 === 'chr8' && pos1 >= 8000000 && pos1 <= 12000000)) {
    actionabilityHtml = `
      <div class="clinical-callout info">
        <div style="font-weight: 700; color: #a855f7; margin-bottom: 0.25rem;">
          <i class="fa-solid fa-arrows-rotate"></i> 8p23.1 Recurrent Inversion (3.85 Mb Benchmark)
        </div>
        <p style="font-size: 0.8rem; margin: 0; color: #cbd5e1;">
          Classic polymorphic inversion in HG002 flanked by REPD/REPB segmental duplications. Predisposes offspring to non-allelic homologous recombination (NAHR) causing 8p23.1 deletion/duplication syndromes.
        </p>
      </div>
    `;
    therapyBadge = '<span class="badge badge-vus">8p23.1 Inversion Benchmark</span>';
  } else if (genes.includes('MAPT') || genes.includes('CRHR1') || (chr1 === 'chr17' && pos1 >= 45000000 && pos1 <= 47000000)) {
    actionabilityHtml = `
      <div class="clinical-callout info">
        <div style="font-weight: 700; color: #a855f7; margin-bottom: 0.25rem;">
          <i class="fa-solid fa-brain"></i> 17q21.31 MAPT Inversion (900 kb H1/H2 Lineage)
        </div>
        <p style="font-size: 0.8rem; margin: 0; color: #cbd5e1;">
          Polymorphic inversion defining European H1 and H2 ancestral haplotypes. H1 clade confers increased risk for Progressive Supranuclear Palsy (PSP) and Corticobasal Degeneration.
        </p>
      </div>
    `;
    therapyBadge = '<span class="badge badge-vus">17q21.31 H1/H2 Inversion</span>';
  } else if (genes.includes('LPA')) {
    actionabilityHtml = `
      <div class="clinical-callout info">
        <div style="font-weight: 700; color: #38bdf8; margin-bottom: 0.25rem;">
          <i class="fa-solid fa-heart-pulse"></i> LPA KIV-2 Tandem Repeat Copy Number Variation
        </div>
        <p style="font-size: 0.8rem; margin: 0; color: #cbd5e1;">
          55 kb variable copy tandem duplication. Inverse correlation with circulating Lipoprotein(a) concentration; major independent genetic risk factor for atherosclerotic cardiovascular disease.
        </p>
      </div>
    `;
    therapyBadge = '<span class="badge badge-likely-path">Cardiovascular Risk Locus</span>';
  } else if (genes.includes('FLT3')) {
    actionabilityHtml = `
      <div class="clinical-callout danger">
        <div style="font-weight: 700; color: #ef4444; margin-bottom: 0.25rem;">
          <i class="fa-solid fa-dna"></i> FLT3 Internal Tandem Duplication (FLT3-ITD)
        </div>
        <p style="font-size: 0.8rem; margin: 0; color: #cbd5e1;">
          Constitutive FLT3 receptor tyrosine kinase activation in AML. Indicates poor prognosis and eligibility for FLT3 inhibitors: <strong>Midostaurin</strong>, <strong>Gilteritinib</strong>, <strong>Quizartinib</strong>.
        </p>
      </div>
    `;
    therapyBadge = '<span class="badge badge-pathogenic">FLT3 Inhibitor Indicated</span>';
  } else if (genes.includes('DMD')) {
    actionabilityHtml = `
      <div class="clinical-callout danger">
        <div style="font-weight: 700; color: #ef4444; margin-bottom: 0.25rem;">
          <i class="fa-solid fa-person-walking-with-cane"></i> DMD Dystrophin Multi-Exon Deletion
        </div>
        <p style="font-size: 0.8rem; margin: 0; color: #cbd5e1;">
          32 kb deletion disrupting dystrophin rod domain. Causes Duchenne/Becker Muscular Dystrophy; evaluation for exon-skipping antisense oligonucleotides (<strong>Eteplirsen</strong>, <strong>Golodirsen</strong>).
        </p>
      </div>
    `;
    therapyBadge = '<span class="badge badge-pathogenic">Dystrophinopathy</span>';
  }

  const vafPercent = sv.vaf ? (sv.vaf * 100).toFixed(1) : '-';
  const sizeText = sv.sv_len ? `${Math.abs(sv.sv_len).toLocaleString()} bp` : 'Translocation Breakend';

  panel.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; border-bottom: 1px solid #1e293b; padding-bottom: 0.75rem;">
      <div>
        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
          <span class="badge ${isTransloc ? 'badge-sv-bnd' : 'badge-sv-del'}">${sv.sv_type}</span>
          <h3 style="font-size: 1.15rem; font-weight: 800; color: #f8fafc; margin: 0;">${geneTitle}</h3>
        </div>
        <span style="font-size: 0.8rem; color: #94a3b8;">Topology: ${isTransloc ? 'Inter-Chromosomal Translocation / Breakend' : 'Intra-Chromosomal Rearrangement'}</span>
      </div>
      <div>${therapyBadge}</div>
    </div>

    <!-- Breakpoint Junction Visualizer -->
    <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 0.85rem; margin-bottom: 1rem;">
      <div style="font-size: 0.75rem; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.5rem;">
        <i class="fa-solid fa-code-merge"></i> Breakpoint Coordinates & Fusion Junction
      </div>
      <div style="display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 0.75rem; text-align: center;">
        <div style="background: #1e293b; padding: 0.5rem; border-radius: 6px;">
          <div style="font-weight: 700; color: #f8fafc;">${genes[0] || chr1}</div>
          <div style="font-family: monospace; font-size: 0.8rem; color: #38bdf8;">${chr1}:${pos1.toLocaleString()}</div>
          <div style="font-size: 0.7rem; color: #64748b;">Breakpoint 1 (5')</div>
        </div>

        <div style="color: #ef4444; font-size: 1.25rem; font-weight: 800;">
          <i class="fa-solid fa-arrow-right-arrow-left"></i>
        </div>

        <div style="background: #1e293b; padding: 0.5rem; border-radius: 6px;">
          <div style="font-weight: 700; color: #f8fafc;">${genes[1] || genes[0] || chr2}</div>
          <div style="font-family: monospace; font-size: 0.8rem; color: #f59e0b;">${chr2}:${pos2.toLocaleString()}</div>
          <div style="font-size: 0.7rem; color: #64748b;">Breakpoint 2 (3')</div>
        </div>
      </div>
    </div>

    <!-- ONT Long-Read Evidence Grid -->
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem; margin-bottom: 1rem;">
      <div class="meta-item" style="background: #0f172a; padding: 0.6rem; border-radius: 6px; border: 1px solid #1e293b;">
        <span class="meta-label">Supporting Reads</span>
        <span class="meta-value" style="color: #10b981; font-weight: 800;">${sv.support_reads || 0} reads</span>
      </div>
      <div class="meta-item" style="background: #0f172a; padding: 0.6rem; border-radius: 6px; border: 1px solid #1e293b;">
        <span class="meta-label">Total Depth</span>
        <span class="meta-value">${sv.total_depth || '-'}x</span>
      </div>
      <div class="meta-item" style="background: #0f172a; padding: 0.6rem; border-radius: 6px; border: 1px solid #1e293b;">
        <span class="meta-label">Variant Allele Frac</span>
        <span class="meta-value" style="color: #f59e0b; font-weight: 800;">${vafPercent}%</span>
      </div>
      <div class="meta-item" style="background: #0f172a; padding: 0.6rem; border-radius: 6px; border: 1px solid #1e293b;">
        <span class="meta-label">Span / Size</span>
        <span class="meta-value">${sizeText}</span>
      </div>
    </div>

    <!-- Clinical Actionability Box -->
    ${actionabilityHtml}

    <!-- Direct Action Buttons -->
    <div style="display: flex; gap: 0.5rem; margin-top: 1rem; flex-wrap: wrap;">
      <button class="btn btn-primary" onclick="jumpToCircosLocus('${chr1}', ${pos1})" style="flex: 1;">
        <i class="fa-solid fa-magnifying-glass-location"></i> Inspect Breakpoint 1 (${chr1})
      </button>
      <button class="btn btn-secondary" onclick="jumpToCircosLocus('${chr2}', ${pos2})" style="flex: 1;">
        <i class="fa-solid fa-magnifying-glass-location"></i> Inspect Breakpoint 2 (${chr2})
      </button>
      ${(typeof isVariantInReport === 'function' && isVariantInReport(sv))
        ? `<button class="btn btn-secondary" disabled style="opacity: 0.75; cursor: not-allowed;"><i class="fa-solid fa-check"></i> Included in Report</button>`
        : `<button class="btn btn-teal" onclick="addSvToReportFromCircos(${sv.id})"><i class="fa-solid fa-file-circle-plus"></i> Add to Report</button>`
      }
    </div>
  `;
}

function jumpToCircosLocus(chrom, pos) {
  const sidebarLocusItem = document.querySelector('[data-view="locus-view"]');
  if (sidebarLocusItem) sidebarLocusItem.click();

  setTimeout(() => {
    const cInput = document.getElementById('locusChromInput');
    const sInput = document.getElementById('locusStartInput');
    const eInput = document.getElementById('locusEndInput');
    if (cInput && sInput && eInput) {
      cInput.value = chrom;
      sInput.value = Math.max(1, pos - 15000);
      eInput.value = pos + 15000;
      const renderBtn = document.getElementById('locusRenderBtn');
      if (renderBtn) renderBtn.click();
    }
  }, 100);
}

function addSvToReportFromCircos(svId) {
  const sv = currentCircosSVs.find((s) => String(s.id) === String(svId));
  if (!sv) return;
  if (typeof addVariantToClinicalReport === 'function') {
    addVariantToClinicalReport(sv);
    renderCircosInspector(sv);
    if (typeof renderSvTable === 'function' && typeof svData !== 'undefined') {
      renderSvTable(svData);
    }
  } else {
    showToast(`Added ${sv.genes_affected || sv.sv_type} to clinical diagnostic report!`, 'success');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const typeFilter = document.getElementById('circosTypeFilter');
  if (typeFilter) {
    typeFilter.addEventListener('change', () => {
      renderCircosPlot(currentCircosSVs);
    });
  }

  const resetBtn = document.getElementById('circosResetBtn');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      if (document.getElementById('circosTypeFilter')) document.getElementById('circosTypeFilter').value = '';
      selectedCircosSV = null;
      renderCircosPlot(currentCircosSVs);
    });
  }
});
