# MangaLens HQ Server

The public gateway is `app.py`. It exposes only the `/v1` contract on the selected
private LAN address. `mit_runner.py` keeps both manga-image-translator processes on
`127.0.0.1`; original uploads and translated PNGs are held in RAM and expire after
30 minutes.

The pairing token is stored outside Git at
`F:\AI\MangaLens\server\pairing-token.txt`. Ollama stays on loopback and serves
the OpenAI-compatible `translategemma:4b` endpoint used by both the APK provider
and the HQ image engine.

The worker bootstrap applies narrowly scoped compatibility fixes without editing
the pinned upstream tree: loopback binary transport, OpenCV large-canvas scaling,
Thai fit-to-balloon rendering, and PyThaiNLP word segmentation. Health becomes
ready only after the inner image worker is reachable.

Run from the suite root:

```powershell
.\scripts\Start-HqServer.ps1
```

Test the gateway-only code without loading models:

```powershell
F:\AI\manga-image-translator-runtime\.venv\Scripts\python.exe -m unittest discover server
```

Run one real-image smoke test (the image is not copied into Git):

```powershell
.\scripts\Smoke-HqPage.ps1 -ImagePath F:\private\page.jpg -SourceLanguage ja
```
