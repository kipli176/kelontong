from io import BytesIO
from flask import Flask, render_template, request, jsonify, g, send_file
import psycopg2
from psycopg2 import pool
from datetime import datetime
import requests
import openpyxl
from openpyxl.utils import get_column_letter
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

app = Flask(__name__)

# ==========================
# KONFIGURASI DATABASE
# ==========================
DB_CONFIG = {
    "host": "postgres",
    "port": 5432,
    "dbname": "iin",
    "user": "kipli_user",
    "password": "kipli_password"
}

db_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=20,
    **DB_CONFIG
)

def get_db():
    if "db_conn" not in g:
        g.db_conn = db_pool.getconn()
    return g.db_conn

@app.teardown_appcontext
def close_db(exception=None):
    db_conn = g.pop("db_conn", None)
    if db_conn is not None:
        db_pool.putconn(db_conn)

def _fetch_today_details():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT tx8, tanggal, pembeli, no_hp,
               item_nama, qty, harga_jual, potongan, subtotal
        FROM v_penjualan_detail_hari_ini
        WHERE penjualan_id = %s
        ORDER BY item_nama
    """)
    rows = cur.fetchall()
    cur.close()
    # columns: id, tx8, tanggal, pembeli, no_hp, item_nama, qty, harga_jual, potongan, subtotal
    return rows

# ==========================
# ROUTE HTML
# ==========================
@app.route("/")
def kasir():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, nama, no_hp FROM pembeli ORDER BY nama")
    pembeli = cur.fetchall()
    cur.close()
    return render_template("kasir.html", pembeli=pembeli)

@app.route("/penjualan-hari-ini")
def penjualan_hari_ini():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, tanggal, tx8, nama, no_hp, total, laba
        FROM v_penjualan_hari_ini
        WHERE DATE(tanggal) = CURRENT_DATE
        ORDER BY tanggal DESC
    """)
    rows = cur.fetchall()

    cur.close()
    return render_template("penjualan_hari_ini.html", rows=rows)


@app.route("/penjualan-hari-ini/export/xlsx")
def export_hari_ini_xlsx():
    rows = _fetch_today_details()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Penjualan Hari Ini"

    headers = ["No Tx", "Waktu", "Pembeli", "HP", "Item", "Qty", "Harga Jual", "Potongan", "Subtotal"]
    ws.append(headers)

    gtotal = 0
    for r in rows:
        _, tx8, tgl, pembeli, hp, item, qty, hj, pot, sub = r
        gtotal += float(sub or 0)
        ws.append([
            f"TX-{tx8.upper()}",
            tgl.strftime("%Y-%m-%d %H:%M:%S"),
            pembeli, hp, item, qty,
            float(hj), float(pot or 0), float(sub)
        ])

    # baris kosong + GRAND TOTAL
    ws.append([])
    ws.append(["", "", "", "", "", "", "", "GRAND TOTAL", gtotal])

    # tebal untuk label total
    from openpyxl.styles import Font
    ws.cell(ws.max_row, 8).font = Font(bold=True)
    ws.cell(ws.max_row, 9).font = Font(bold=True)

    for col in range(1, len(headers)+1):
        ws.column_dimensions[get_column_letter(col)].width = 16

    bio = BytesIO()
    wb.save(bio); bio.seek(0)
    filename = f"penjualan_hari_ini_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(bio, as_attachment=True, download_name=filename,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


from datetime import datetime, timedelta
from flask import request, render_template, jsonify, send_file
from io import BytesIO
import openpyxl
from openpyxl.utils import get_column_letter

# ---------- Helper query ----------
def _parse_date(s, default):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except:
        return default

def _fetch_laporan_harian(d1, d2):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT tgl, jumlah_transaksi, total_penjualan, total_laba
        FROM v_laporan_harian
        WHERE tgl BETWEEN %s AND %s
        ORDER BY tgl DESC
    """, (d1, d2))
    rows = cur.fetchall()
    cur.close()
    # rows: (tgl, jumlah_transaksi, total_penjualan, total_laba)
    return rows

def _fetch_laporan_per_barang(d1, d2):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT barcode, nama,
               SUM(qty_total) AS qty_total,
               SUM(omzet)     AS omzet,
               SUM(laba)      AS laba
        FROM v_laporan_per_barang_harian
        WHERE tgl BETWEEN %s AND %s
        GROUP BY barcode, nama
        ORDER BY omzet DESC NULLS LAST, nama
    """, (d1, d2))
    rows = cur.fetchall()
    cur.close()
    # rows: (barcode, nama, qty_total, omzet, laba)
    return rows

# ---------- Halaman laporan (HTML) ----------
@app.route("/laporan")
def laporan():
    # default: 7 hari terakhir
    today = datetime.now().date()
    start_default = today - timedelta(days=6)
    start = request.args.get("start", start_default.strftime("%Y-%m-%d"))
    end   = request.args.get("end",   today.strftime("%Y-%m-%d"))
    return render_template("laporan.html", start=start, end=end)

# ---------- API data untuk tabel (AJAX) ----------
@app.route("/api/laporan/harian")
def api_laporan_harian():
    today = datetime.now().date()
    d1 = _parse_date(request.args.get("start", ""), today - timedelta(days=6))
    d2 = _parse_date(request.args.get("end",   ""), today)
    rows = _fetch_laporan_harian(d1, d2)
    gtotal = sum((r[2] or 0) for r in rows)
    glaba  = sum((r[3] or 0) for r in rows)
    data = [{"tgl": r[0].strftime("%Y-%m-%d"),
             "jumlah": int(r[1] or 0),
             "total": float(r[2] or 0),
             "laba": float(r[3] or 0)} for r in rows]
    return jsonify({"rows": data, "gtotal": gtotal, "glaba": glaba})

@app.route("/api/laporan/per-barang")
def api_laporan_per_barang():
    today = datetime.now().date()
    d1 = _parse_date(request.args.get("start", ""), today - timedelta(days=6))
    d2 = _parse_date(request.args.get("end",   ""), today)
    q  = (request.args.get("q") or "").strip().lower()

    rows = _fetch_laporan_per_barang(d1, d2)
    items = [{"barcode": r[0], "nama": r[1], "qty": int(r[2] or 0),
              "omzet": float(r[3] or 0), "laba": float(r[4] or 0)} for r in rows]

    # filter sederhana di server (opsional; bisa juga filter di client)
    if q:
        items = [x for x in items
                 if (q in (x["barcode"] or "").lower()
                     or q in (x["nama"] or "").lower())]
    return jsonify({"rows": items})

# ---------- Export Excel (rekap harian) ----------
@app.route("/laporan/export/xlsx")
def export_laporan_xlsx():
    today = datetime.now().date()
    d1 = _parse_date(request.args.get("start", ""), today - timedelta(days=6))
    d2 = _parse_date(request.args.get("end",   ""), today)
    rows = _fetch_laporan_harian(d1, d2)
    gtotal = sum((r[2] or 0) for r in rows)
    glaba  = sum((r[3] or 0) for r in rows)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rekap Harian"
    headers = ["Tanggal", "Jumlah Transaksi", "Total Penjualan", "Total Laba"]
    ws.append(headers)

    for r in rows:
        ws.append([
            r[0].strftime("%Y-%m-%d"),
            int(r[1] or 0),
            float(r[2] or 0),
            float(r[3] or 0)
        ])

    ws.append([])
    ws.append(["", "GRAND TOTAL", gtotal, glaba])

    from openpyxl.styles import Font
    ws.cell(ws.max_row, 2).font = Font(bold=True)
    ws.cell(ws.max_row, 3).font = Font(bold=True)
    ws.cell(ws.max_row, 4).font = Font(bold=True)

    for col in range(1, len(headers)+1):
        ws.column_dimensions[get_column_letter(col)].width = 22

    bio = BytesIO()
    wb.save(bio); bio.seek(0)
    filename = f"laporan_harian_{d1.strftime('%Y%m%d')}_{d2.strftime('%Y%m%d')}.xlsx"
    return send_file(bio, as_attachment=True, download_name=filename,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ==========================
# API SINKRONISASI
# ==========================
@app.route("/api/pembeli")
def api_pembeli():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, nama, COALESCE(no_hp,'') FROM pembeli ORDER BY nama")
    rows = cur.fetchall()
    cur.close()
    # return JSON: [{id:1, nama:"...", no_hp:"..."}, ...]
    return jsonify([{"id": r[0], "nama": r[1], "no_hp": r[2]} for r in rows])

@app.route("/api/sync-pembeli", methods=["POST"])
def sync_pembeli():
    """
    Terima pembeli baru dari frontend offline.
    JSON: { "nama": "Budi", "no_hp": "62812345678", "alamat": "Jl. Mawar" }
    """
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO pembeli (nama, no_hp, alamat)
            VALUES (%s, %s, %s)
            ON CONFLICT (no_hp) DO UPDATE
            SET nama = EXCLUDED.nama,
                alamat = EXCLUDED.alamat
            RETURNING id
        """, (data.get("nama"), data.get("no_hp"), data.get("alamat")))
        new_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({"status": "ok", "id": new_id})
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "msg": str(e)}), 500
    finally:
        cur.close()

@app.route("/api/sync-transaksi", methods=["POST"])
def sync_transaksi():
    """
    Terima transaksi dari frontend offline.
    JSON:
    {
      "client_tx_id": "uuid-string",
      "tanggal_client": "2025-09-14T12:34:00",
      "pembeli": 1,
      "metode_bayar": "tunai",
      "bayar": 50000,
      "kembalian": 6500,
      "items": [
        {"barcode":"123", "nama":"Gula", "qty":2, "harga_jual":15000, "harga_beli":12000, "potongan":0}
      ]
    }
    """
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor()
    try:
        # Cek apakah transaksi sudah pernah masuk (idempotent)
        cur.execute("SELECT id FROM penjualan WHERE client_tx_id=%s", (data["client_tx_id"],))
        if cur.fetchone():
            return jsonify({"status": "duplicate", "msg": "Transaksi sudah ada"})

        # Insert header
        cur.execute("""
            INSERT INTO penjualan (client_tx_id, tanggal, pembeli_id, metode_bayar, bayar, kembalian)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            data["client_tx_id"],
            datetime.fromisoformat(data.get("tanggal_client")),
            data.get("pembeli"),
            data.get("metode_bayar"),
            data.get("bayar"),
            data.get("kembalian"),
        ))
        penjualan_id = cur.fetchone()[0]

        # Insert detail
        for item in data.get("items", []):
            cur.execute("""
                INSERT INTO penjualan_detail
                (penjualan_id, barcode, nama, qty, harga_jual, harga_beli, potongan)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                penjualan_id,
                item["barcode"],
                item["nama"],
                item["qty"],
                item["harga_jual"],
                item["harga_beli"],
                item.get("potongan",0)
            ))

        conn.commit()
        return jsonify({"status": "ok", "id": penjualan_id})
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "msg": str(e)}), 500
    finally:
        cur.close()


@app.route("/api/send-wa", methods=["POST"])
def api_send_wa():
    """
    Proxy ke https://blast.sukipli.work/send-message agar tidak CORS.
    Body JSON: { "number": "62xxxxxxxxxx", "message": "..." }
    """
    payload = request.get_json() or {}
    number = (payload.get("number") or "").strip()
    message = (payload.get("message") or "").strip()

    # validasi sederhana
    if not number or not message:
        return jsonify({"status": "error", "msg": "number & message wajib"}), 400
    if not number.startswith("62") or not number.isdigit():
        return jsonify({"status": "error", "msg": "format nomor harus 62..."}), 400

    try:
        r = requests.post(
            "https://blast.sukipli.work/send-message",
            json={"number": number, "message": message},
            timeout=10,
        )
        # teruskan status dan isi dari server WA
        try:
            return jsonify(r.json()), r.status_code
        except ValueError:
            return r.text, r.status_code, {"Content-Type": r.headers.get("Content-Type", "text/plain")}
    except Exception as e:
        return jsonify({"status": "error", "msg": f"gagal kirim WA: {e}"}), 502

@app.route("/api/penjualan/<int:pid>")
def api_penjualan_detail(pid):
    conn = get_db()
    cur = conn.cursor()
    try:
        # header
        cur.execute("""
            SELECT p.id, p.tanggal, p.metode_bayar, p.bayar, p.kembalian,
                   COALESCE(pb.nama,''), COALESCE(pb.no_hp,'')
            FROM penjualan p
            LEFT JOIN pembeli pb ON pb.id = p.pembeli_id
            WHERE p.id = %s
        """, (pid,))
        h = cur.fetchone()
        if not h:
            return jsonify({"status":"error","msg":"not found"}), 404

        header = {
            "id": h[0],
            "id_hex": f"{h[0]:08x}",
            "tanggal": h[1].isoformat(),
            "metode_bayar": h[2],
            "bayar": float(h[3] or 0),
            "kembalian": float(h[4] or 0),
            "pembeli_nama": h[5],
            "no_hp": h[6],
        }

        # items
        cur.execute("""
            SELECT nama, qty, harga_jual, harga_beli, potongan
            FROM penjualan_detail
            WHERE penjualan_id = %s
            ORDER BY id
        """, (pid,))
        items = []
        for r in cur.fetchall():
            items.append({
                "nama": r[0],
                "qty": int(r[1]),
                "harga_jual": float(r[2]),
                "harga_beli": float(r[3]),
                "potongan": float(r[4] or 0)
            })

        return jsonify({ "header": header, "items": items })
    finally:
        cur.close()

# ==========================
# MAIN
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
