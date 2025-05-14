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
    WU_API_KEY = os.getenv('API_KEY') # JAMAIS COMPARTILHAR ESSA API KEY
    url = f"http://api.weather.com/v2/pws/observations/hourly/7day?stationId={station_id}&format=json&units=m&numericPrecision=decimal&apiKey={WU_API_KEY}"
    response = requests.get(url)
    # Check the status code of the response
    if response.status_code == 200:
        try:
            data = response.json()
            if 'observations' in data and len(data['observations']) > 0:
                observation = data['observations'][-2]
                horalocal = observation.get('obsTimeLocal', np.nan)
                if horalocal is not np.nan:
                  # Converter para objeto datetime
                  dt = datetime.strptime(horalocal, "%Y-%m-%d %H:%M:%S")  # Formato típico do WU
                  
                  # Somar 5 segundos
                  dt_mais5 = dt + timedelta(seconds=5)
                  
                  # Formatar para o formato desejado
                  hora_formatada = dt_mais5.strftime("%d/%b/%Y %H:%M")  # Ex: 14/Mai/2025 13:47
                else:
                  hora_formatada = np.nan
                temp = observation.get('metric', {}).get('tempAvg', np.nan)
                if temp is None or (isinstance(temp, float) and np.isnan(temp)):
                    print(f"Station {station_id} with no data")
                    return None, None, None, hora_formatada
                else:
                    return temp, observation['lat'], observation['lon'], hora_formatada
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

hora = datetime.now(brasilia_tz).strftime("%d/%b/%Y %H:%M")

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

# Definir o colormap baseado na temperatura
c1 = plt.cm.Purples(np.linspace(0, 1, 50))
c2 = plt.cm.turbo(np.linspace(0, 1, 176))
c3 = plt.cm.get_cmap('PuRd_r')(np.linspace(0, 1, 50))
col = np.vstack((c1, c2, c3))
custom_colormap = ListedColormap(col)

# Before using contextily, initialize the providers
ctx.providers.keys()  # This will trigger the initialization

# Criação do gráfico usando matplotlib diretamente
fig, ax = plt.subplots(1, 1, figsize=(10, 7))
gdf = gpd.GeoDataFrame(dados, geometry=gpd.points_from_xy(dados.Longitude, dados.Latitude), crs="EPSG:4326")
gdf = gdf.to_crs(epsg=3857)  # Convertendo para o CRS usado pelo contextily

norm = Normalize(vmin=-10, vmax=45)  # Definindo os limites do colormap

sc = ax.scatter(gdf.geometry.x, gdf.geometry.y, c=gdf['Temperatura'], cmap=custom_colormap, s=700, edgecolor='k', linewidth=0, norm=norm)

# Adicionando o mapa de fundo
ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, zoom=20)  # Changed provider

# Adicionando títulos e labels
plt.figtext(0.5, 1.00, f"Temperaturas médias no IFUSP - Atualizado em {horas[0]}", fontsize=18, ha='center')
#ax.set_xlabel('Longitude')
#ax.set_ylabel('Latitude')
ax.set_xticks([])
ax.set_yticks([])

# Adicionando colorbar
#cbar = plt.colorbar(sc, ax=ax, orientation='vertical', shrink=0.9)
#cbar.set_label('Temperatura (ºC)')
#cbar.set_ticks(np.arange(-10, 46, 5))  # Ajustando os ticks do colorbar

# Adicionando textos ao mapa
plt.figtext(0.5, 0.00, f"Atualizado a cada 1 hora", fontsize=10, ha='center')
for idx, row in gdf.iterrows():
    if not np.isnan(row['Temperatura']):
        if idx in [0]:
            ax.text(row.geometry.x, row.geometry.y + 1500, f"Barigui", color='black', va='center', ha='center', fontsize=8, weight='bold')
        elif idx in [1]:
            ax.text(row.geometry.x, row.geometry.y - 1500, f"Pelletron - topo", color='black', va='center', ha='center', fontsize=8, weight='bold')
        if (33 <= row['Temperatura'] < 40) or (-5 < row['Temperatura'] <= 5):
            ax.text(row.geometry.x, row.geometry.y, f'{row["Temperatura"]:.1f}', color='white', ha='center', va='center', fontsize=10, weight='bold')
        else:
            ax.text(row.geometry.x, row.geometry.y, f'{row["Temperatura"]:.1f}', color='black', ha='center', va='center', fontsize=10, weight='bold')

# Salvar o gráfico em um arquivo
plt.tight_layout()
plt.savefig('mapa.png', bbox_inches='tight')
plt.close(fig)
