from bs4 import BeautifulSoup
import pandas as pd
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# -------------------------
# SETTINGS
# -------------------------

BASE_URL = "http://ufcstats.com/statistics/events/completed?page="
OUTPUT_FILE = "ufc_fights.csv"

MAX_PAGES = 1      # keep this at 1 while testing
MAX_EVENTS = 3     # keep this small while testing

SLEEP_TIME = 1


# -------------------------
# BROWSER SETUP
# -------------------------

def start_browser():
    options = Options()

    options.add_argument("--headless=new")

    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1400,1200")

    driver = webdriver.Chrome(options=options)

    return driver


def get_soup(driver, url, wait_for_class):
    print("Loading:", url)

    driver.get(url)

    wait = WebDriverWait(driver, 30)

    wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, wait_for_class))
    )

    html = driver.page_source

    print("HTML length:", len(html))

    soup = BeautifulSoup(html, "html.parser")

    return soup


# -------------------------
# GET EVENT LINKS
# -------------------------

def get_events_from_page(driver, page_number):
    url = BASE_URL + str(page_number)

    soup = get_soup(
        driver,
        url,
        "b-statistics__table-events"
    )

    events = []

    event_table = soup.find("table", class_="b-statistics__table-events")

    if event_table is None:
        print("Could not find event table.")
        return events

    rows = event_table.find_all("tr", class_="b-statistics__table-row")

    for row in rows:
        link = row.find("a", class_="b-link b-link_style_black")

        if link is None:
            continue

        event_name = link.text.strip()
        event_url = link.get("href")

        if event_name == "":
            continue

        if event_url is None:
            continue

        events.append({
            "event_name": event_name,
            "event_url": event_url
        })

    return events


def get_all_events(driver):
    all_events = []

    page_number = 1

    while True:
        if MAX_PAGES is not None and page_number > MAX_PAGES:
            break

        print()
        print("Scraping events page:", page_number)

        events = get_events_from_page(driver, page_number)

        print("Events found:", len(events))

        if len(events) == 0:
            break

        for event in events:
            all_events.append(event)

        page_number += 1

        time.sleep(SLEEP_TIME)

    return all_events


def get_fighter_names(fight_data):
    fighters = []

    if len(fight_data) < 2:
        return fighters

    name_cell = fight_data[1]

    name_tags = name_cell.find_all("p")

    for tag in name_tags:
        name = tag.text.strip()

        if name != "":
            fighters.append(name)

    return fighters


def scrape_event_fights(driver, event):
    event_name = event["event_name"]
    event_url = event["event_url"]

    print()
    print("Scraping event:", event_name)

    soup = get_soup(
        driver,
        event_url,
        "b-fight-details__table-body"
    )

    fight_table_body = soup.find("tbody", class_="b-fight-details__table-body")

    if fight_table_body is None:
        print("Could not find fight table body.")
        return []

    fight_rows = fight_table_body.find_all("tr", class_="b-fight-details__table-row")

    print("Fight rows found:", len(fight_rows))

    fights = []

    for fight_row in fight_rows:
        fight_data = fight_row.find_all("td")

        if len(fight_data) == 0:
            continue

        fighters = get_fighter_names(fight_data)

        if len(fighters) < 2:
            continue

        result = ""
        method = ""
        round_number = ""
        fight_time = ""

        if len(fight_data) > 0:
            result = fight_data[0].text.strip()

        if len(fight_data) > 7:
            method = fight_data[7].text.strip()

        if len(fight_data) > 8:
            round_number = fight_data[8].text.strip()

        if len(fight_data) > 9:
            fight_time = fight_data[9].text.strip()


        fight_details = {
            "event": event_name,
            "fighter_1": fighters[0],
            "fighter_2": fighters[1],
            "result": result,
            "method": method,
            "round": round_number,
            "time": fight_time
        }

        fights.append(fight_details)

    print("Fights scraped:", len(fights))

    return fights


# -------------------------
# MAIN PROGRAM
# -------------------------

def main():
    driver = start_browser()

    try:
        all_events = get_all_events(driver)

        print()
        print("Total events collected:", len(all_events))

        if MAX_EVENTS is not None:
            all_events = all_events[:MAX_EVENTS]

        all_fights = []

        for event in all_events:
            fights = scrape_event_fights(driver, event)

            for fight in fights:
                all_fights.append(fight)

            time.sleep(SLEEP_TIME)

        df = pd.DataFrame(all_fights)

        df.to_csv(OUTPUT_FILE, index=False)

        print()
        print("Done.")
        print("Total fights saved:", len(df))
        print("Output file:", OUTPUT_FILE)

        if len(df) > 0:
            print()
            print(df.head())

    finally:
        driver.quit()


if __name__ == "__main__":
    main()