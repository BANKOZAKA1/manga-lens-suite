# MangaLens benchmark

เก็บภาพลิขสิทธิ์จริงใน `private/` เท่านั้น (โฟลเดอร์นี้ไม่เข้า Git) ชุด release ต้องมี
อย่างน้อย 60 หน้า: ญี่ปุ่น 30 และเกาหลี 30 พร้อมอีก 10 หน้าจากผู้ใช้หลังผ่านสองรอบ
ติดกัน

แต่ละรอบบันทึกไฟล์ JSONL ใน `results/` หนึ่งบรรทัดต่อหน้า โดยมีอย่างน้อย:

```json
{"id":"ja-001","language":"ja","expected_regions":12,"detected_regions":12,"ocr_chars":80,"ocr_correct":77,"glossary_ok":true,"translation_score":4.5,"clean_regions":12,"layout_regions":12,"latency_ms":4200,"crash":false}
```

คำนวณเกณฑ์และ regression ด้วย:

```powershell
python .\benchmark\score.py .\benchmark\results\round-01.jsonl
python .\benchmark\score.py .\benchmark\results\round-02.jsonl --baseline .\benchmark\results\round-01.jsonl
```

ห้ามประกาศว่าผ่านเกณฑ์จาก unit test หรือหน้าสังเคราะห์ ต้องตรวจ OCR/คำแปล/พื้นหลังและ
layout กับภาพจริงโดยคนก่อนออก release

