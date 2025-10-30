# Project RULES (AI Image Analyzer)

Purpose
- Ensure changes scale to huge libraries, remain Windows‑native, and keep Lightroom/web compatibility without rework.

Guiding principles
1) Windows‑native first
- No WSL requirements for this app. Use CUDA (PyTorch) and ExifTool for performance/compat.

2) Predictability and preflight
- Add explicit provider checks (Ollama reachable, Gemini key valid) before runs.
- Fail fast with clear, actionable messages; no silent fallbacks that hide misconfig.

3) No surprise model switching
- Never change user’s chosen provider/model behind the scenes. Add options, don’t override.

4) Idempotence and resumability
- Operate safely on huge libraries: catalog (SQLite), chunking, commit checkpoints, resume where left off.
- Skip unchanged files using (size, mtime, xxh3 hash) and versioned prompts/models.

5) Two‑pass culling
- Cheap prefilters (IQA fallback + blur + EXIF heuristics) → expensive AI only on curated subset.
- Support per‑folder top‑percent/top‑N to respect shoot structure.

6) Metadata compatibility
- Write both flat and hierarchical tags:
  - IPTC:Keywords, XMP-dc:Subject (flat)
  - XMP‑lr:HierarchicalSubject (hierarchy)
- Clamp EXIF:Rating 1–5; optional EXIF:ImageDescription caption.
- Prefer XMP sidecar for RAW on write failures; batch small groups; retry with backoff.

7) UX for long runs
- Show batch governor (batch size, delay, concurrency) and live ETA.
- Provide Pause/Resume, Dry‑Run, and CSV export.

8) Performance defaults
- Resize AI inputs to ≤1024px per side.
- Minimize GPU stalls with a small queued worker and Load Profile rate limits.

9) Safety and logging
- Never embed secrets in code. Read keys from env or config store.
- Log decisions (skips, retries, provider status) for auditability.

10) Minimal disruption
- Add features behind toggles; default to today’s behavior.
- Avoid breaking Lightroom/web metadata expectations.

Process for changes
- Document intent (what/why), then implement in small PRs (A/B/C phases recommended).
- Provide a quick test plan (sample folder, Dry‑Run, CSV check, Lightroom readback).
