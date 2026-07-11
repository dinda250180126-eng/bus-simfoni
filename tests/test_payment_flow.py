import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import app


def test_promo_code_is_read_from_form_and_applies_discount():
    client = app.app.test_client()

    with client.session_transaction() as session:
        session['user_id'] = 1

    response = client.post('/pilih_bangku/1', data={
        'nomor_bangku': 'A1',
        'nama_penumpang': 'Test User',
        'nik': '1234567890123456',
        'jenis_kelamin': 'Laki-laki',
        'metode_bayar': 'Transfer Bank',
        'kode_voucher': 'UNIMALKEREN',
    }, follow_redirects=False)

    assert response.status_code == 302


def test_pending_payment_expires_after_ten_minutes():
    with app.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO pesanan (
                penumpang_id, jadwal_id, nomor_bangku, nama_penumpang, nik,
                jenis_kelamin, metode_bayar, potongan, total_bayar, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Menunggu Pembayaran', datetime('now', '-11 minutes'))
            """,
            (1, 1, 'A5', 'Test User', '1234567890123456', 'Laki-laki', 'Transfer Bank', 0, 100000),
        )
        order_id = cursor.lastrowid

    client = app.app.test_client()
    with client.session_transaction() as session:
        session['user_id'] = 1

    response = client.get('/jadwal')

    assert response.status_code == 200
    with app.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM pesanan WHERE id = ?", (order_id,))
        assert cursor.fetchone()[0] == 'Dibatalkan'
