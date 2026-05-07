# Daily Startup Prompt Template

Copy-paste prompt นี้ตอนเริ่มต้น session ใหม่ทุกวัน

---

## Prompt สำหรับ copy ไปใส่ใน Claude Code

```
อ่าน CLAUDE.md และ CURRENT_PROJECT_STATUS.md ก่อนเลย
แล้วอ่าน research/daily/ ไฟล์ล่าสุดด้วย
สรุปให้ฉันฟังสั้นๆ ว่า:
1. ตอนนี้โปรเจคอยู่ที่ไหน
2. มี issue อะไรค้างอยู่
3. วันนี้ควรทำอะไรก่อน
```

---

## Prompt เพิ่มเติมตามสถานการณ์

### ถ้าอยากรันระบบดูสถานะ
```
รัน smoke test 3 วันให้ฉันดูก่อน แล้วเช็ค balance wallet ด้วย
```

### ถ้าจะแก้ strategy
```
ฉันอยากลอง [ไอเดีย] — ช่วยวิเคราะห์ว่ามีผลกับ backtest ยังไง
ก่อนแก้ให้รัน baseline 60d backtest เก็บตัวเลขไว้ก่อน
```

### ถ้าจะเริ่ม paper trading
```
เริ่ม paper trading loop ให้ฉัน — เช็ค MATIC balance ก่อน แล้ว start realtime mode
```

### ถ้าจะดู backtest ผล
```
รัน 60-day backtest แล้วสรุปผลเปรียบกับ baseline (Sharpe 1.18, WinRate 55.9%, MaxDD 10%)
```

### ถ้ามี bug
```
[อธิบาย error / paste traceback]
ช่วย debug และ fix ให้ แล้ว run smoke test ยืนยันด้วย
```

### ปิดวัน / เขียน daily log
```
วันนี้ทำ [สรุปงาน] — ช่วยเขียน research/daily/[วันที่].md ให้ฉันหน่อย
```
