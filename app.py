from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'bus_super_rahasia_unimal'

def init_db():
    conn = sqlite3.connect('tiket_bus.db')
    cursor = conn.cursor()
    # Tabel Pengguna
    cursor.execute('''CREATE TABLE IF NOT EXISTS penumpang 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, email TEXT, password TEXT)''')
    # Tabel Jadwal Bus
    cursor.execute('''CREATE TABLE IF NOT EXISTS jadwal 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, asal TEXT, tujuan TEXT, jam TEXT, harga INTEGER)''')
    # Tabel Pesanan
    cursor.execute('''CREATE TABLE IF NOT EXISTS pesanan 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, penumpang_id INTEGER, jadwal_id INTEGER, 
                       nomor_bangku TEXT, nama_penumpang TEXT, nik TEXT, jenis_kelamin TEXT, 
                       metode_bayar TEXT, potongan INTEGER, total_bayar INTEGER, status TEXT)''')
    
    # Akun Demo Otomatis
    cursor.execute("SELECT COUNT(*) FROM penumpang")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO penumpang (nama, email, password) VALUES ('Dinda Mutiara', 'dinda@gmail.com', '123')")
    
    # Jadwal default
    cursor.execute("SELECT COUNT(*) FROM jadwal")
    if cursor.fetchone()[0] == 0:
        jadwal_awal = [
            ('Lhokseumawe', 'Langsa', '08:00 WIB', 100000),
            ('Lhokseumawe', 'Medan', '10:00 WIB', 180000),
            ('Langsa', 'Medan', '14:00 WIB', 90000)
        ]
        cursor.executemany("INSERT INTO jadwal (asal, tujuan, jam, harga) VALUES (?, ?, ?, ?)", jadwal_awal)
    conn.commit()
    conn.close()

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
        conn = sqlite3.connect('tiket_bus.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO penumpang (nama, email, password) VALUES (?, ?, ?)", (nama, email, password))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
    return render_template('daftar.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # JALAN PINTAS KE DASHBOARD ADMIN
        if email == 'admin@gmail.com' and password == 'admin123':
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
            
        conn = sqlite3.connect('tiket_bus.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM penumpang WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            session['nama'] = user[1]
            return redirect(url_for('jadwal'))
        else:
            return "Email atau Password Salah!"
    return render_template('login.html')

@app.route('/jadwal')
def jadwal():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('tiket_bus.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jadwal")
    list_jadwal = cursor.fetchall()
    conn.close()
    return render_template('jadwal.html', list_jadwal=list_jadwal)

@app.route('/pilih_bangku/<int:jadwal_id>', methods=['GET', 'POST'])
def pilih_bangku(jadwal_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('tiket_bus.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jadwal WHERE id=?", (jadwal_id,))
    detail_jadwal = cursor.fetchone()
    
    if request.method == 'POST':
        nomor_bangku = request.form['nomor_bangku']
        nama_penumpang = request.form['nama_penumpang']
        nik = request.form['nik']
        jenis_kelamin = request.form['jenis_kelamin']
        metode_bayar = request.form['metode_bayar']
        kode_promo = request.form.get('kode_promo', '').strip().upper()
        
        # Logika Voucher Diskon
        harga_asli = detail_jadwal[4]
        potongan = 0
        if kode_promo == 'UNIMALKEREN':
            potongan = 20000
        
        total_bayar = harga_asli - potongan
        user_id = session['user_id']
        
        cursor.execute("""INSERT INTO pesanan (penumpang_id, jadwal_id, nomor_bangku, nama_penumpang, nik, jenis_kelamin, metode_bayar, potongan, total_bayar, status) 
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Lunas')""", (user_id, jadwal_id, nomor_bangku, nama_penumpang, nik, jenis_kelamin, metode_bayar, potongan, total_bayar))
        conn.commit()
        pesanan_id = cursor.lastrowid
        conn.close()
        return redirect(url_for('struk', pesanan_id=pesanan_id))
        
    cursor.execute("SELECT nomor_bangku FROM pesanan WHERE jadwal_id=?", (jadwal_id,))
    bangku_terisi = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    semua_bangku = [f"A{i}" for i in range(1, 6)] + [f"B{i}" for i in range(1, 6)]
    return render_template('pilih_bangku.html', semua_bangku=semua_bangku, bangku_terisi=bangku_terisi, detail_jadwal=detail_jadwal)

@app.route('/struk/<int:pesanan_id>')
def struk(pesanan_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('tiket_bus.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.id, p.nama_penumpang, j.asal, j.tujuan, j.jam, p.total_bayar, p.nomor_bangku, p.metode_bayar, p.status, p.nik, p.jenis_kelamin, p.potongan, j.harga
        FROM pesanan p JOIN jadwal j ON p.jadwal_id = j.id WHERE p.id = ?
    """, (pesanan_id,))
    data_struk = cursor.fetchone()
    conn.close()
    return render_template('struk.html', s=data_struk)

@app.route('/admin')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('tiket_bus.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(total_bayar) FROM pesanan")
    stats = cursor.fetchone()
    cursor.execute("""
        SELECT p.id, p.nama_penumpang, j.asal, j.tujuan, p.nomor_bangku, p.total_bayar, p.metode_bayar 
        FROM pesanan p JOIN jadwal j ON p.jadwal_id = j.id ORDER BY p.id DESC
    """)
    semua_pesanan = cursor.fetchall()
    conn.close()
    return render_template('admin.html', stats=stats, pesanan=semua_pesanan)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)