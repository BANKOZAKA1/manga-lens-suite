# คู่มือติดตั้ง MangaLens Suite บน vivo X200 Pro (OriginOS China)

## 1. ติดตั้ง APK โดยไม่ทับแอปเดิม

ติดตั้ง `MangaLens-Overlay-1.0.0-arm64-v8a.apk` และ
`MangaLens-Reader-1.0.0-arm64-v8a.apk` จาก `artifacts/` ทั้งสองใช้ package name
ใหม่ จึงติดตั้งข้าง Mihon และ MangaLens v0.2 เดิมได้ ข้อมูล Mihon ให้นำเข้าผ่าน
ไฟล์ backup จากหน้า Settings ของ Reader ห้ามคัดลอกฐานข้อมูลแอปโดยตรง

APK ทั้งสองลงนามด้วย release key เดียวกันซึ่งเก็บที่ `F:\AI\MangaLens\signing`;
ต้องสำรองทั้ง `mangalens-release.jks` และ `signing.json` ถ้าคีย์หายจะอัปเดตทับแอปเดิมไม่ได้

## 2. สิทธิ์ที่ OriginOS ต้องเปิด

ใน App info ของ MangaLens Overlay เปิด:

1. Display over other apps / Floating window
2. Notifications
3. Auto start
4. Background high power consumption และ Unrestricted battery
5. อนุญาต MediaProjection เมื่อ Android แสดงหน้าต่าง Share/Capture screen

ถ้า Overlay ถูกปิดเมื่อดับจอ ให้ล็อกแอปไว้ใน Recent apps และตรวจ iManager >
Battery > Background power consumption อีกครั้ง Shizuku เป็นตัวเลือกเพื่อช่วย recovery
และการควบคุม overlay เท่านั้น ไม่ได้ใช้หลบ `FLAG_SECURE` หรือ DRM

## 3. โหมดมือถือ (Balanced Auto)

เลือก preset Japanese → Thai หรือ Korean → Thai แล้วกด Start แอปจะรอภาพนิ่ง,
ตรวจ page change และข้ามภาพ hash ซ้ำ ค่าเริ่มต้นใช้ OCR/ML Kit บนเครื่องและไม่ต้องมี
API key แตะ SFX ที่ต้องการแปลเป็นรายจุดเพื่อไม่ให้หน้ารก

## 4. ติดตั้ง HQ Server บน PC

เปิด PowerShell ในโฟลเดอร์ suite แล้วรัน:

```powershell
.\scripts\Install-HqRuntime.ps1
.\scripts\Start-HqServer.ps1
```

ขั้นแรกดาวน์โหลด Ollama จากเว็บทางการและ `translategemma:4b` ไป F: (ประมาณหลาย GB)
ครั้งแรกจึงใช้เวลานาน จากนั้น launcher แสดง Base URL, pairing token และไฟล์ QR ที่
`F:\AI\MangaLens\server\pairing.png` โทรศัพท์กับ PC ต้องอยู่ Wi-Fi/LAN เดียวกัน
และ Windows Firewall ต้องอนุญาต TCP 8765 เฉพาะ Private network

launcher จะรอจนทั้ง gateway และ image worker พร้อมจริงก่อนแสดง `Ready: True` โดย
โมเดลภาพ, Hugging Face cache, Ollama และผลทดสอบทั้งหมดอยู่ใต้ `F:\AI\MangaLens`
PyThaiNLP แบ่งคำไทยแบบออฟไลน์ จึงไม่มีค่า API และไม่ส่งข้อความไปบริการภายนอก

ใน Overlay/Reader ตั้ง provider เป็น Custom/OpenAI-compatible:

- Base URL: ค่าที่ launcher แสดง ลงท้ายด้วย `/v1`
- Model: `translategemma:4b`
- API key: pairing token (เป็น token ภายในบ้าน ไม่ใช่ Google/OpenAI key)

หยุด server ด้วย:

```powershell
.\scripts\Stop-HqServer.ps1
```

ภาพต้นฉบับและผลลัพธ์อยู่ใน RAM ของ gateway และหมดอายุหลัง 30 นาทีโดยค่าเริ่มต้น
โมเดล/cache อยู่ `F:\AI\MangaLens` ห้ามเปิดพอร์ต 8765 ออกอินเทอร์เน็ต

## 5. ความหมายของ Circle-like

MangaLens ให้ประสบการณ์จับหน้าจอแล้วแปลทับคล้าย Circle to Search แต่ไม่ใช่และไม่สามารถ
แทน Google system integration ของ Global ROM ได้ เนื้อหาที่แอปต้นทางตั้ง `FLAG_SECURE`
จะจับภาพไม่ได้ตามข้อจำกัดของ Android
