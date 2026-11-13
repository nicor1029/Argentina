#!/usr/bin/env python3
"""
Une varias listas M3U en una sola, conservando las categorías (group-title).

- Mantiene las líneas extra de cada canal (#KODIPROP, #EXTVLCOPT, etc.),
  importantes para streams con DRM.
- Si un canal no trae categoría, usa el nombre de la fuente (ej. "LG AR").
- Elimina canales duplicados (misma URL de stream).
- Ordena por categoría para que queden agrupados.

Uso:  python unir_m3u.py
Solo usa la librería estándar de Python (no requiere pip).
"""
import re
import urllib.request

# ---------------------------------------------------------------- CONFIG ---
# "Nombre de la fuente": "URL". Dejá solo las que quieras.
FUENTES = {
    "LG AR": "https://www.apsattv.com/arlg.m3u",
    "LG MX": "https://www.apsattv.com/mxlg.m3u",
    "LG BR": "https://www.apsattv.com/brlg.m3u",
    "Samsung BR": "https://www.apsattv.com/ssungbra.m3u",
    "Samsung MX": "https://www.apsattv.com/ssungmex.m3u",
    "Distro": "https://www.apsattv.com/distro.m3u",
    "Vizio": "https://www.apsattv.com/vizio.m3u",
    "HP": "https://www.apsattv.com/hp.m3u",
    "Local Now": "https://www.apsattv.com/localnow.m3u",
    "Tubi": "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/refs/heads/main/playlists/tubi_all.m3u",
}

# False: respeta la categoría original del canal (ej. "Noticias").
# True:  la antepone con la fuente (ej. "LG AR | Noticias"), útil si
#        querés distinguir de dónde viene cada canal.
PREFIJO_FUENTE = False

SALIDA = "mi_lista.m3u"
# ---------------------------------------------------------------------------

RE_GRUPO = re.compile(r'group-title="([^"]*)"', re.IGNORECASE)


def descargar(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", errors="replace")


def poner_grupo(extinf, grupo):
    """Reemplaza o inserta group-title en una línea #EXTINF."""
    nuevo = f'group-title="{grupo}"'
    if RE_GRUPO.search(extinf):
        return RE_GRUPO.sub(nuevo, extinf, count=1)
    return re.sub(r"^(#EXTINF:[^ ,]+)", r"\1 " + nuevo, extinf, count=1)


def parsear(texto, fuente):
    """Devuelve (lista de canales, lista de url-tvg del encabezado)."""
    canales, epgs = [], []
    extinf, extras = None, []
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        if linea.upper().startswith("#EXTM3U"):
            epgs += re.findall(r'(?:url-tvg|x-tvg-url)="([^"]+)"', linea)
        elif linea.startswith("#EXTINF"):
            extinf, extras = linea, []
        elif linea.startswith("#EXTGRP:") and extinf:
            extras.append(linea)
        elif linea.startswith("#"):
            if extinf:
                extras.append(linea)  # KODIPROP, EXTVLCOPT, etc.
        elif extinf:  # línea de URL del stream
            grupo = None
            m = RE_GRUPO.search(extinf)
            if m and m.group(1).strip():
                grupo = m.group(1).strip()
            else:
                for e in extras:
                    if e.startswith("#EXTGRP:") and e[8:].strip():
                        grupo = e[8:].strip()
            if not grupo:
                grupo = fuente
            elif PREFIJO_FUENTE:
                grupo = f"{fuente} | {grupo}"
            canales.append({
                "grupo": grupo,
                "extinf": poner_grupo(extinf, grupo),
                "extras": [e for e in extras if not e.startswith("#EXTGRP:")],
                "url": linea,
            })
            extinf, extras = None, []
    return canales, epgs


def construir(fetch=descargar):
    todos, epgs, vistos = [], [], set()
    for fuente, url in FUENTES.items():
        try:
            canales, e = parsear(fetch(url), fuente)
        except Exception as ex:
            print(f"ERR  {fuente}: {ex}")
            continue
        epgs += [x for x in e if x not in epgs]
        nuevos = 0
        for c in canales:
            if c["url"] in vistos:
                continue
            vistos.add(c["url"])
            todos.append(c)
            nuevos += 1
        print(f"OK   {fuente}: {nuevos} canales")

    todos.sort(key=lambda c: c["grupo"].lower())  # orden estable por categoría

    cabecera = "#EXTM3U"
    if epgs:
        cabecera += f' x-tvg-url="{",".join(epgs)}"'
    salida = [cabecera]
    for c in todos:
        salida.append(c["extinf"])
        salida += c["extras"]
        salida.append(c["url"])
    return "\n".join(salida) + "\n", len(todos)


if __name__ == "__main__":
    texto, total = construir()
    with open(SALIDA, "w", encoding="utf-8") as f:
        f.write(texto)
    print(f"\nListo: {total} canales únicos en {SALIDA}")
          
