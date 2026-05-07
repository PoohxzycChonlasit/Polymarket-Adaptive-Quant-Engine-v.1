import asyncio
import logging
from dotenv import load_dotenv

# โหลดค่าจาก .env
load_dotenv()

# ตั้งค่า Logging ให้อ่านง่าย
logging.basicConfig(level=logging.INFO, format="%(message)s")

from polymarket.client import PolymarketClient

def main():
    print("=" * 50)
    print("🔍 กำลังทดสอบเชื่อมต่อและดึงยอดเงินจาก Polymarket...")
    print("=" * 50)
    
    client = PolymarketClient()
    
    try:
        # เชื่อมต่อเพื่อโหลด Credentials
        client.connect()
        
        # ดึงยอดเงิน (จะเช็คทั้งจาก CLOB และ On-chain ตาม logic)
        balance = client.get_usdc_balance()
        
        print("\n" + "=" * 50)
        print(f"✅ สำเร็จ! ยอดเงินคงเหลือของคุณคือ: ${balance:.4f} USDC")
        print("=" * 50)
        
    except Exception as e:
        print("\n❌ เกิดข้อผิดพลาดในการดึงยอดเงิน:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
