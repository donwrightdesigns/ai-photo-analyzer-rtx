# AI Image Analyzer: Large-Library Culling and Metadata Plan

Last updated: 2025-10-13

Objective
- Run across very large photo libraries to: (1) cull best images, (2) auto-apply structured keywords/categories/ratings, (3) embed Lightroom- and web-friendly metadata, without redundant work.

Key additions (practical, low-risk)
1) Hierarchical keywords end‑to‑end
- Prompting: require “Category > Subcategory > Detail, …” (OBtagger pattern)
- Parsing: split by ", ", then split each by " > ", trim/dedupe
- Metadata writing:
  - Flat tags: IPTC:Keywords, XMP-dc:Subject (for gallery compatibility)
  - Hierarchy: XMP-lr:HierarchicalSubject (for Lightroom native hierarchy)

2) Catalog + resumability (SQLite)
- Track files(path, size, mtime, hash_xxh3, first_seen, last_seen)
- Track results(file_id, model_id, quality_score, tags_json, rating, wrote_metadata_at)
- Use (size, mtime, hash) to skip unchanged; process in chunks; resume cleanly

3) Batch governor + ETA in GUI
- Surface batch size, delay, concurrency, predicted ETA
- Add Pause/Resume and Dry‑Run (analyze only) + CSV export

4) Two‑pass culling that scales with folder structure
- Per‑folder top‑percent (or top N) selection to ensure coverage of each shoot
- Pre‑filter: BRISQUE/fallback + fast blur metric + EXIF heuristics (ISO/shutter penalties)

5) Provider selection + preflight (OBtagger‑style)
- Test Ollama button; Test Gemini key button; show status in header (OK/Not configured)

6) Metadata throughput and safety
- Use PyExifTool in batch mode, write in small groups; retry with backoff if locked
- Prefer XMP sidecar when EXIF write fails (RAW workflows)

Lightroom & Web field mapping (recommended)
- XMP-lr:HierarchicalSubject = ["Nature|Wildlife|Birds|Eagles", …]
- XMP-dc:Subject = ["Nature","Wildlife","Birds","Eagles", …]
- IPTC:Keywords = same flat set as above
- EXIF:Rating = 1–5 (clamped)
- EXIF:ImageDescription = short caption (optional)

Mapping to current code
- pipeline_core.py
  - ImageCurationEngine.curate_images_by_quality: add per‑folder top selection + blur/EXIF heuristic
  - MetadataPersistenceLayer.write_embedded_metadata: add XMP‑lr hierarchical write
  - MultiStageProcessingPipeline.process_directory: chunking, resumability hooks via catalog
- ai_image_analyzer_gui.py
  - Header: batch governor + ETA + provider status checks; Dry‑Run toggle; Pause/Resume
  - Settings: enable hierarchical keywords; choose separator; per‑folder top‑N/percent
- New module catalog.py: SQLite wrapper for files/results/models/runs
- Prompt presets: small module or JSON presets (sports, nature, architecture)

Throughput tips
- Keep AI input resized to ≤1024px max dimension
- Small GPU worker queue; rate‑limit via Load Profile
- Batch metadata writes (20–50 files) where safe; commit per chunk

Next steps (pick one to start)
- A) Hierarchical keywords + metadata write + one preset + GUI toggle (fastest visible win)
- B) SQLite resumability + per‑folder top selection (biggest win for huge archives)
- C) Provider preflight + GUI status, then catalog

Notes from OBtagger to adopt
- Provider factory + connection tests and status in UI
- Genre‑specific prompt presets
- Hierarchical keyword instruction and storage
