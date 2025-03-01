import pandas as pd

df_final_1 = pd.read_csv("datasets/Datasetfinale_1.csv")
df_final_2 = pd.read_csv("datasets/pokemon_sentiment.csv")

df_final_2['Positivo'] = df_final_2['Positivo'] + (df_final_2['Neutrale'] / 2)
df_final_2['Negativo'] = df_final_2['Negativo'] + (df_final_2['Neutrale'] / 2)

df_final_2.drop(columns=['Neutrale'],inplace=True)


database = pd.merge(df_final_1, df_final_2, on='Pokemon', how='inner')
database.to_csv("database_ultimate.csv", index=False)