import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from matplotlib.colors import ListedColormap, Normalize
import matplotlib.colors as mcolors
import numpy as np
import pytz
import json
import geopandas as gpd
import contextily as ctx
from datetime import datetime, timezone, timedelta
import os
from bs4 import BeautifulSoup
import folium
import re

# --- 3. Lista de Estações (Com POSTO ID e Coordenadas) ---
# Estrutura: [('Nome da Estação', POSTO_ID, Latitude, Longitude)]
estacoes_cge = [
    ("Penha", 1000887, -23.530763, -46.528744),
    ("Perus", 504, -23.40716, -46.75264),
    ("Pirituba", 515, -23.489, -46.727),
    ("Freguesia do Ó", 509, -23.47706, -46.66537),
    ("Santana", 510, -23.51064, -46.61746),
    ("Tremembé", 1000944, -23.459841, -46.585572),
    ("S. Miguel", 1000862, -23.491511, -46.46361),
    ("Itaim Paulista", 1000882, -23.49067, -46.43599),
    ("S. Mateus", 1000844, -23.594199, -46.465567),
    ("Sé", 503, -23.553, -46.656),
    ("Butantã", 1000842, -23.5545389, -46.7259528),
    ("Ipiranga", 1000840, -23.632978, -46.583518),
    ("Santo Amaro", 1000852, -23.634789, -46.667657),
    ("M Boi Mirim", 1000850, -23.671486, -46.727305),
    ("Cidade Ademar", 592, -23.6675, -46.675),
    ("Parelheiros", 507, -23.8678, -46.6522),
    ("Marsilac", 1000300, -23.916332, -46.727397),
    ("Lapa", 1000848, -23.52556, -46.75083),
    ("Campo Limpo", 1000854, -23.65818, -46.76749),
    ("Cap. Socorro Sub", 846, -23.723035, -46.699263),
    ("Cap. Socorro", 1000857, -23.781133, -46.725217),
    ("Vila Formosa", 1000859, -23.56403, -46.508234),
    ("Mooca", 1000860, -23.530444, -46.595059),
    ("Itaquera", 1000864, -23.552301, -46.44611),
    ("Vila Prudente", 524, -23.583219, -46.560179),
    ("Vila Maria", 540, -23.501611, -46.591534),
    ("Vila Mariana", 495, -23.58472, -46.63556),
    ("Riacho Grande", 400, -23.752079, -46.532528),
    ("Mauá", 1000876, -23.667, -46.465),
    ("S. de Parnaíba", 1000880, -23.43794, -46.90945),
    ("Jabaquara", 634, -23.650814, -46.646581),
    ("Pinheiros", 1000635, -23.551871, -46.695939)
]

def obter_dados_estacao(posto_id):
    url = f"https://www.cgesp.org/v3/estacao.jsp?POSTO={posto_id}"

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # 1. Tentar encontrar o bloco de chuva
        chuva_atual = 'N/D'
        chuva_element = soup.find(lambda tag: tag.name == 'td' and "Per. Atual:" in tag.text)
        if chuva_element:
            match = re.search(r'Per\. Atual:\s*(\d+[,.]\d+)\s*mm', chuva_element.text.replace(",", "."))
            if match:
                chuva_atual = float(match.group(1))

        # 2. Tentar encontrar a Temperatura Atual
        temperatura = 'N/D'
        temp_element = soup.find(lambda tag: tag.name == 'td' and "Atual:" in tag.text and "°C" in tag.text)
        if temp_element:
            match = re.search(r'Atual:\s*(\d+[,.]\d+)\s*°C', temp_element.text.replace(",", "."))
            if match:
                temperatura = float(match.group(1))

        dados_tempo_real = {
            "Temperatura": temperatura,
            "Chuva_Atual": chuva_atual,
            # Adicionando o campo, mas ele será N/D
            "Last_Update_Str": timestamp_texto
        }

        return dados_tempo_real

    except Exception as e:
        print(f"Erro ao processar dados da estação: {e}")
        return None

dados_para_plotagem = []
for nome, posto_id, lat, lon in estacoes_cge:
    dados_reais = obter_dados_estacao(posto_id)

    if dados_reais:
        dados_reais['Estacao'] = nome
        dados_reais['Latitude'] = lat
        dados_reais['Longitude'] = lon
        dados_para_plotagem.append(dados_reais)
    else:
        dados_para_plotagem.append({
            'Estacao': nome,
            'Latitude': lat,
            'Longitude': lon,
            'Temperatura': 'N/D',
            'Chuva_Atual': 'N/D'
        })
    print(f" -> Coletando dados para {nome} (Temp: {dados_reais.Temperatura})...")

df = pd.DataFrame(dados_para_plotagem)

# Código de hora/fuso horário no final (não usado para filtro nesta versão):
fuso_sp = pytz.timezone('America/Sao_Paulo')
agora_utc = datetime.now(pytz.utc)
agora_sp = agora_utc.astimezone(fuso_sp)
horario_formatado = agora_sp.strftime("%d/%b/%Y %H:%M")

# 1. DEFINIÇÃO DO COLORMAP CUSTOMIZADO
c1_mpl = np.flipud(plt.cm.gray(np.linspace(0, 1, 50)))
c2_mpl = plt.cm.turbo(np.linspace(0, 1, 176))
c3_mpl = plt.cm.pink(np.linspace(0, 1, 50))
col_combined_rgba = np.vstack((c1_mpl, c2_mpl, c3_mpl))

new_cmap = mcolors.LinearSegmentedColormap.from_list(
    'combined_cmap', col_combined_rgba, N=col_combined_rgba.shape[0]
)


# 2. Preparação dos Dados para GeoPandas (INCLUINDO CHUVA NUMÉRICA) <--- MUDANÇA AQUI
df['Temperatura_Num'] = df['Temperatura'].str.replace('°C', '').replace('N/D', np.nan).astype(float)
# Cria a coluna de chuva, substituindo N/D por 0 para que a barra não seja plotada
df['Chuva_Num'] = df['Chuva_Atual'].str.replace('mm', '').replace('N/D', '0').astype(float)

# Cria e projeta o GeoDataFrame
gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df.Longitude, df.Latitude),
    crs="EPSG:4326"
)
gdf_web_mercator = gdf.to_crs(epsg=3857)
gdf_plot = gdf_web_mercator[gdf_web_mercator['Temperatura_Num'].notna()]


# 3. Cria o objeto de figura e eixos do Matplotlib
fig, ax = plt.subplots(figsize=(10, 10))


# 4. Desenhar o Scatter Plot (Temperatura)
sc = gdf_plot.plot(
    ax=ax,
    column='Temperatura_Num',
    cmap=new_cmap,
    vmin=-10,
    vmax=45,
    markersize=450,
    alpha=0.8,
    edgecolors='black',
    legend=False
)


# 5. Adicionar o Fundo Geográfico (CartoDB Positron)
ctx.add_basemap(
    ax,
    source=ctx.providers.CartoDB.Positron,
    crs=gdf_web_mercator.crs
)

# 6. Personalização (Eixos e Título)
ax.set_title("Dados de Estações do CGE-SP - Temperatura e Precipitação", fontsize=14)
ax.set_axis_off()


# 7. Adicionar a Barra de Cores (Temperatura)
sm = plt.cm.ScalarMappable(cmap=new_cmap, norm=plt.Normalize(vmin=-10, vmax=45))
sm.set_array([])




# 8. Adicionar Barras de Chuva e Rótulos <--- MUDANÇA PRINCIPAL AQUI
estacoes_acima = ["Jabaquara", "Campo Limpo", "M Boi Mirim", "S. Miguel", "Vila Maria", "Santana", "Marsilac", "Pinheiros", "S. de Parnaíba", "Lapa"]
estacoes_esquerda = ["Campo Limpo", "Santana", "S. Miguel", "Parelheiros", "M Boi Mirim", "Cidade Ademar", "Butantã"]
deslocamento_barra_x = 1700  # Posição da barra ao lado do ponto (em metros)
largura_barra = 200         # Largura da barra (em metros)
escala_maxima_chuva = 15.0  # Chuva máxima para controle da altura (15mm)
altura_max_barra = 2000     # Altura máxima da barra no mapa (em metros)
deslocamento_nome = 1400    # Deslocamento do nome (para longe da barra)


for index, row in gdf_plot.iterrows():
    temp_num = row['Temperatura_Num']
    chuva_num = row['Chuva_Num'] # Usamos a nova coluna!
    x = row.geometry.x
    y = row.geometry.y
    nome_estacao = row['Estacao']

    if not pd.isna(temp_num):

        # --- 1. PLOTAGEM DA BARRA DE CHUVA (SE HOUVER CHUVA) ---
        if chuva_num > 0.0:
            # Normaliza a altura da barra:
            # (chuva_atual / escala_maxima) * altura_max_barra
            altura_barra = (chuva_num / escala_maxima_chuva) * altura_max_barra
            if altura_barra > altura_max_barra:
                altura_barra = altura_max_barra

            if nome_estacao in estacoes_esquerda:
              # Desenha a barra vertical (usando ax.bar)
              ax.bar(
                  x - deslocamento_barra_x, # Posição X (ao lado do marcador)
                  altura_barra,             # Altura da barra
                  width=largura_barra,      # Largura da barra
                  bottom=y-1000,                 # Começa na Latitude do ponto
                  color='blue',
                  alpha=0.7,
                  edgecolor='darkblue',
                  zorder=5 # Abaixo dos rótulos
              )

              if nome_estacao in estacoes_acima and chuva_num > 10:
                # Adiciona o rótulo do valor da chuva (topo da barra)
                ax.annotate(
                    f"{chuva_num:.1f}",
                    (x - deslocamento_barra_x - 500, y - altura_barra), # Posição: abaixo da barra
                    fontsize=7,
                    color='blue',
                    ha='center',
                    va='bottom',
                    fontweight='bold',
                    zorder=12
                )
              else:
                # Adiciona o rótulo do valor da chuva (topo da barra)
                ax.annotate(
                    f"{chuva_num:.1f}",
                    (x - deslocamento_barra_x - 500, y + altura_barra - 900), # Posição: topo da barra
                    fontsize=7,
                    color='blue',
                    ha='center',
                    va='bottom',
                    fontweight='bold',
                    zorder=12
                )
            else:
              # Desenha a barra vertical (usando ax.bar)
              ax.bar(
                  x + deslocamento_barra_x, # Posição X (ao lado do marcador)
                  altura_barra,             # Altura da barra
                  width=largura_barra,      # Largura da barra
                  bottom=y-1000,                 # Começa na Latitude do ponto
                  color='blue',
                  alpha=0.7,
                  edgecolor='darkblue',
                  zorder=5 # Abaixo dos rótulos
              )

              if nome_estacao in estacoes_acima and chuva_num > 10:
                # Adiciona o rótulo do valor da chuva (topo da barra)
                ax.annotate(
                    f"{chuva_num:.1f}",
                    (x + deslocamento_barra_x + 500, y - altura_barra - 900), # Posição: abaixo da barra
                    fontsize=7,
                    color='blue',
                    ha='center',
                    va='bottom',
                    fontweight='bold',
                    zorder=12
                )
              else:
                # Adiciona o rótulo do valor da chuva (topo da barra)
                ax.annotate(
                    f"{chuva_num:.1f}",
                    (x + deslocamento_barra_x + 500, y + altura_barra - 900), # Posição: topo da barra
                    fontsize=7,
                    color='blue',
                    ha='center',
                    va='bottom',
                    fontweight='bold',
                    zorder=12
                )


        # --- 2. PLOTAGEM DO RÓTULO DE TEMPERATURA (DENTRO) ---
        text_color = 'white'
        if 8 <= temp_num <= 32:
            text_color = 'black'

        ax.annotate(
            f"{temp_num:.1f}",
            (x, y),
            fontsize=8,
            color=text_color,
            ha='center',
            va='center',
            fontweight='bold',
            zorder=12
        )

        # --- 3. PLOTAGEM DO NOME DA ESTAÇÃO ---
        if nome_estacao in estacoes_acima:
            # Desloca o nome para longe da barra (e.g., para a esquerda)
            x_pos = x
            vertical_pos = y + deslocamento_nome
            alinhamento_horizontal = 'right' # Alinha à direita do ponto
            alinhamento_vertical = 'bottom'
        else:
            # Mantém à esquerda do ponto (longe da barra)
            x_pos = x
            vertical_pos = y - deslocamento_nome
            alinhamento_horizontal = 'right'
            alinhamento_vertical = 'top'

        ax.annotate(
            nome_estacao,
            (x_pos, vertical_pos),
            fontsize=7,
            ha='center',
            va=alinhamento_vertical,
            color='black',
            zorder=12
        )


# 9. ADICIONAR O HORÁRIO DE ATUALIZAÇÃO DOS DADOS (Mantido)
texto_horario = f"Última Atualização (BRT):\n{horario_formatado}"
box_props = dict(boxstyle="round,pad=0.5", fc="white", alpha=0.7, ec="black", lw=1)

ax.annotate(
    texto_horario,
    xy=(0.05, 0.07),
    xycoords='axes fraction',
    fontsize=9,
    ha='left',
    va='top',
    bbox=box_props
)

# 10. ADICIONAR O HORÁRIO DE ATUALIZAÇÃO DA CHUVA
texto_horario = "Chuva contabilizada desde as 07:00"
box_props = dict(boxstyle="round,pad=0.5", fc="white", alpha=0.7, ec="black", lw=1)

ax.annotate(
    texto_horario,
    xy=(0.60, 0.05),
    xycoords='axes fraction',
    fontsize=9,
    ha='left',
    va='top',
    bbox=box_props
)


# Salvar o gráfico em um arquivo
plt.tight_layout()
plt.savefig('mapa_cge.png', bbox_inches='tight')
plt.close(fig)
