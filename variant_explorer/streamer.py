"""
Zero-Copy Genomic File Streamer supporting HTTP 206 Partial Content (Range Requests).
Allows IGV.js and external clients to stream BAM, CRAM, VCF, BigWig, and bedMethyl
files directly via byte-range requests without loading files into server RAM.
"""

import os
import re
from typing import Generator, Optional, Tuple
from flask import Response, request, abort, current_app


def parse_range_header(range_header: str, file_size: int) -> Optional[Tuple[int, int]]:
    """
    Parses an HTTP 'Range: bytes=start-end' header.
    Returns (start, end) byte offsets inclusive, or None if invalid.
    """
    if not range_header or not range_header.startswith("bytes="):
        return None

    range_spec = range_header[6:].strip()
    match = re.match(r"^(\d+)-(\d*)$", range_spec)
    if not match:
        # Suffix byte range: bytes=-500
        suffix_match = re.match(r"^-(\d+)$", range_spec)
        if suffix_match:
            suffix_len = int(suffix_match.group(1))
            start = max(0, file_size - suffix_len)
            return (start, file_size - 1)
        return None

    start = int(match.group(1))
    end_str = match.group(2)
    end = int(end_str) if end_str else file_size - 1

    if start >= file_size or start > end:
        return None

    end = min(end, file_size - 1)
    return (start, end)


def iter_file_chunk(file_path: str, start: int, length: int, chunk_size: int = 65536) -> Generator[bytes, None, None]:
    """Yields chunks of binary data from a file starting at an offset."""
    with open(file_path, "rb") as f:
        f.seek(start)
        remaining = length
        while remaining > 0:
            read_len = min(remaining, chunk_size)
            data = f.read(read_len)
            if not data:
                break
            remaining -= len(data)
            yield data


def stream_genomic_file(file_path: str, mimetype: Optional[str] = None) -> Response:
    """
    Streams a genomic binary file with full HTTP 206 Partial Content support.
    Safely handles arbitrary file sizes (e.g. 100 GB BAMs/CRAMs).
    """
    if not os.path.isfile(file_path):
        abort(404, description=f"Genomic file not found: {os.path.basename(file_path)}")

    file_size = os.path.getsize(file_path)

    # Automatically deduce mimetype if not provided
    if not mimetype:
        ext = file_path.lower()
        if ext.endswith(".bam"):
            mimetype = "application/octet-stream"
        elif ext.endswith(".bai"):
            mimetype = "application/octet-stream"
        elif ext.endswith(".cram") or ext.endswith(".crai"):
            mimetype = "application/octet-stream"
        elif ext.endswith(".vcf.gz") or ext.endswith(".vcf"):
            mimetype = "text/plain"
        elif ext.endswith(".tbi"):
            mimetype = "application/octet-stream"
        elif ext.endswith(".bed.gz") or ext.endswith(".bed"):
            mimetype = "text/plain"
        elif ext.endswith(".bw") or ext.endswith(".bigwig"):
            mimetype = "application/octet-stream"
        elif ext.endswith(".json"):
            mimetype = "application/json"
        else:
            mimetype = "application/octet-stream"

    range_header = request.headers.get("Range", None)

    # 1. Standard full response if no Range header is sent
    if not range_header:
        # For small index files or full downloads
        resp = Response(
            iter_file_chunk(file_path, 0, file_size),
            status=200,
            mimetype=mimetype,
            direct_passthrough=True
        )
        resp.headers["Content-Length"] = str(file_size)
        resp.headers["Accept-Ranges"] = "bytes"
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Range, Origin, Content-Type, Accept"
        resp.headers["Access-Control-Expose-Headers"] = "Content-Range, Content-Length, Accept-Ranges"
        resp.headers["Content-Disposition"] = f'inline; filename="{os.path.basename(file_path)}"'
        return resp

    # 2. Range request: parse offsets
    range_bounds = parse_range_header(range_header, file_size)
    if range_bounds is None:
        # Invalid range -> 416 Range Not Satisfiable
        resp = Response(status=416)
        resp.headers["Content-Range"] = f"bytes */{file_size}"
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp

    start, end = range_bounds
    content_length = end - start + 1

    resp = Response(
        iter_file_chunk(file_path, start, content_length),
        status=206,
        mimetype=mimetype,
        direct_passthrough=True
    )
    resp.headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
    resp.headers["Content-Length"] = str(content_length)
    resp.headers["Accept-Ranges"] = "bytes"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Range, Origin, Content-Type, Accept"
    resp.headers["Access-Control-Expose-Headers"] = "Content-Range, Content-Length, Accept-Ranges"
    resp.headers["Content-Disposition"] = f'inline; filename="{os.path.basename(file_path)}"'
    return resp
