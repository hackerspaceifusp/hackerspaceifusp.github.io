import requests
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import pytz
import json
import geopandas as gpd
from matplotlib.colors import ListedColormap, Normalize
import contextily as ctx
from datetime import datetime, timedelta
import os

# Fuso horário de Brasília
brasilia_tz = pytz.timezone("America/Sao_Paulo")

# Função para buscar os dados da API do WU
def get_station_temperature(station_id):
    WU_API_KEY = os.getenv('WU_API_KEY')
    if not WU_API_KEY:
        raise ValueError("A chave da API não foi encontrada. Defina 'WU_API_KEY' como uma variável de ambiente.")
    url = f"http://api.weather.com/v2/pws/observations/hourly/7day?stationId={station_id}&format=json&units=m&numericPrecision=decimal&apiKey={WU_API_KEY}"
    response = requests.get(url)
    print({url})
    print({response.status_code})
    # Check the status code of the response
    if response.status_code == 200:
        try:
            data = response.json()
            if 'observations' in data and len(data['observations']) > 0:
                observation = data['observations'][-2]
                horalocal = observation.get('obsTimeLocal', np.nan)
                temp = observation.get('metric', {}).get('tempAvg', np.nan)
                if temp is None or (isinstance(temp, float) and np.isnan(temp)):
                    print(f"Station {station_id} with no data")
                    return None, None, None, horalocal
                else:
                    return temp, observation['lat'], observation['lon'], horalocal
            else:
                print(f"No observations found for station {station_id}")
                return None, None, None, None
        except ValueError:
            print(f"Invalid JSON response for station {station_id}: {response.text}")
            return None, None, None, None
    else:
        print(f"Station is offline: {station_id}")
        return None, None, None, None

# Ler o arquivo de estações
with open('estacoes.txt', 'r') as f:
    stations = [line.strip() for line in f.readlines()]

# Dados de saída
temperatures = []
latitudes = []
longitudes = []
estacoes = []
horas = []

hora_atual = datetime.now(brasilia_tz).strftime("%d/%b/%Y %H:%M")

# Pega dados das estações suspeitas só se for à noite.
for station in stations:
    temp, lat, lon, hora_WU = get_station_temperature(station)
    estacoes.append(station)
    temperatures.append(temp if temp is not None else np.nan)  # Aceitar np.nan
    latitudes.append(lat)
    longitudes.append(lon)
    horas.append(hora_WU)

# Criar o DataFrame
dados = pd.DataFrame({
    'Estacao': estacoes,
    'Temperatura': temperatures,
    'Latitude': latitudes,
    'Longitude': longitudes,
    'Hora': horas
})

# Convertendo as horas para datetime e filtrando atualizações da última hora
dados['Hora'] = pd.to_datetime(dados['Hora'], utc=False).dt.tz_localize(None).dt.tz_localize('America/Sao_Paulo')
agora = datetime.now(brasilia_tz)
limite_inferior = agora - timedelta(hours=1)
dados = dados[(dados['Hora'] >= limite_inferior) & (dados['Hora'] <= agora)].copy()

# Corrige a posição da estação do gramado e do Pelletron, se ainda estiverem no DataFrame
if 'ISOPAU314' in dados['Estacao'].iloc[0]:
    dados.loc[dados.index[0], 'Latitude'] = -23.561243
    dados.loc[dados.index[0], 'Longitude'] = -46.734260
if 'ISOPAU334' in dados['Estacao'].iloc[0]:
    dados.loc[dados.index[0], 'Latitude'] = -23.561464
    dados.loc[dados.index[0], 'Longitude'] = -46.735002
if dados.shape[0] > 1:
    dados.loc[dados.index[1], 'Latitude'] = -23.561464
    dados.loc[dados.index[1], 'Longitude'] = -46.735002

# Definir o colormap baseado na temperatura
c1 = plt.cm.Purples(np.linspace(0, 1, 50))
c2 = plt.cm.turbo(np.linspace(0, 1, 176))
c3 = plt.cm.get_cmap('PuRd_r')(np.linspace(0, 1, 50))
col = np.vstack((c1, c2, c3))
custom_colormap = ListedColormap(col)

# Before using contextily, initialize the providers
ctx.providers.keys()  # This will trigger the initialization

# Criação do gráfico usando matplotlib diretamente
fig, ax = plt.subplots(1, 1, figsize=(10, 10))
gdf = gpd.GeoDataFrame(dados, geometry=gpd.points_from_xy(dados.Longitude, dados.Latitude), crs="EPSG:4326")
gdf = gdf.to_crs(epsg=3857)  # Convertendo para o CRS usado pelo contextily

norm = Normalize(vmin=-10, vmax=45)  # Definindo os limites do colormap

# Plota os pontos, adiciona o mapa de fundo e corrige os limites dos eixos
xlim = [gdf.geometry.x.min() - 200, gdf.geometry.x.max() + 150]
ylim = [gdf.geometry.y.min() - 150, gdf.geometry.y.max() + 200]

sc = ax.scatter(gdf.geometry.x, gdf.geometry.y, c=gdf['Temperatura'], cmap=custom_colormap, s=3000, edgecolor='k', linewidth=0, norm=norm)
# Adiciona um ponto invisível na área à esquerda
ax.plot(gdf.geometry.x.min() - 300, gdf.geometry.y.mean(), alpha=0)
ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, crs=gdf.crs, reset_extent=False, zoom=17)  # Changed provider

ax.set_xlim(xlim)
ax.set_ylim(ylim)
ax.set_xticks([])
ax.set_yticks([])

# Título com H1 e H2
if not gdf.empty:
    hora_ref = gdf['Hora'].iloc[0].astimezone(brasilia_tz)
    h1 = hora_ref.hour
    h2 = (h1 + 1) % 24
    plt.figtext(0.5, 1.00, f"Temperaturas no IFUSP - Médias entre as {h1:02d} e {h2:02d}h", fontsize=22, ha='center')
#plt.figtext(0.5, 1.00, f"Temperaturas médias no IFUSP - Atualizado em {horas[0]}", fontsize=22, ha='center')

# Adicionando colorbar
#cbar = plt.colorbar(sc, ax=ax, orientation='vertical', shrink=0.9)
#cbar.set_label('Temperatura (ºC)')
#cbar.set_ticks(np.arange(-10, 46, 5))  # Ajustando os ticks do colorbar

# Adicionando textos ao mapa
plt.figtext(0.5, -0.01, f"Atualizado a cada 1 hora", fontsize=18, ha='center')
for idx, row in gdf.iterrows():
    if not np.isnan(row['Temperatura']):
        if idx in [0]:
            ax.text(row.geometry.x, row.geometry.y + 16, f"Gramado", color='black', va='center', ha='center', fontsize=15, weight='bold')
        elif idx in [1]:
            ax.text(row.geometry.x, row.geometry.y - 16, f"Pelletron - topo", color='black', va='center', ha='center', fontsize=15, weight='bold')
        if (32 <= row['Temperatura'] < 40) or (-5 < row['Temperatura'] < 8):
            ax.text(row.geometry.x, row.geometry.y, f'{row["Temperatura"]:.1f}', color='white', ha='center', va='center', fontsize=18, weight='bold')
        else:
            ax.text(row.geometry.x, row.geometry.y, f'{row["Temperatura"]:.1f}', color='black', ha='center', va='center', fontsize=18, weight='bold')

# Salvar o gráfico em um arquivo
plt.tight_layout()
plt.savefig('mapa.png', bbox_inches='tight')
plt.close(fig)
