import pandas as pd
from bs4 import BeautifulSoup
import requests
import regex as re
import numpy as np

df = pd.read_csv("datasets/pokemon_card_data_ultimo.csv")


# Filtraggio del dataframe per avere solo Carte con Pokemon
def pokemon_filter(df, Pokemon):
    filtro = pd.Series([False] * len(df))
    for nome in Pokemon:
        regex = rf"\b{nome}\b"
        filtro = filtro | df['Nome Carta Pokemon'].str.contains(regex, case=False, na=False,
                                                                regex=True)
    return df[filtro]


def get_all_pokemon_generations():
    page = requests.get('https://pokemondb.net/pokedex/national')
    soup = BeautifulSoup(page.text, 'html.parser')

    generations = {}
    for gen in range(1, 10):
        gen_id = f'gen-{gen}'
        gen_section = soup.find('h2', id=gen_id)
        if gen_section:
            gen_pokemon = gen_section.find_next('div', class_='infocard-list infocard-list-pkmn-lg')
            if gen_pokemon:
                pokemon_names = gen_pokemon.find_all('a', class_='ent-name')
                generations[f'Gen-{gen}'] = [pokemon.get_text() for pokemon in pokemon_names]

    return generations


def clean_pokemon_name(name):
    name = re.sub(r'\s+(Ex|GX|V|VMAX|VSTAR)$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^(Alolan|Galarian|Hisuian)\s+', '', name, flags=re.IGNORECASE)
    # Rimuove simboli di genere e spazi extra
    name = re.sub(r'[♀♂]', '', name).strip()
    return name


# Funzione per trovare la generazione di un Pokémon
def find_generation(pokemon_name):
    cleaned_name = clean_pokemon_name(pokemon_name).lower()

    if cleaned_name in pokemon_to_gen:
        return pokemon_to_gen[cleaned_name]

    for base_name, gen in pokemon_to_gen.items():
        if base_name in cleaned_name or cleaned_name in base_name:
            return gen

    return 'Sconosciuta'


# Funzione per trovare nome Pokemon
def find_pokemon_name(card_name, Pokemon):
    for pokemon in Pokemon:
        if re.search(r'\b' + re.escape(pokemon) + r'\b', card_name, re.IGNORECASE):
            return pokemon
    return None


def convert_to_numeric(lst):
    result = []
    for item in lst:
        try:
            # Converti in float o int se possibile
            num = float(item)
            if not np.isnan(num):  # Aggiungi solo se non è NaN
                result.append(int(num) if num.is_integer() else num)
        except (ValueError, TypeError):  # Ignora se non è convertibile
            continue
    return result


if __name__ == '__main__':
    # Manipolazione colonne dataset
    df.rename(columns={'Nome Carta': 'Nome Carta Pokemon', 'Prezzo': 'Prezzo(€)', 'Edition': 'Edizione'}, inplace=True)

    # converto la colonna prezzi in valori numerici
    df.loc[5252, 'Prezzo(€)'] = 0.22
    df['Prezzo(€)'] = pd.to_numeric(df['Prezzo(€)'], errors='coerce')
    df['Prezzo(€)'] = df['Prezzo(€)'] * 1.16
    df['Prezzo(€)'] = df['Prezzo(€)'].round(2)

    # Accesso a una lista con i nomi di tutti i pokemon
    pagina = requests.get('https://pokemondb.net/pokedex/national#gen-9')
    soup = BeautifulSoup(pagina.text, 'html.parser')
    contenutogrezzo = soup.find_all('a', class_="ent-name")
    Pokemon = [p.get_text() for p in contenutogrezzo]
    Pokemon.remove('Nidoran♀')
    Pokemon.remove('Nidoran♂')
    Pokemon.append('Nidoran')

    # Applicare la funzione
    df_filtrato = pokemon_filter(df, Pokemon)

    # Ottieni tutte le generazioni in una sola chiamata
    all_generations = get_all_pokemon_generations()

    # Crea un dizionario per mappare ogni Pokémon alla sua generazione
    pokemon_to_gen = {clean_pokemon_name(pokemon).lower(): gen for gen, pokemon_list in all_generations.items() for
                      pokemon
                      in pokemon_list}

    # Assegna le generazioni al DataFrame
    df_filtrato = df_filtrato.copy()
    df_filtrato['Gen'] = df_filtrato['Nome Carta Pokemon'].apply(find_generation)

    # Raggruppa per 'Nome Carta Pokemon', 'Numero Carta', 'Set', 'Edizione', 'Gen', e 'Info Holo'
    # Concatena i valori dei prezzi come stringhe
    df_filtrato_2 = df_filtrato.groupby(['Nome Carta Pokemon', 'Numero Carta', 'Set', 'Edizione', 'Gen', 'Info Holo'])[
        'Prezzo(€)'].apply(lambda x: ', '.join(x.astype(str))).reset_index()

    # Esegui il pivot
    df_filtrato_2 = df_filtrato_2.pivot(index=['Nome Carta Pokemon', 'Numero Carta', 'Set', 'Edizione', 'Gen'],
                                        columns='Info Holo',
                                        values='Prezzo(€)').reset_index()

    # Rinomina le colonne per maggiore chiarezza
    df_filtrato_2.columns = ['Nome Carta Pokemon', 'Numero Carta', 'Set', 'Edizione', 'Gen',
                             'Prezzo Non-Holo', 'Prezzo Holo', 'Prezzo Reverse Holo']

    # Applica la funzione per trovare il nome del Pokémon
    df_filtrato_2['Pokemon'] = df_filtrato_2['Nome Carta Pokemon'].apply(lambda x: find_pokemon_name(x, Pokemon))

    # Raggruppa le carte per 'Nome Pokemon' e crea una lista delle carte per ogni Pokémon
    grouped_df = df_filtrato_2.groupby('Pokemon').agg({
        'Nome Carta Pokemon': lambda x: list(x),
        'Set': lambda x: set(x),
        'Gen': lambda x: set(x),
        'Prezzo Non-Holo': lambda x: list(x),
        'Prezzo Holo': lambda x: list(x),
        'Prezzo Reverse Holo': lambda x: list(x),
    }).reset_index()

    # Rinomina la colonna per chiarezza
    grouped_df = grouped_df.rename(
        columns={'Nome Carta Pokemon': 'Numero Carte', 'Set': 'Numero Set', 'Gen': 'Generazione Pokemon',
                 'Prezzo Non-Holo': 'Prezzo medio Non-Holo(€)', 'Prezzo Holo': 'Prezzo medio Holo(€)',
                 'Prezzo Reverse Holo': 'Prezzo medio Reverse Holo(€)'})
    # Numero Carte
    grouped_df['Numero Carte'] = grouped_df['Numero Carte'].apply(len)

    # Numero Set
    grouped_df['Numero Set'] = grouped_df['Numero Set'].apply(len)

    # Generazione Pokemon
    grouped_df['Generazione Pokemon'] = grouped_df['Generazione Pokemon'].apply(
        lambda x: ''.join(x))  # trasformazione da set a stringa
    grouped_df.at[267, 'Generazione Pokemon'] = 'Gen-8'  # rimozione di alcune eccezioni
    grouped_df.at[675, 'Generazione Pokemon'] = 'Gen-1'
    grouped_df.at[676, 'Generazione Pokemon'] = 'Gen-2'
    grouped_df['Generazione Pokemon'] = grouped_df['Generazione Pokemon'].astype('category')

    ####NON-HOLO#######
    grouped_df['Prezzo medio Non-Holo(€)'] = grouped_df['Prezzo medio Non-Holo(€)'].apply(convert_to_numeric)
    grouped_df['Prezzo medio Non-Holo(€)'] = grouped_df['Prezzo medio Non-Holo(€)'].apply(
        lambda x: [i for i in x if isinstance(i, (int, float)) and pd.notna(i)]
    )
    grouped_df['Prezzo medio Non-Holo(€)'] = grouped_df['Prezzo medio Non-Holo(€)'].apply(
        lambda x: sum(x) / len(x) if len(x) > 0 else 0)
    grouped_df['Prezzo medio Non-Holo(€)'] = grouped_df['Prezzo medio Non-Holo(€)'].round(2)

    ######HOLO#######
    grouped_df['Prezzo medio Holo(€)'] = grouped_df['Prezzo medio Holo(€)'].apply(convert_to_numeric)
    grouped_df['Prezzo medio Holo(€)'] = grouped_df['Prezzo medio Holo(€)'].apply(
        lambda x: [i for i in x if isinstance(i, (int, float)) and pd.notna(i)]
    )
    grouped_df['Prezzo medio Holo(€)'] = grouped_df['Prezzo medio Holo(€)'].apply(
        lambda x: sum(x) / len(x) if len(x) > 0 else 0)
    grouped_df['Prezzo medio Holo(€)'] = grouped_df['Prezzo medio Holo(€)'].round(2)

    ####REVERSE-HOLO#####
    grouped_df['Prezzo medio Reverse Holo(€)'] = grouped_df['Prezzo medio Reverse Holo(€)'].apply(convert_to_numeric)
    grouped_df['Prezzo medio Reverse Holo(€)'] = grouped_df['Prezzo medio Reverse Holo(€)'].apply(
        lambda x: [i for i in x if isinstance(i, (int, float)) and pd.notna(i)]
    )
    grouped_df['Prezzo medio Reverse Holo(€)'] = grouped_df['Prezzo medio Reverse Holo(€)'].apply(
        lambda x: sum(x) / len(x) if len(x) > 0 else 0)
    grouped_df['Prezzo medio Reverse Holo(€)'] = grouped_df['Prezzo medio Reverse Holo(€)'].round(2)

    grouped_df.to_csv("Datasetfinale_1.csv", index=False)