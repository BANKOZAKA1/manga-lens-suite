# MangaLens Suite 1.0.0

รุ่นแรกของ MangaLens Suite สำหรับแปล Manga/Manhwa เป็นภาษาไทยบน vivo X200 Pro / OriginOS

## ไฟล์ติดตั้ง

- `MangaLens-Overlay-1.0.0-arm64-v8a.apk` — แปลแบบลอยทับแอปอื่นด้วย MediaProjection
- `MangaLens-Reader-1.0.0-arm64-v8a.apk` — Reader ที่แปลจากภาพต้นฉบับและเตรียมหน้าถัดไปล่วงหน้า
- `SHA256SUMS.txt` — ค่า SHA-256 สำหรับตรวจสอบไฟล์ APK

APK ทั้งสองรองรับเฉพาะ `arm64-v8a` และลงนามสำหรับรุ่น Release แล้ว

## สิ่งที่มีในรุ่นนี้

- โหมด Balanced บนอุปกรณ์และโหมด HQ ผ่าน LAN
- OCR ญี่ปุ่น เกาหลี และจีน พร้อมเป้าหมายภาษาไทย
- การลบข้อความเดิม วางข้อความไทย glossary และ translation memory
- ตรวจจับภาพนิ่ง/เปลี่ยนหน้า cache และ fallback เมื่อ HQ server หลุด
- Windows HQ server, launcher, health check และ benchmark harness
- คู่มือติดตั้งภาษาไทยสำหรับ OriginOS

## สถานะการตรวจสอบ

- Android unit tests ผ่านทั้ง Overlay และ Reader
- HQ server tests ผ่าน 9 รายการ
- APK signature v2, package name และ ABI ผ่านการตรวจสอบ
- ผล smoke test อยู่ใน `benchmark/results/smoke-2026-08-23.json`

รุ่นนี้ยังไม่ถือว่าผ่าน benchmark 60 หน้าและการทดสอบจริงครบตาม release gate ทั้งหมด โปรดอ่าน `docs/IMPLEMENTATION-STATUS.md` ก่อนใช้งาน

## ความเป็นส่วนตัว

HQ server เปิดใช้งานเฉพาะ LAN, ใช้ pairing token และไม่เก็บภาพถาวรโดยค่าเริ่มต้น ไม่มี API key หรือ signing key อยู่ใน repository หรือ APK release assets
