import pandas as pd
import folium
import csv

# Detecta delimitador com sniff, fallback para ';'
with open('mapatktmedio.csv', encoding='utf-8-sig') as f:
    sample = f.read(2048)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=';,')
        sep = dialect.delimiter
    except csv.Error:
        sep = ';'

# Carrega o CSV e limpa colunas
df = pd.read_csv('mapatktmedio.csv', sep=sep, engine='python', encoding='utf-8-sig')
df.columns = df.columns.str.strip()

# Converte LATITUDE e LONGITUDE para float
for col in ['LATITUDE', 'LONGITUDE']:
    df[col] = (
        df[col].astype(str)
               .str.replace(',', '.', regex=False)
               .astype(float)
    )

# Converte coluna TKT MED para float, mantendo NaN para valores não numéricos
if 'TKT MED' in df.columns:
    df['TKT MED'] = (
        df['TKT MED'].astype(str)
                     .str.replace(r'[^0-9,.-]', '', regex=True)
                     .str.replace(',', '.', regex=False)
    )
    df['TKT MED'] = pd.to_numeric(df['TKT MED'], errors='coerce')

# Converte coluna LUCRO MEDIO para float e preenche NaN com zero
if 'LUCRO MEDIO' in df.columns:
    df['LUCRO MEDIO'] = (
        df['LUCRO MEDIO'].astype(str)
                        .str.replace(r'[^0-9,.-]', '', regex=True)
                        .str.replace(',', '.', regex=False)
    )
    df['LUCRO MEDIO'] = pd.to_numeric(df['LUCRO MEDIO'], errors='coerce').fillna(0)

# Remove linhas sem coordenadas
df = df.dropna(subset=['LATITUDE', 'LONGITUDE'])

# Função de cor baseada em regras com prioridade:
# 1) Sem comprar = 'NEGOCIACAO' -> laranja
# 2) ticket médio zero -> cinza
# 3) Faixa máxima/acima -> verde; demais -> vermelho
def color_by_rules(faixa, tkt_med, sem_comprar):
    # Regra 1: negociação
    if isinstance(sem_comprar, str) and sem_comprar.strip().upper() == 'NEGOCIACAO':
        return 'orange'
    # Regra 2: tkt médio zero
    if pd.notna(tkt_med) and tkt_med == 0:
        return 'gray'
    # Regra 3: faixa
    f = str(faixa).strip().upper()
    if any(k in f for k in ['MÁXIMO', 'MAXIMO', 'REGULAR', 'ACIMA']):
        return 'green'
    return 'red'

# Cria mapa usando o primeiro ponto como centro
def create_map(df):
    center = [df.iloc[0]['LATITUDE'], df.iloc[0]['LONGITUDE']]
    m = folium.Map(location=center, zoom_start=8)

    for supervisor, grp in df.groupby('SUPERVISOR'):
        fg = folium.FeatureGroup(name=supervisor, show=False)
        for _, row in grp.iterrows():
            cor = color_by_rules(row.get('FAIXA'), row.get('TKT MED'), row.get('SEM COMPRAR?'))
            icon = folium.Icon(icon='shopping-cart', prefix='fa', color=cor)
            tooltip = (
                f"Codigo: {row.get('CNPJ', '')}<br>"
                f"Fantasia: {row.get('FANTASIA', '')}<br>"
                f"Supervisor: {row.get('SUPERVISOR', '')}<br>"
                f"Vendedor: {row.get('VENDEDOR', '')}<br>"
                f"Rota: {row.get('ROTA', '')}<br>"
                f"Forma de pagamento: {row.get('FORMA DE PAGAMENTO', '')}<br>"
                f"Faixa: {row.get('FAIXA', '')}<br>"
                f"Sem comprar?: {row.get('SEM COMPRAR?', '')}<br>"
                f"Ticket Medio: {'R$ {:.2f}'.format(row['TKT MED']) if pd.notna(row['TKT MED']) else '-'}<br>"
                f"Lucro medio: R$ {row['LUCRO MEDIO']:.2f}<br>"
            )
            folium.Marker(location=[row['LATITUDE'], row['LONGITUDE']], icon=icon, tooltip=tooltip).add_to(fg)
        fg.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m

# Legenda dinâmica
legend = folium.Element(
    '<div style="position:fixed;bottom:50px;left:50px;width:300px;'
    'background:white;border:2px solid grey;z-index:9999;padding:10px;'
    'box-shadow:2px 2px 5px rgba(0,0,0,0.3)">' +
    '<b>Regras de cores:</b><br>' +
    '<b>🛑 Clientes com tkt médio abaixo de R$150,00</b><br>' +
    '<b>🟢Clientes com tkt médio acima de R$150,00</b><br>' +
    '<b>🟠 Clientes em negociação</b><br>' +
    '<b>⚫ Clientes que estão sem comprar há 90 dias</b><br>' +
    
   
    '</div>'
)

# Gera e salva mapa
mapa = create_map(df)
mapa.get_root().html.add_child(legend)
mapa.save('mapa_tudo_com_carrinho.html')
print('Mapa salvo em mapa_tudo_com_carrinho.html')
