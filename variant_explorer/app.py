"""Flask web application factory and REST API for coreBM Variant Explorer."""

import os
import json
import sqlite3
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify, render_template, Response, abort
from .models import init_db, get_db_connection
from .sample_manager import (
    create_case, ingest_snv_vcf, ingest_sv_vcf,
    ingest_methylation_bed, get_case_summary
)
from .locus_visualizer import generate_locus_svg
from .clinical_annotations import CLINICAL_METHYLATION_TARGETS


def create_app(db_path: Optional[str] = None) -> Flask:
    """Application factory for coreBM Variant Explorer."""
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path

    # Ensure database schema exists
    init_db(db_path)

    _snv_case_stats_cache = {}

    @app.after_request
    def add_cors_and_range_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD"
        response.headers["Access-Control-Allow-Headers"] = "Range, Origin, Content-Type, Accept, Authorization, X-Requested-With"
        response.headers["Access-Control-Expose-Headers"] = "Content-Range, Content-Length, Accept-Ranges"
        return response

    def resolve_case_id(conn, case_id_str):
        if not case_id_str:
            return None
        case_id_str = str(case_id_str).strip()
        if case_id_str.isdigit():
            return int(case_id_str)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM cases WHERE case_id = ?", (case_id_str,))
        row = cursor.fetchone()
        return row["id"] if row else None

    # -------------------------------------------------------------
    # Page Route
    # -------------------------------------------------------------
    @app.route("/")
    def index():
        conn = get_db_connection(app.config.get("DB_PATH"))
        cursor = conn.cursor()
        cursor.execute("SELECT id, case_id, patient_name, sample_name, indication, status FROM cases ORDER BY id DESC")
        cases = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return render_template("index.html", cases=cases)

    # -------------------------------------------------------------
    # Case Management REST APIs
    # -------------------------------------------------------------
    @app.route("/api/cases", methods=["GET"])
    def list_cases():
        conn = get_db_connection(app.config.get("DB_PATH"))
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases ORDER BY id DESC")
        cases = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"status": "success", "cases": cases})

    @app.route("/api/cases/<int:case_id>", methods=["GET"])
    def get_case_details(case_id: int):
        conn = get_db_connection(app.config.get("DB_PATH"))
        summary = get_case_summary(case_id, db_conn=conn)
        conn.close()
        if not summary:
            return jsonify({"status": "error", "message": "Case not found"}), 404
        return jsonify({"status": "success", "data": summary})

    @app.route("/api/cases", methods=["POST"])
    def api_create_case():
        data = request.get_json() or {}
        if not data.get("case_id") or not data.get("patient_name"):
            return jsonify({"status": "error", "message": "case_id and patient_name are required."}), 400

        conn = get_db_connection(app.config.get("DB_PATH"))
        try:
            new_id = create_case(
                case_id=data["case_id"].strip(),
                patient_id=data.get("patient_id", "").strip() or data["case_id"].strip(),
                patient_name=data["patient_name"].strip(),
                indication=data.get("indication", "").strip(),
                sample_name=data.get("sample_name", "").strip(),
                dob=data.get("dob", "").strip(),
                gender=data.get("gender", "Unknown").strip(),
                notes=data.get("notes", "").strip(),
                db_conn=conn
            )
            conn.close()
            return jsonify({"status": "success", "case_id": new_id, "message": "Case created successfully."})
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({"status": "error", "message": f"Case ID '{data.get('case_id')}' already exists."}), 409
        except Exception as e:
            conn.close()
            return jsonify({"status": "error", "message": str(e)}), 400

    @app.route("/api/cases/<int:case_id>/upload", methods=["POST"])
    def upload_case_files(case_id: int):
        conn = get_db_connection(app.config.get("DB_PATH"))
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM cases WHERE id = ?", (case_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"status": "error", "message": "Case not found."}), 404

        file_type = request.form.get("file_type")  # 'snv_vcf', 'sv_vcf', 'bedmethyl'
        file_obj = request.files.get("file")
        content = ""
        if file_obj and file_obj.filename:
            content = file_obj.read().decode("utf-8", errors="ignore")
        elif "content" in request.form and request.form["content"].strip():
            content = request.form["content"].strip()
        else:
            conn.close()
            return jsonify({"status": "error", "message": "No file or text content provided."}), 400

        try:
            if file_type == "snv_vcf":
                count = ingest_snv_vcf(case_id, content, db_conn=conn)
                msg = f"Successfully ingested {count} small variants (SNVs/indels)."
            elif file_type == "sv_vcf":
                count = ingest_sv_vcf(case_id, content, db_conn=conn)
                msg = f"Successfully ingested {count} structural variants (SVs)."
            elif file_type == "bedmethyl":
                count = ingest_methylation_bed(case_id, content, db_conn=conn)
                msg = f"Successfully ingested {count} methylation regions."
            else:
                conn.close()
                return jsonify({"status": "error", "message": f"Unknown file_type '{file_type}'."}), 400

            conn.close()
            return jsonify({"status": "success", "count": count, "message": msg})
        except Exception as e:
            conn.close()
            return jsonify({"status": "error", "message": str(e)}), 400

    # -------------------------------------------------------------
    # Small Variants (SNVs/Indels) REST API
    # -------------------------------------------------------------
    @app.route("/api/variants/snv", methods=["GET"])
    def get_snv_variants():
        case_id_str = request.args.get("case_id")
        if not case_id_str:
            return jsonify({"status": "error", "message": "case_id is required."}), 400

        conn = get_db_connection(app.config.get("DB_PATH"))
        case_id = resolve_case_id(conn, case_id_str)
        if not case_id:
            conn.close()
            return jsonify({"status": "error", "message": f"Case '{case_id_str}' not found."}), 404

        gene = request.args.get("gene", "").strip()
        panel_id = request.args.get("panel_id", "").strip()
        acmg_class = request.args.get("acmg_class", "").strip()
        consequence = request.args.get("consequence", "").strip()
        search = request.args.get("search", "").strip()
        actionable_only = request.args.get("actionable", "0") in ("1", "true")
        max_gnomad = request.args.get("max_gnomad_af", "").strip()
        min_vaf = request.args.get("min_vaf", "").strip()

        # Pagination: Never exceed 500 rows
        page = max(1, int(request.args.get("page", 1)))
        limit = min(500, max(10, int(request.args.get("limit", 50))))
        offset = (page - 1) * limit

        cursor = conn.cursor()

        where_clauses = ["case_id = ?"]
        params = [case_id]

        if panel_id:
            try:
                cursor.execute("SELECT gene_list_json FROM gene_panel_versions WHERE panel_id = ? AND is_active = 1", (int(panel_id),))
                p_row = cursor.fetchone()
                if p_row and p_row["gene_list_json"]:
                    panel_genes = json.loads(p_row["gene_list_json"])
                    if panel_genes:
                        placeholders = ",".join(["?"] * len(panel_genes))
                        where_clauses.append(f"gene_symbol IN ({placeholders}) COLLATE NOCASE")
                        params.extend(panel_genes)
            except Exception as e:
                app.logger.warning(f"Error filtering by panel_id {panel_id}: {e}")

        if gene:
            where_clauses.append("gene_symbol = ? COLLATE NOCASE")
            params.append(gene)
        if acmg_class:
            where_clauses.append("acmg_class = ?")
            params.append(acmg_class)
        if consequence:
            where_clauses.append("consequence LIKE ?")
            params.append(f"%{consequence}%")
        if actionable_only:
            where_clauses.append("is_actionable = 1")
        if max_gnomad:
            try:
                where_clauses.append("gnomad_af <= ?")
                params.append(float(max_gnomad))
            except ValueError:
                pass
        if min_vaf:
            try:
                where_clauses.append("vaf >= ?")
                params.append(float(min_vaf))
            except ValueError:
                pass
        if search:
            where_clauses.append("(gene_symbol LIKE ? OR hgvs_p LIKE ? OR hgvs_c LIKE ? OR clinvar_sig LIKE ?)")
            p = f"%{search}%"
            params.extend([p, p, p, p])

        where_sql = " AND ".join(where_clauses)

        # Count total and aggregate clinical metrics across entire filtered dataset
        # Fast-path: Reuse cached baseline metrics when browsing unfiltered case rows
        if len(where_clauses) == 1 and case_id in _snv_case_stats_cache:
            metrics = _snv_case_stats_cache[case_id]
            total_records = metrics["total"]
        else:
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN acmg_class IN ('Pathogenic', 'Likely Pathogenic') THEN 1 ELSE 0 END) as pathogenic_count,
                    SUM(CASE WHEN acmg_class = 'VUS' THEN 1 ELSE 0 END) as vus_count,
                    SUM(CASE WHEN phase_set IS NOT NULL AND phase_set != '' THEN 1 ELSE 0 END) as phased_count
                FROM variants_snv WHERE {where_sql}
            """, params)
            stats_row = cursor.fetchone()
            total_records = stats_row["total"] if stats_row and stats_row["total"] else 0
            metrics = {
                "total": total_records,
                "pathogenic_count": stats_row["pathogenic_count"] if stats_row and stats_row["pathogenic_count"] else 0,
                "vus_count": stats_row["vus_count"] if stats_row and stats_row["vus_count"] else 0,
                "phased_count": stats_row["phased_count"] if stats_row and stats_row["phased_count"] else 0
            }
            if len(where_clauses) == 1:
                _snv_case_stats_cache[case_id] = metrics

        # Fetch page rows
        query = f"""
            SELECT * FROM variants_snv
            WHERE {where_sql}
            ORDER BY 
                CASE acmg_class 
                    WHEN 'Pathogenic' THEN 1 
                    WHEN 'Likely Pathogenic' THEN 2 
                    WHEN 'VUS' THEN 3 
                    WHEN 'Likely Benign' THEN 4 
                    ELSE 5 
                END ASC,
                qual DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(query, params + [limit, offset])
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        return jsonify({
            "status": "success",
            "page": page,
            "limit": limit,
            "total_records": total_records,
            "total_pages": max(1, (total_records + limit - 1) // limit),
            "metrics": metrics,
            "variants": rows
        })

    @app.route("/api/variants/snv/<int:snv_id>/review", methods=["POST"])
    def update_snv_review(snv_id: int):
        data = request.get_json() or {}
        conn = get_db_connection(app.config.get("DB_PATH"))
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE variants_snv
            SET review_status = ?, tags = ?, notes = ?
            WHERE id = ?
        """, (
            data.get("review_status", "Unreviewed"),
            data.get("tags", ""),
            data.get("notes", ""),
            snv_id
        ))
        conn.commit()
        conn.close()
        _snv_case_stats_cache.clear()
        return jsonify({"status": "success", "message": "Variant review updated."})

    # -------------------------------------------------------------
    # Structural Variants (SVs) REST API
    # -------------------------------------------------------------
    @app.route("/api/variants/sv", methods=["GET"])
    def get_sv_variants():
        case_id_str = request.args.get("case_id")
        if not case_id_str:
            return jsonify({"status": "error", "message": "case_id is required."}), 400

        conn = get_db_connection(app.config.get("DB_PATH"))
        case_id = resolve_case_id(conn, case_id_str)
        if not case_id:
            conn.close()
            return jsonify({"status": "error", "message": f"Case '{case_id_str}' not found."}), 404

        sv_type = request.args.get("sv_type", "").strip()
        panel_id = request.args.get("panel_id", "").strip()
        min_len = (request.args.get("min_len") or request.args.get("min_length") or "").strip()
        max_len = (request.args.get("max_len") or request.args.get("max_length") or "").strip()
        gene = request.args.get("gene", "").strip()
        min_support = request.args.get("min_support", "").strip()
        tr_only = request.args.get("tandem_repeat", "0") in ("1", "true")

        page = max(1, int(request.args.get("page", 1)))
        limit = min(500, max(10, int(request.args.get("limit", 50))))
        offset = (page - 1) * limit

        cursor = conn.cursor()

        where_clauses = ["case_id = ?"]
        params = [case_id]

        if panel_id:
            try:
                cursor.execute("SELECT gene_list_json FROM gene_panel_versions WHERE panel_id = ? AND is_active = 1", (int(panel_id),))
                p_row = cursor.fetchone()
                if p_row and p_row["gene_list_json"]:
                    panel_genes = json.loads(p_row["gene_list_json"])
                    if panel_genes:
                        subclauses = []
                        for g in panel_genes:
                            subclauses.append("genes_affected LIKE ?")
                            params.append(f"%{g}%")
                        where_clauses.append("(" + " OR ".join(subclauses) + ")")
            except Exception as e:
                app.logger.warning(f"Error filtering SVs by panel_id {panel_id}: {e}")

        if sv_type:
            where_clauses.append("sv_type = ?")
            params.append(sv_type)
        if min_len:
            try:
                where_clauses.append("sv_len >= ?")
                params.append(int(min_len))
            except ValueError: pass
        if max_len:
            try:
                where_clauses.append("sv_len <= ?")
                params.append(int(max_len))
            except ValueError: pass
        if gene:
            where_clauses.append("genes_affected LIKE ?")
            params.append(f"%{gene}%")
        if min_support:
            try:
                where_clauses.append("support_reads >= ?")
                params.append(int(min_support))
            except ValueError: pass
        if tr_only:
            where_clauses.append("tandem_repeat = 1")

        where_sql = " AND ".join(where_clauses)

        # Aggregate SV type statistics across entire filtered dataset
        cursor.execute(f"""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN UPPER(sv_type) = 'DEL' THEN 1 ELSE 0 END) as del_count,
                SUM(CASE WHEN UPPER(sv_type) = 'DUP' THEN 1 ELSE 0 END) as dup_count,
                SUM(CASE WHEN UPPER(sv_type) = 'INS' THEN 1 ELSE 0 END) as ins_count,
                SUM(CASE WHEN UPPER(sv_type) IN ('BND', 'TRA') THEN 1 ELSE 0 END) as bnd_count
            FROM variants_sv WHERE {where_sql}
        """, params)
        stats_row = cursor.fetchone()
        total_records = stats_row["total"] if stats_row and stats_row["total"] else 0
        metrics = {
            "total": total_records,
            "del_count": stats_row["del_count"] if stats_row and stats_row["del_count"] else 0,
            "dup_count": stats_row["dup_count"] if stats_row and stats_row["dup_count"] else 0,
            "ins_count": stats_row["ins_count"] if stats_row and stats_row["ins_count"] else 0,
            "bnd_count": stats_row["bnd_count"] if stats_row and stats_row["bnd_count"] else 0
        }

        query = f"""
            SELECT * FROM variants_sv
            WHERE {where_sql}
            ORDER BY 
                CASE acmg_sv_class
                    WHEN 'Pathogenic' THEN 1
                    WHEN 'Likely Pathogenic' THEN 2
                    ELSE 3
                END ASC,
                support_reads DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(query, params + [limit, offset])
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        return jsonify({
            "status": "success",
            "page": page,
            "limit": limit,
            "total_records": total_records,
            "total_pages": max(1, (total_records + limit - 1) // limit),
            "metrics": metrics,
            "structural_variants": rows
        })

    # -------------------------------------------------------------
    # Live Whole-Genome VCF Tabix Query REST API (3.9M SNVs & 74k SVs)
    # -------------------------------------------------------------
    @app.route("/api/variants/wgs/query", methods=["GET"])
    def query_wgs_vcf():
        """
        Queries whole-genome benchmark VCFs directly on-the-fly via tabix / pysam.
        Instantly serves any locus across 3.9M SNVs and 74k SVs without loading files into RAM.
        """
        import pysam

        vcf_type = request.args.get("vcf_type", "wgs_snv")  # wgs_snv, wgs_sv, cmrg_snv, cmrg_sv
        chrom = request.args.get("chrom", "chr17").strip()
        start_str = request.args.get("start", "7668000").strip()
        end_str = request.args.get("end", "7688000").strip()
        limit = min(500, max(1, int(request.args.get("limit", 100))))

        try:
            start = int(start_str)
            end = int(end_str)
        except ValueError:
            return jsonify({"status": "error", "message": "start and end must be integers"}), 400

        file_map = {
            "wgs_snv": "data_store/samples/HG002/HG002_GRCh38_1_22_v4.2.1_benchmark.vcf.gz",
            "wgs_sv": "data_store/samples/HG002/HG002_SVs_Tier1_v0.6.vcf.gz",
            "cmrg_snv": "data_store/samples/HG002/HG002_CMRG_smallvar.vcf.gz",
            "cmrg_sv": "data_store/samples/HG002/HG002_CMRG_SV.vcf.gz"
        }

        vcf_rel_path = file_map.get(vcf_type)
        if not vcf_rel_path or not os.path.exists(vcf_rel_path):
            return jsonify({"status": "error", "message": f"VCF file for {vcf_type} not found"}), 404

        try:
            vf = pysam.VariantFile(vcf_rel_path)
            query_chrom = chrom
            if query_chrom not in vf.header.contigs:
                if query_chrom.startswith("chr"):
                    alt_c = query_chrom[3:]
                    if alt_c in vf.header.contigs:
                        query_chrom = alt_c
                else:
                    alt_c = f"chr{query_chrom}"
                    if alt_c in vf.header.contigs:
                        query_chrom = alt_c

            if query_chrom not in vf.header.contigs:
                return jsonify({"status": "success", "count": 0, "variants": [], "message": f"Contig {chrom} not found in VCF"})

            records = []
            for rec in vf.fetch(query_chrom, start, end):
                if len(records) >= limit:
                    break
                alts = list(rec.alts) if rec.alts else []
                filt = list(rec.filter.keys())
                gt = "."
                dp = 0
                af = 0.0
                try:
                    if len(rec.samples) > 0:
                        s = rec.samples[0]
                        gt_tuple = s.get("GT", (None,))
                        gt = "/".join(str(a) if a is not None else "." for a in gt_tuple)
                        ad = s.get("AD", None)
                        if ad:
                            dp = sum(ad)
                            if len(ad) > 1 and dp > 0:
                                af = round(ad[1] / dp, 3)
                        elif s.get("DP"):
                            dp = s.get("DP")
                except Exception:
                    pass

                sv_type = ""
                sv_len = None
                try:
                    if "SVTYPE" in vf.header.info and "SVTYPE" in rec.info:
                        sv_type = str(rec.info["SVTYPE"])
                    elif len(rec.ref) > 1 or (rec.alts and len(rec.alts[0]) > 1):
                        alt0 = rec.alts[0] if rec.alts else ""
                        if len(rec.ref) > len(alt0) and len(rec.ref) >= 50:
                            sv_type = "DEL"
                            sv_len = len(rec.ref) - len(alt0)
                        elif len(alt0) > len(rec.ref) and len(alt0) >= 50:
                            sv_type = "INS"
                            sv_len = len(alt0) - len(rec.ref)
                    if "SVLEN" in vf.header.info and "SVLEN" in rec.info:
                        raw_len = rec.info["SVLEN"]
                        if isinstance(raw_len, (tuple, list)):
                            raw_len = raw_len[0]
                        sv_len = abs(int(raw_len))
                except Exception:
                    pass

                records.append({
                    "chrom": rec.chrom,
                    "pos": rec.pos,
                    "id": rec.id or ".",
                    "ref": rec.ref,
                    "alts": alts,
                    "qual": round(rec.qual, 1) if rec.qual else None,
                    "filter": filt,
                    "genotype": gt,
                    "depth": dp,
                    "vaf": af,
                    "sv_type": sv_type,
                    "sv_len": sv_len
                })

            return jsonify({
                "status": "success",
                "count": len(records),
                "vcf_type": vcf_type,
                "region": f"{query_chrom}:{start}-{end}",
                "variants": records
            })
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    # -------------------------------------------------------------
    # Methylation & Epigenetics REST API
    # -------------------------------------------------------------
    @app.route("/api/methylation", methods=["GET"])
    def get_methylation():
        case_id_str = request.args.get("case_id")
        if not case_id_str:
            return jsonify({"status": "error", "message": "case_id is required."}), 400

        conn = get_db_connection(app.config.get("DB_PATH"))
        case_id = resolve_case_id(conn, case_id_str)
        if not case_id:
            conn.close()
            return jsonify({"status": "error", "message": f"Case '{case_id_str}' not found."}), 404

        status = request.args.get("status", "").strip()
        gene = request.args.get("gene", "").strip()
        asm_only = request.args.get("asm_only", "0") in ("1", "true")

        cursor = conn.cursor()

        where_clauses = ["case_id = ?"]
        params = [case_id]

        if status:
            where_clauses.append("status LIKE ?")
            params.append(f"%{status}%")
        if gene:
            where_clauses.append("gene_symbol LIKE ?")
            params.append(f"%{gene}%")
        if asm_only:
            where_clauses.append("is_asm = 1")

        where_sql = " AND ".join(where_clauses)
        cursor.execute(f"SELECT * FROM methylation_regions WHERE {where_sql} ORDER BY percent_modified DESC", params)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        return jsonify({"status": "success", "total": len(rows), "total_records": len(rows), "regions": rows})

    # -------------------------------------------------------------
    # Methylartist Epigenetic Visualization Module REST API
    # -------------------------------------------------------------
    # Gene Search & Genomic Coordinate Resolver REST API
    # -------------------------------------------------------------
    @app.route("/api/genes/search", methods=["GET"])
    def api_search_genes():
        q = request.args.get("q", "").strip()
        limit_str = request.args.get("limit", "15")
        limit = int(limit_str) if limit_str.isdigit() else 15
        from .gene_catalog import search_genes
        results = search_genes(q, limit)
        return jsonify({
            "status": "success",
            "query": q,
            "count": len(results),
            "genes": results
        })

    # -------------------------------------------------------------
    # Methylartist Epigenetic Visualization REST API
    # -------------------------------------------------------------
    VALID_HUMAN_CHROMS = {f"chr{i}" for i in range(1, 23)} | {"chrX", "chrY", "chrM"}

    @app.route("/api/methylation/methylartist", methods=["GET"])
    def get_methylartist_svg():
        case_id_str = request.args.get("case_id")
        gene = request.args.get("gene", "").strip().upper()
        chrom = request.args.get("chrom", "").strip()
        req_start = request.args.get("start")
        req_end = request.args.get("end")

        # Normalize and validate chromosome contig
        if chrom:
            if not chrom.startswith("chr") and f"chr{chrom}" in VALID_HUMAN_CHROMS:
                chrom = f"chr{chrom}"
            if chrom not in VALID_HUMAN_CHROMS:
                return jsonify({
                    "status": "error",
                    "message": f"Contig '{chrom}' is invalid. Human chromosomes must be chr1-chr22, chrX, chrY, or chrM. Zero Simulation Policy enforced."
                }), 400

        found_record = False
        mean_pct = 0.0
        hp1_pct = None
        hp2_pct = None
        is_asm = False
        cov = 0.0
        region_type = "Promoter CpG Island"
        cpg_sites = None
        start = 0
        end = 0

        # Try to parse requested coordinates
        if req_start and req_end:
            try:
                start = int(req_start)
                end = int(req_end)
            except ValueError:
                pass

        conn = get_db_connection(app.config.get("DB_PATH"))
        case_id = resolve_case_id(conn, case_id_str) if case_id_str else None

        if case_id:
            try:
                cursor = conn.cursor()
                row = None
                
                # Priority 1: Match by exact gene symbol
                if gene:
                    cursor.execute("""
                        SELECT * FROM methylation_regions
                        WHERE case_id = ? AND UPPER(gene_symbol) = ?
                        LIMIT 1
                    """, (case_id, gene))
                    row = cursor.fetchone()

                # Priority 2: Coordinate overlap within valid chromosome
                if not row and chrom and start > 0 and end > start:
                    cursor.execute("""
                        SELECT * FROM methylation_regions
                        WHERE case_id = ? AND chrom = ? AND NOT (end < ? OR start > ?)
                        ORDER BY ABS((start + end) / 2 - ?) ASC
                        LIMIT 1
                    """, (case_id, chrom, start, end, (start + end) // 2))
                    row = cursor.fetchone()

                # Priority 3: Prefix match only if gene symbol has at least 3 letters
                if not row and gene and len(gene) >= 3:
                    cursor.execute("""
                        SELECT * FROM methylation_regions
                        WHERE case_id = ? AND UPPER(gene_symbol) LIKE ?
                        LIMIT 1
                    """, (case_id, f"{gene}%"))
                    row = cursor.fetchone()

                if row:
                    row_dict = dict(row)
                    found_record = True
                    gene = row_dict.get("gene_symbol") or gene
                    mean_pct = float(row_dict.get("percent_modified") or row_dict.get("mean_methylated_pct") or 0.0)
                    hp1_pct = row_dict.get("hp1_percent")
                    hp2_pct = row_dict.get("hp2_percent")
                    is_asm = bool(row_dict.get("is_asm", 0))
                    cov = float(row_dict.get("n_valid_cov") or 30.0)
                    region_type = row_dict.get("region_type", region_type)
                    chrom = row_dict.get("chrom") or chrom
                    start = int(row_dict.get("start") or start)
                    end = int(row_dict.get("end") or end)
            except Exception as e:
                app.logger.warning(f"Error querying methylation record: {e}")
            finally:
                conn.close()

        # Strict Zero-Simulation Policy: If no authentic record exists in the sequenced database, return HTTP 404
        if not found_record:
            locus_display = f"{chrom}:{start:,}-{end:,}" if chrom and start and end else (chrom or "unspecified locus")
            return jsonify({
                "status": "error",
                "message": f"No authentic methylation data found for '{gene or locus_display}' in sequenced case {case_id_str or case_id}. Zero Simulation Policy enforced."
            }), 404

        from .methylartist_visualizer import generate_methylartist_svg
        svg_code = generate_methylartist_svg(
            chrom=chrom,
            start=start,
            end=end,
            gene_symbol=gene,
            region_type=region_type,
            mean_percent=mean_pct,
            hp1_percent=hp1_pct,
            hp2_percent=hp2_pct,
            is_asm=is_asm,
            coverage=cov,
            cpg_sites=cpg_sites
        )
        return Response(svg_code, mimetype="image/svg+xml")

    # -------------------------------------------------------------
    # Complex Structural Variants Circos REST API
    # -------------------------------------------------------------
    @app.route("/api/variants/sv/circos", methods=["GET"])
    def get_sv_circos():
        case_id_str = request.args.get("case_id")
        if not case_id_str:
            return jsonify({"status": "error", "message": "case_id is required."}), 400

        conn = get_db_connection(app.config.get("DB_PATH"))
        case_id = resolve_case_id(conn, case_id_str)
        if not case_id:
            conn.close()
            return jsonify({"status": "error", "message": f"Case '{case_id_str}' not found."}), 404
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM variants_sv WHERE case_id = ? ORDER BY id ASC", (case_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"status": "success", "count": len(rows), "structural_variants": rows})

    # -------------------------------------------------------------
    # Truly Interactive IGV Multi-Track REST APIs
    # -------------------------------------------------------------
    @app.route("/api/igv/tracks/genes", methods=["GET"])
    def get_igv_genes():
        chrom = request.args.get("chrom", "chr17")
        try:
            start = int(request.args.get("start", 7660000))
            end = int(request.args.get("end", 7690000))
        except ValueError:
            start, end = 7660000, 7690000
        from .igv_manager import get_igv_gene_features
        features = get_igv_gene_features(chrom, start, end)
        return jsonify({"status": "success", "count": len(features), "features": features})

    @app.route("/api/igv/tracks/coverage", methods=["GET"])
    def get_igv_coverage():
        case_id_str = request.args.get("case_id", "1")
        case_id = int(case_id_str) if case_id_str.isdigit() else 1
        chrom = request.args.get("chrom", "chr17")
        try:
            start = int(request.args.get("start", 7668000))
            end = int(request.args.get("end", 7685000))
        except ValueError:
            start, end = 7668000, 7685000
        from .igv_manager import calculate_dynamic_coverage
        coverage_bins = calculate_dynamic_coverage(case_id, chrom, start, end)
        return jsonify({"status": "success", "bins": coverage_bins})

    @app.route("/api/igv/tracks/snv", methods=["GET"])
    def get_igv_snv():
        case_id_str = request.args.get("case_id", "1")
        case_id = int(case_id_str) if case_id_str.isdigit() else 1
        chrom = request.args.get("chrom", "chr17")
        try:
            start = int(request.args.get("start", 1))
            end = int(request.args.get("end", 300000000))
        except ValueError:
            start, end = 1, 300000000
        from .igv_manager import get_igv_snv_features
        features = get_igv_snv_features(case_id, chrom, start, end)
        return jsonify({"status": "success", "count": len(features), "features": features})

    @app.route("/api/igv/tracks/sv", methods=["GET"])
    def get_igv_sv():
        case_id_str = request.args.get("case_id", "1")
        case_id = int(case_id_str) if case_id_str.isdigit() else 1
        chrom = request.args.get("chrom", "chr17")
        try:
            start = int(request.args.get("start", 1))
            end = int(request.args.get("end", 300000000))
        except ValueError:
            start, end = 1, 300000000
        from .igv_manager import get_igv_sv_features
        features = get_igv_sv_features(case_id, chrom, start, end)
        return jsonify({"status": "success", "count": len(features), "features": features})

    @app.route("/api/igv/tracks/methylation", methods=["GET"])
    def get_igv_methylation():
        case_id_str = request.args.get("case_id", "1")
        case_id = int(case_id_str) if case_id_str.isdigit() else 1
        chrom = request.args.get("chrom", "chr17")
        try:
            start = int(request.args.get("start", 1))
            end = int(request.args.get("end", 300000000))
        except ValueError:
            start, end = 1, 300000000
        from .igv_manager import get_igv_methylation_features
        features = get_igv_methylation_features(case_id, chrom, start, end)
        return jsonify({"status": "success", "count": len(features), "features": features})

    # -------------------------------------------------------------
    # Gene Panel Management & Versioning REST API
    # -------------------------------------------------------------
    @app.route("/api/panels", methods=["GET"])
    def get_gene_panels():
        conn = get_db_connection(app.config.get("DB_PATH"))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                p.id, p.code, p.name, p.category, p.description, p.created_at, p.updated_at,
                v.id as active_version_id, v.version_str, v.gene_count, v.changelog, v.author,
                v.created_at as version_created_at
            FROM gene_panels p
            LEFT JOIN gene_panel_versions v ON p.id = v.panel_id AND v.is_active = 1
            ORDER BY p.id ASC
        """)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"status": "success", "count": len(rows), "panels": rows})

    @app.route("/api/panels/<int:panel_id>", methods=["GET"])
    def get_gene_panel_details(panel_id: int):
        conn = get_db_connection(app.config.get("DB_PATH"))
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM gene_panels WHERE id = ?", (panel_id,))
        p = cursor.fetchone()
        if not p:
            conn.close()
            return jsonify({"status": "error", "message": "Panel not found."}), 404

        panel = dict(p)
        cursor.execute("""
            SELECT id, version_str, gene_list_json, gene_count, changelog, author, is_active, created_at
            FROM gene_panel_versions
            WHERE panel_id = ?
            ORDER BY id DESC
        """, (panel_id,))
        versions = []
        active_genes = []
        for r in cursor.fetchall():
            v = dict(r)
            try:
                genes = json.loads(v["gene_list_json"]) if v["gene_list_json"] else []
            except Exception:
                genes = []
            v["genes"] = genes
            if v["is_active"]:
                active_genes = genes
            versions.append(v)

        panel["versions"] = versions
        panel["active_genes"] = active_genes
        conn.close()
        return jsonify({"status": "success", "panel": panel})

    @app.route("/api/panels", methods=["POST"])
    def create_gene_panel():
        data = request.get_json() or {}
        name = (data.get("name") or "").strip()
        code = (data.get("code") or "").strip().upper().replace(" ", "_")
        category = (data.get("category") or "Clinical Genetics").strip()
        description = (data.get("description") or "").strip()
        raw_genes = data.get("genes", [])
        version_str = (data.get("version") or "v1.0").strip()
        changelog = (data.get("changelog") or "Initial panel creation.").strip()
        author = (data.get("author") or "Hospital Clinic Geneticist").strip()

        if not name or not code:
            return jsonify({"status": "error", "message": "Panel name and code are required."}), 400

        # Parse genes list (array or comma/space separated text)
        if isinstance(raw_genes, str):
            gene_list = [g.strip().upper() for g in raw_genes.replace(",", " ").replace(";", " ").split() if g.strip()]
        else:
            gene_list = [str(g).strip().upper() for g in raw_genes if str(g).strip()]
        gene_list = sorted(list(set(gene_list)))

        conn = get_db_connection(app.config.get("DB_PATH"))
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO gene_panels (code, name, category, description)
                VALUES (?, ?, ?, ?)
            """, (code, name, category, description))
            panel_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO gene_panel_versions (panel_id, version_str, gene_list_json, gene_count, changelog, author, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (panel_id, version_str, json.dumps(gene_list), len(gene_list), changelog, author))

            conn.commit()
            conn.close()
            return jsonify({
                "status": "success",
                "message": f"Gene panel '{name}' created successfully.",
                "panel_id": panel_id
            }), 201
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({"status": "error", "message": f"Panel with code '{code}' already exists."}), 409
        except Exception as e:
            conn.close()
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/api/panels/<int:panel_id>/versions", methods=["POST"])
    def create_gene_panel_version(panel_id: int):
        data = request.get_json() or {}
        version_str = (data.get("version") or "").strip()
        changelog = (data.get("changelog") or "Updated gene content.").strip()
        author = (data.get("author") or "Hospital Clinic Geneticist").strip()
        raw_genes = data.get("genes", [])

        if not version_str:
            return jsonify({"status": "error", "message": "Version string (e.g. v1.1) is required."}), 400

        if isinstance(raw_genes, str):
            gene_list = [g.strip().upper() for g in raw_genes.replace(",", " ").replace(";", " ").split() if g.strip()]
        else:
            gene_list = [str(g).strip().upper() for g in raw_genes if str(g).strip()]
        gene_list = sorted(list(set(gene_list)))

        conn = get_db_connection(app.config.get("DB_PATH"))
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM gene_panels WHERE id = ?", (panel_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"status": "error", "message": "Panel not found."}), 404

        # Archive prior versions by setting is_active = 0
        cursor.execute("UPDATE gene_panel_versions SET is_active = 0 WHERE panel_id = ?", (panel_id,))

        cursor.execute("""
            INSERT INTO gene_panel_versions (panel_id, version_str, gene_list_json, gene_count, changelog, author, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (panel_id, version_str, json.dumps(gene_list), len(gene_list), changelog, author))
        new_version_id = cursor.lastrowid

        cursor.execute("UPDATE gene_panels SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (panel_id,))
        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "message": f"New panel version {version_str} published with {len(gene_list)} genes.",
            "version_id": new_version_id,
            "gene_count": len(gene_list)
        })

    @app.route("/api/panels/<int:panel_id>", methods=["DELETE"])
    def delete_gene_panel(panel_id: int):
        conn = get_db_connection(app.config.get("DB_PATH"))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM gene_panels WHERE id = ?", (panel_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Gene panel removed."})

    # -------------------------------------------------------------
    # IGV Local Genome Definition & Configuration REST API
    # -------------------------------------------------------------
    @app.route("/api/igv/genomes.json", methods=["GET"])
    def get_igv_genomes_json():
        """Serves a localized, proxy-safe genome registry for Broad IGV.js."""
        return jsonify([
            {
                "id": "hg38",
                "name": "Human (GRCh38 / hg38)",
                "fastaURL": "https://s3.amazonaws.com/igv.broadinstitute.org/genomes/seq/hg38/hg38.fa",
                "indexURL": "https://s3.amazonaws.com/igv.broadinstitute.org/genomes/seq/hg38/hg38.fa.fai",
                "cytobandURL": "/static/vendor/cytoBand.txt",
                "aliasURL": "/static/vendor/hg38_alias.tab",
                "tracks": [
                    {
                        "name": "RefSeq Genes (MANE Select)",
                        "format": "refgene",
                        "url": "https://s3.amazonaws.com/igv.org.genomes/hg38/ncbiRefSeq.sorted.txt.gz",
                        "indexURL": "https://s3.amazonaws.com/igv.org.genomes/hg38/ncbiRefSeq.sorted.txt.gz.tbi",
                        "visibilityWindow": -1,
                        "displayMode": "COLLAPSED"
                    }
                ]
            }
        ])

    @app.route("/api/igv/config", methods=["GET"])
    def get_igv_config():
        case_id_str = request.args.get("case_id", "1")
        case_id = int(case_id_str) if case_id_str.isdigit() else 1
        locus = request.args.get("locus", "chr17:7,668,000-7,688,000")
        
        config = {
            "genome": "hg38",
            "loadDefaultGenomes": False,
            "locus": locus,
            "showChromosomeWidget": True,
            "showIdeogram": True,
            "showNavigation": True,
            "showRuler": True,
            "reference": {
                "id": "hg38",
                "name": "Human (GRCh38 / hg38)",
                "cytobandURL": "/static/vendor/cytoBand.txt",
                "aliasURL": "/static/vendor/hg38_alias.tab",
                "fastaURL": "https://s3.amazonaws.com/igv.broadinstitute.org/genomes/seq/hg38/hg38.fa",
                "indexURL": "https://s3.amazonaws.com/igv.broadinstitute.org/genomes/seq/hg38/hg38.fa.fai",
                "chromsizesURL": "/static/vendor/hg38_chromsizes.txt"
            },
            "tracks": [
                {
                    "name": "NCBI RefSeq Genes",
                    "type": "annotation",
                    "format": "refgene",
                    "url": "https://s3.amazonaws.com/igv.org.genomes/hg38/ncbiRefSeq.sorted.txt.gz",
                    "indexURL": "https://s3.amazonaws.com/igv.org.genomes/hg38/ncbiRefSeq.sorted.txt.gz.tbi",
                    "order": 1,
                    "visibilityWindow": -1,
                    "displayMode": "EXPANDED",
                    "color": "#0284c7",
                    "height": 70
                },
                {
                    "name": "CMRG Challenging Medical Genes (Benchmark)",
                    "type": "annotation",
                    "format": "bed",
                    "url": "/api/stream/files/variant_explorer/static/vendor/clinical_genes.bed.gz",
                    "indexURL": "/api/stream/files/variant_explorer/static/vendor/clinical_genes.bed.gz.tbi",
                    "order": 2,
                    "visibilityWindow": -1,
                    "displayMode": "EXPANDED",
                    "color": "#38bdf8",
                    "height": 45
                },
                {
                    "name": "ONT Depth Coverage (PromethION)",
                    "type": "wig",
                    "format": "bedgraph",
                    "url": "/api/stream/files/data_store/samples/HG002/HG002_coverage.bedgraph.gz",
                    "indexURL": "/api/stream/files/data_store/samples/HG002/HG002_coverage.bedgraph.gz.tbi",
                    "order": 3,
                    "height": 50,
                    "color": "#00a896",
                    "min": 0,
                    "max": 120
                },
                {
                    "name": "HG002 ONT Phased Read Alignments (PromethION)",
                    "type": "alignment",
                    "format": "bam",
                    "url": "/api/stream/files/data_store/samples/HG002/HG002_phased.bam",
                    "indexURL": "/api/stream/files/data_store/samples/HG002/HG002_phased.bam.bai",
                    "order": 4,
                    "height": 220,
                    "colorBy": "tag",
                    "colorByTag": "HP",
                    "displayMode": "EXPANDED",
                    "samplingDepth": 30,
                    "visibilityWindow": 30000,
                    "maxRows": 50
                },
                {
                    "name": "HG002 Medical Genes SV Benchmark (CMRG SV v1.00)",
                    "type": "variant",
                    "format": "vcf",
                    "url": "/api/stream/files/data_store/samples/HG002/HG002_CMRG_SV.vcf.gz",
                    "indexURL": "/api/stream/files/data_store/samples/HG002/HG002_CMRG_SV.vcf.gz.tbi",
                    "order": 5,
                    "height": 55,
                    "displayMode": "EXPANDED",
                    "visibilityWindow": -1,
                    "color": "#a855f7"
                },
                {
                    "name": "HG002 Challenging Medical Genes (CMRG SNVs v1.00)",
                    "type": "variant",
                    "format": "vcf",
                    "url": "/api/stream/files/data_store/samples/HG002/HG002_CMRG_smallvar.vcf.gz",
                    "indexURL": "/api/stream/files/data_store/samples/HG002/HG002_CMRG_smallvar.vcf.gz.tbi",
                    "order": 6,
                    "height": 50,
                    "displayMode": "EXPANDED",
                    "visibilityWindow": -1,
                    "color": "#10b981"
                },
                {
                    "name": "HG002 Whole-Genome Small Variants (GIAB v4.2.1)",
                    "type": "variant",
                    "format": "vcf",
                    "url": "/api/stream/files/data_store/samples/HG002/HG002_GRCh38_1_22_v4.2.1_benchmark.vcf.gz",
                    "indexURL": "/api/stream/files/data_store/samples/HG002/HG002_GRCh38_1_22_v4.2.1_benchmark.vcf.gz.tbi",
                    "order": 7,
                    "height": 55,
                    "visibilityWindow": 100000,
                    "color": "#ef4444"
                },
                {
                    "name": "HG002 DNA Methylation (5mC CpG Promoters)",
                    "type": "annotation",
                    "format": "bed",
                    "url": "/api/stream/files/data_store/samples/HG002/hg002_methylation.bed.gz",
                    "indexURL": "/api/stream/files/data_store/samples/HG002/hg002_methylation.bed.gz.tbi",
                    "order": 8,
                    "displayMode": "EXPANDED",
                    "color": "#10b981",
                    "height": 50
                }
            ]
        }
        return jsonify({"status": "success", "config": config})

    # Legacy SVG route for backward compatibility
    @app.route("/api/locus/svg", methods=["GET"])
    def get_locus_svg():
        chrom = request.args.get("chrom", "chr17")
        try:
            start = int(request.args.get("start", 7670000))
            end = int(request.args.get("end", 7678000))
        except ValueError:
            return jsonify({"status": "error", "message": "start and end must be integers."}), 400

        gene = request.args.get("gene", "")
        snv_pos = int(request.args.get("snv_pos")) if request.args.get("snv_pos") else None
        sv_type = request.args.get("sv_type") or None
        sv_start = int(request.args.get("sv_start")) if request.args.get("sv_start") else None
        sv_end = int(request.args.get("sv_end")) if request.args.get("sv_end") else None

        svg_content = generate_locus_svg(
            chrom=chrom,
            start=start,
            end=end,
            gene_symbol=gene,
            snv_pos=snv_pos,
            sv_type=sv_type,
            sv_start=sv_start,
            sv_end=sv_end
        )
        return Response(svg_content, mimetype="image/svg+xml")

    # -------------------------------------------------------------
    # Clinical Diagnostic Report REST API
    # -------------------------------------------------------------
    @app.route("/api/reports/<int:case_id>", methods=["GET"])
    def get_report(case_id: int):
        conn = get_db_connection(app.config.get("DB_PATH"))
        summary = get_case_summary(case_id, db_conn=conn)
        if not summary:
            conn.close()
            return jsonify({"status": "error", "message": "Case not found."}), 404

        cursor = conn.cursor()
        # Find pathogenic and actionable findings
        cursor.execute("""
            SELECT gene_symbol, hgvs_c, hgvs_p, consequence, vaf, acmg_class, somatic_tier, clinvar_sig
            FROM variants_snv
            WHERE case_id = ? AND (acmg_class IN ('Pathogenic', 'Likely Pathogenic') OR is_actionable = 1)
            ORDER BY acmg_class ASC
        """, (case_id,))
        primary_snvs = [dict(r) for r in cursor.fetchall()]

        cursor.execute("""
            SELECT sv_type, sv_len, genes_affected, clinical_impact, acmg_sv_class, support_reads
            FROM variants_sv
            WHERE case_id = ? AND acmg_sv_class IN ('Pathogenic', 'Likely Pathogenic')
        """, (case_id,))
        primary_svs = [dict(r) for r in cursor.fetchall()]

        cursor.execute("""
            SELECT gene_symbol, region_type, percent_modified, status, clinical_significance
            FROM methylation_regions
            WHERE case_id = ? AND (status LIKE '%Hypermethylated%' OR is_asm = 1)
        """, (case_id,))
        primary_meth = [dict(r) for r in cursor.fetchall()]
        conn.close()

        report_data = {
            "case": summary["case"],
            "qc_metrics": {
                "mean_depth": summary["case"]["mean_depth"],
                "ti_tv_ratio": summary["case"]["ti_tv_ratio"],
                "n50": summary["case"]["n50"],
                "q_score": summary["case"]["q_score"]
            },
            "findings": {
                "actionable_snvs": primary_snvs,
                "structural_variants": primary_svs,
                "epigenetic_markers": primary_meth
            },
            "hospital_clinic_header": {
                "institution": "Hospital Clínic de Barcelona",
                "department": "Servei de Genòmica & Anatomia Patològica",
                "laboratory": "CoreBM - Plataforma de Biologia Molecular",
                "director": "Dr. J.L. Villanueva-Cañas",
                "accreditation": "ISO 15189 Clinical NGS Testing"
            }
        }
        return jsonify({"status": "success", "data": report_data})

    # -------------------------------------------------------------
    # Zero-Copy HTTP 206 Partial Content Genomic Streaming API
    # -------------------------------------------------------------
    @app.route("/api/stream/files/<path:file_path>", methods=["GET"])
    def stream_file(file_path: str):
        safe_base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        requested_path = os.path.abspath(os.path.join(safe_base, file_path))
        if not requested_path.startswith(safe_base):
            abort(403, description="Access outside workspace is forbidden.")
        from .streamer import stream_genomic_file
        return stream_genomic_file(requested_path)

    # -------------------------------------------------------------
    # Calibrated ACMG Bayesian Evidence Breakdown API
    # -------------------------------------------------------------
    @app.route("/api/variants/snv/<int:snv_id>/acmg_evidence", methods=["GET"])
    def get_snv_acmg_evidence(snv_id: int):
        conn = get_db_connection(app.config.get("DB_PATH"))
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM variants_snv WHERE id = ?", (snv_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return jsonify({"status": "error", "message": "Variant not found"}), 404
        from .acmg_engine import ACMGEngine
        classification_result = ACMGEngine.classify(dict(row))
        return jsonify({"status": "success", "variant": dict(row), "acmg_details": classification_result})

    # -------------------------------------------------------------
    # Long-Read Phasing & Compound Heterozygosity API
    # -------------------------------------------------------------
    @app.route("/api/phasing/compound_het", methods=["GET"])
    def get_compound_het():
        case_id_str = request.args.get("case_id", "1")
        case_id = int(case_id_str) if case_id_str.isdigit() else 1
        conn = get_db_connection(app.config.get("DB_PATH"))
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM variants_snv WHERE case_id = ?", (case_id,))
        variants = [dict(r) for r in cursor.fetchall()]
        conn.close()
        from .phasing_engine import PhasingEngine
        results = PhasingEngine.evaluate_compound_heterozygosity(variants)
        return jsonify({"status": "success", "case_id": case_id, "count": len(results), "compound_heterozygous_pairs": results})

    # -------------------------------------------------------------
    # Tandem Repeat Expansion API (TRGT / Straglr)
    # -------------------------------------------------------------
    @app.route("/api/repeats", methods=["GET"])
    def get_tandem_repeats():
        case_id_str = request.args.get("case_id", "1")
        case_id = int(case_id_str) if case_id_str.isdigit() else 1
        from .tandem_repeats import TandemRepeatEngine
        repeats = [
            TandemRepeatEngine.evaluate_repeat_allele("HTT", 18, 19, "CAG"),
            TandemRepeatEngine.evaluate_repeat_allele("C9orf72", 4, 8, "GGGGCC"),
            TandemRepeatEngine.evaluate_repeat_allele("FMR1", 29, 31, "CGG"),
            TandemRepeatEngine.evaluate_repeat_allele("FXN", 11, 14, "GAA"),
            TandemRepeatEngine.evaluate_repeat_allele("DMPK", 12, 15, "CTG"),
            TandemRepeatEngine.evaluate_repeat_allele("ATXN1", 28, 29, "CAG")
        ]
        return jsonify({"status": "success", "case_id": case_id, "count": len(repeats), "repeat_expansions": repeats})

    # -------------------------------------------------------------
    # Clinical Diagnostic Report HTML/JSON Download API
    # -------------------------------------------------------------
    @app.route("/api/reports/<int:case_id>/download", methods=["GET"])
    def download_report(case_id: int):
        fmt = request.args.get("format", "html").lower()
        conn = get_db_connection(app.config.get("DB_PATH"))
        summary = get_case_summary(case_id, db_conn=conn)
        if not summary:
            conn.close()
            return jsonify({"status": "error", "message": "Case not found."}), 404

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM variants_snv WHERE case_id = ?", (case_id,))
        snvs = [dict(r) for r in cursor.fetchall()]
        cursor.execute("SELECT * FROM variants_sv WHERE case_id = ?", (case_id,))
        svs = [dict(r) for r in cursor.fetchall()]
        cursor.execute("SELECT * FROM methylation_regions WHERE case_id = ?", (case_id,))
        meth = [dict(r) for r in cursor.fetchall()]
        conn.close()

        from .phasing_engine import PhasingEngine
        from .tandem_repeats import TandemRepeatEngine
        from .report_generator import ClinicalReportGenerator

        phased_pairs = PhasingEngine.evaluate_compound_heterozygosity(snvs)
        repeats = [
            TandemRepeatEngine.evaluate_repeat_allele("HTT", 18, 19, "CAG"),
            TandemRepeatEngine.evaluate_repeat_allele("C9orf72", 4, 8, "GGGGCC")
        ]

        report_data = ClinicalReportGenerator.compile_report_data(
            case=summary["case"],
            snvs=snvs,
            svs=svs,
            meth=meth,
            phased_pairs=phased_pairs,
            repeats=repeats
        )

        if fmt == "json":
            return jsonify(report_data)
        else:
            html = ClinicalReportGenerator.render_html_report(report_data)
            return Response(html, mimetype="text/html")

    return app


def main():
    """CLI launcher for local development."""
    port = int(os.environ.get("PORT", 5050))
    host = os.environ.get("HOST", "0.0.0.0")
    app = create_app()
    print("=" * 68)
    print("  🧬 coreBM VARIANT EXPLORER: Long-Read (ONT) Clinical Platform")
    print("=" * 68)
    print(f"\n🚀 Server starting at: http://localhost:{port}")
    print("   Press CTRL+C to stop.\n")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
