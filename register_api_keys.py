import os
from dotenv import load_dotenv
from py_clob_client_v2.client import ClobClient
from py_clob_client_v2.clob_types import ApiCreds

load_dotenv()

def register():
    pk = os.getenv("POLYMARKET_PRIVATE_KEY")
    if not pk:
        print("❌ ERROR: ไม่พบ POLYMARKET_PRIVATE_KEY ใน .env")
        return

    proxy_wallet = os.getenv("POLYMARKET_PROXY_WALLET")
    funder = proxy_wallet if proxy_wallet else os.getenv("POLYMARKET_FUNDER")
    sig_type = 2 if proxy_wallet else 0
    
    print(f"⏳ กำลังขอดึง API Key สำหรับกระเป๋า: {funder}")
    print(f"   (Signature Type: {sig_type})")

    try:
        client = ClobClient(
            host="https://clob.polymarket.com",
            key=pk,
            chain_id=137,
            signature_type=sig_type,
            funder=funder or None
        )
        
        creds = client.create_or_derive_api_key()
        
        print("\n✅ ได้รับ API Keys เรียบร้อยแล้ว! นำข้อมูลนี้ไปใส่ใน .env ได้เลย:\n")
        print(f"POLYMARKET_API_KEY={creds.api_key}")
        print(f"POLYMARKET_API_SECRET={creds.api_secret}")
        print(f"POLYMARKET_API_PASSPHRASE={creds.api_passphrase}")
        
    except Exception as e:
        print(f"\n❌ ยังคงเกิดข้อผิดพลาด: {e}")
        print("\nคำแนะนำสุดท้าย: กรุณาเปิด VPN ไปที่ 'สิงคโปร์' แล้วลองรันใหม่อีกรอบครับ")

if __name__ == "__main__":
    register()
