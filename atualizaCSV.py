# Importa bibliotecas
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import pandas as pd
from datetime import datetime, timezone, timedelta
import requests
import pytz
import numpy as np
import os

# Fuso horário de Brasília
brasilia_tz = pytz.timezone("America/Sao_Paulo")

# Função para pegar os dados do Weather Underground
def get_weather_data():
    WU_API_KEY = os.getenv('WU_API_KEY') # JAMAIS COMPARTILHAR ESSA API KEY
    print(WU_API_KEY)
    STATION_ID = "ISOPAU334"
    url = f"https://api.weather.com/v2/pws/observations/current?stationId={STATION_ID}&format=json&units=m&numericPrecision=decimal&apiKey={WU_API_KEY}"
    timestamp = datetime.now(timezone.utc).astimezone(brasilia_tz)  # Captura o timestamp em UTC e converte para HBR
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        observation = data['observations'][0]
        temp = observation["metric"]["temp"]
        precip_total = observation["metric"]["precipTotal"]
        humidity = observation["humidity"]
        dew_point = observation["metric"]["dewpt"]
        solar_rad = observation["solarRadiation"]
        uv = observation["uv"]
        wind_speed = observation["metric"]["windSpeed"]
        wind_dir = observation["winddir"]
        wind_gust = observation["metric"]["windGust"]
        pressure = observation["metric"]["pressure"]
        return timestamp, temp, precip_total, humidity, dew_point, solar_rad, uv, wind_speed, wind_dir, wind_gust, pressure
    except (requests.exceptions.RequestException, KeyError) as e:
        print("Erro:", e)
        return timestamp, None, None, None, None, None, None, None, None, None, None

# Caminho do arquivo CSV
csv_file = 'weather_data.csv'

# Verificar se o arquivo existe
if os.path.exists(csv_file):
    # Ler os dados existentes
    df = pd.read_csv(csv_file, parse_dates=['Timestamp'])
    # Filtrar para manter apenas os dados das últimas 24 horas
    now = datetime.now(brasilia_tz)
    df = df[df['Timestamp'] >= now - pd.Timedelta(hours=24)]
else:
    # Criar um DataFrame vazio
    df = pd.DataFrame(columns=['Timestamp', 'Temperature', 'Precip', 'Humidity', 'Dew Point', 'Radiation', 'UV Index', 'Wind Speed', 'Wind Dir', 'Wind Gust', 'Pressure'])

# Obter os dados atuais
timestamp, temp, precip_total, humidity, dew_point, solar_rad, uv_index, wind_speed, wind_dir, wind_gust, pressure = get_weather_data()
# Remover fração de segundos do timestamp
timestamp = timestamp.replace(microsecond=0)

# Limites do eixo x: de timestamp - 25h até timestamp + 1h
start_time = timestamp - timedelta(hours=25)
end_time = timestamp + timedelta(hours=1)

if temp is not None:
    # Verificar se o timestamp já existe no DataFrame
    if timestamp not in df['Timestamp'].values:
        # Criar um DataFrame com o novo dado
        new_data = pd.DataFrame({
            'Timestamp': [timestamp],
            'Temperature': [temp],
            'Precip': [precip_total],
            'Humidity': [humidity],
            'Dew Point': [dew_point],
            'Radiation': [solar_rad],
            'UV Index': [uv_index],
            'Wind Speed': [wind_speed],
            'Wind Dir': [wind_dir],
            'Wind Gust': [wind_gust],
            'Pressure': [pressure]
        })
    
        # Concatenar com o DataFrame existente
        df = pd.concat([df, new_data])
    
        # Filtrar para manter apenas os dados das últimas 24 horas
        now = datetime.now(brasilia_tz)
        df = df[df['Timestamp'] >= now - pd.Timedelta(hours=24)]
        
        # Salvar no arquivo CSV
        df.to_csv(csv_file, index=False, date_format='%Y-%m-%d %H:%M:%S%z')
        estadoEstacao = 'Online'
    else:
        print("Dados já existentes para o timestamp:", timestamp)
        #Estacao On/Off
        estadoEstacao = 'Offline'
    
    # Configurar subplots
    fig, axs = plt.subplots(5, 1, figsize=(10, 12), sharex=True)
    fig.suptitle("Tempo nas últimas 24 horas", fontsize=18)
    
    # Definir o colormap baseado na temperatura
    c1 = plt.cm.Purples(np.linspace(0, 1, 50))
    c2 = plt.cm.turbo(np.linspace(0, 1, 176))
    c3 = plt.get_cmap('PuRd_r')(np.linspace(0, 1, 50))
    col = np.vstack((c1, c2, c3))
    cmap = plt.cm.colors.ListedColormap(col)
    cmap_hum = plt.cm.colors.ListedColormap(plt.cm.coolwarm(np.linspace(1, 0, 100)))
    cmap_rad = plt.cm.colors.ListedColormap(plt.cm.Blues(np.linspace(0, 1, 50)))
    temp_norm = (temp + 10) / 55  # Normaliza a temperatura dos limites [-10, 45]ºC para o intervalo [0, 1]
    temp_norm = np.clip(temp_norm, 0, 1)  # Garante que o valor esteja entre 0 e 1
    state_color = 'red' if estadoEstacao == "Offline" else 'green'
    temp_color = cmap(temp_norm)
    hum_color = cmap_hum(humidity / 100)
    precip_color = cmap_rad(precip_total/50)
    
    hora_atual = f"{timestamp.hour:02d}"
    minuto_atual = f"{timestamp.minute:02d}"
    dia_atual = f"{timestamp.day:02d}"
    mes_atual = f"{timestamp.month:02d}"
    ano_atual = f"{timestamp.year}"
    fig.text(0.5, 1.00, estadoEstacao, color=state_color, fontsize=16, ha='center')
    # Exibir a temperatura, umidade, P.O. e pressão acima dos plots
    plt.figtext(0.5, 1.15, f"Condições meteorológicas atuais no IFUSP (Pelletron) - Atualizado {dia_atual}/{mes_atual}/{ano_atual} às {hora_atual}:{minuto_atual}", fontsize=16, ha='center')
    
    quadrado = plt.Rectangle((0.15, 1.06), 0.22, 0.07, transform=fig.transFigure, color=temp_color, lw=0)
    fig.patches.append(quadrado)
    # Definir a cor do texto com base na temperatura
    text_color = 'white' if (temp >= 32 or temp < 8) else 'black'
    # Usar o texto com a cor definida
    plt.figtext(0.26, 1.075, f"Temperatura:\n {temp:.1f} °C", fontsize=18, ha='center', color=text_color)
    plt.figtext(0.26, 1.03, f"Ponto de orvalho: {dew_point:.1f} °C", fontsize=11, ha='center', color='black')
    
    quadrado = plt.Rectangle((0.39, 1.06), 0.22, 0.07, transform=fig.transFigure, color=hum_color, lw=0)
    fig.patches.append(quadrado)
    text_color = 'white' if (humidity >= 90) else 'black'
    plt.figtext(0.50, 1.075, f"Umidade:\n {humidity:.0f} %", fontsize=18, ha='center', color=text_color)
    plt.figtext(0.50, 1.03, f"Radiação solar: {solar_rad:.0f} W/m²", fontsize=11, ha='center', color='black')
    
    quadrado = plt.Rectangle((0.63, 1.06), 0.22, 0.07, transform=fig.transFigure, color=precip_color, lw=0)
    fig.patches.append(quadrado)
    text_color = 'white' if (precip_total >= 30) else 'black'
    plt.figtext(0.74, 1.075, f"Chuva acum.:\n {precip_total:.1f} mm", fontsize=18, ha='center', color=text_color)
    plt.figtext(0.74, 1.03, f"Índice UV: {uv_index:.0f}", fontsize=11, ha='center', color='black')
    
    #plt.subplots_adjust(right=0.5)
    
    # Temperatura
    axs[0].plot(df['Timestamp'], df['Temperature'], label="Temperatura", color='red', marker='o')
    axs[0].plot(df['Timestamp'], df['Dew Point'], label="Ponto de orvalho", color="green", linestyle="--", marker='o',markersize=3)
    axs[0].set_ylabel("Temperatura (°C)",fontsize=14)
    axs[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}"))
    axs[0].legend(loc="best")
    axs[0].grid(True)
    for label in axs[0].get_yticklabels(): #Tamanho dos rótulos
        label.set_fontsize(14)
    
    # Chuva
    #axs[1].plot(df['Timestamp'], df['Precip'], color='indigo', label='Precipitação acumulada', marker='o')
    precip_diff = df['Precip'].diff().fillna(0)
    axs[1].bar(df['Timestamp'], precip_diff, color='skyblue', label='Taxa de precipitação', width=0.02)
    axs[1].set_ylabel("Precipitação (mm)",fontsize=14)
    axs[1].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}"))
    #axs[1].legend(loc="best")
    axs[1].grid(True)
    for label in axs[1].get_yticklabels(): #Tamanho dos rótulos
        label.set_fontsize(14)
    
    # Umidade
    axs[2].plot(df['Timestamp'], df['Humidity'], color='blue', marker='o')
    axs[2].set_ylabel("Umidade relativa (%)",fontsize=14)
    axs[2].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}"))
    axs[2].grid(True)
    for label in axs[2].get_yticklabels(): #Tamanho dos rótulos
        label.set_fontsize(14)
    
    # Vento
    axs[3].plot(df['Timestamp'], df['Wind Speed'], color='navy', label='Vento', marker='o')
    axs[3].scatter(df['Timestamp'], df['Wind Gust'], color='orange', label='Rajadas', alpha=0.7)
    axs[3].set_ylabel("Vento (km/h)",fontsize=14)
    axs[3].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}"))
    axs[3].grid(True)
    axs[3].legend(loc="best")
    for label in axs[3].get_yticklabels(): #Tamanho dos rótulos
        label.set_fontsize(14)
    
    # Radiação
    axs[4].plot(df['Timestamp'], df['Radiation'], color='orange', marker='o')
    axs[4].set_ylabel("Radiação solar (W/m²)",fontsize=14)
    axs[4].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}"))
    axs[4].grid(True)
    for label in axs[4].get_yticklabels(): #Tamanho dos rótulos
        label.set_fontsize(14)
    
    # Formatação do eixo X
    axs[4].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M', tz=brasilia_tz))
    axs[4].xaxis.set_major_locator(mdates.HourLocator(interval=2))
    axs[4].set_xlim([start_time, end_time])
    for label in axs[4].get_xticklabels():
        label.set_fontsize(14)
    plt.xlabel("Hora local",fontsize=14)
    plt.gcf().autofmt_xdate()
    #print(f"Número de ticks no eixo X: {len(axs[2].get_xticks())}")
    
    # Configurar limites para cada eixo Y em cada subplot
    axs[0].set_ylim(df['Dew Point'].min()-2, df['Temperature'].max()+2)
    axs[1].set_ylim(0, precip_diff.max()+5)
    axs[2].set_ylim([0, 103])
    axs[3].set_ylim(0, df['Wind Gust'].max()+3)
    axs[4].set_ylim([0, 1350])
    
    # Salvar o gráfico em um arquivo
    plt.tight_layout()
    plt.savefig('graph.png', bbox_inches='tight')
    plt.close(fig)

else:
    print("Dados não foram obtidos.")
    estadoEstacao = 'Offline'

    # Configurar subplots
    fig, axs = plt.subplots(5, 1, figsize=(10, 12), sharex=True)
    fig.suptitle("Tempo nas últimas 24 horas", fontsize=18)
    
    # Definir o colormap baseado na temperatura
    c1 = plt.cm.Purples(np.linspace(0, 1, 50))
    c2 = plt.cm.turbo(np.linspace(0, 1, 176))
    c3 = plt.get_cmap('PuRd_r')(np.linspace(0, 1, 50))
    col = np.vstack((c1, c2, c3))
    cmap = plt.cm.colors.ListedColormap(col)
    cmap_hum = plt.cm.colors.ListedColormap(plt.cm.coolwarm(np.linspace(1, 0, 100)))
    cmap_rad = plt.cm.colors.ListedColormap(plt.cm.Blues(np.linspace(0, 1, 50)))
    state_color = 'red' if estadoEstacao == "Offline" else 'green'
    temp_color = cmap_hum(0.5)
    hum_color = cmap_hum(0.5)
    precip_color = cmap_hum(0.5)
    
    hora_atual = f"{timestamp.hour:02d}"
    minuto_atual = f"{timestamp.minute:02d}"
    dia_atual = f"{timestamp.day:02d}"
    mes_atual = f"{timestamp.month:02d}"
    ano_atual = f"{timestamp.year}"
    fig.text(0.5, 1.00, estadoEstacao, color=state_color, fontsize=16, ha='center')
    # Exibir a temperatura, umidade, P.O. e pressão acima dos plots
    plt.figtext(0.5, 1.15, f"Condições meteorológicas atuais em Curitiba (Parque Barigui) - Atualizado {dia_atual}/{mes_atual}/{ano_atual} às {hora_atual}:{minuto_atual}", fontsize=16, ha='center')
    
    quadrado = plt.Rectangle((0.15, 1.06), 0.22, 0.07, transform=fig.transFigure, color=temp_color, lw=0)
    fig.patches.append(quadrado)
    # Definir a cor do texto com base na temperatura
    text_color = 'black'
    # Usar o texto com a cor definida
    plt.figtext(0.26, 1.075, f"Temperatura:\n NaN °C", fontsize=18, ha='center', color=text_color)
    plt.figtext(0.26, 1.03, f"Ponto de orvalho: NaN °C", fontsize=11, ha='center', color='black')
    
    quadrado = plt.Rectangle((0.39, 1.06), 0.22, 0.07, transform=fig.transFigure, color=hum_color, lw=0)
    fig.patches.append(quadrado)
    plt.figtext(0.50, 1.075, f"Umidade:\n NaN %", fontsize=18, ha='center', color=text_color)
    plt.figtext(0.50, 1.03, f"Radiação solar: NaN W/m²", fontsize=11, ha='center', color='black')
    
    quadrado = plt.Rectangle((0.63, 1.06), 0.22, 0.07, transform=fig.transFigure, color=precip_color, lw=0)
    fig.patches.append(quadrado)
    plt.figtext(0.74, 1.075, f"Chuva acum.:\n NaN mm", fontsize=18, ha='center', color=text_color)
    plt.figtext(0.74, 1.03, f"Índice UV: NaN", fontsize=11, ha='center', color='black')
    
    #plt.subplots_adjust(right=0.5)
    
    # Temperatura
    axs[0].plot(df['Timestamp'], df['Temperature'], label="Temperatura", color='red', marker='o')
    axs[0].plot(df['Timestamp'], df['Dew Point'], label="Ponto de orvalho", color="green", linestyle="--", marker='o',markersize=3)
    axs[0].set_ylabel("Temperatura (°C)",fontsize=14)
    axs[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}"))
    axs[0].legend(loc="best")
    axs[0].grid(True)
    for label in axs[0].get_yticklabels(): #Tamanho dos rótulos
        label.set_fontsize(14)
    
    # Chuva
    #axs[1].plot(df['Timestamp'], df['Precip'], color='indigo', label='Precipitação acumulada', marker='o')
    precip_diff = df['Precip'].diff().fillna(0)
    axs[1].bar(df['Timestamp'], precip_diff, color='skyblue', label='Taxa de precipitação', width=0.02)
    axs[1].set_ylabel("Precipitação (mm)",fontsize=14)
    axs[1].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}"))
    #axs[1].legend(loc="best")
    axs[1].grid(True)
    for label in axs[1].get_yticklabels(): #Tamanho dos rótulos
        label.set_fontsize(14)
    
    # Umidade
    axs[2].plot(df['Timestamp'], df['Humidity'], color='blue', marker='o')
    axs[2].set_ylabel("Umidade relativa (%)",fontsize=14)
    axs[2].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}"))
    axs[2].grid(True)
    for label in axs[2].get_yticklabels(): #Tamanho dos rótulos
        label.set_fontsize(14)
    
    # Vento
    axs[3].plot(df['Timestamp'], df['Wind Speed'], color='navy', label='Vento', marker='o')
    axs[3].scatter(df['Timestamp'], df['Wind Gust'], color='orange', label='Rajadas', alpha=0.7)
    axs[3].set_ylabel("Vento (km/h)",fontsize=14)
    axs[3].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}"))
    axs[3].grid(True)
    axs[3].legend(loc="best")
    for label in axs[3].get_yticklabels(): #Tamanho dos rótulos
        label.set_fontsize(14)
    
    # Radiação
    axs[4].plot(df['Timestamp'], df['Radiation'], color='orange', marker='o')
    axs[4].set_ylabel("Radiação solar (W/m²)",fontsize=14)
    axs[4].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}"))
    axs[4].grid(True)
    for label in axs[4].get_yticklabels(): #Tamanho dos rótulos
        label.set_fontsize(14)
    
    # Formatação do eixo X
    axs[4].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M', tz=brasilia_tz))
    axs[4].xaxis.set_major_locator(mdates.HourLocator(interval=2))
    axs[4].set_xlim([start_time, end_time])
    for label in axs[4].get_xticklabels():
        label.set_fontsize(14)
    plt.xlabel("Hora local",fontsize=14)
    plt.gcf().autofmt_xdate()
    #print(f"Número de ticks no eixo X: {len(axs[2].get_xticks())}")
    
    # Configurar limites para cada eixo Y em cada subplot
    axs[0].set_ylim(df['Dew Point'].min()-2, df['Temperature'].max()+2)
    axs[1].set_ylim(0, precip_diff.max()+5)
    axs[2].set_ylim([0, 103])
    axs[3].set_ylim(0, df['Wind Gust'].max()+3)
    axs[4].set_ylim([0, 1350])
    
    # Salvar o gráfico em um arquivo
    plt.tight_layout()
    plt.savefig('graph.png', bbox_inches='tight')
    plt.close(fig)
