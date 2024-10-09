import pandas as pd
import numpy as np

# Load the CSV
ufcfights_not_sorted = pd.read_csv("ufcfights_update.csv", index_col=0)
ufcfights = ufcfights_not_sorted.reset_index()

# Sort with the most recent at the bottom
ufcfights = ufcfights.sort_index(ascending=False)

# Create unique event IDs
unique_events = ufcfights[['event']].drop_duplicates().reset_index(drop=True)

unique_events['event_id'] = range(1, len(unique_events) + 1)
ufcfights = ufcfights.merge(unique_events, on='event')

#clean up KO and Subs
ufcfights['method'] = ufcfights['method'].apply(lambda x: 'KO' if 'KO' in x else ('SUB' if 'SUB' in x else x))
# Drop unnecessary columns
ufcfights.drop(columns=["round", "time"], inplace=True)

#NEW - elo update for method
def get_k_factor(method, base_k=40):
    if method == 'KO' or method == 'SUB':
        return base_k * 1.15  # Increase K by 15% for KO or submission
    else:
        return base_k  # Default to base K for other outcomes

# Initialize Elo ratings
initial_elo = 1000
elo_ratings = {}
base_k_factor = 40
peak_elo_ratings = {}

# Function to calculate the expected score
def expected_score(elo_a, elo_b):
    return 1/(1+10**((elo_b - elo_a) / 400))

# Function to update Elo ratings
def update_elo(winner_elo, loser_elo, k_factor):
    expected_win = expected_score(winner_elo, loser_elo)
    new_winner_elo = winner_elo + k_factor * (1 - expected_win)
    new_loser_elo = loser_elo + k_factor * (0 - (1 - expected_win))
    return round(new_winner_elo, 2), round(new_loser_elo, 2)

# Create unique match IDs
ufcfights['cc_match'] = np.arange(1, len(ufcfights) + 1)

# Add columns for Elo ratings
ufcfights['fighter_1_elo_start'] = 0
ufcfights['fighter_2_elo_start'] = 0
ufcfights['fighter_1_elo_end'] = 0
ufcfights['fighter_2_elo_end'] = 0

# Calculate Elo ratings for each match
for index, row in ufcfights.iterrows():
    fighter_1 = row['fighter_1']
    fighter_2 = row['fighter_2']

    # Initialize Elo ratings if fighters are encountered for the first time
    if fighter_1 not in elo_ratings:
        elo_ratings[fighter_1] = initial_elo
    if fighter_2 not in elo_ratings:
        elo_ratings[fighter_2] = initial_elo


    # Get starting Elo ratings
    fighter_1_elo_start = elo_ratings[fighter_1]
    fighter_2_elo_start = elo_ratings[fighter_2]

    #kfactor adjust
    fight_method = row["method"]
    current_k = get_k_factor(fight_method,base_k_factor)


    # Record starting Elo ratings
    ufcfights.at[index, 'fighter_1_elo_start'] = fighter_1_elo_start
    ufcfights.at[index, 'fighter_2_elo_start'] = fighter_2_elo_start

    # Update Elo based on the result
    if row['result'] == 'win':  # Fighter 1 wins
        new_fighter1_elo, new_fighter2_elo = update_elo(fighter_1_elo_start, fighter_2_elo_start, current_k)
    elif row["result"] == 'draw':  # Draw
        new_fighter1_elo, new_fighter2_elo = update_elo(fighter_1_elo_start, fighter_2_elo_start, current_k / 2)
    else:  # No contest
        new_fighter1_elo, new_fighter2_elo = fighter_1_elo_start, fighter_2_elo_start
    
    if fighter_1 not in peak_elo_ratings or new_fighter1_elo > peak_elo_ratings[fighter_1]:
        peak_elo_ratings[fighter_1] = new_fighter1_elo
    if fighter_2 not in peak_elo_ratings or new_fighter2_elo > peak_elo_ratings[fighter_2]:
        peak_elo_ratings[fighter_2] = new_fighter2_elo

    # Record updated Elo ratings
    ufcfights.at[index, 'fighter_1_elo_end'] = new_fighter1_elo
    ufcfights.at[index, 'fighter_2_elo_end'] = new_fighter2_elo

    # Update Elo ratings in the dictionary
    elo_ratings[fighter_1] = new_fighter1_elo
    elo_ratings[fighter_2] = new_fighter2_elo

def get_fighter_info(fighter_name, elo_ratings, ufcfights, initial_elo=1000):
    # Check if the fighter exists in the Elo ratings dictionary
    if fighter_name in elo_ratings:
        elo = elo_ratings[fighter_name]
    else:
        elo = initial_elo

    # Find all matches where the fighter appeared as either fighter_1 or fighter_2
    fighter_matches = ufcfights[(ufcfights['fighter_1'] == fighter_name) | 
                                (ufcfights['fighter_2'] == fighter_name)]
    
    # Return Elo rating and their matches
    if not fighter_matches.empty:
        print(f"{fighter_name}'s current Elo rating: {elo}\n")
        print(f"{fighter_name}'s matches:")
        return fighter_matches[['event', 'fighter_1', 'fighter_2', 'result', 'fighter_1_elo_start', 'fighter_2_elo_start','fighter_1_elo_end','fighter_2_elo_end']]
    else:
        return f"{fighter_name} has no recorded matches."

#finds peak elo ratings
'''

'''
# Export to CSV
'''
ufcfights.to_csv('ufcfights_with_elo.csv', index=False)
'''
'''
# Find the fighter with the highest Elo
highest_elo_fighter = max(elo_ratings, key=elo_ratings.get)
highest_elo_value = elo_ratings[highest_elo_fighter]
print(f"The fighter with the highest Elo is {highest_elo_fighter} with an Elo of {highest_elo_value}.")

#find the fghter with the lowest elo
lowest_elo_fighter = min(elo_ratings, key= elo_ratings.get)
lowest_elo_value = elo_ratings[lowest_elo_fighter]
print(f"The fighter with the highest Elo is {lowest_elo_fighter} with an Elo of {lowest_elo_value}")

top_50_fighters = sorted(elo_ratings.items(), key=lambda x: x[1], reverse=True)[:50]
top_50_df = pd.DataFrame(top_50_fighters, columns=['Fighter', 'Elo Rating'])
top_50_df.to_csv('top_50_fighters_elo.csv', index=False)

fighter_name = "Anderson Silva"
fighter_info = get_fighter_info(fighter_name, elo_ratings, ufcfights)
print(fighter_info)
'''


all_fighters = sorted(elo_ratings.items(), key=lambda x: x[1], reverse=True)
all_fighters_df = pd.DataFrame(all_fighters, columns=['Fighter', 'Elo Rating'])
all_fighters_df.to_csv('k_factor_adjust_current.csv', index=False)

peak_elo = sorted(peak_elo_ratings.items(), key = lambda x: x[1], reverse = True)
peak_elo_df = pd.DataFrame(peak_elo, columns=['Fighter', 'Peak Elo'])
peak_elo_df.to_csv('peak_elo.csv', index=False)


