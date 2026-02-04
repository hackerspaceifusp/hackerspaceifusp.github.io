import requests
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from io import BytesIO
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
from cartopy.geodesic import Geodesic
from datetime import datetime
import pytz
from geopy.distance import geodesic
import matplotlib.colors as mcolors

# Definições do mapa
LAT_CENTRO, LON_CENTRO = -23.56, -46.73  # São Paulo, Brasil
ZOOM = 7  # Define o zoom do radar e do mapa
SIZE = 512  # Resolução do radar
COLOR_SCHEME = 4  # Paleta de cores do radar
OPTIONS = "1_1"  # Remove fundo preto do radar

# Tabela de conversão: Zoom → Resolução (m/pixel)
zoom_to_resolution = {
    0: 78271.517, 1: 39135.7585, 2: 19567.8792, 3: 9783.9396,
    4: 4891.9698, 5: 2445.9849, 6: 1222.9925, 7: 611.4962,
    8: 305.7481, 9: 152.8741, 10: 76.437
}

# Aproximadamente quantos metros há em 1 grau de latitude
METROS_POR_GRAU = 111320

# Obter a resolução correspondente ao zoom selecionado (metros/pixel)
resolucao_metros = zoom_to_resolution.get(ZOOM, 1222.9925)

# Calcular quantos graus aproximadamente representam a resolução do radar
resolucao_graus = resolucao_metros / METROS_POR_GRAU

# Ajustar a extensão do mapa com base na resolução
grau_extensao = resolucao_graus * 215  # Assumindo imagem de 256x256 pixels
delta_lat, delta_lon = grau_extensao, grau_extensao

# Definição da paleta de cores da chuva usada pelo RainViewer
rain_colors = [
    (0, "white"),         # Sem precipitação
    (0.1, "lightblue"),  # Chuva fraca
    (0.3, "blue"),       # Chuva moderada
    (0.5, "yellow"),      # Chuva forte
    (0.7, "orange"),      # Chuva muito forte
    (0.9, "red"),         # Tempestade
    (1.0, "purple")       # Chuva extrema
]

# Obtém o timestamp mais recente da API
rainviewer_url = "https://api.rainviewer.com/public/weather-maps.json"
response = requests.get(rainviewer_url)
data = response.json()

if "radar" in data and "past" in data["radar"]:
    latest_timestamp = data["radar"]["past"][-1]["time"]
else:
    raise ValueError("Não foi possível obter o timestamp mais recente.")

# Converter o timestamp UTC para o fuso horário de Brasília
utc_time = datetime.utcfromtimestamp(latest_timestamp)
brt_time = utc_time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone("America/Sao_Paulo"))
timestamp_brasilia = brt_time.strftime("%d/%b/%Y - %H:%M")

# Constrói a URL da imagem de radar
radar_image_url = f"https://tilecache.rainviewer.com/v2/radar/{latest_timestamp}/{SIZE}/{ZOOM}/{LAT_CENTRO}/{LON_CENTRO}/{COLOR_SCHEME}/{OPTIONS}.png"

# Baixa a imagem de radar
response = requests.get(radar_image_url)
if response.status_code == 200:
    radar_image = Image.open(BytesIO(response.content))
else:
    raise ValueError("Erro ao baixar a imagem de radar.")

# Criar o mapa com Cartopy
fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={'projection': ccrs.PlateCarree()})
ax.set_extent([LON_CENTRO - delta_lon, LON_CENTRO + delta_lon, LAT_CENTRO - delta_lat, LAT_CENTRO + delta_lat], crs=ccrs.PlateCarree())

# Adicionar camadas geográficas
ax.add_feature(cfeature.LAND, facecolor='lightgray')
ax.add_feature(cfeature.OCEAN, facecolor='lightblue')
ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
ax.add_feature(cfeature.BORDERS, linewidth=1.5)

# Adicionar fronteiras estaduais com mais destaque
ax.add_feature(cfeature.NaturalEarthFeature(category='cultural',
                                            name='admin_1_states_provinces_lines',
                                            scale='10m',
                                            facecolor='none',
                                            edgecolor='black',
                                            linewidth=1.2))

# Adicionar estradas principais
ax.add_feature(cfeature.NaturalEarthFeature(category='cultural',
                                            name='roads',
                                            scale='10m',
                                            facecolor='none',
                                            edgecolor='gray',
                                            linewidth=0.8))

# Adicionar áreas urbanas ao mapa
ax.add_feature(cfeature.NaturalEarthFeature(category='cultural',
                                            name='urban_areas',
                                            scale='10m',
                                            facecolor='dimgrey',  # Cor cinza escuro
                                            alpha=0.5))  # Transparência para não cobrir tudo

# Adicionar imagem de radar sobre o mapa
ax.imshow(np.array(radar_image), extent=[LON_CENTRO-delta_lon, LON_CENTRO+delta_lon, LAT_CENTRO-delta_lat, LAT_CENTRO+delta_lat], 
          transform=ccrs.PlateCarree(), alpha=0.6)

# Adicionar cidades importantes
shapefile = shpreader.natural_earth(resolution='10m', category='cultural', name='populated_places')
reader = shpreader.Reader(shapefile)

for city in reader.records():
    lat, lon = city.geometry.y, city.geometry.x
    nome = city.attributes['NAME']
    pop = city.attributes['POP_MAX']  # População da cidade

    # Exibir cidades com população relevante dentro da área do mapa
    if (LAT_CENTRO-delta_lat+0.1 <= lat <= LAT_CENTRO+delta_lat-0.1) and (LON_CENTRO-delta_lon+0.1 <= lon <= LON_CENTRO+delta_lon-0.1) and pop > 100000:
        ax.scatter(lon, lat, color='red', s=30, transform=ccrs.PlateCarree(), label=nome)
        ax.text(lon, lat + 0.02, nome, fontsize=9, color='black', transform=ccrs.PlateCarree(), ha='center')

# Adicionar círculo de 30 km ao redor do centro
geod = Geodesic()
circle = geod.circle(lon=LON_CENTRO, lat=LAT_CENTRO, radius=30000, n_samples=100)
circle_lons, circle_lats = zip(*circle)

ax.plot(circle_lons, circle_lats, color='black', linewidth=1.5, transform=ccrs.PlateCarree(), linestyle='dashed', alpha=0.8)

# Ajuste automático da escala de distâncias
#escala_km = int((resolucao_metros * 50) / 1000)  # Baseado na resolução do zoom
# Ponto inicial da escala de distância
scale_start = (LAT_CENTRO - delta_lat * 0.85, LON_CENTRO - delta_lon * 0.7)

# Ponto final a 20 km de distância para a escala
scale_end = geodesic(kilometers=20).destination(scale_start, 90)  # 90° = direção leste

# Desenhar a escala corretamente
ax.plot([scale_start[1], scale_end.longitude], [scale_start[0], scale_end.latitude],
        color='black', linewidth=3, transform=ccrs.PlateCarree())

ax.text((scale_start[1] + scale_end.longitude) / 2, scale_start[0] - 0.07,
        "20 km", fontsize=10, color='black', ha='center', transform=ccrs.PlateCarree())

# Adicionar horário no canto inferior direito
ax.text(LON_CENTRO+delta_lon*0.85, LAT_CENTRO-delta_lat*0.9, timestamp_brasilia, fontsize=10, color='black', ha='right')
ax.scatter(LON_CENTRO, LAT_CENTRO, color='blue', s=70, transform=ccrs.PlateCarree(), label=nome)
#ax.text(LON_CENTRO, LAT_CENTRO - 0.04, "IFUSP", fontsize=12, color='black', transform=ccrs.PlateCarree(), ha='center')

# Criar colormap personalizado
colors = [cor for _, cor in rain_colors]  # Pegamos apenas as cores da lista
positions = [pos for pos, _ in rain_colors]  # Pegamos as posições da lista

# Criar o colormap corretamente
cmap = mcolors.LinearSegmentedColormap.from_list("rain_cmap", list(zip(positions, colors)))

# Normalizar valores
norm = mcolors.Normalize(vmin=0, vmax=1)

# Criar a barra de cores discreta
cbar_ax = fig.add_axes([0.92, 0.3, 0.015, 0.4])  # Mais estreito e menor altura
cbar = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cbar_ax)

# Ajustar fonte e espaçamento para um estilo mais discreto
cbar.set_label("Intensidade da chuva", fontsize=16)  # Fonte menor
cbar.set_ticks([0.2, 0.5, 0.8, 1])  # Menos marcações
cbar.set_ticklabels(["", "", "", ""])  # Labels curtos
cbar.outline.set_visible(False)  # Remove a borda para ficar mais clean

# Mostrar o mapa
# Ajustar título para ficar no topo
fig.suptitle("Radar de Chuvas - São Paulo e região", fontsize=16)
ax.text(LON_CENTRO, LAT_CENTRO-delta_lat*1.07, "Atualizado a cada 20 minutos", fontsize=12, color='black', ha='center')
ax.text(LON_CENTRO, LAT_CENTRO-delta_lat*1.14, "Fonte: RainViewer", fontsize=10, color='black', ha='center')
plt.subplots_adjust(top=0.95)  # Reduz o espaço superior

plt.savefig('radar.png')
plt.close(fig)
