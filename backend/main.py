from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os
import aiosqlite
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SYSTEM_PROMPT = """Eres el asistente virtual de Pureza y Sabor, una tienda de postres saludables sin azúcar y sin gluten en Honduras.

PRODUCTOS Y PRECIOS (en Lempiras):
- Loaf de Almendra: L 600 — Sabor suave y sofisticado, textura delicada con toque de almendra.
- Torta de Vainilla con Yogurt: L 800 — Suave, ligera, con toque fresco del yogurt.
- Pastel de Chocolate para 6 personas: L 800 — Textura suave y sabor profundo, ideal para regalar o celebrar.
- Loaf de Banano: L 800 — Combinación deliciosa de banano y arándanos.
- Pastel de Fresa 10 a 12 personas: L 1,450 — Suave, fresco y naturalmente dulce.
- Pastel de Zanahoria 6 personas: L 900 — Aromático, nutritivo y delicioso.
- Pastel de Zanahoria 10 a 12 personas: L 1,500 — Presentación familiar ideal para eventos.

CATEGORÍAS: Pasteles, Tortas, Combos para regalar.

INFORMACIÓN IMPORTANTE:
- Todos los productos son sin azúcar añadida y sin gluten. Ingredientes naturales, sin conservantes.
- Pedidos con mínimo 3 días de anticipación.
- Pago: 100% al confirmar el pedido. Se acepta efectivo y transferencia bancaria.
- Delivery disponible en Tegucigalpa y Comayagüela. Máximo 20 km fuera de la ciudad. Costo según zona.
- Atención 24/7 por este chat.

Responde en español, de forma amable y cálida. Máximo 3 oraciones por respuesta.
Responde DIRECTAMENTE preguntas sobre productos, precios, delivery y disponibilidad.
Solo menciona WhatsApp cuando el cliente esté listo para confirmar su pedido.
IMPORTANTE: Responde SOLO con el texto del mensaje. Nunca incluyas JSON ni metadatos."""

class HistoryMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[HistoryMessage] = []

class ChatResponse(BaseModel):
    reply: str
    redirect_wa: bool = False

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    keywords_wa = [
        "quiero ordenar", "quiero pedir", "hacer pedido", "quiero el pedido",
        "quiero comprar", "voy a comprar", "me lo haces", "quiero uno",
        "como ordeno", "cómo ordeno", "como hago el pedido", "cómo hago el pedido",
        "quiero pagar", "como pago", "cómo pago", "hacer la transferencia",
        "hablar con alguien", "hablar con una persona", "humano", "persona real",
        "quiero hablar", "confirmar pedido", "apartar", "reservar",
        "listo para pedir", "voy a pedir", "quiero hacer un pedido",
        "me interesa ordenar", "quiero ese", "quiero esa",
    ]
    redirect = any(kw in req.message.lower() for kw in keywords_wa)

    if redirect:
        return ChatResponse(
            reply="¡Perfecto! Te conecto con el equipo de Pureza y Sabor para coordinar tu pedido. 🎂👇",
            redirect_wa=True
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 300,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": m.role, "content": m.content} for m in req.history[-8:]] + [{"role": "user", "content": req.message}]
        },
        timeout=30
    )
    data = response.json()
    print(f"Anthropic status: {response.status_code}")
    reply = data["content"][0]["text"]
    return ChatResponse(reply=reply, redirect_wa=False)

@app.get("/health")
def health():
    return {"status": "ok"}


# ── BLOG ──────────────────────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(__file__), "blog.db")
BLOG_PASSWORD = os.environ.get("BLOG_PASSWORD", "pureza2026")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await db.commit()

@app.on_event("startup")
async def startup():
    await init_db()

class PostCreate(BaseModel):
    password: str
    title: str
    content: str

class PostUpdate(BaseModel):
    password: str
    title: str
    content: str

@app.get("/posts")
async def get_posts():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, title, content, created_at FROM posts ORDER BY id DESC") as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]

@app.post("/posts")
async def create_post(body: PostCreate):
    if body.password != BLOG_PASSWORD:
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    now = datetime.now().strftime("%d de %B de %Y").replace(
        "January","enero").replace("February","febrero").replace("March","marzo").replace(
        "April","abril").replace("May","mayo").replace("June","junio").replace(
        "July","julio").replace("August","agosto").replace("September","septiembre").replace(
        "October","octubre").replace("November","noviembre").replace("December","diciembre")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO posts (title, content, created_at) VALUES (?, ?, ?)",
            (body.title.strip(), body.content.strip(), now)
        )
        await db.commit()
        post_id = cur.lastrowid
    return {"id": post_id, "title": body.title, "created_at": now}

@app.put("/posts/{post_id}")
async def update_post(post_id: int, body: PostUpdate):
    if body.password != BLOG_PASSWORD:
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE posts SET title=?, content=? WHERE id=?",
            (body.title.strip(), body.content.strip(), post_id)
        )
        await db.commit()
    return {"ok": True}

@app.delete("/posts/{post_id}")
async def delete_post(post_id: int, password: str):
    if password != BLOG_PASSWORD:
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM posts WHERE id=?", (post_id,))
        await db.commit()
    return {"ok": True}
