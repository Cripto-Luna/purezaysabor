// ── REEMPLAZAR con la URL de Railway después del deploy ──
const BACKEND_URL = "https://web-production-20207.up.railway.app";
const WA_NUMBER  = "50497083296";
const WA_MSG     = encodeURIComponent("Hola, quiero hacer un pedido en Pureza y Sabor");

let chatHistory = [];

function filtrar(cat, el) {
    document.querySelectorAll('.cat-card').forEach(c => c.classList.remove('active'));
    el.classList.add('active');
    document.querySelectorAll('.product-card').forEach(card => {
        card.style.display = (cat === 'todos' || card.dataset.cat === cat) ? '' : 'none';
    });
}
let chatOpen = false;

function toggleChat() {
    chatOpen = !chatOpen;
    const widget = document.getElementById("chatWidget");
    const fab    = document.getElementById("chatFab");
    widget.classList.toggle("open", chatOpen);
    fab.classList.toggle("hidden", chatOpen);
    if (!chatOpen) chatHistory = [];
}

function openChat() {
    if (!chatOpen) toggleChat();
}

function quickOrder(nombre, precio) {
    openChat();
    setTimeout(() => {
        const msg = `Quiero ordenar: ${nombre} (L ${precio.toLocaleString()})`;
        document.getElementById("chatInput").value = msg;
        sendMessage();
    }, 300);
}

function sendQuick(text) {
    document.getElementById("chatInput").value = text;
    sendMessage();
}

async function sendMessage() {
    const input = document.getElementById("chatInput");
    const text  = input.value.trim();
    if (!text) return;
    input.value = "";

    addMsg(text, "user");
    const qBtns = document.getElementById("quickBtns");
    if (qBtns) qBtns.style.display = "none";

    const typingId = showTyping();

    try {
        const res = await fetch(`${BACKEND_URL}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text, history: chatHistory })
        });
        const data = await res.json();
        removeTyping(typingId);

        chatHistory.push({ role: "user",      content: text });
        chatHistory.push({ role: "assistant", content: data.reply });

        if (data.redirect_wa) {
            addMsg(data.reply, "bot", true);
        } else {
            addMsg(data.reply, "bot");
        }
    } catch {
        removeTyping(typingId);
        addMsg("Hubo un problema de conexión. Intenta de nuevo.", "bot");
    }
}

function addMsg(text, who, showWA = false) {
    const messages = document.getElementById("chatMessages");
    const div = document.createElement("div");
    div.className = `msg ${who}-msg`;
    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.innerHTML = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    if (showWA) {
        const waLink = document.createElement("a");
        waLink.href = `https://wa.me/${WA_NUMBER}?text=${WA_MSG}`;
        waLink.target = "_blank";
        waLink.className = "wa-btn";
        waLink.innerHTML = "💬 Escribir por WhatsApp";
        bubble.appendChild(document.createElement("br"));
        bubble.appendChild(waLink);
    }

    div.appendChild(bubble);
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
}

function showTyping() {
    const messages = document.getElementById("chatMessages");
    const id = "typing-" + Date.now();
    const div = document.createElement("div");
    div.className = "msg bot-msg"; div.id = id;
    div.innerHTML = `<div class="msg-bubble typing"><span></span><span></span><span></span></div>`;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return id;
}

function removeTyping(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}
