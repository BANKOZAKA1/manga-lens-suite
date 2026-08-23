# MangaLens Suite

ชุดแปล Manga/Manhwa เป็นภาษาไทยสำหรับ vivo X200 Pro / OriginOS โดยไม่ต้องใช้ Google Cloud API แบบเสียเงิน

## แอปในชุด

- `overlay/` — **MangaLens Overlay**: MediaProjection/Shizuku, OCR ญี่ปุ่น/เกาหลี/จีน, loop เมื่อหน้าจอนิ่ง, glossary, translation memory และการซ่อมพื้นหลังแบบมังงะ
- `reader/` — **MangaLens Reader**: Mihon fork พร้อม DBNet + MangaOCR + AOT-GAN, live translation, แปลตอนที่ดาวน์โหลด และ queue ข้ามหน้า
- `server/` — **MangaLens HQ Server**: LAN gateway สำหรับ TranslateGemma 4B และงานแปลภาพ HQ ผ่าน manga-image-translator

ซอร์สเดิม `../manga-translator` และ `../manga-image-translator` ไม่ถูกเขียนทับ

## ค่าเริ่มต้น

- เป้าหมายภาษาไทย (`th` / `THA`)
- Overlay ใช้ Google ML Kit แบบออฟไลน์ก่อน โดยมี preset ญี่ปุ่น→ไทยและเกาหลี→ไทย
- Reader ใช้ AOT-GAN ลบคำและตั้งค่า SFX เป็นไม่แปลอัตโนมัติ
- โหมด HQ ใช้ `translategemma:4b` ผ่าน Ollama บน PC; โทรศัพท์และ PC ต้องอยู่ LAN เดียวกัน
- โมเดล/cache บน Windows อยู่ที่ `F:\AI\MangaLens`

## Build

เปิด PowerShell ที่โฟลเดอร์นี้แล้วรัน:

```powershell
.\scripts\Build-All.ps1
```

ผลลัพธ์จะอยู่ใน `artifacts/` พร้อมไฟล์ SHA-256 โดย build script ใช้ Android SDK ที่ `M:\android-sdk` และ Gradle cache บน F: เพื่อไม่กินพื้นที่ C:

Reader ปิด telemetry เป็นค่าเริ่มต้น จึง build ได้โดยไม่ต้องมี `google-services.json`; หากเปิด telemetry ให้สร้าง Firebase project ของตัวเองและวางไฟล์ config ส่วนตัวไว้ที่ `reader/app/google-services.json` ซึ่ง Git จะไม่นำขึ้น repository

## HQ server

1. ติดตั้ง Ollama แบบ portable ที่ `F:\AI\MangaLens\ollama` และดาวน์โหลด `translategemma:4b`
2. รัน `.\scripts\Start-HqServer.ps1`
3. เปิด URL ที่แสดงบนมือถือ แล้วใส่ LAN base URL และ pairing token ใน provider แบบ OpenAI-compatible ของทั้งสองแอป

เซิร์ฟเวอร์ bind เฉพาะ LAN, ทุก `/v1/*` endpoint ที่มีข้อมูลต้องใช้ Bearer token และไม่เก็บภาพต้นฉบับถาวรโดยค่าเริ่มต้น

## ข้อจำกัดที่ตั้งใจไว้

- แอปนี้เลียนแบบขั้นตอน Circle to Search สำหรับมังงะ แต่ไม่สามารถแทน system-level Google Circle to Search บน China ROM ได้
- เนื้อหาที่ Android ทำเครื่องหมาย `FLAG_SECURE` จะจับภาพไม่ได้และไม่มีการพยายามหลบ DRM
- ภาพทดสอบที่มีลิขสิทธิ์ต้องอยู่ใน `benchmark/private/` ซึ่งถูก ignore จาก Git
