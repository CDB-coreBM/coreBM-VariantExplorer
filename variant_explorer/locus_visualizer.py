"""Interactive SVG multi-track genomic visualizer for ONT long-read loci."""

import math
from typing import Dict, Any, List, Optional


def generate_locus_svg(
    chrom: str,
    start: int,
    end: int,
    gene_symbol: str = "",
    transcript_id: str = "",
    snv_pos: Optional[int] = None,
    sv_type: Optional[str] = None,
    sv_start: Optional[int] = None,
    sv_end: Optional[int] = None,
    methylation_points: Optional[List[Dict[str, Any]]] = None,
    mean_depth: float = 45.0,
    width: int = 860,
    height: int = 340
) -> str:
    """
    Renders an interactive, publication-ready SVG containing:
      1. Coordinate axis with cytoband scale
      2. Gene & exon structures
      3. Sequencing depth profile (simulated ONT pileup)
      4. Variant indicator / SV breakpoint arcs
      5. CpG Methylation lollipops (0-100% 5mC)
    """
    span = max(1, end - start)
    margin_left = 70
    margin_right = 30
    plot_width = width - margin_left - margin_right

    def x_coord(pos: int) -> float:
        ratio = (pos - start) / span
        ratio = max(0.0, min(1.0, ratio))
        return margin_left + (ratio * plot_width)

    svg_parts: List[str] = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" xmlns="http://www.w3.org/2000/svg" style="background:#0f172a; border-radius:8px; font-family:Inter, system-ui, sans-serif;">',
        '<defs>',
        '  <linearGradient id="covGrad" x1="0" y1="0" x2="0" y2="1">',
        '    <stop offset="0%" stop-color="#00a896" stop-opacity="0.6"/>',
        '    <stop offset="100%" stop-color="#00a896" stop-opacity="0.05"/>',
        '  </linearGradient>',
        '  <filter id="glow">',
        '    <feGaussianBlur stdDeviation="2" result="coloredBlur"/>',
        '    <feMerge>',
        '      <feMergeNode in="coloredBlur"/>',
        '      <feMergeNode in="SourceGraphic"/>',
        '    </feMerge>',
        '  </filter>',
        '</defs>'
    ]

    # Track 1: Genomic Coordinates Axis
    y_axis = 35
    svg_parts.append(f'<line x1="{margin_left}" y1="{y_axis}" x2="{width - margin_right}" y2="{y_axis}" stroke="#334155" stroke-width="1.5"/>')
    svg_parts.append(f'<text x="{margin_left - 10}" y="{y_axis + 4}" fill="#94a3b8" font-size="11" font-weight="600" text-anchor="end">{chrom}</text>')
    
    # Tick marks
    ticks = 5
    for i in range(ticks + 1):
        tick_pos = start + int((i / ticks) * span)
        tx = x_coord(tick_pos)
        svg_parts.append(f'<line x1="{tx}" y1="{y_axis - 4}" x2="{tx}" y2="{y_axis + 4}" stroke="#64748b" stroke-width="1.2"/>')
        svg_parts.append(f'<text x="{tx}" y="{y_axis - 8}" fill="#94a3b8" font-size="10" text-anchor="middle">{tick_pos:,}</text>')

    # Track 2: Gene Model & Exons
    y_gene = 75
    svg_parts.append(f'<text x="{margin_left - 10}" y="{y_gene + 5}" fill="#38bdf8" font-size="11" font-weight="600" text-anchor="end">{gene_symbol or "GENE"}</text>')
    # Intron line
    svg_parts.append(f'<line x1="{margin_left}" y1="{y_gene}" x2="{width - margin_right}" y2="{y_gene}" stroke="#38bdf8" stroke-width="2" stroke-dasharray="4,4"/>')

    # Simulated exons across locus
    num_exons = 4
    exon_span = span / (num_exons * 2)
    for e in range(num_exons):
        e_start = start + int((e * 2 + 0.5) * exon_span)
        e_end = e_start + int(exon_span * 0.8)
        ex1 = x_coord(e_start)
        ex2 = x_coord(e_end)
        ew = max(6, ex2 - ex1)
        svg_parts.append(f'<rect x="{ex1}" y="{y_gene - 8}" width="{ew}" height="16" rx="3" fill="#0284c7" stroke="#38bdf8" stroke-width="1"/>')
        svg_parts.append(f'<text x="{ex1 + ew/2}" y="{y_gene + 4}" fill="#ffffff" font-size="9" font-weight="700" text-anchor="middle">E{e+1}</text>')

    # Track 3: ONT Long-Read Coverage Depth Profile
    y_cov_base = 180
    y_cov_height = 65
    svg_parts.append(f'<text x="{margin_left - 10}" y="{y_cov_base - y_cov_height/2}" fill="#00a896" font-size="11" font-weight="600" text-anchor="end">Depth</text>')
    
    # 30x clinical threshold line
    y_30x = y_cov_base - int((30.0 / max(60.0, mean_depth * 1.5)) * y_cov_height)
    svg_parts.append(f'<line x1="{margin_left}" y1="{y_30x}" x2="{width - margin_right}" y2="{y_30x}" stroke="#ef4444" stroke-width="1" stroke-dasharray="3,3"/>')
    svg_parts.append(f'<text x="{width - margin_right + 4}" y="{y_30x + 3}" fill="#ef4444" font-size="9">30x</text>')

    # Coverage area path
    cov_points: List[str] = [f"{margin_left},{y_cov_base}"]
    step_px = 12
    steps = int(plot_width / step_px)
    for s_idx in range(steps + 1):
        cur_x = margin_left + (s_idx * step_px)
        cur_ratio = s_idx / steps
        # Natural fluctuation around mean depth
        depth_val = mean_depth * (0.85 + 0.3 * math.sin(cur_ratio * 14) * math.cos(cur_ratio * 7))
        # If there's a deletion, dip to 0
        if sv_type == "DEL" and sv_start and sv_end:
            if x_coord(sv_start) <= cur_x <= x_coord(sv_end):
                depth_val = depth_val * 0.45  # heterozygous drop
        cur_y = y_cov_base - int((depth_val / max(60.0, mean_depth * 1.5)) * y_cov_height)
        cov_points.append(f"{cur_x:.1f},{cur_y:.1f}")
    cov_points.append(f"{width - margin_right},{y_cov_base}")
    svg_parts.append(f'<polygon points="{" ".join(cov_points)}" fill="url(#covGrad)"/>')
    svg_parts.append(f'<polyline points="{" ".join(cov_points[1:-1])}" fill="none" stroke="#00a896" stroke-width="1.8"/>')

    # Track 4: Variant Indicators & Structural Variant Arcs
    if snv_pos and start <= snv_pos <= end:
        vx = x_coord(snv_pos)
        svg_parts.append(f'<line x1="{vx}" y1="45" x2="{vx}" y2="{y_cov_base}" stroke="#f43f5e" stroke-width="2" stroke-dasharray="2,2"/>')
        svg_parts.append(f'<circle cx="{vx}" y="75" r="6" fill="#f43f5e" stroke="#ffffff" stroke-width="2" filter="url(#glow)"/>')
        svg_parts.append(f'<text x="{vx}" y="60" fill="#f43f5e" font-size="10" font-weight="700" text-anchor="middle">SNV</text>')

    if sv_type and sv_start and sv_end:
        sx1 = x_coord(sv_start)
        sx2 = x_coord(sv_end)
        sw = max(8, sx2 - sx1)
        sv_col = "#e63946" if sv_type == "DEL" else "#a855f7" if sv_type == "INS" else "#f59e0b"
        
        # Breakpoint arc
        arc_height = 25
        y_arc = y_cov_base + 35
        svg_parts.append(f'<path d="M {sx1} {y_arc} Q {sx1 + sw/2} {y_arc - arc_height} {sx2} {y_arc}" fill="none" stroke="{sv_col}" stroke-width="2.5"/>')
        svg_parts.append(f'<circle cx="{sx1}" cy="{y_arc}" r="4" fill="{sv_col}"/>')
        svg_parts.append(f'<circle cx="{sx2}" cy="{y_arc}" r="4" fill="{sv_col}"/>')
        svg_parts.append(f'<rect x="{sx1}" y="{y_arc + 4}" width="{sw}" height="10" rx="2" fill="{sv_col}" opacity="0.3"/>')
        svg_parts.append(f'<text x="{sx1 + sw/2}" y="{y_arc + 26}" fill="{sv_col}" font-size="10" font-weight="700" text-anchor="middle">{sv_type} ({abs(sv_end - sv_start):,} bp)</text>')

    # Track 5: CpG Methylation Lollipop Track (0 - 100% 5mC)
    y_meth_base = 310
    svg_parts.append(f'<text x="{margin_left - 10}" y="{y_meth_base - 15}" fill="#f59e0b" font-size="11" font-weight="600" text-anchor="end">5mC %</text>')
    svg_parts.append(f'<line x1="{margin_left}" y1="{y_meth_base}" x2="{width - margin_right}" y2="{y_meth_base}" stroke="#334155" stroke-width="1"/>')
    
    # Render methylation lollipops
    points_to_render = methylation_points or [
        {"pos": start + int(span * 0.15), "pct": 12.0},
        {"pos": start + int(span * 0.30), "pct": 82.0},
        {"pos": start + int(span * 0.45), "pct": 88.0},
        {"pos": start + int(span * 0.60), "pct": 15.0},
        {"pos": start + int(span * 0.75), "pct": 92.0},
        {"pos": start + int(span * 0.88), "pct": 8.0},
    ]

    for p in points_to_render:
        p_pos = p.get("pos", p.get("start", start))
        if start <= p_pos <= end:
            mx = x_coord(p_pos)
            pct = float(p.get("percent_modified", p.get("pct", 50.0)))
            # Height proportional to % 5mC (max height: 35px)
            pin_h = int((pct / 100.0) * 35)
            my = y_meth_base - pin_h
            
            m_col = "#e63946" if pct >= 60.0 else "#2a9d8f" if pct <= 20.0 else "#f59e0b"
            svg_parts.append(f'<line x1="{mx}" y1="{y_meth_base}" x2="{mx}" y2="{my}" stroke="{m_col}" stroke-width="1.5"/>')
            svg_parts.append(f'<circle cx="{mx}" cy="{my}" r="4.5" fill="{m_col}" stroke="#ffffff" stroke-width="1"/>')

    svg_parts.append('</svg>')
    return "".join(svg_parts)
