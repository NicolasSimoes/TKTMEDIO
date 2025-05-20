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
# Remove linhas sem coordenadas
df = df.dropna(subset=['LATITUDE', 'LONGITUDE'])

# Cor por FAIXA
def color_by_faixa(faixa):
    f = str(faixa).strip().upper()
    return 'green' if any(k in f for k in ['MÁXIMO', 'MAXIMO', 'REGULAR', 'ACIMA']) else 'red'

# Cria mapa usando o primeiro ponto como centro (sem cálculo de média)
def create_map(df):
    first = df.iloc[0]
    center = [first['LATITUDE'], first['LONGITUDE']]
    m = folium.Map(location=center, zoom_start=8)

    # Plota todos os pontos agrupados por supervisor com ícone de carrinho
    for supervisor, grp in df.groupby('SUPERVISOR'):
        fg = folium.FeatureGroup(name=supervisor, show=False)
        for _, row in grp.iterrows():
            cor = color_by_faixa(row['FAIXA'])
            # Usa ícone de carrinho de mercado (FontAwesome)
            icon = folium.Icon(
                icon='shopping-cart',
                prefix='fa',
                color=cor
            )
            folium.Marker(
                location=[row['LATITUDE'], row['LONGITUDE']],
                icon=icon,
                tooltip=(
                     f"Codigo: {row['CNPJ']}<br>"
                    f"Fantasia: {row['FANTASIA']}<br>"
                    f"Supervisor: {row['SUPERVISOR']}<br>"
                      f"Venderdor: {row['VENDEDOR']}<br>"
                    f"Faixa: {row['FAIXA']}<br>"
                    f"Sem comprar?: {row['SEM COMPRAR?']}<br>"
                    f"Ticket Medio: {row['TKT MED']}<br>"
                    f"Lucro medio: {row['LUCRO MEDIO']}<br>"
                     
                )
            ).add_to(fg)
        fg.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m
legend = folium.Element(
    '<div style="position:fixed;bottom:50px;left:50px;width:300px;'
    'background:white;border:2px solid grey;z-index:9999;padding:10px;'
    'box-shadow:2px 2px 5px rgba(0,0,0,0.3)">' +
    f'<b> 🛑 Clientes com tkt médio abaixo de R$150,00</b><br>' +
    f'<b> 🟢 Clientes com tkt médio acima de R$150,00:</b><br>' +
    '</div>'   
)

# Gera o mapa
mapa = create_map(df)

# Adiciona a legenda ao HTML do mapa
mapa.get_root().html.add_child(legend)

mapa.save('mapa_tudo_com_carrinho.html')
print('Mapa salvo em mapa_tudo_com_carrinho.html')