# Implementation status — 2026-08-23

## Delivered and verified

- Release-signed arm64-v8a Overlay and Reader APKs with distinct package names.
- GPL-3.0 source tree, pinned upstream commits, notices, Thai setup guide, build/signing scripts, and SHA-256 artifacts.
- LAN-only authenticated HQ gateway, QR pairing, memory-only jobs, cancellation, WebSocket events, and adaptive fallback contract.
- Official Ollama portable runtime with `translategemma:4b`, CUDA execution on RTX 5060, F-drive model/cache layout, MangaOCR, detector, and LaMa weights.
- End-to-end Japanese page smoke test completed after OCR, translation, cleanup, Thai rendering, and PNG retrieval.
- Two consecutive warmed end-to-end samples completed in 10.470 and 10.877 seconds with byte-identical PNG output; observed peak VRAM was 7,548/8,151 MiB with no OOM.
- Nine Windows gateway unit tests pass; Android release builds, unit tests, R8/lint, APK signatures, ABI, package IDs, and hashes were verified.

## Not yet release-qualified

- The required human-reviewed 60-page (30 Japanese + 30 Korean) benchmark has not been supplied or run.
- Two consecutive passing benchmark rounds, 100 page turns on the vivo X200 Pro, Wi-Fi loss recovery on-device, and 10 extra user pages remain unverified.
- The cold render and warmed render differed by 3.3434% of pixels, although the next two warmed renders were byte-identical; cross-start determinism remains unproven.
- The current smoke page still shows expected unselected SFX and some OCR region fragmentation. It cannot establish the 95% detection, 94% OCR, 4/5 Thai translation, 95% cleanup, or 98% layout targets.
- Source and artifacts are prepared locally under GPL-3.0 but have not been pushed to a public Git host.
