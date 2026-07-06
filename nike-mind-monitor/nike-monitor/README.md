# 👟 Monitor de stock — Nike Mind 001 (nike.com.co)

Backend que revisa cada 10 minutos si las **Nike Mind 001** aparecen con stock en la tienda oficial de Nike Colombia y te avisa por **Discord** (y opcionalmente **WhatsApp**).

Funciona porque nike.com.co corre sobre **VTEX**, cuya API pública de catálogo (`/api/catalog_system/pub/products/search/`) devuelve la disponibilidad por talla en JSON. No hay que abrir un navegador ni scrapear HTML.

## 🚀 Configuración (unos 10 minutos, todo gratis)

### 1. Crea el webhook de Discord

1. En tu servidor de Discord: **Ajustes del canal → Integraciones → Webhooks → Nuevo webhook**.
2. Copia la URL del webhook (empieza con `https://discord.com/api/webhooks/...`).

Si no tienes servidor, crea uno propio (botón `+` en Discord) — toma 30 segundos y las notificaciones te llegarán al celular si tienes la app.

### 2. Sube este proyecto a GitHub

1. Crea un repositorio nuevo (puede ser privado) en github.com.
2. Sube estos archivos (`monitor.py`, `README.md` y la carpeta `.github/workflows/`). Puedes arrastrarlos en la interfaz web de GitHub con "Add file → Upload files". **Importante:** la carpeta `.github/workflows/monitor.yml` debe conservar esa ruta exacta.

### 3. Agrega los secretos

En tu repo: **Settings → Secrets and variables → Actions → New repository secret**

| Nombre | Valor | Obligatorio |
|---|---|---|
| `DISCORD_WEBHOOK_URL` | La URL del webhook del paso 1 | ✅ Sí |
| `CALLMEBOT_PHONE` | Tu número con indicativo, ej. `+573001234567` | Opcional (WhatsApp) |
| `CALLMEBOT_APIKEY` | Tu API key de CallMeBot | Opcional (WhatsApp) |

### 4. Activa el workflow

Ve a la pestaña **Actions** del repo, habilita los workflows si GitHub lo pide, y ejecuta "Nike Mind 001 Stock Monitor" manualmente una vez con **Run workflow** para probar. Luego correrá solo cada 10 minutos.

## 📱 WhatsApp (opcional, gratis con CallMeBot)

1. Agrega el número de CallMeBot a tus contactos (está en su página oficial: callmebot.com → "WhatsApp → API").
2. Envíale por WhatsApp el mensaje de activación que indica la página ("I allow callmebot to send me messages").
3. Te responderá con tu **API key**. Ponla en los secretos del paso 3.

Nota: CallMeBot es un servicio de terceros gratuito; si prefieres algo más robusto, Twilio ofrece WhatsApp API (de pago). Discord es la vía más confiable.

## 💻 Probarlo en tu PC

```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/TU_WEBHOOK"
python monitor.py
```

No necesita librerías externas — solo Python 3.8+ estándar.

## ⚙️ Cómo funciona

1. Busca "mind 001" y "nike mind" en la API de catálogo de VTEX de nike.com.co.
2. Filtra productos cuyo nombre contenga "mind" y "001".
3. Revisa `IsAvailable` y `AvailableQuantity` por talla y vendedor.
4. Si hay stock **nuevo** (tallas que antes no estaban), envía la notificación con tallas, cantidades, precio y link directo de compra.
5. Guarda el estado en `state.json` para no repetir el mismo aviso; si el stock se agota, se resetea y volverá a avisar en el próximo restock.

## 🔧 Ajustes

- **Frecuencia:** cambia el cron en `.github/workflows/monitor.yml`. `*/5 * * * *` = cada 5 min (GitHub a veces demora los crons unos minutos en horas pico).
- **Otro producto:** edita `SEARCH_TERMS`, `NAME_MUST_CONTAIN` y `NAME_MUST_CONTAIN_ANY` en `monitor.py`.
- **Solo ciertas tallas:** filtra en `extract_availability()` comparando `size` con tu talla.

## ⚠️ Notas

- El producto aún puede no existir en el catálogo de nike.com.co (a hoy la página `/mind` es solo informativa). El monitor está hecho justo para eso: en cuanto lo publiquen con stock, te llega la alerta.
- Es una consulta ligera cada 10 minutos a una API pública — un uso razonable y de bajo impacto.
