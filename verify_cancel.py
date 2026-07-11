import sqlite3
import sys
sys.path.insert(0, r'c:/Users/LENOVO/Documents/tiket-web')
import app

conn = sqlite3.connect('tiket_bus.db')
cur = conn.cursor()
cur.execute("DELETE FROM pesanan WHERE id > 0")
cur.execute("INSERT INTO pesanan (penumpang_id,jadwal_id,nomor_bangku,nama_penumpang,nik,jenis_kelamin,metode_bayar,potongan,total_bayar,status,created_at) VALUES (1,1,'A9','Test','1234567890123456','Laki-laki','Transfer Bank',0,100000,'Menunggu Pembayaran', datetime('now','-11 minutes'))")
conn.commit()
app.auto_cancel_expired_payments()
cur.execute("SELECT status FROM pesanan WHERE nomor_bangku='A9'")
print(cur.fetchone()[0])
conn.close()
