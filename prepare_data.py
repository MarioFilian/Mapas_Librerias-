# prepare_data.py
import pandas as pd
import time
import sys
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import json
import os

if len(sys.argv) < 2:
    print("Uso: python prepare_data.py input.xlsx")
    sys.exit(1)

input_file = sys.argv[1]
cache_file = "parroquia_coords_cache.csv"
output_file = "markers.json"

# 1) Leer Excel (ajusta sheet_name si hace falta)
df = pd.read_excel(input_file, dtype=str).fillna("")

# Asegúrate de que estas columnas existan (ajusta nombres si tu excel usa otros)
prov_col = 'DESCRIPCION_PROVINCIA_EST'
canton_col = 'DESCRIPCION_CANTON_EST'
parroquia_col = 'DESCRIPCION_PARROQUIA_EST'
nombre_col = 'NOMBRE_FANTASIA_COMERCIAL'

for c in [prov_col, canton_col, parroquia_col, nombre_col]:
    if c not in df.columns:
        raise SystemExit(f"Falta columna esperada en el Excel: {c}")

# 2) Obtener parroquias únicas
parroquias = df[[prov_col, canton_col, parroquia_col]].drop_duplicates().reset_index(drop=True)
parroquias['query'] = parroquias.apply(lambda r: f"{r[parroquia_col]}, {r[canton_col]}, {r[prov_col]}, Ecuador", axis=1)

# 3) Cargar cache si existe
cache = {}
if os.path.exists(cache_file):
    cdf = pd.read_csv(cache_file, dtype=str)
    for _, r in cdf.iterrows():
        cache[r['query']] = (float(r['lat']), float(r['lon']))

# 4) Inicializar geocoder con rate limiter
geolocator = Nominatim(user_agent="mapa_librerias_script_v1")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1, max_retries=2, error_wait_seconds=5)

# 5) Geocodificar y guardar en cache incrementalmente
rows = []
for q in parroquias['query'].tolist():
    if q in cache:
        lat, lon = cache[q]
    else:
        try:
            loc = geocode(q, timeout=10)
            if loc:
                lat, lon = loc.latitude, loc.longitude
            else:
                lat, lon = None, None
        except Exception as e:
            print("Error geocodificando:", q, e)
            lat, lon = None, None
        # guardar en cache
        cache[q] = (lat, lon)
        # también escribir cache parcial cada iteración para reanudar si algo falla
        tmp_df = pd.DataFrame([{'query': k, 'lat': (v[0] if v[0] is not None else ""), 'lon': (v[1] if v[1] is not None else "")} for k,v in cache.items()])
        tmp_df.to_csv(cache_file, index=False)

    rows.append({'query': q, 'lat': lat, 'lon': lon})

# 6) Mapear coordenadas a la tabla original y agrupar librerías por parroquia
# Crear un DataFrame de cache para merge
coord_df = pd.DataFrame(rows)
# Split query back to components is not necessary since we merged earlier by exact strings:
parroquias = parroquias.merge(coord_df, on='query', how='left')

# Merge con df original
df2 = df.merge(parroquias[[prov_col, canton_col, parroquia_col, 'lat', 'lon']], 
               on=[prov_col, canton_col, parroquia_col], how='left')

# 7) Agrupar: un marcador por parroquia con lista de librerías
grouped = df2.groupby([prov_col, canton_col, parroquia_col, 'lat', 'lon'], dropna=False)
markers = []
id_counter = 0
for (prov, canton, parroquia, lat, lon), g in grouped:
    if pd.isna(lat) or pd.isna(lon) or lat=="":
        # Si no hay coordenadas, opcionalmente saltamos
        continue
    librerias = sorted(list(g[nombre_col].dropna().unique()))
    marker = {
        "id": id_counter,
        "provincia": prov,
        "canton": canton,
        "parroquia": parroquia,
        "lat": float(lat),
        "lon": float(lon),
        "librerias": librerias,
        "count": len(librerias)
    }
    markers.append(marker)
    id_counter += 1

# 8) Guardar markers.json
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(markers, f, ensure_ascii=False, indent=2)

print(f"Generado {output_file} con {len(markers)} marcadores.")
print(f"Cache de coordenadas: {cache_file}")
