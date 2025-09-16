
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



const btnFs = document.getElementById('btnFullscreen');
btnFs.onclick = () => {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen();
    } else {
        document.exitFullscreen();
    }
};
document.addEventListener('fullscreenchange', () => {
    btnFs.textContent = document.fullscreenElement ? "❌" : "🔲";
    btnFs.title = document.fullscreenElement ? "Keluar Fullscreen" : "Masuk Fullscreen";
});
 
// Register service worker
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/static/service-worker.js")
    .then(() => console.log("Service Worker registered"))
    .catch(err => console.log("SW failed:", err));
}

// Install prompt
let deferredPrompt;
const installBtn = document.createElement("button");
installBtn.textContent = "⬇️ Install Program Kasir";
installBtn.className = "fixed bottom-4 right-4 bg-emerald-600 text-white px-4 py-2 rounded shadow-lg hidden";
document.body.appendChild(installBtn);

window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredPrompt = e;
  installBtn.classList.remove("hidden");
});

installBtn.addEventListener("click", async () => {
  installBtn.classList.add("hidden");
  if (deferredPrompt) {
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    console.log(`User response: ${outcome}`);
    deferredPrompt = null;
  }
}); 