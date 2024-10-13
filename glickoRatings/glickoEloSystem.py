import pandas as pd
import math
from datetime import datetime
from collections import defaultdict

# Load the fight data
df = pd.read_csv("ufcfights.csv")

# Convert the event_date to datetime
df['event_date'] = pd.to_datetime(df['event_date'], errors='coerce')

# Sort fights by date in ascending order so the earliest fights are processed first
df = df.sort_values(by='event_date', ascending=True)

# Initialize constants for Glicko-2
DEFAULT_ELO = 1500
VOLATILITY = 0.06  # Example starting volatility
TAU = 0.5  # Controls volatility dynamics
RD_INIT = 350.0  # Initial rating deviation (uncertainty)
RD_MIN = 30.0  # Minimum rating deviation to avoid excessive confidence
K_FACTOR = 40  # Increased constant for Elo calculation due to fewer fights per year
BONUS_POINTS = 5  # Bonus points for early stoppages
BonusOn = True  # Boolean to toggle bonus points for early stoppages

# Store fighter ratings and volatility
glicko_data = defaultdict(lambda: {'rating': DEFAULT_ELO, 'rd': RD_INIT, 'volatility': VOLATILITY, 'last_fight': None, 'peak_rating': DEFAULT_ELO})

# Function to calculate Glicko-2 rating deviation (RD) decay based on inactivity
def calculate_rd_decay(current_rd, time_inactive_months):
    # Increase the RD based on how long the fighter has been inactive
    # Increase proportionally to their current RD, with a rate of 5% per month of inactivity
    new_rd = min(math.sqrt(current_rd**2 + (current_rd * 0.05 * time_inactive_months)**2), RD_INIT)
    return max(new_rd, RD_MIN)

# Function to update volatility based on Glicko-2
def update_volatility(current_volatility, rating, rd, expected_score, actual_score):
    variance = 1 / ((1 / (rd ** 2)) + (1 / (400 ** 2)))
    delta = variance * (actual_score - expected_score)
    new_volatility = current_volatility + TAU * (delta ** 2 - current_volatility ** 2)
    return max(new_volatility, 0.01)  # Ensure volatility is always positive

# Function to update Glicko ratings after a fight
def update_elo(winner, loser, event_date, method):
    winner_data = glicko_data[winner]
    loser_data = glicko_data[loser]

    # Calculate time since last fight in months
    if winner_data['last_fight'] is not None:
        time_inactive_winner = (event_date - winner_data['last_fight']).days / 30
        winner_data['rd'] = calculate_rd_decay(winner_data['rd'], time_inactive_winner)
    if loser_data['last_fight'] is not None:
        time_inactive_loser = (event_date - loser_data['last_fight']).days / 30
        loser_data['rd'] = calculate_rd_decay(loser_data['rd'], time_inactive_loser)

    # Update last fight date
    winner_data['last_fight'] = event_date
    loser_data['last_fight'] = event_date

    # Calculate expected score
    expected_winner = 1 / (1 + 10 ** ((loser_data['rating'] - winner_data['rating']) / 400))
    expected_loser = 1 / (1 + 10 ** ((winner_data['rating'] - loser_data['rating']) / 400))

    # Update ratings
    winner_data['rating'] += K_FACTOR * (1 - expected_winner)
    loser_data['rating'] += K_FACTOR * (0 - expected_loser)

    # Apply bonus points if the win was via an early stoppage and BonusOn is True
    if BonusOn and (method.startswith('KO/TKO') or method.startswith('SUB')):
        winner_data['rating'] += BONUS_POINTS

    # Update volatility for both fighters
    winner_data['volatility'] = update_volatility(winner_data['volatility'], winner_data['rating'], winner_data['rd'], expected_winner, 1)
    loser_data['volatility'] = update_volatility(loser_data['volatility'], loser_data['rating'], loser_data['rd'], expected_loser, 0)

    # Update peak ratings
    winner_data['peak_rating'] = max(winner_data['peak_rating'], winner_data['rating'])
    loser_data['peak_rating'] = max(loser_data['peak_rating'], loser_data['rating'])

    # Update RD (simplified, as Glicko-2 involves more complex calculations)
    winner_data['rd'] = max(winner_data['rd'] * 0.9, RD_MIN)  # Decrease RD after a fight
    loser_data['rd'] = max(loser_data['rd'] * 0.9, RD_MIN)

# Function to handle draw outcome
def handle_draw(fighter_1, fighter_2, event_date):
    fighter_1_data = glicko_data[fighter_1]
    fighter_2_data = glicko_data[fighter_2]

    # Calculate time since last fight in months
    if fighter_1_data['last_fight'] is not None:
        time_inactive_fighter_1 = (event_date - fighter_1_data['last_fight']).days / 30
        fighter_1_data['rd'] = calculate_rd_decay(fighter_1_data['rd'], time_inactive_fighter_1)
    if fighter_2_data['last_fight'] is not None:
        time_inactive_fighter_2 = (event_date - fighter_2_data['last_fight']).days / 30
        fighter_2_data['rd'] = calculate_rd_decay(fighter_2_data['rd'], time_inactive_fighter_2)

    # Update last fight date
    fighter_1_data['last_fight'] = event_date
    fighter_2_data['last_fight'] = event_date

    # Calculate expected score
    expected_fighter_1 = 1 / (1 + 10 ** ((fighter_2_data['rating'] - fighter_1_data['rating']) / 400))
    expected_fighter_2 = 1 / (1 + 10 ** ((fighter_1_data['rating'] - fighter_2_data['rating']) / 400))

    # Update ratings such that only the lower-rated fighter increases in rating
    if fighter_1_data['rating'] < fighter_2_data['rating']:
        fighter_1_data['rating'] += K_FACTOR * (0.5 - expected_fighter_1)
    elif fighter_2_data['rating'] < fighter_1_data['rating']:
        fighter_2_data['rating'] += K_FACTOR * (0.5 - expected_fighter_2)

    # Update volatility for both fighters
    fighter_1_data['volatility'] = update_volatility(fighter_1_data['volatility'], fighter_1_data['rating'], fighter_1_data['rd'], expected_fighter_1, 0.5)
    fighter_2_data['volatility'] = update_volatility(fighter_2_data['volatility'], fighter_2_data['rating'], fighter_2_data['rd'], expected_fighter_2, 0.5)

    # Update peak ratings
    fighter_1_data['peak_rating'] = max(fighter_1_data['peak_rating'], fighter_1_data['rating'])
    fighter_2_data['peak_rating'] = max(fighter_2_data['peak_rating'], fighter_2_data['rating'])

    # Update RD (simplified, as Glicko-2 involves more complex calculations)
    fighter_1_data['rd'] = max(fighter_1_data['rd'] * 0.9, RD_MIN)  # Decrease RD after a fight
    fighter_2_data['rd'] = max(fighter_2_data['rd'] * 0.9, RD_MIN)

# Iterate through each fight and update ratings
for _, fight in df.iterrows():
    fighter_1 = fight['fighter_1']
    fighter_2 = fight['fighter_2']
    result = fight['result']
    event_date = fight['event_date']
    method = fight.get('method', '').strip()  # Extract fight method if available

    if result == 'win':
        update_elo(fighter_1, fighter_2, event_date, method)
    elif result == 'loss':
        update_elo(fighter_2, fighter_1, event_date, method)
    elif result == 'draw':
        handle_draw(fighter_1, fighter_2, event_date)

# Convert the glicko_data to a DataFrame for analysis
ratings_df = pd.DataFrame.from_dict(glicko_data, orient='index').reset_index()
ratings_df.columns = ['fighter', 'rating', 'rd', 'volatility', 'last_fight', 'peak_rating']

# Sort the DataFrame by rating in descending order
ratings_df = ratings_df.sort_values(by='rating', ascending=False)

# Save the updated ratings to a CSV file
ratings_df.to_csv("ufc_fighter_ratings.csv", index=False)

# Create a DataFrame to track peak ratings
peak_ratings_df = ratings_df[['fighter', 'peak_rating']].copy()
peak_ratings_df = peak_ratings_df.sort_values(by='peak_rating', ascending=False)

# Save the peak ratings to a CSV file
peak_ratings_df.to_csv("ufc_fighter_peak_ratings.csv", index=False)

print("Ratings updated and saved to ufc_fighter_ratings.csv and peak ratings saved to ufc_fighter_peak_ratings.csv")