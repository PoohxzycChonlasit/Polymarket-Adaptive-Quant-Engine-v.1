import os
import time
from dotenv import load_dotenv
load_dotenv('.env')
from py_clob_client_v2.client import ClobClient

def main():
    pk = os.getenv('POLYMARKET_PRIVATE_KEY')
    proxy = os.getenv('POLYMARKET_PROXY_WALLET')

    client = ClobClient(
        host='https://clob.polymarket.com',
        key=pk,
        chain_id=137,
        signature_type=2,
        funder=proxy
    )
    
    # Generate signature using the current time
    h = client._l1_headers(nonce=None)

    js_code = f"""
// ----------------------------------------------------
// ก๊อปปี้โค้ดด้านล่างทั้งหมดนี้ ไปวางในช่อง Console แล้วกด Enter
// ----------------------------------------------------
fetch('https://clob.polymarket.com/auth/api-key', {{
    method: 'POST',
    headers: {{
        'POLY_ADDRESS': '{h['POLY_ADDRESS']}',
        'POLY_SIGNATURE': '{h['POLY_SIGNATURE']}',
        'POLY_TIMESTAMP': '{h['POLY_TIMESTAMP']}',
        'POLY_NONCE': '{h['POLY_NONCE']}',
        'Content-Type': 'application/json'
    }}
}}).then(r => r.json()).then(console.log);
"""
    print("\n" + "="*60)
    print("🚀 สคริปต์สร้างโค้ดเจาะระบบ Cloudflare สำเร็จแล้ว! 🚀")
    print("="*60)
    print(js_code)

if __name__ == "__main__":
    main()
