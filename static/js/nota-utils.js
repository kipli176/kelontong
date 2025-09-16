
    // ===== Helper ===== 
    function isProbablyAndroid() {
      const ua = navigator.userAgent || navigator.vendor || window.opera;
      const hasTouch = navigator.maxTouchPoints && navigator.maxTouchPoints > 1;
      const isSmallScreen = window.matchMedia("(max-width: 1024px)").matches;

      if (/android/i.test(ua)) return true;
      if (/linux/i.test(ua) && hasTouch && isSmallScreen) return true;
      return false;
    }

    function wrapText(text, width) {
      const lines = [];
      let start = 0;
      while (start < text.length) {
        let end = Math.min(start + width, text.length);
        let line = text.slice(start, end);
        if (end < text.length) {
          const lastSpace = line.lastIndexOf(" ");
          const lastComma = line.lastIndexOf(",");
          const breakPos = Math.max(lastSpace, lastComma);
          if (breakPos > 0) {
            line = line.slice(0, breakPos + 1);
            end = start + breakPos + 1;
          }
        }
        lines.push(line.trimEnd());
        start = end;
      }
      return lines;
    }

    function centerText(text, width) {
      if (!text) return "";
      const space = Math.max(0, Math.floor((width - text.length) / 2));
      return " ".repeat(space) + text;
    }

    function formatLine(left, right, width) {
      left = left.length > width ? left.slice(0, width) : left;
      right = right.length > width ? right.slice(0, width) : right;
      const space = width - left.length - right.length;
      if (space < 1) return left + "\n" + right;
      return left + " ".repeat(space) + right;
    }

    // ===== Nota Base =====
    function generateNotaBase(head, items, toko, width) {
      const notaId = "TX-" + ((head.client_tx_id || "").slice(0, 8).toUpperCase());
      const tanggalStr = new Date(head.tanggal_client || head.tanggal || Date.now())
        .toLocaleString("id-ID");
      const total = items.reduce((a, b) => a + b.qty * b.harga_jual - (b.potongan || 0), 0);

      return {
        toko: { nama: toko.nama || "TOKO", alamat: toko.alamat || "" },
        notaId,
        tanggalStr,
        items: items.map(it => ({
          nama: it.nama,
          qty: it.qty,
          harga: it.harga_jual,
          potongan: it.potongan || 0,
          sub: it.qty * it.harga_jual - (it.potongan || 0),
        })),
        total,
        bayar: head.bayar,
        kembali: head.kembalian,
        metode: head.metode_bayar,
        width
      };
    }

    // ===== Generator ESC/POS =====
    function generateEscposNota(head, items, toko) {
      const encoder = new EscPosEncoder();
      const width = parseInt(localStorage.getItem("paperSize") || "32", 10);
      const nota = generateNotaBase(head, items, toko, width);

      encoder.initialize();
      encoder.align('center').line(nota.toko.nama);
      encoder.align('left').line(nota.toko.alamat);
      encoder.line("-".repeat(width));
      encoder.align('left')
        .line(`Nota: ${nota.notaId}`)
        .line(`Tanggal: ${nota.tanggalStr}`)
        .line("-".repeat(width));

      nota.items.forEach(it => {
        encoder.align('left').line(it.nama);
        encoder.line(formatLine(`${it.qty} x ${fmt(it.harga)}`, fmt(it.sub), width));
        if (it.potongan) {
          encoder.line(formatLine("Potongan", fmt(it.potongan), width));
        }
      });

      encoder
        .line("-".repeat(width))
        .line(formatLine("TOTAL", fmt(nota.total), width))
        .line(formatLine("Bayar", fmt(nota.bayar), width))
        .line(formatLine("Kembali", fmt(nota.kembali), width))
        .line(`Metode: ${nota.metode}`)
        .newline()
        .align('center')
        .line("Terima kasih 🙏")
        .newline();

      return encoder.encode();
    }

    // ===== Generator HTML =====
    function generateNotaHTML(head, items, toko) {
      const width = parseInt(localStorage.getItem("paperSize") || "32", 10);
      const nota = generateNotaBase(head, items, toko, width);

      let html = `<div style="font-family:monospace;white-space:pre;width:${width}ch;">`;
      wrapText(nota.toko.nama, width).forEach(line => { html += centerText(line, width) + "\n"; });
      wrapText(nota.toko.alamat, width).forEach(line => { html += centerText(line, width) + "\n"; });

      html += "-".repeat(width) + "\n";
      html += `Nota: ${nota.notaId}\n`;
      html += `Tanggal: ${nota.tanggalStr}\n`;
      html += "-".repeat(width) + "\n";

      nota.items.forEach(it => {
        wrapText(it.nama, width).forEach(line => { html += line + "\n"; });
        html += formatLine(`${it.qty} x ${fmt(it.harga)}`, fmt(it.sub), width) + "\n";
        if (it.potongan) {
          html += formatLine("Potongan", fmt(it.potongan), width) + "\n";
        }
      });

      html += "-".repeat(width) + "\n";
      html += formatLine("TOTAL", fmt(nota.total), width) + "\n";
      html += formatLine("Bayar", fmt(nota.bayar), width) + "\n";
      html += formatLine("Kembali", fmt(nota.kembali), width) + "\n";
      html += `Metode: ${nota.metode}\n\n`;
      html += centerText("Terima kasih 🙏", width) + "\n";
      html += '<div class="page-break"></div>';
      html += "</div>";
      return html;
    }

    // ===== Generator WA =====
    function generateNotaWA(head, items, toko) {
      const width = parseInt(localStorage.getItem("paperSize") || "32", 10);
      const nota = generateNotaBase(head, items, toko, width);

      let wa = "";
      wa += nota.toko.nama + "\n";
      wa += nota.toko.alamat + "\n";
      wa += "-".repeat(width) + "\n";
      wa += `Nota: ${nota.notaId}\n`;
      wa += `Tanggal: ${nota.tanggalStr}\n`;
      wa += "-".repeat(width) + "\n";

      nota.items.forEach(it => {
        wa += it.nama + "\n";
        wa += formatLine(`${it.qty} x ${fmt(it.harga)}`, fmt(it.sub), width) + "\n";
        if (it.potongan) {
          wa += formatLine("Potongan", fmt(it.potongan), width) + "\n";
        }
      });

      wa += "-".repeat(width) + "\n";
      wa += formatLine("TOTAL", fmt(nota.total), width) + "\n";
      wa += formatLine("Bayar", fmt(nota.bayar), width) + "\n";
      wa += formatLine("Kembali", fmt(nota.kembali), width) + "\n";
      wa += `Metode: ${nota.metode}\n\n`;
      wa += "Terima kasih 🙏\n";
      return wa;
    }

    // ===== API Fetch =====
    async function fetchDetail(id) {
      const r = await fetch(`/api/penjualan/${id}`);
      if (!r.ok) {
        const js = await r.json().catch(() => ({}));
        throw new Error(js.msg || "Gagal ambil data penjualan");
      }
      return await r.json(); // {header, items}
    }

    // ===== Print Nota =====
    function printNota(trx, toko) {
      const isAndroid = isProbablyAndroid();
      console.log("📱 Deteksi Android?", isAndroid, navigator.userAgent);

      if (isAndroid) {
        try {
          const escposData = generateEscposNota(trx, trx.items, toko);
          let binary = '';
          escposData.forEach(b => binary += String.fromCharCode(b));
          const S = "#Intent;scheme=rawbt;";
          const P = "package=ru.a402d.rawbtprinter;end;";
          const intentUrl = "intent:" + encodeURIComponent(binary) + S + P;
          setTimeout(() => { window.open(intentUrl, "_blank"); }, 200);
          console.log("✅ Nota ESC/POS dikirim ke RawBT");
          return;
        } catch (err) {
          console.error("⚠️ Print ke RawBT gagal:", err);
          alert("Print gagal, fallback ke browser");
        }
      }

      // ==== Fallback Desktop ====
      const notaHtml = generateNotaHTML(trx, trx.items, toko);
      const w = window.open("", "_blank");
      w.document.write(`
    <html>
    <head>
      <title>Nota</title>
      <style>
        body { margin:0; font-family:monospace; }
        .page-break {
        page-break-after: always; /* CSS lama */
        break-after: page;        /* CSS baru */
        }
        @media print {
          @page { margin: 0; }
          body { margin: 0; }
        }
      </style>
    </head>
    <body onload="window.print(); setTimeout(()=>window.close(),500)">
      ${notaHtml}
    </body>
    </html>
  `);
      w.document.close();
        const checkClosed = setInterval(() => {
        if (w.closed) {
            clearInterval(checkClosed);
            if (typeof focusQuickBarcode === 'function') {
                focusQuickBarcode();
            }
        }
    }, 300);

    }
 