import pandas as pd
import folium
import csv
from folium.plugins import HeatMap

# 1) Detecta delimitador com sniff, fallback para ';'
with open('mapatktmedio.csv', encoding='utf-8-sig') as f:
    sample = f.read(2048)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=';,')
        sep = dialect.delimiter
    except csv.Error:
        sep = ';'

# 2) Carrega o CSV e padroniza colunas
df = pd.read_csv('mapatktmedio.csv', sep=sep, engine='python', encoding='utf-8-sig')
df.columns = df.columns.str.strip()

# 3) Converte LATITUDE e LONGITUDE para float
for col in ['LATITUDE', 'LONGITUDE']:
    df[col] = (
        df[col].astype(str)
               .str.replace(',', '.', regex=False)
               .astype(float)
    )

# 4) Converte TKT MED para float
if 'TKT MED' in df.columns:
    tmp = df['TKT MED'].astype(str).str.replace(r'[^0-9,.-]', '', regex=True)
    tmp = tmp.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    df['TKT MED'] = pd.to_numeric(tmp, errors='coerce')

# 5) Converte LUCRO MEDIO para float corretamente (remove milhares)
if 'LUCRO MEDIO' in df.columns:
    tmp = df['LUCRO MEDIO'].astype(str).str.replace(r'[^0-9,.-]', '', regex=True)
    # remove pontos de milhares, depois vírgula decimal
    tmp = tmp.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    df['LUCRO MEDIO'] = pd.to_numeric(tmp, errors='coerce').fillna(0)

# 6) Converte % MARGEM CONTRIBUIÇÃO e define peso fixo
if '% MARGEM CONTRIBUIÇÃO' in df.columns:
    tmp = df['% MARGEM CONTRIBUIÇÃO'].astype(str).str.replace(r'[^0-9,.-]', '', regex=True)
    tmp = tmp.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    df['% MARGEM CONTRIBUIÇÃO'] = pd.to_numeric(tmp, errors='coerce')
    # Peso fixo: <25% => 1000, >=25% => 10
    df['heat_weight'] = df['% MARGEM CONTRIBUIÇÃO'].apply(
        lambda x: 1000 if pd.notna(x) and x < 25 else (10 if pd.notna(x) else 0)
    )
else:
    df['heat_weight'] = 0

# 7) Remove linhas sem coordenadas
df = df.dropna(subset=['LATITUDE', 'LONGITUDE'])

# 8) Função de cores para marcadores
import numpy as np

def color_by_rules(faixa, tkt_med, sem_comprar):
    if isinstance(sem_comprar, str) and sem_comprar.strip().upper() == 'NEGOCIACAO':
        return 'orange'
    if pd.notna(tkt_med) and tkt_med == 0:
        return 'gray'
    f = str(faixa).strip().upper()
    if any(k in f for k in ['MÁXIMO', 'MAXIMO', 'REGULAR', 'ACIMA']):
        return 'green'
    return 'red'

# 9) Cria o mapa e adiciona HeatMap estático no gradiente
m = folium.Map(location=[df.iloc[0]['LATITUDE'], df.iloc[0]['LONGITUDE']], zoom_start=12)
heat_data = df[['LATITUDE', 'LONGITUDE', 'heat_weight']].values.tolist()
HeatMap(
    heat_data,
    name='Heatmap Margem Contribuição',
    min_opacity=0.8,
    radius=15,
    blur=10,
    max_zoom=18,
    max_val=1000,
    use_local_extrema=False,
    scale_radius=True,
    gradient={
        '0.0': 'blue',
        '0.5': 'lime',
        '0.8': 'orange',
        '1.0': 'red'
    }
).add_to(m)

# 10) Adiciona marcadores por supervisor
for supervisor, grp in df.groupby('SUPERVISOR'):
    fg = folium.FeatureGroup(name=supervisor, show=False)
    for _, row in grp.iterrows():
        cor = color_by_rules(row.get('FAIXA'), row.get('TKT MED'), row.get('SEM COMPRAR?'))
        icon = folium.Icon(icon='shopping-cart', prefix='fa', color=cor)
        tooltip = (
            f"Codigo: {row.get('CNPJ','')}<br>"
            f"Fantasia: {row.get('FANTASIA','')}<br>"
            f"Supervisor: {row.get('SUPERVISOR','')}<br>"
            f"Vendedor: {row.get('VENDEDOR','')}<br>"
            f"Rota: {row.get('ROTA','')}<br>"
            f"Forma de pagamento: {row.get('FORMA DE PAGAMENTO','')}<br>"
            f"Faixa: {row.get('FAIXA','')}<br>"
            f"Sem comprar?: {row.get('SEM COMPRAR?','')}<br>"
            f"Ticket Medio: {'R$ {:.2f}'.format(row['TKT MED']) if pd.notna(row['TKT MED']) else '-'}<br>"
            f"Lucro medio: R$ {row['LUCRO MEDIO']:.2f}<br>"
            f"Margem Contr.: {'{:.2f}%'.format(row['% MARGEM CONTRIBUIÇÃO']) if pd.notna(row['% MARGEM CONTRIBUIÇÃO']) else '-'}<br>"
        )
        folium.Marker([row['LATITUDE'], row['LONGITUDE']], icon=icon, tooltip=tooltip).add_to(fg)
    fg.add_to(m)

# 11) Legenda e salvar
legend = folium.Element(
    '<div style="position:fixed;bottom:50px;left:50px;width:300px;'
    'background:white;border:2px solid grey;z-index:9999;padding:10px;'
    'box-shadow:2px 2px 5px rgba(0,0,0,0.3)">' +
    '<b>Regras de cores:</b><br>' +
    '<b>🛑 Clientes com TKT MEDIO abaixo de R$150,00</b><br>' +
    '<b>🟢Clientes com TKT MEDio acima de R$150,00</b><br>' +
    '<b>🟠 Clientes em negociação</b><br>' +
    '<b>⚫ Clientes que estão sem comprar há 90 dias</b><br>' +
    '<b>🔥 Calor = Margem de contribuição < 25% </b><br>' +
    '<b> ❄ Frio = Margem de contribuição > 25% </b><br>' +
    '</div>'
)


m.get_root().html.add_child(legend)
folium.LayerControl(collapsed=False).add_to(m)
m.save('mapa_tudo_com_carrinho_heatmap.html')
print('Mapa salvo em mapa_tudo_com_carrinho_heatmap.html')
