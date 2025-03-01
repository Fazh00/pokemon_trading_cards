import requests
from bs4 import BeautifulSoup
import praw
import pandas as pd
from transformers import pipeline
import numpy as np
from tqdm import tqdm
import swifter

tqdm.pandas()

#Raccolta commenti di un post per ogni Pokemon
def get_comments_for_pokemon(reddit, pokemon_name, subreddit='Pokemon', limit=1):
    try:
        search_results = reddit.subreddit(subreddit).search(pokemon_name, limit=limit)
        all_comments = []
        for submission in search_results:
            print(f"Post trovato: {submission.title} (ID: {submission.id})")
            submission.comments.replace_more(limit=None)
            all_comments.extend([comment.body for comment in submission.comments.list()])

        return all_comments
    except Exception as e:
        print(f"Errore durante il recupero dei commenti per {pokemon_name}: {str(e)}")
        return []



# Classificatore basato su Roberta
classifier = pipeline("sentiment-analysis", model='cardiffnlp/twitter-roberta-base-sentiment-latest',
                      tokenizer='cardiffnlp/twitter-roberta-base-sentiment-latest', top_k=None)


def extract_results(doc):
    if len(doc.split()) > 0:
        try:
            try:
                output = classifier(doc)
                return {item.get('label'): item.get('score') for item in
                        output[0]}
            except:
                truncated_words = doc.split()[:300]
                doc = ' '.join(truncated_words)
                output = classifier(doc)
                return {item.get('label'): item.get('score') for item in output[0]}
        except:
            return None
    else:
        return None


if __name__ == '__main__':

    # Accesso a Reddit
    reddit = praw.Reddit(client_id="zicoLWBapm8glD5xqAJBsQ",
                         client_secret="DOe0vIEAWGkg9WE18O3-YOS9DBYkbA",
                         user_agent="Pokemon_project",
                         )
    #Lista di nomi di tutti i Pokemon
    pagina = requests.get('https://pokemondb.net/pokedex/national#gen-9')
    soup = BeautifulSoup(pagina.text, 'html.parser')
    contenuto_pokemon = soup.find_all('a', class_="ent-name")
    Pokemon = [p.get_text() for p in contenuto_pokemon]
    pokemon_list = Pokemon

    dati = []

    for pokemon in pokemon_list:
        comments = get_comments_for_pokemon(reddit, pokemon)
        for comment in comments:
            dati.append({
                "Pokemon": pokemon,
                "Content": comment}
            )
        print("\n" + "=" * 50 + "\n")

    df = pd.DataFrame(dati)
    df["sentiment_score"] = df["Content"].swifter.progress_bar().apply(extract_results)
    df[['Neutrale', 'Positivo', 'Negativo']] = df['sentiment_score'].apply(pd.Series)
    df.drop(columns=['sentiment_score'],
            inplace=True)
    df.to_csv('pokemon_comments.csv', index=False)

    df.drop(columns=['Content'], inplace=True)
    df_Final = df.groupby('Pokemon').mean().reset_index()
    df_Final.to_csv('pokemon_sentiment.csv', index=False)