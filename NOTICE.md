# Third-party notices

MangaLens Suite is distributed under GPL-3.0 because it combines and modifies GPL software.

- MangaLens Reader is based on Yakuyomi and Mihon. Yakuyomi and yakuyomi-engine are GPL-3.0; Mihon is Apache-2.0.
- MangaLens Overlay is based on Screen Translator by ciddwd, licensed Apache-2.0. The modified suite is distributed under GPL-3.0.
- The HQ image pipeline uses manga-image-translator, licensed GPL-3.0.
- NCNN is BSD-3-Clause, ONNX Runtime is MIT, Google ML Kit is subject to Google's SDK terms, and bundled/downloaded model weights retain the licenses documented by their upstream manifests.
- PyThaiNLP 5.3.7 is Apache-2.0 and is used by the Windows HQ renderer for offline Thai word segmentation.
- TranslateGemma is subject to the Gemma terms accepted by the user before download. Its weights are not redistributed in this repository or APKs.

Exact pinned commits are recorded in `UPSTREAM.lock`. Upstream copyright and license files remain in each source tree.

Build-only provenance:

- Android SDK/NDK/CMake are installed separately and are not redistributed.
- llvm-mingw 20260616 is downloaded from the official mstorsjo/llvm-mingw release;
  archive SHA-256: `b9b68a4d276e16fa25802aaba458e4638f64b3884c290aaccdc2d87083b6ca35`.
- Ollama and TranslateGemma weights are downloaded by the user to `F:\AI\MangaLens`;
  neither binary nor weights are committed to or bundled with the APKs.
