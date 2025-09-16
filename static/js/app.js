
function initPaperSizeSelector() {
    // cari footer
    const footer = document.querySelector("footer");
    if (!footer) return;

    // cek kalau sudah ada select jangan ditambah lagi
    if (document.getElementById("paperSizeSelect")) return;

    // buat elemen <select>
    const select = document.createElement("select");
    select.id = "paperSizeSelect";
    select.className = "bg-white border rounded px-2 py-1 ml-2";
    select.innerHTML = `
        <option value="32">Printer 58mm</option>
        <option value="42">Printer 80mm</option>
    `;

    // load nilai dari localStorage
    const saved = localStorage.getItem("paperSize") || "32";
    select.value = saved;

    // event simpan pilihan
    select.addEventListener("change", function () {
        localStorage.setItem("paperSize", this.value);
        console.log("Ukuran kertas diset ke", this.value);
    });

    // sisipkan select ke dalam footer
    footer.appendChild(select);
}

// jalankan saat halaman siap
document.addEventListener("DOMContentLoaded", initPaperSizeSelector);