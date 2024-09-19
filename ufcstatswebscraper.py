import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# Base URL for UFC events
base_url = "http://ufcstats.com/statistics/events/completed?page="

# Function to get the HTML of a given page number
def get_page_html(page_number):
    url = base_url + str(page_number)
    response = requests.get(url)
    return BeautifulSoup(response.content, "html.parser")

# Scrape all pages of completed UFC events
all_events = []
page_number = 1
has_more_pages = True

while has_more_pages:
    soup = get_page_html(page_number)
    
    # Extract event details from the current page
    event_list = soup.find_all("a", class_="b-link b-link_style_black")
    if not event_list:
        has_more_pages = False  # Exit if no more events are found on the page
    else:
        for event in event_list:
            event_name = event.text.strip()
            event_url = event['href']
            all_events.append({"event_name": event_name, "event_url": event_url})
        
        page_number += 1  # Move to the next page
        time.sleep(1)  # Delay to avoid overloading the server

# Convert to DataFrame
events_df = pd.DataFrame(all_events)

# Scrape fights for each event and store them all in one list
all_fights = []
for index, row in events_df.iterrows():
    event_name = row['event_name']
    event_url = row['event_url']
    
    # Request the event page
    event_response = requests.get(event_url)
    event_soup = BeautifulSoup(event_response.content, "html.parser")
    
    # Scrape fight details (fight table)
    fight_table = event_soup.find("tbody")
    
    # Some pages might not have fights listed, so we check first
    if fight_table:
        for fight_row in fight_table.find_all("tr"):
            fight_data = fight_row.find_all("td")
            
            # Ensure the correct number of columns are present (should be 7 for each fight)
            if len(fight_data) >= 7:
                # Collect fight details
                fight_details = {
                    "event": event_name,
                    "fighter_1": fight_data[1].find_all("p")[0].text.strip(),  # First fighter name
                    "fighter_2": fight_data[1].find_all("p")[1].text.strip(),  # Second fighter name
                    "result": fight_data[0].text.strip(),  # Win/Loss
                    "method": fight_data[7].text.strip(),  # Method of victory
                    "round": fight_data[8].text.strip(),  # Round number
                    "time": fight_data[9].text.strip()  # Time of fight
                }
                
                # Append the fight details to the all_fights list
                all_fights.append(fight_details)
    
    
    time.sleep(1)  # 1-second delay between event scrapes

Convert the all_fights list into a DataFrame
all_fights_df = pd.DataFrame(all_fights)

Save the entire dataset to one CSV file
all_fights_df.to_csv("ufcfights.csv", index=False)
