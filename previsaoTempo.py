import numpy as np
import requests
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.ticker import MaxNLocator
import matplotlib.image as mpimg
import textwrap
from datetime import datetime, timezone, timedelta
import pytz
from PIL import Image
import os

# Função para quebrar o texto entre palavras com um limite de largura
def wrap_text(text, width=13):
    return '\n'.join(textwrap.wrap(text, width=width))

# Define os parâmetros da API
WU_API_KEY = os.getenv('WU_API_KEY')

latitude = -23.56  # Latitude de São Paulo
longitude = -46.73  # Longitude de São Paulo
url = f"https://api.weather.com/v3/wx/forecast/daily/5day?geocode={latitude},{longitude}&format=json&units=m&language=pt&apiKey={WU_API_KEY}"

# Obtendo o horário atual em HBR
sao_paulo_tz = pytz.timezone("America/Sao_Paulo")
current_time = datetime.now(sao_paulo_tz)

# Formatação para exibir valores inteiros (0 casas decimais)
formatter = FuncFormatter(lambda x, _: f'{int(x)}')

# Faz a requisição para a API
response = requests.get(url)
if response.status_code == 200:
    # Extrai os dados JSON
    forecast_data = response.json()
    #print(forecast_data)
else:
    print(f"Erro na requisição: {response.status_code}")

# Preparando os dados para o gráfico
dias = forecast_data['dayOfWeek']
temp_max = forecast_data['calendarDayTemperatureMax']
temp_min = forecast_data['calendarDayTemperatureMin']
temp_max_parc = forecast_data['temperatureMax']
temp_min_parc = forecast_data['temperatureMin']
precip_volume = forecast_data['qpf']
narrativas = [narr.split('.')[0] + '.' for narr in forecast_data['narrative']]

dias[0] = 'Hoje'    ##################################################################
dias[1] = 'Amanhã'
name_days = forecast_data['daypart'][0]['daypartName']

posicao_amanha = name_days.index('Amanhã')

if posicao_amanha == 2: #Quando Hoje está disponivel e Amanhã é o terceiro elemento
  precip_prob = forecast_data['daypart'][0]['precipChance'][0::2]  # Filtra apenas as chances diurnas
  icons = forecast_data['daypart'][0]['iconCode'][0::2]  # Filtra apenas os ícones diurnos

elif posicao_amanha == 1: #Quando Hoje não esta disponivel e Amanhã é o segundo elemento
  precip_prob = forecast_data['daypart'][0]['precipChance'][1::2]  # Filtra apenas as chances diurnas
  icons = forecast_data['daypart'][0]['iconCode'][1::2]  # Filtra apenas os ícones diurnos
  ##################################################################

else: #Quando acontecer algo estranho e Amanhã estiver numa posição diferente do esperado
  precip_prob = forecast_data['daypart'][0]['precipChance'][posicao_amanha::2]  # Filtra apenas as chances diurnas
  icons = forecast_data['daypart'][0]['iconCode'][posicao_amanha::2]  # Filtra apenas os ícones diurnos


fig, ax1 = plt.subplots(figsize=(12, 10))

# Plot das temperaturas
ax1.plot(dias, temp_max, '-o', label='Temp máx', color='red')
ax1.plot(dias, temp_min, '-o', label='Temp mín', color='blue')
ax1.set_ylim(5*np.floor((min(temp_min)-4)/5), 5*np.ceil((max(temp_max)+4)/5))  # Ajusta o limite do eixo Y

# Adicionando as temperaturas no gráfico com asterisco para mínimas invertidas
for i in range(len(dias)):  ##
    max_temp = temp_max[i]  ##
    min_temp = temp_min[i]  ##

    # Exibe a temperatura máxima
    ax1.text(i, max_temp + 0.5, f'{max_temp}°C', ha='center', va='bottom', color='red', fontsize=20)  ##

    # Verifica se a mínima do dia seguinte (i+1) é invertida, comparando com a mínima parcial do dia atual (i)
    if i > 0 and min_temp < temp_min_parc[i - 1]: ##
        ax1.text(i, min_temp + 0.5, f'{min_temp}°C*', ha='center', va='bottom', color='blue', fontsize=20)  ##
    else: ##
        ax1.text(i, min_temp + 0.5, f'{min_temp}°C', ha='center', va='bottom', color='blue', fontsize=20) ##


# Plot da precipitação
ax2 = ax1.twinx()
bars = ax2.bar(dias, precip_volume, alpha=0.3, color='blue', label='Chuva') ##
ax2.set_ylabel('Precipitação (mm)', color='blue',fontsize=20)
ax2.tick_params(axis='y', labelcolor='blue')
ax2.set_ylim(0, max(20, 5*np.ceil(1.3*max(precip_volume)/5)))  # Ajusta o limite do eixo Y (mínimo ymax = 20 mm)

# Adicionando probabilidade e volume de chuva sobre cada barra
for i, (bar, prob, vol) in enumerate(zip(bars, precip_prob, precip_volume)):
    ax2.text(bar.get_x() + bar.get_width() / 2, ax2.get_ylim()[1] * 0.08, f'Prob: {prob} %', ha='center', color='blue', fontsize=11, transform=ax2.transData)
    ax2.text(bar.get_x() + bar.get_width() / 2, ax2.get_ylim()[1] * 0.03, f'{vol:.0f} mm', ha='center', color='blue', fontsize=16, transform=ax2.transData)

# Defina o mesmo número de ticks para os dois eixos
num_ticks = 6  # Pode ajustar conforme necessário
ax1.yaxis.set_major_locator(MaxNLocator(num_ticks))
ax2.yaxis.set_major_locator(MaxNLocator(num_ticks))

# Configurações finais do gráfico
ax1.set_xticks(range(len(dias)))
ax1.set_xticklabels(dias)
ax1.set_ylabel('Temperatura (°C)',fontsize=20)
ax1.set_title('Previsão do tempo para os próximos dias',fontsize=20)
ax1.grid(True, linestyle='--', alpha=0.5)
ax1.yaxis.set_major_formatter(formatter)
ax2.yaxis.set_major_formatter(formatter)

# Obtendo handles e labels de ambas as legendas
handles1, labels1 = ax1.get_legend_handles_labels()
handles2, labels2 = ax2.get_legend_handles_labels()

# Combinando os handles e labels das duas legendas em uma só
handles = handles1 + handles2
labels = labels1 + labels2

# Criando uma legenda única
ax1.legend(handles, labels, loc='best')  # Escolha a posição desejada para a legenda

# Adicionando os ícones e condições do tempo abaixo do gráfico
for i, (dia, cond) in enumerate(zip(dias, narrativas)):
    
    icone = icons[i]

    # Ícone fictício, substitua pelo caminho dos seus ícones para condições meteorológicas
    try:
        img = Image.open(f'iconesPrevisao/{icone}.png')
    except:
        img = Image.open(f'iconesPrevisao/{44}.png')
        
    # Redimensione a imagem (exemplo: 50% do tamanho original)
    img = img.resize((int(img.width * 0.5), int(img.height * 0.5)))

    #icon_path = f'iconesPrevisao/{icone}.png'

    #img = mpimg.imread(icon_path)
    if len(dias) == 6:
        ax1.figure.figimage(img, 110 + i * 120, 130, alpha=1.0, zorder=1)  # Ajuste a posição conforme necessário
    elif len(dias) == 5:
        ax1.figure.figimage(img, 110 + i * 150, 130, alpha=1.0, zorder=1)  # Ajuste a posição conforme necessário

    # Texto da condição abaixo do ícone
    # Aplica a quebra de linha à narrativa, sem quebrar palavras no meio
    cond_wrapped = wrap_text(cond, width=12)
    ax2.text(i, ax2.get_ylim()[1] * -0.27, cond_wrapped, ha='center', va='center', fontsize=10, color='black', transform=ax2.transData)

# Adicionando o texto "Fonte: Weather Channel" abaixo do gráfico
plt.text(0.5, -0.36, '* - A mínima desse dia acontecerá à noite', ha='center', va='center', fontsize=14, color='black', transform=ax1.transAxes) ##
plt.text(0.5, -0.4, 'Fonte: Weather Channel', ha='center', va='center', fontsize=14, color='black', transform=ax1.transAxes)

#plt.legend(loc='best')
plt.tight_layout()
plt.savefig('previsao.png', bbox_inches='tight')
plt.close(fig)
