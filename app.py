from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'bus_super_rahasia_unimal'

DB_PATH = 'tiket_bus.db'


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    return conn


def auto_cancel_expired_payments():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE pesanan
            SET status = 'Dibatalkan'
            WHERE status = 'Menunggu Pembayaran'
              AND created_at <= datetime('now', '-10 minutes')
            """
        )


def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS penumpang (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nama TEXT,
                email TEXT,
                password TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jadwal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asal TEXT,
                tujuan TEXT,
                jam TEXT,
                harga INTEGER
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pesanan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                penumpang_id INTEGER,
                jadwal_id INTEGER,
                nomor_bangku TEXT,
                nama_penumpang TEXT,
                nik TEXT,
                jenis_kelamin TEXT,
                metode_bayar TEXT,
                potongan INTEGER,
                total_bayar INTEGER,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tambah kolom created_at jika belum ada
        try:
            cursor.execute("SELECT created_at FROM pesanan LIMIT 1")
        except:
            cursor.execute("ALTER TABLE pesanan ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

        cursor.execute("SELECT COUNT(*) FROM penumpang")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO penumpang (nama, email, password) VALUES (?, ?, ?)",
                ('Dinda Mutiara', 'dinda@gmail.com', '123')
            )

        cursor.execute("SELECT COUNT(*) FROM jadwal")
        if cursor.fetchone()[0] == 0:
            jadwal_awal = [
                ('Lhokseumawe', 'Langsa', '08:00 WIB', 100000),
                ('Lhokseumawe', 'Medan', '10:00 WIB', 180000),
                ('Langsa', 'Medan', '14:00 WIB', 90000),
            ]
            cursor.executemany(
                "INSERT INTO jadwal (asal, tujuan, jam, harga) VALUES (?, ?, ?, ?)",
                jadwal_awal,
            )


init_db()


@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/daftar', methods=['GET', 'POST'])
def daftar():
    if request.method == 'POST':
        nama = request.form['nama']
        email = request.form['email']
        password = request.form['password']

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO penumpang (nama, email, password) VALUES (?, ?, ?)",
                (nama, email, password),
            )

        return redirect(url_for('login'))

    return render_template('daftar.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if email == 'admin@gmail.com' and password == 'admin123':
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM penumpang WHERE email=? AND password=?",
                (email, password),
            )
            user = cursor.fetchone()

        if user:
            session['user_id'] = user[0]
            session['nama'] = user[1]
            return redirect(url_for('jadwal'))

        return "Email atau Password Salah!"

    return render_template('login.html')


@app.route('/jadwal')
def jadwal():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    #auto_cancel_expired_payments()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jadwal")
        list_jadwal = cursor.fetchall()

        cursor.execute(
            """
            SELECT id, nomor_bangku, nama_penumpang, total_bayar, status, created_at
            FROM pesanan
            WHERE penumpang_id = ?
            ORDER BY id DESC
            """,
            (session['user_id'],),
        )
        riwayat_pesanan = cursor.fetchall()

    return render_template('jadwal.html', list_jadwal=list_jadwal, riwayat_pesanan=riwayat_pesanan)


@app.route('/batal_pesanan/<int:pesanan_id>', methods=['POST'])
def batal_pesanan(pesanan_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM pesanan WHERE id=? AND penumpang_id=? AND status <> 'Dibatalkan'",
            (pesanan_id, session['user_id']),
        )
        pesanan = cursor.fetchone()

        if pesanan:
            cursor.execute(
                "UPDATE pesanan SET status='Dibatalkan' WHERE id=? AND penumpang_id=?",
                (pesanan_id, session['user_id']),
            )

    return redirect(url_for('bukti_pembatalan', pesanan_id=pesanan_id))


@app.route('/pilih_bangku/<int:jadwal_id>', methods=['GET', 'POST'])
def pilih_bangku(jadwal_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jadwal WHERE id=?", (jadwal_id,))
        detail_jadwal = cursor.fetchone()

        cursor.execute("SELECT nomor_bangku FROM pesanan WHERE jadwal_id=? AND status <> 'Dibatalkan'", (jadwal_id,))
        bangku_terisi = [row[0] for row in cursor.fetchall()]

        if detail_jadwal is None:
            return redirect(url_for('jadwal'))

        if request.method == 'POST':
            nomor_bangku = request.form.get('nomor_bangku', '').strip()
            nama_penumpang = request.form.get('nama_penumpang', '').strip()
            nik = request.form.get('nik', '').strip()
            jenis_kelamin = request.form.get('jenis_kelamin', '').strip()
            metode_bayar = request.form.get('metode_bayar', '').strip()
            kode_promo = request.form.get('kode_promo', request.form.get('kode_voucher', '')).strip().upper()

            if not nomor_bangku:
                flash('Pilih kursi terlebih dahulu sebelum melanjutkan pembayaran.')
            elif nomor_bangku in bangku_terisi:
                flash('Maaf, kursi ini sudah terisi. Pilih kursi lain.')
            elif not nama_penumpang or not nik or not jenis_kelamin or not metode_bayar:
                flash('Semua data penumpang wajib diisi.')
            elif not nik.isdigit() or len(nik) != 16:
                flash('NIK harus 16 digit angka.')
            else:
                harga_asli = detail_jadwal[4]
                potongan = 0
                if kode_promo == 'UNIMALKEREN':
                    potongan = 20000
                    flash('Kode promo UNIMALKEREN berhasil diterapkan.')
                elif kode_promo:
                    flash('Kode promo tidak valid.')

                total_bayar = max(harga_asli - potongan, 0)
                user_id = session['user_id']

                cursor.execute(
                    """
                    INSERT INTO pesanan (
                        penumpang_id, jadwal_id, nomor_bangku, nama_penumpang, nik,
                        jenis_kelamin, metode_bayar, potongan, total_bayar, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Menunggu Pembayaran', CURRENT_TIMESTAMP)
                    """,
                    (user_id, jadwal_id, nomor_bangku, nama_penumpang, nik, jenis_kelamin, metode_bayar, potongan, total_bayar),
                )
                pesanan_id = cursor.lastrowid

                return redirect(url_for('bukti_penambahan', pesanan_id=pesanan_id))


    semua_bangku = [f"A{i}" for i in range(1, 6)] + [f"B{i}" for i in range(1, 6)]
    return render_template(
        'pilih_bangku.html',
        semua_bangku=semua_bangku,
        bangku_terisi=bangku_terisi,
        detail_jadwal=detail_jadwal,
    )


@app.route('/bukti_penambahan/<int:pesanan_id>')
def bukti_penambahan(pesanan_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    auto_cancel_expired_payments()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT p.id, p.nama_penumpang, j.asal, j.tujuan, j.jam, p.total_bayar,
                   p.nomor_bangku, p.metode_bayar, p.status, p.nik,
                   p.jenis_kelamin, p.potongan, j.harga, p.created_at, pen.nama
            FROM pesanan p
            JOIN jadwal j ON p.jadwal_id = j.id
            JOIN penumpang pen ON p.penumpang_id = pen.id
            WHERE p.id = ? AND p.penumpang_id = ?
            """,
            (pesanan_id, session['user_id']),
        )
        data_bukti = cursor.fetchone()

    return render_template('bukti_penambahan.html', b=data_bukti)


@app.route('/konfirmasi_pembayaran/<int:pesanan_id>', methods=['POST'])
def konfirmasi_pembayaran(pesanan_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with get_db_connection() as conn:
        cursor = conn.cursor()
        #cursor.execute(
        #    "UPDATE pesanan SET status='Lunas' WHERE id=? AND penumpang_id=? AND status='Menunggu Pembayaran'",
         #   (pesanan_id, session['user_id']),
        #)

    return redirect(url_for('bukti_penambahan', pesanan_id=pesanan_id))


@app.route('/struk/<int:pesanan_id>')
def struk(pesanan_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT p.id, p.nama_penumpang, j.asal, j.tujuan, j.jam, p.total_bayar,
                   p.nomor_bangku, p.metode_bayar, p.status, p.nik,
                   p.jenis_kelamin, p.potongan, j.harga, p.created_at
            FROM pesanan p
            JOIN jadwal j ON p.jadwal_id = j.id
            WHERE p.id = ?
            """,
            (pesanan_id,),
        )
        data_struk = cursor.fetchone()

    return render_template('struk.html', s=data_struk)


@app.route('/admin')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('login'))

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), SUM(total_bayar) FROM pesanan WHERE status <> 'Dibatalkan'")
        stats = cursor.fetchone()

        cursor.execute(
            """
            SELECT p.id, p.nama_penumpang, j.asal, j.tujuan, p.nomor_bangku,
                   p.total_bayar, p.metode_bayar, p.status, p.created_at
            FROM pesanan p
            JOIN jadwal j ON p.jadwal_id = j.id
            WHERE p.status <> 'Dibatalkan'
            ORDER BY p.id DESC
            """
        )
        semua_pesanan = cursor.fetchall()

    return render_template('admin.html', stats=stats, pesanan=semua_pesanan)


@app.route('/bukti_pembatalan/<int:pesanan_id>')
def bukti_pembatalan(pesanan_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT p.id, p.nama_penumpang, j.asal, j.tujuan, j.jam, p.total_bayar,
                   p.nomor_bangku, p.metode_bayar, p.status, p.nik,
                   p.jenis_kelamin, p.potongan, j.harga, p.created_at
            FROM pesanan p
            JOIN jadwal j ON p.jadwal_id = j.id
            WHERE p.id = ? AND p.penumpang_id = ?
            """,
            (pesanan_id, session['user_id']),
        )
        data_bukti = cursor.fetchone()

    return render_template('bukti_pembatalan.html', b=data_bukti, pembatalan_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)