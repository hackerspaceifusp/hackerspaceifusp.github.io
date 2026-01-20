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
from bs4 import BeautifulSoup
import folium
import re

# Fuso horário de Brasília
brasilia_tz = pytz.timezone("America/Sao_Paulo")

def obter_dados_estacao():
    url = "https://www.cgesp.org/v3/estacao.jsp?POSTO=1000842"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # 1. Tentar encontrar o bloco de chuva
        chuva_atual = 'N/D'
        chuva_element = soup.find(lambda tag: tag.name == 'td' and "Per. Atual:" in tag.text)
        if chuva_element:
            match = re.search(r'Per\. Atual:\s*(\d+[,.]\d+)\s*mm', chuva_element.text.replace(",", "."))
            if match:
                chuva_atual = f"{float(match.group(1)):.1f}mm"

        # 2. Tentar encontrar a Temperatura Atual
        temperatura = 'N/D'
        temp_element = soup.find(lambda tag: tag.name == 'td' and "Atual:" in tag.text and "°C" in tag.text)
        if temp_element:
            match = re.search(r'Atual:\s*(\d+[,.]\d+)\s*°C', temp_element.text.replace(",", "."))
            if match:
                temperatura = f"{float(match.group(1)):.1f}°C"

        # 3. Tentar encontrar a Umidade Atual
        umidade = 'N/D'
        umidade_element = soup.find(lambda tag: tag.name == 'td' and "Atual:" in tag.text and "%" in tag.text)
        if umidade_element:
            match = re.search(r'Atual:\s*(\d+[,.]\d+)\s*%', umidade_element.text.replace(",", "."))
            if match:
                umidade = f"{float(match.group(1)):.1f}%"
                gamma = np.log(umidade/100) + (17.625*temperatura)/(243.04 + temperatura)
                dew_point = (243.04 * gamma)/(17.625 - gamma)

        # 4. Tentar encontrar a Velocidade do Vento
        vento_velocidade = 'N/D'
        vento_element = soup.find(lambda tag: tag.name == 'td' and "Velocidade:" in tag.text)
        if vento_element:
            match = re.search(r'Velocidade:\s*(\d+[,.]\d+)\s*(km/h|m/s)', vento_element.text.replace(",", "."))
            if match:
                velocidade = float(match.group(1))
                unidade = match.group(2)
                vento_velocidade = f"{velocidade:.1f}{unidade}"

        timestamp = datetime.now(brasilia_tz)
      
        return temperatura, dew_point, chuva_atual, umidade, vento_velocidade, timestamp

    except requests.RequestException as e:
        print(f"Erro de requisição ao acessar a estação: {e}")
        timestamp = datetime.now(brasilia_tz)
        return None, None, None, None, None, timestamp
    except Exception as e:
        print(f"Erro inesperado no scraping da estação: {e}")
        return None, None, None, None, None, None




# Caminho do arquivo CSV
csv_file = 'CGE_weather_data.csv'

# Verificar se o arquivo existe
if os.path.exists(csv_file):
    # Ler os dados existentes
    df = pd.read_csv(csv_file, parse_dates=['Timestamp'])
    # Filtrar para manter apenas os dados das últimas 24 horas
    now = datetime.now(brasilia_tz)
    df = df[df['Timestamp'] >= now - pd.Timedelta(hours=24)]
else:
    # Criar um DataFrame vazio
    df = pd.DataFrame(columns=['Timestamp', 'Temperature', 'Humidity', 'Rain', 'WindSpeed', 'Dew Point'])

# Obter os dados atuais
temp, dew_point, rain, humidity, wind, timestamp = obter_dados_estacao()

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
            'Humidity': [humidity],
            'Rain': [rain],
            'WindSpeed': [wind],
            'Dew Point': [dew_point]
        })

        # Concatenar com o DataFrame existente
        df = pd.concat([df, new_data], ignore_index=True)

        # Filtrar para manter apenas os dados das últimas 24 horas
        now = datetime.now(brasilia_tz)
        df = df[df['Timestamp'] >= now - pd.Timedelta(hours=24)]

        # Salvar no arquivo CSV
        df.to_csv(csv_file, index=False)
        #Estacao On/Off
        estadoEstacao = 'Online'
    else:
        print("Dados já existentes para o timestamp:", timestamp)
        #Estacao On/Off
        estadoEstacao = 'Offline'

    # Configurar subplots
    fig, axs = plt.subplots(3, 1, figsize=(10, 11), sharex=True)
    fig.suptitle("Tempo nas últimas 24 horas")

    # Definir o colormap baseado na temperatura - NÃO ALTERAR O COLORMAP
    c1 = plt.cm.Purples(np.linspace(0, 1, 50))
    c2 = plt.cm.turbo(np.linspace(0, 1, 176))
    c3 = plt.cm.get_cmap('PuRd_r')(np.linspace(0, 1, 50))
    col = np.vstack((c1, c2, c3))
    cmap = plt.cm.colors.ListedColormap(col)
    cmap_hum = plt.cm.colors.ListedColormap(plt.cm.coolwarm(np.linspace(1, 0, 100)))
    cmap_rad = plt.cm.colors.ListedColormap(plt.cm.Blues(np.linspace(0, 1, 50)))
    temp_norm = (temp + 10) / 55  # Normaliza a temperatura dos limites [-10, 45]ºC para o intervalo [0, 1]
    temp_norm = np.clip(temp_norm, 0, 1)  # Garante que o valor esteja entre 0 e 1
    state_color = 'red' if estadoEstacao == "Offline" else 'green'
    temp_color = cmap(temp_norm)
    hum_color = cmap_hum(humidity / 100)
    precip_color = cmap_rad(rain / 50)

    hora_atual = f"{timestamp.hour:02d}"
    minuto_atual = f"{timestamp.minute:02d}"
    dia_atual = f"{timestamp.day:02d}"
    mes_atual = f"{timestamp.month:02d}"
    ano_atual = f"{timestamp.year}"
    fig.text(0.5, 0.99, estadoEstacao, color=state_color, fontsize=16, ha='center')
    # Exibir a temperatura, umidade, P.O. e pressão acima dos plots
    plt.figtext(0.5, 1.15, f"Condições meteorológicas atuais na USP (Poli) - Atualizado {dia_atual}/{mes_atual}/{ano_atual} às {hora_atual}:{minuto_atual}", fontsize=18, ha='center')
    
    quadrado = plt.Rectangle((0.15, 1.03), 0.22, 0.10, transform=fig.transFigure, color=temp_color, lw=0)
    fig.patches.append(quadrado)
    # Definir a cor do texto com base na temperatura
    text_color = 'white' if (temp >= 32 or temp < 8) else 'black'
    # Usar o texto com a cor definida
    plt.figtext(0.26, 1.055, f"Temperatura:\n {temp:.1f} °C", fontsize=20, ha='center', color=text_color)
    plt.figtext(0.26, 1.00, f"Ponto de orvalho: {dew_point:.1f} °C", fontsize=12, ha='center', color='black')

    quadrado = plt.Rectangle((0.39, 1.03), 0.22, 0.10, transform=fig.transFigure, color=hum_color, lw=0)
    fig.patches.append(quadrado)
    text_color = 'white' if (humidity >= 90) else 'black'
    plt.figtext(0.50, 1.055, f"Umidade:\n {humidity:.0f} %", fontsize=20, ha='center', color=text_color)

    quadrado = plt.Rectangle((0.63, 1.03), 0.22, 0.10, transform=fig.transFigure, color=precip_color, lw=0)
    fig.patches.append(quadrado)
    text_color = 'white' if (rain >= 30) else 'black'
    plt.figtext(0.74, 1.055, f"Chuva acum.:\n {rain:.1f} mm", fontsize=20, ha='center', color=text_color)

    
 
    
    # Temperatura
    axs[0].plot(df['Timestamp'], df['Temperature'], label="Temperatura", color='red', marker='o')
    axs[0].plot(df['Timestamp'], df['Dew Point'], label="Ponto de orvalho", color="green", linestyle="--", marker='o',markersize=3)
    axs[0].set_ylabel("Temperatura (°C)",fontsize=14)
    axs[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x}"))
    axs[0].legend(loc="upper left")
    axs[0].grid(True)
    for label in axs[0].get_yticklabels(): #Tamanho dos rótulos
        label.set_fontsize(14)

    # Umidade
    axs[1].plot(df['Timestamp'], df['Humidity'], color='blue', marker='o')
    axs[1].set_ylabel("Umidade relativa (%)",fontsize=14)
    axs[1].set_ylim([0, 102]) 
    axs[1].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}"))
    axs[1].grid(True)
    for label in axs[1].get_yticklabels(): #Tamanho dos rótulos
        label.set_fontsize(14)

    # Pressão
    axs[2].plot(df['Timestamp'], df['Rain'], color='black', marker='o')
    axs[2].set_ylabel("Chuva (mm)",fontsize=14)
    axs[2].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}"))
    axs[2].grid(True)
    for label in axs[2].get_yticklabels(): #Tamanho dos rótulos
        label.set_fontsize(14)

    # Formatação do eixo X
    axs[2].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M', tz=brasilia_tz))
    axs[2].xaxis.set_major_locator(mdates.HourLocator(interval=2))
    axs[2].set_xlim([start_time, end_time])
    for label in axs[2].get_xticklabels():
        label.set_fontsize(14)
    plt.xlabel("Hora local",fontsize=14)
    plt.gcf().autofmt_xdate()

    # Configurar limites para cada eixo Y em cada subplot
    axs[0].set_ylim(df['Dew Point'].min()-2, df['Temperature'].max()+2)
    #axs[1].set_ylim(max(df['Humidity'].min()-10, 0), 101)
    axs[2].set_ylim(0, df['Rain'].max()+5)

    # Salvar o gráfico em um arquivo
    plt.tight_layout()
    plt.savefig('graph_cge.png', bbox_inches='tight')
    plt.close(fig)

else:
    print("Dados não foram obtidos.")
    estadoEstacao = 'Offline'

    # Configurar subplots
    fig, axs = plt.subplots(3, 1, figsize=(10, 11), sharex=True)
    fig.suptitle("Tempo e Extremos nas últimas 24 horas")

    # Definir o colormap baseado na temperatura - NÃO ALTERAR O COLORMAP
    c1 = plt.cm.Purples(np.linspace(0, 1, 50))
    c2 = plt.cm.turbo(np.linspace(0, 1, 176))
    c3 = plt.cm.get_cmap('PuRd_r')(np.linspace(0, 1, 50))
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
    fig.text(0.5, 0.99, estadoEstacao, color=state_color, fontsize=16, ha='center')
    # Exibir a temperatura, umidade, P.O. e pressão acima dos plots
    plt.figtext(0.5, 1.15, f"Condições meteorológicas atuais na USP (Poli) - Atualizado {dia_atual}/{mes_atual}/{ano_atual} às {hora_atual}:{minuto_atual}", fontsize=18, ha='center')
    
    quadrado = plt.Rectangle((0.15, 1.03), 0.22, 0.10, transform=fig.transFigure, color=temp_color, lw=0)
    fig.patches.append(quadrado)
    text_color = 'black'
    # Usar o texto com a cor definida
    plt.figtext(0.26, 1.055, f"Temperatura:\n NaN °C", fontsize=20, ha='center', color=text_color)
    plt.figtext(0.26, 1.00, f"Ponto de orvalho: NaN °C", fontsize=12, ha='center', color='black')

    quadrado = plt.Rectangle((0.39, 1.03), 0.22, 0.10, transform=fig.transFigure, color=hum_color, lw=0)
    fig.patches.append(quadrado)
    plt.figtext(0.50, 1.055, f"Umidade:\n NaN %", fontsize=20, ha='center', color='black')

    quadrado = plt.Rectangle((0.63, 1.03), 0.22, 0.10, transform=fig.transFigure, color=precip_color, lw=0)
    fig.patches.append(quadrado)
    plt.figtext(0.74, 1.055, f"Chuva acum.:\n NaN mm", fontsize=20, ha='center', color='black')
  

    # Temperatura
    axs[0].plot(df['Timestamp'], df['Temperature'], label="Temperatura", color='red', marker='o')
    axs[0].plot(df['Timestamp'], df['Dew Point'], label="Ponto de orvalho", color="green", linestyle="--", marker='o',markersize=3)
    axs[0].set_ylabel("Temperatura (°C)",fontsize=14)
    axs[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x}"))
    axs[0].legend(loc="upper left")
    axs[0].grid(True)
    for label in axs[0].get_yticklabels(): #Tamanho dos rótulos
        label.set_fontsize(14)

    # Umidade
    axs[1].plot(df['Timestamp'], df['Humidity'], color='blue', marker='o')
    axs[1].set_ylabel("Umidade relativa (%)",fontsize=14)
    axs[1].set_ylim([0, 110]) 
    axs[1].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}"))
    axs[1].grid(True)
    for label in axs[1].get_yticklabels(): #Tamanho dos rótulos
        label.set_fontsize(14)

    # Pressão
    axs[2].plot(df['Timestamp'], df['Rain'], color='black', marker='o')
    axs[2].set_ylabel("Chuva (mm)",fontsize=14)
    axs[2].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}"))
    axs[2].grid(True)
    for label in axs[2].get_yticklabels(): #Tamanho dos rótulos
        label.set_fontsize(14)

    # Formatação do eixo X
    axs[2].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M', tz=brasilia_tz))
    axs[2].xaxis.set_major_locator(mdates.HourLocator(interval=2))
    axs[2].set_xlim([start_time, end_time])
    for label in axs[2].get_xticklabels():
        label.set_fontsize(14)
    plt.xlabel("Hora local",fontsize=14)
    plt.gcf().autofmt_xdate()

    # Configurar limites para cada eixo Y em cada subplot
    axs[0].set_ylim(df['Dew Point'].min()-2, df['Temperature'].max()+2)
    #axs[1].set_ylim(max(df['Humidity'].min()-10, 0), 101)
    axs[2].set_ylim(0, df['Rain'].max()+5)

    # Salvar o gráfico em um arquivo
    plt.tight_layout()
    plt.savefig('graph_cge.png', bbox_inches='tight')
    plt.close(fig)
