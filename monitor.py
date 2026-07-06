#!/usr/bin/env python3
"""
Monitor de stock — Nike Mind 001 en nike.com.co (tienda VTEX).

Consulta la API pública de catálogo de VTEX y notifica por Discord
(y opcionalmente WhatsApp vía CallMeBot) cuando el producto aparece
con stock disponible.

Uso local:
    pip install -r requirements.txt
    export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
    python monitor.py

En GitHub Actions corre solo (ver .github/workflows/monitor.yml).
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

STORE_BASE = "https://www.nike.com.co"

# Términos de búsqueda en el catálogo. "mind 001" y "mind" por si el nombre
# exacto del producto cambia al publicarse.
SEARCH_TERMS = ["mind 001", "nike mind"]

# Palabras que DEBEN aparecer en el nombre del producto para considerarlo
# (evita falsos positivos con otros productos que mencionen "mind").
NAME_MUST_CONTAIN = ["mind"]
NAME_MUST_CONTAIN_ANY = ["001", "mind 001"]  # al menos una de estas

# Notificaciones
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()

# WhatsApp vía CallMeBot (opcional, gratis): https://www.callmebot.com/blog/free-api-whatsapp-messages/
CALLMEBOT_PHONE = os.environ.get("CALLMEBOT_PHONE", "").strip()      # ej: +573001234567
CALLMEBOT_APIKEY = os.environ.get("CALLMEBOT_APIKEY", "").strip()

# Archivo de estado para no notificar lo mismo mil veces
STATE_FILE = os.environ.get("STATE_FILE", "state.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

# ---------------------------------------------------------------------------
# Utilidades HTTP
# ---------------------------------------------------------------------------

def http_get_json(url: str):
    req = urllib.request.Request(url, headers=HEADERS)
            urllib.request.urlopen(req, timeout=30).read()
        body = resp.read().decode("utf-8", errors="replace")
        if not body.strip():
            return []
        return json.loads(body)


def http_post_json(url: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={**HEADERS, "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


# ---------------------------------------------------------------------------
# Consulta al catálogo VTEX
# ---------------------------------------------------------------------------

def search_products(term: str):
    """Busca productos por texto libre (ft) en la API pública de VTEX."""
    q = urllib.parse.quote(term)
    url = f"{STORE_BASE}/api/catalog_system/pub/products/search/{q}?map=ft&_from=0&_to=49"
    try:
        return http_get_json(url)
    except Exception as e:
        print(f"[WARN] Falló búsqueda '{term}': {e}")
        return []


def product_matches(product: dict) -> bool:
    name = (product.get("productName") or "").lower()
    if not all(w in name for w in NAME_MUST_CONTAIN):
        return False
    return any(w in name for w in NAME_MUST_CONTAIN_ANY)


def extract_availability(product: dict):
    """Devuelve lista de tallas disponibles con cantidad y precio."""
    available = []
    for item in product.get("items", []):
        size = item.get("name") or item.get("itemId")
        for seller in item.get("sellers", []):
            offer = seller.get("commertialOffer") or {}
            qty = offer.get("AvailableQuantity", 0) or 0
            is_avail = offer.get("IsAvailable", False)
            if is_avail and qty > 0:
                available.append(
                    {
                        "size": size,
                        "qty": qty,
                        "price": offer.get("Price"),
                    }
                )
                break  # con un seller disponible basta
    return available


def check_stock():
    """Retorna dict {productId: info} de productos Mind 001 con stock."""
    found = {}
    seen_ids = set()
    for term in SEARCH_TERMS:
        for product in search_products(term):
            pid = product.get("productId")
            if not pid or pid in seen_ids:
                continue
            seen_ids.add(pid)
            if not product_matches(product):
                continue
            sizes = extract_availability(product)
            link = product.get("link") or f"{STORE_BASE}/{product.get('linkText','')}/p"
            info = {
                "name": product.get("productName"),
                "link": link,
                "sizes": sizes,
                "in_stock": bool(sizes),
            }
            print(
                f"[INFO] {info['name']} -> "
                f"{'EN STOCK ' + str([s['size'] for s in sizes]) if sizes else 'sin stock'}"
            )
            if sizes:
                found[pid] = info
    return found


# ---------------------------------------------------------------------------
# Notificaciones
# ---------------------------------------------------------------------------

def fmt_price(p):
    if not p:
        return ""
    return f"${p:,.0f} COP".replace(",", ".")


def notify_discord(products: dict):
    if not DISCORD_WEBHOOK_URL:
        print("[WARN] DISCORD_WEBHOOK_URL no configurado, omito Discord.")
        return
    for info in products.values():
        sizes_txt = "\n".join(
            f"• Talla **{s['size']}** — {s['qty']} und. {fmt_price(s['price'])}"
            for s in info["sizes"]
        )
        payload = {
            "content": "🚨 **¡STOCK DISPONIBLE!** 🚨",
            "embeds": [
                {
                    "title": info["name"],
                    "url": info["link"],
                    "description": f"Hay stock en Nike Colombia:\n\n{sizes_txt}\n\n[👉 Comprar ahora]({info['link']})",
                    "color": 0xFF6B00,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ],
        }
        try:
            http_post_json(DISCORD_WEBHOOK_URL, payload)
            print("[OK] Notificación enviada a Discord.")
        except Exception as e:
            print(f"[ERROR] Discord falló: {e}")


def notify_whatsapp(products: dict):
    if not (CALLMEBOT_PHONE and CALLMEBOT_APIKEY):
        return
    for info in products.values():
        sizes_txt = ", ".join(s["size"] for s in info["sizes"])
        msg = f"🚨 STOCK Nike Mind 001 en nike.com.co! Tallas: {sizes_txt}. {info['link']}"
        url = (
            "https://api.callmebot.com/whatsapp.php?"
            + urllib.parse.urlencode(
                {"phone": CALLMEBOT_PHONE, "text": msg, "apikey": CALLMEBOT_APIKEY}
            )
        )
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            urllib.request.urlopen(req, timeout=30).read()
            print("[OK] Notificación enviada a WhatsApp (CallMeBot).")
        except Exception as e:
            print(f"[ERROR] WhatsApp falló: {e}")


# ---------------------------------------------------------------------------
# Estado (evitar notificaciones repetidas)
# ---------------------------------------------------------------------------

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"notified": {}}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def main():
    print(f"[INFO] Chequeando stock en {STORE_BASE} — {datetime.now(timezone.utc).isoformat()}")
    products = check_stock()

    state = load_state()
    notified = state.get("notified", {})

    # Notifica solo productos/combinaciones de tallas nuevas
    to_notify = {}
    for pid, info in products.items():
        signature = ",".join(sorted(s["size"] or "" for s in info["sizes"]))
        if notified.get(pid) != signature:
            to_notify[pid] = info
            notified[pid] = signature

    # Si un producto ya no tiene stock, limpia su registro para poder
    # volver a avisar en el próximo restock.
    for pid in list(notified.keys()):
        if pid not in products:
            del notified[pid]

    if to_notify:
        notify_discord(to_notify)
        notify_whatsapp(to_notify)
    else:
        print("[INFO] Sin stock nuevo. Nada que notificar.")

    state["notified"] = notified
    state["last_check"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
