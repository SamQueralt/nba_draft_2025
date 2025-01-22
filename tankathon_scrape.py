import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import unicodedata
from tqdm import tqdm
import time

def get_players(soup):
    player_list = []
    players = soup.select('.mock-row-name')

    for player in players:
        player_list.append(player.text)

    return list(set(player_list))

def get_player_links(players):
    link_list = []

    for player in players:
        player = player.lower().replace(' ', '-')
        player = player.lower().replace('.', '-')
        player = player.lower().replace('--', '-')
        player = unicodedata.normalize('NFKD', player)
        player = ''.join(c for c in player if not unicodedata.combining(c))
        
        link = 'https://www.tankathon.com/players/' + player
        link_list.append(link)

    return players, link_list

def acquire_player_pages(url):

    ## headers = {
    ##     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
    ## }

    response = requests.get(url) #, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        players = get_players(soup)

        link_list = get_player_links(players)

        return link_list

    else:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")

def stat_scrape(link):
    response = requests.get(link) #, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        bio_data = soup.select('.data')
        
        school = bio_data[0].text
        year = bio_data[1].text
        position = bio_data[2].text.split('/')

        height = bio_data[3].text.split(' ')[0]
        height_list = re.split(r'[\'\"]', height)  # re.findall(r'\d+', height)
        height_float = round(int(height_list[0]) + (float(height_list[1]) / 12), 2)
        # height = {'Feet' : height_list[0],
        #           'Inches': height_list[1]}

        weight = int(re.findall(r'\d+', bio_data[4].text)[0]) 
        rank = int(re.findall(r'\d+', bio_data[6].text)[0])

        try: # catch players that are not in the mock draft
            age = float(re.findall(r'\b\d+\.\d+\b', bio_data[7].text)[0])
        except:
            age = float(re.findall(r'\b\d+\.\d+\b', bio_data[6].text)[0])


        stat_labels = soup.select('.stat-label')

        for i, label in enumerate(stat_labels): # id 36 min stats
            if i > 14 and i < 30:
                stat_labels[i] = label.text + " per 36"
            else:
                stat_labels[i] = label.text

        stat_data = soup.select('.stat-data')
        stat_dict = {'School': school,
                    'Class': year,
                    'Position(s)': position,
                    'Height': height,
                    'Height (dec)': height_float,
                    'Weight': weight,
                    'Tankathon Rank': rank,
                    'Age': age}

        try: # catch players with wingspans
            wingspan = bio_data[3].text.split(' ')[1][1:]
            wingspan_list = re.split(r'[\'\"]', wingspan)
            wingspan_float = round(int(wingspan_list[0]) + (float(wingspan_list[1]) / 12), 2)

            stat_dict['Wingspan'] = wingspan
            stat_dict['Wingspan (dec)'] = wingspan_float
        except:
            stat_dict['Wingspan'] = ''
            stat_dict['Wingspan (dec)'] = ''

        for i in range(len(stat_labels)):
            try:
                stat_dict[stat_labels[i]] = float(stat_data[i].text)
            except:
                if stat_data[i].text:
                    label = re.search(r'(.*?)-(.*)', stat_labels[i])
                    stat = re.search(r'(.*?)-(.*)', stat_data[i].text)
                    stat_dict[label.group(1)] = float(stat.group(1))
                    stat_dict[label.group(2)] = float(stat.group(2))
                else:
                    stat_dict[stat_labels[i]] = ''

        return stat_dict
        
    else:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")


url = "https://www.tankathon.com/big_board"

players, links = acquire_player_pages(url)
player_list = []

for i in tqdm(range(len(links)), desc = 'Scraping Players:'):

    stats = stat_scrape(links[i])

    stats['Name'] = players[i]

    player_list.append(stats)

(pd.DataFrame(player_list)).to_csv('tankathon_scrape.csv', index = False)
