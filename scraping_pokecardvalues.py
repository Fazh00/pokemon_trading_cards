import tqdm
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup


##funzione di scrolling della pagina##
def scroll_page(driver, scroll_pause_time=10):
    last_height = driver.execute_script(
        "return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause_time)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def extract_data(soup):
    # Estrazione prezzi
    prezzi = [p.get_text(strip=True).replace('NM/M VALUE:', '').replace('£', '').replace(',', '') for p in
              soup.find_all('div', class_="price-info")]

    # Estrazione Nome e numeri carte
    card_info = [ci.get_text(strip=True) for ci in soup.find_all('div', class_="card-title-info")]
    nome_carta = [ci.split(' - ')[0] for ci in card_info]
    numeri_carte = [ci.split(' - ')[1] if '-' in ci else '' for ci in
                    card_info]

    # Estrazione Info carte
    card_info_elements = soup.find_all('div', class_="card-holo-edition-info")
    Holo_info = [br.previous_sibling.strip() for element in card_info_elements for br in element.find_all('br') if
                 br.previous_sibling]
    Rarity = [br.next_sibling.split(" - ")[0] for element in card_info_elements for br in element.find_all_next('br') if
              br.next_sibling]
    Edition = [br.next_sibling.split(" - ")[1].strip() for element in card_info_elements for br in
               element.find_all_next('br') if br.next_sibling]

    Set = [soup.find('strong').getText()]
    Set = [s for s in Set * len(nome_carta)]

    return nome_carta, numeri_carte, prezzi, Holo_info, Rarity, Edition, Set


def main():
    driver_path = "chromedriver/chromedriver.exe"
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service)

    url_iniziale = "https://pokecardvalues.co.uk/sets/"
    all_data = []

    try:
        driver.get(url_iniziale)
        wait = WebDriverWait(driver, 10)
        links = wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, 'a')))

        card_set_links = list(set([link.get_attribute('href') for link in links
                                   if link.get_attribute('href') and "sets" in link.get_attribute('href')
                                   and '?' not in link.get_attribute('href') and '#' not in link.get_attribute('href')
                                   and link.get_attribute('href') != url_iniziale]))

        for link in tqdm.tqdm(card_set_links, desc="SCRAPING CARD SETS..."):
            try:
                driver.get(link)
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "price-info")))
                scroll_page(driver)

                html_content = driver.page_source
                soup = BeautifulSoup(html_content, 'html.parser')

                nome_carta, numeri_carte, prezzi, Holo_info, Rarity, Edition, Set = extract_data(soup)

                for i in range(len(nome_carta)):
                    all_data.append({
                        'Nome Carta': nome_carta[i],
                        'Numero Carta': numeri_carte[i] if i < len(numeri_carte) else '',
                        'Prezzo': prezzi[i] if i < len(prezzi) else '',
                        'Info Holo': Holo_info[i] if i < len(Holo_info) else '',
                        'Rarità': Rarity[i] if i < len(Rarity) else '',
                        'Edition': Edition[i] if i < len(Edition) else '',
                        'Set': Set[i] if i < len(Set) else '',
                    })
            except Exception as e:
                print(f"Errore durante lo scraping del set {link}:{e}")
    except Exception as e:
        print(f"Si è verificato un errore: {e}")

    finally:
        driver.quit()

    # Salva i dati in un file CSV
    df = pd.DataFrame(all_data)
    df.to_csv('pokemon_card_data_ultimo.csv', index=False)
    print("Dati salvati in 'pokemon_card_data.csv'")


if __name__ == "__main__":
    main()
