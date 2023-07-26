import numpy as np
import pandas as pd 
import seaborn as sns 
import glob
from collections import deque
from statistics import mean
import re 
from xgboost import XGBClassifier
from sklearn.metrics import mean_absolute_error

#All my pipeline functions will live here. 

##Below are the cleaning functions. These are all written 
#for Sackman's Tennis Abstract data. 

def read_csvs():
    #reads all the csv files in a directory to a pandas dataframe. 

    path = "/Users/rileywilson/Documents/tennis_analysis/WTA_modeling/WTA_all_matches/*.csv"
    files = glob.glob(path)

    #reading the dataframe in
    df_list = []

    for file in files: 
        df = pd.read_csv(file, encoding= 'latin-1')
        df_list.append(df)
    
    df = pd.concat(df_list, axis = 0)
    
    return df 

def de_sackify(df):
    #taking a Sackman-formatted dataset and amending it to my
    #purposes

    #making a copy of the dataframe:
    data = df.copy()

    #converting the dates to datetime format  
    data['tourney_date'] = pd.to_datetime(data['tourney_date'], format=('%Y%m%d'))

    #getting rid of the "BR" rounds
    data.drop(data[data['round'] == 'BR'].index, inplace = True)

    #changing special characters to their english counterparts (just for Alize Cornet right now)
    data['winner_name'] = data['winner_name'].apply(lambda x: x.replace('é', 'e'))
    data['loser_name'] = data['loser_name'].apply(lambda x: x.replace('é', 'e'))

    #replacing cocos with coris
    data['winner_name'] = data['winner_name'].apply(lambda x: x.replace('Coco', 'Cori'))
    data['loser_name'] = data['loser_name'].apply(lambda x: x.replace('Coco', 'Cori'))

    #making a 'year' column. This is useful for some other functions. 
    data['year'] = data['tourney_date'].apply(lambda x: x.year)

    #Making a 'WTA_tour' indicator feature. It tells us whether a tournament is WTA level. 
    sub_WTA = ['CC', '40', '75', '80', 'C', '100', '50', '60', '10', '15', '20', '25']
    data['WTA'] = ~data['tourney_level'].isin(sub_WTA)
    
    #cleaning all tournament names. Taking out all numbers and spaces. 
    data['tourney_name'] = data['tourney_name'].apply(lambda x: x.lower())

    replacements = ['1', '2', ' ', '-', "'"]
    for word in replacements:
        data['tourney_name'] = data['tourney_name'].apply(lambda x: x.replace(word, ''))

    #introducing other categories to sort the dataframe by:
    data['tourney_name'] = pd.Categorical(data['tourney_name'], categories = data['tourney_name'].value_counts().index)

    rounds = ['RR', 'R128', 'R64', 'R32', 'R16', 'QF', 'SF', 'F']

    data['round'] = pd.Categorical(data['round'], categories= rounds)

    data = data.sort_values(by= ['tourney_date', 'tourney_name', 'round'], ascending= True )

    #dropping a bunch of columns for abundance of nans: 
    drops = ['winner_seed', 'winner_entry', 'loser_seed', 'loser_entry', 'minutes', 'w_SvGms', 'l_SvGms', 'winner_rank',
         'winner_rank_points', 'loser_rank', 'loser_rank_points', 'match_num'] 

    data.drop(drops, axis =1, inplace = True)

    #replacing all -1's with nans
    data = data.replace(-1, np.nan)

    #ensuring everything in the 'scores' column is a string. 
    data['score'] = data['score'].astype(str)

    #dropping walkovers, retirements, and other strange results. 
    data = data[~data['score'].apply(lambda x: x.split(' ')[-1]).isin(['RET', 'W/O', 'unfinished', 'DEF', 'RET+H64', 'RET+H61'])]

    #turning all scores into the same format.
    #I'm dropping the tiebreak scores first. 
    data['score'] = data['score'].apply(lambda x: re.sub(r'\([^()]*\)', '', x))

    #now I'm stripping all parentheses and spaces
    data['score'] = data['score'].apply(lambda x: x.replace(' ', ''))
    data['score'] = data['score'].apply(lambda x: x.replace('-', ''))

    #dropping matches where the surface is not specified. 
    data.dropna(subset = ['surface'], inplace= True)

    #imputing height and age. The average WTA player is 172cm tall and 24.25 years 
    #old. 
    data['winner_ht'] = data['winner_ht'].fillna(172)
    data['loser_ht'] = data['winner_ht'].fillna(172)

    data['winner_age'] = data['winner_age'].fillna(24.25)
    data['loser_age'] = data['loser_age'].fillna(24.25)

    #when scraping, if a player doesn't have a listed age I say they were born in 1900.
    #I'm replacing all the 100+ year old ages with 24.25
    data.loc[data['winner_age'] > 100, 'winner_age'] = 24.25
    data.loc[data['loser_age'] > 100, 'loser_age'] = 24.25

    #imputing hand:
    data['loser_hand'] = data['loser_hand'].fillna('R')

    return data 

#MATCH ID UNFINISHED
def match_id(df):
    mid = []
    df.reset_index(inplace = True, drop = True) 

    for i in df.index:
        y = df.iloc[i]['tourney_date'].year
        location = df.iloc[i]['tourney_name']
        w_name = df.iloc[i]['winner_name'].split(' ')[1]
        l_name = df.iloc[i]['loser_name'].split(' ')[1]
        id = y+ '_' + location + '_' + w_name + '_' + l_name 
        mid.append(id) 

    #adding to the dataframe
    df['match_id'] = mid 
    return df 

#feature functions 
#######################################
def days_since_last_tourney(df):
    #Note: this is a weird function. If a player is deep in a tournament, they'll
    #have their "last tourney date" be 0, even if their last tourney, besides this 
    #one, was long ago. 
    #I see this feature being helpful during first rounds. 
    #resetting index because this seems to work 
    df.reset_index(inplace = True, drop= True)

    last_match_date = {}
    winner_last_match_date = []
    loser_last_match_date = [] 


    for i in df.index:

        #for debugging 
        #print(i)

        #checking to see if a player has a last match date If not, I add one. 
        if df.iloc[i]['winner_name'] not in last_match_date.keys():
            last_match_date[df.iloc[i]['winner_name']] = df.iloc[i]['tourney_date']
            
        if df.iloc[i]['loser_name'] not in last_match_date.keys():
            last_match_date[df.iloc[i]['loser_name']] = df.iloc[i]['tourney_date']

        #setting the last match dates
        today_date = df.iloc[i]['tourney_date']

        #calculating the delta between the dates
        winner_delta = today_date - last_match_date[df.iloc[i]['winner_name']]
        loser_delta = today_date - last_match_date[df.iloc[i]['loser_name']]

        #appending the delta to the column
        winner_last_match_date.append(winner_delta.days)
        loser_last_match_date.append(loser_delta.days)

        #updating the last match dates 
        last_w = {df.iloc[i]['winner_name']: df.iloc[i]['tourney_date']}
        last_l = {df.iloc[i]['loser_name']: df.iloc[i]['tourney_date']}
        
        last_match_date.update(last_w)
        last_match_date.update(last_l) 
        

    df['w_last_match'] = pd.Series(winner_last_match_date)
    df['l_last_match'] = pd.Series(loser_last_match_date)

    return df

def win_pct_last_n(df, n):
    #calculates a player's win percentage over the last 
    #n matches 

    #setting up 
     df.reset_index(inplace = True, drop = True)
     player_dict = {}
     w_pre = []
     l_pre = [] 
     for i in df.index:
        #for debugging 
        #print(i)
        #checking to see if a player has an entry. If not I'll add one. 
        if df.iloc[i]['winner_name'] not in player_dict.keys():
            player_dict[df.iloc[i]['winner_name']] = deque()
            
        if df.iloc[i]['loser_name'] not in player_dict.keys():
            player_dict[df.iloc[i]['loser_name']] = deque()
        
        ###########################
        if len(player_dict[df.iloc[i]['winner_name']]) == 0:
            w_pre.append(0)
        elif len(player_dict[df.iloc[i]['winner_name']]) < n+1:
            w_pre.append(mean(player_dict[df.iloc[i]['winner_name']]))
        else:
            player_dict[df.iloc[i]['winner_name']].popleft()
            w_pre.append(mean(player_dict[df.iloc[i]['winner_name']]))

        if len(player_dict[df.iloc[i]['loser_name']]) == 0:
            l_pre.append(0)
        elif len(player_dict[df.iloc[i]['loser_name']]) < n+1:
            l_pre.append(mean(player_dict[df.iloc[i]['loser_name']]))
        else:
            player_dict[df.iloc[i]['loser_name']].popleft()
            l_pre.append(mean(player_dict[df.iloc[i]['loser_name']]))

        #I want to add wins as a 1 and losses as a 0 for the loser and winner. 
        player_dict[df.iloc[i]['winner_name']].append(1)
        player_dict[df.iloc[i]['loser_name']].append(0) 
     
     df['w_pct_pre'] = pd.Series(w_pre)
     df['l_pct_pre'] = pd.Series(l_pre)

     return df, player_dict 

def game_mov_last_n(df, n):
    
    #setting up 
     df.reset_index(inplace = True, drop = True)
     player_dict = {}
     w_pre = []
     l_pre = [] 
    
     #adding a winner mov column 
     w_game_mov = []

     for i in df.index:
        #for debugging 
        #print(i)
        #checking to see if a player has an entry. If not I'll add one. 
        if df.iloc[i]['winner_name'] not in player_dict.keys():
            player_dict[df.iloc[i]['winner_name']] = deque()

        if df.iloc[i]['loser_name'] not in player_dict.keys():
            player_dict[df.iloc[i]['loser_name']] = deque()

        #######################################
        if len(player_dict[df.iloc[i]['winner_name']]) == 0:
            w_pre.append(0)
        elif len(player_dict[df.iloc[i]['winner_name']])< n+1:
            w_pre.append(mean(player_dict[df.iloc[i]['winner_name']]))
        else:
            player_dict[df.iloc[i]['winner_name']].popleft()
            w_pre.append(mean(player_dict[df.iloc[i]['winner_name']]))
        
        if len(player_dict[df.iloc[i]['loser_name']]) == 0:
            l_pre.append(0)
        elif len(player_dict[df.iloc[i]['loser_name']])< n+1:
            l_pre.append(mean(player_dict[df.iloc[i]['loser_name']]))
        else:
            player_dict[df.iloc[i]['loser_name']].popleft()
            l_pre.append(mean(player_dict[df.iloc[i]['loser_name']]))

        #I want to get the number of games the loser won and the number of games the winner won.
        winner_games = 0
        loser_games = 0  

        if len(df.iloc[i]['score']) <= 6:
            for j in range(len(df.iloc[i]['score'])):
                if j % 2 == 0:
                    winner_games = winner_games + int(df.iloc[i]['score'][j])
                else:
                    loser_games = loser_games + int(df.iloc[i]['score'][j])
        else:
            for j in range(4):
                if j % 2 == 0:
                    winner_games = winner_games + int(df.iloc[i]['score'][j])
                else:
                    loser_games = loser_games + int(df.iloc[i]['score'][j]) 
            #if the third set is abnormal, then the winner will win two more games. 
            winner_games = winner_games + 2

        #print('winner games', winner_games)
        #print('loser_games', loser_games)
        mov = winner_games - loser_games 

        w_game_mov.append(mov) 

        #putting the mov in both players' deques
        player_dict[df.iloc[i]['winner_name']].append(mov)
        player_dict[df.iloc[i]['loser_name']].append(-mov)

     df['w_mov_rolling'] = pd.Series(w_pre)
     df['l_mov_rolling'] = pd.Series(l_pre)
     df['w_game_mov'] = w_game_mov 

     return df, player_dict

def h2h(df):
    #this probably isn't the best way to do this, but we'll go for it. 

    df.reset_index(inplace = True, drop = True)

    #structures we'll need
    wl_dict = {}
    w_wl = []
    l_wl = [] 

    #now I'm going to loop through. 

    for i in df.index:
        #adding a winner entry if there isn't already one 
        if (df.iloc[i]['winner_name']+'_'+df.iloc[i]['loser_name']) not in wl_dict.keys():
            wl_dict[df.iloc[i]['winner_name']+'_'+df.iloc[i]['loser_name']] = 0 
        
        if (df.iloc[i]['loser_name']+'_'+df.iloc[i]['winner_name']) not in wl_dict.keys():
            wl_dict[df.iloc[i]['loser_name']+'_'+df.iloc[i]['winner_name']] = 0
        
        #putting the wins and losses in the appropriate lists 
        w_wl.append(wl_dict[df.iloc[i]['winner_name']+'_'+df.iloc[i]['loser_name']])
        l_wl.append(wl_dict[df.iloc[i]['loser_name']+'_'+df.iloc[i]['winner_name']])

        #updating the win loss based on the results of the match 

        prior_wins = wl_dict[df.iloc[i]['winner_name']+'_'+df.iloc[i]['loser_name']]
        win_update = {df.iloc[i]['winner_name']+'_'+df.iloc[i]['loser_name']: prior_wins + 1}

        wl_dict.update(win_update)

    #updating the dataframe:
    df['w_h2h'] = pd.Series(w_wl)
    df['l_h2h'] = pd.Series(l_wl) 
    return df, wl_dict 

def compute_elo(df, k, n):
    #Computing the pre-match ELO of each player 
    #also computing pre-match rolling elo change in last n matches
    df.reset_index(drop = True, inplace = True)
    elo_dict = {}
    winner_elo = []
    loser_elo = []

    elo_change_dict = {}
    w_elo_change = []
    l_elo_change = [] 

    #calculating pre-match elo for each player based on the previous elo ranking.
    #If the player doesn't have an elo then I'll add one. 
    for i in df.index:

        #for debugging 
        #print(i)

        #checking to see if a player has an elo. If not, I add one. 
        if df.iloc[i]['winner_name'] not in elo_dict.keys():
            elo_dict[df.iloc[i]['winner_name']] = 1500
            
        if df.iloc[i]['loser_name'] not in elo_dict.keys():
            elo_dict[df.iloc[i]['loser_name']] = 1500

        #checking to see if a player has an elo change dict. If not, I add one. 
        if df.iloc[i]['winner_name'] not in elo_change_dict.keys():
            elo_change_dict[df.iloc[i]['winner_name']] = deque()
            
        if df.iloc[i]['loser_name'] not in elo_change_dict.keys():
            elo_change_dict[df.iloc[i]['loser_name']] = deque()
            
        #setting the pre-match elo scores
        winner_elo.append(elo_dict[df.iloc[i]['winner_name']])
        loser_elo.append(elo_dict[df.iloc[i]['loser_name']])
        
        #updating their elo scores for after the match. These will be pulled the next time the players play.

        score_difference_w = (elo_dict[df.iloc[i]['loser_name']] - elo_dict[df.iloc[i]['winner_name']] ) / 400
        score_difference_l = (elo_dict[df.iloc[i]['winner_name']] - elo_dict[df.iloc[i]['loser_name']] ) / 400
        expected_score_winner = 1 / (1 + 10**score_difference_w)
        expected_score_loser = 1 / (1 + 10**score_difference_l) 

        #using expected scores to modify the winner and loser elos

        w_elo = elo_dict[df.iloc[i]['winner_name']]
        l_elo = elo_dict[df.iloc[i]['loser_name']]

        holder_w = {df.iloc[i]['winner_name'] : w_elo + k*(1 - expected_score_winner)}
        elo_dict.update(holder_w)

        holder_l = {df.iloc[i]['loser_name']: l_elo + k*(-expected_score_loser)}
        elo_dict.update(holder_l)

        #putting in the rolling elo stats
        ###########################
        if len(elo_change_dict[df.iloc[i]['winner_name']]) == 0:
            w_elo_change.append(0)
        elif len(elo_change_dict[df.iloc[i]['winner_name']]) < n+1:
            w_elo_change.append(sum(elo_change_dict[df.iloc[i]['winner_name']]))
        else:
            elo_change_dict[df.iloc[i]['winner_name']].popleft()
            w_elo_change.append(sum(elo_change_dict[df.iloc[i]['winner_name']]))

        if len(elo_change_dict[df.iloc[i]['loser_name']]) == 0:
            l_elo_change.append(0)
        elif len(elo_change_dict[df.iloc[i]['loser_name']]) < n+1:
            l_elo_change.append(sum(elo_change_dict[df.iloc[i]['loser_name']]))
        else:
            elo_change_dict[df.iloc[i]['loser_name']].popleft()
            l_elo_change.append(sum(elo_change_dict[df.iloc[i]['loser_name']]))

        #adding to the rolling elo dictionaries .
        elo_change_dict[df.iloc[i]['winner_name']].append(k*(1 - expected_score_winner))
        elo_change_dict[df.iloc[i]['loser_name']].append(k*(-expected_score_loser))

    
    df['winner_elo'] = pd.Series(winner_elo)
    df['loser_elo'] = pd.Series(loser_elo)

    df['w_elo_change'] = w_elo_change
    df['l_elo_change'] = l_elo_change 

    #performing a dictionary comprehension to get what I want 
    elo_change_dict = {key : sum(value) for key, value in elo_change_dict.items()}


    #this gives me a list of current elos. 
    return df, elo_dict, elo_change_dict

#SURFACE ENCODING MUST BE RUN FIRST 
#TODO: BAKE SURFACE ENCODING INTO SURFACE ELOS. THAT WAY WE DON'T HAVE TO 
#LOOP THROUGH THE DATA TWICE
def surface_encoding(df):
    df.reset_index(inplace = True, drop = True)
    s_map = {'Hard': 1, 'Clay': 0, 'Grass': 2, 'Carpet': 2}

    surfaces = []

    for i in df.index:
        surfaces.append(s_map[df.iloc[i]['surface']])

    df['surface'] = surfaces 
    return df 

def surface_elos(df, k):
    #Computing the pre-match ELO of each player 

    df = surface_encoding(df)

    df.reset_index(drop = True, inplace = True)

    hard_elo_dict = {}
    clay_elo_dict = {}
    grass_elo_dict = {}
    
    hard_winner_elo = []
    hard_loser_elo = []

    clay_winner_elo = []
    clay_loser_elo = []

    grass_winner_elo = []
    grass_loser_elo = []


    #calculating pre-match elo for each player based on the previous elo ranking.
    #If the player doesn't have an elo then I'll add one. 
    for i in df.index:

        #for debugging 
        #print(i)

        #checking to see if a player has an elo or last match date If not, I add one. 
        #TODO: THIS STEP MAY TAKE A LOT OF TIME. SEE IF IT CAN BE BETTER.
        ##########################################################
        #checking if they have a hard elo 
        if df.iloc[i]['winner_name'] not in hard_elo_dict.keys():
            hard_elo_dict[df.iloc[i]['winner_name']] = 1500
            
        if df.iloc[i]['loser_name'] not in hard_elo_dict.keys():
            hard_elo_dict[df.iloc[i]['loser_name']] = 1500

        #checking if they have a clay elo
        if df.iloc[i]['winner_name'] not in clay_elo_dict.keys():
            clay_elo_dict[df.iloc[i]['winner_name']] = 1500
            
        if df.iloc[i]['loser_name'] not in clay_elo_dict.keys():
            clay_elo_dict[df.iloc[i]['loser_name']] = 1500

        #checking if they have a grass elo
        if df.iloc[i]['winner_name'] not in grass_elo_dict.keys():
            grass_elo_dict[df.iloc[i]['winner_name']] = 1500
            
        if df.iloc[i]['loser_name'] not in grass_elo_dict.keys():
            grass_elo_dict[df.iloc[i]['loser_name']] = 1500
            
        #setting the blended pre-match elo scores
        #hard
        hard_winner_elo.append((hard_elo_dict[df.iloc[i]['winner_name']] + df.iloc[i]['winner_elo']) / 2)
        hard_loser_elo.append((hard_elo_dict[df.iloc[i]['loser_name']] + df.iloc[i]['loser_elo']) / 2)

        #clay
        clay_winner_elo.append((clay_elo_dict[df.iloc[i]['winner_name']] + df.iloc[i]['winner_elo']) /2)
        clay_loser_elo.append((clay_elo_dict[df.iloc[i]['loser_name']] + df.iloc[i]['loser_elo']) /2  )

        #grass
        grass_winner_elo.append((grass_elo_dict[df.iloc[i]['winner_name']] + df.iloc[i]['winner_elo']) /2 )
        grass_loser_elo.append((grass_elo_dict[df.iloc[i]['loser_name']]+ df.iloc[i]['loser_elo']) / 2)

        
        #updating their elo scores for after the match. These will be pulled the next time the players play.
        #I will do different things depending on the surface they're playing on

        #clay 
        if df.iloc[i]['surface'] == 0:
            score_difference_w = (clay_elo_dict[df.iloc[i]['loser_name']] - clay_elo_dict[df.iloc[i]['winner_name']] ) / 400
            score_difference_l = (clay_elo_dict[df.iloc[i]['winner_name']] - clay_elo_dict[df.iloc[i]['loser_name']] ) / 400
            expected_score_winner = 1 / (1 + 10**score_difference_w)
            expected_score_loser = 1 / (1 + 10**score_difference_l) 

            #using expected scores to modify the winner and loser elos

            w_elo = clay_elo_dict[df.iloc[i]['winner_name']]
            l_elo = clay_elo_dict[df.iloc[i]['loser_name']]

            holder_w = {df.iloc[i]['winner_name'] : w_elo + k*(1 - expected_score_winner)}
            clay_elo_dict.update(holder_w)

            holder_l = {df.iloc[i]['loser_name']: l_elo + k*(-expected_score_loser)}
            clay_elo_dict.update(holder_l)
        elif df.iloc[i]['surface'] == 1:
            #hard
            score_difference_w = (hard_elo_dict[df.iloc[i]['loser_name']] - hard_elo_dict[df.iloc[i]['winner_name']] ) / 400
            score_difference_l = (hard_elo_dict[df.iloc[i]['winner_name']] - hard_elo_dict[df.iloc[i]['loser_name']] ) / 400
            expected_score_winner = 1 / (1 + 10**score_difference_w)
            expected_score_loser = 1 / (1 + 10**score_difference_l) 

            #using expected scores to modify the winner and loser elos

            w_elo = hard_elo_dict[df.iloc[i]['winner_name']]
            l_elo = hard_elo_dict[df.iloc[i]['loser_name']]

            holder_w = {df.iloc[i]['winner_name'] : w_elo + k*(1 - expected_score_winner)}
            hard_elo_dict.update(holder_w)

            holder_l = {df.iloc[i]['loser_name']: l_elo + k*(-expected_score_loser)}
            hard_elo_dict.update(holder_l)
        elif df.iloc[i]['surface'] == 2:
            #grass/carpet
            score_difference_w = (grass_elo_dict[df.iloc[i]['loser_name']] - grass_elo_dict[df.iloc[i]['winner_name']] ) / 400
            score_difference_l = (grass_elo_dict[df.iloc[i]['winner_name']] - grass_elo_dict[df.iloc[i]['loser_name']] ) / 400
            expected_score_winner = 1 / (1 + 10**score_difference_w)
            expected_score_loser = 1 / (1 + 10**score_difference_l) 

            #using expected scores to modify the winner and loser elos

            w_elo = grass_elo_dict[df.iloc[i]['winner_name']]
            l_elo = grass_elo_dict[df.iloc[i]['loser_name']]

            holder_w = {df.iloc[i]['winner_name'] : w_elo + k*(1 - expected_score_winner)}
            grass_elo_dict.update(holder_w)

            holder_l = {df.iloc[i]['loser_name']: l_elo + k*(-expected_score_loser)}
            grass_elo_dict.update(holder_l)
    
    df['winner_hard_elo'] = hard_winner_elo
    df['loser_hard_elo'] = hard_loser_elo
    df['winner_clay_elo'] =  clay_winner_elo
    df['loser_clay_elo'] = clay_loser_elo
    df['winner_grass_elo'] = grass_winner_elo 
    df['loser_grass_elo'] = grass_loser_elo 
    #this gives me a list of current elos. 
    return df, hard_elo_dict, clay_elo_dict, grass_elo_dict 

#function for extracting the win probability of p1 from two elos 
def extract_prob(p1_elo, p2_elo):
    #I'm getting a win probability for the winner based on a difference in elos.

    loser_minus_winner_elo = p2_elo - p1_elo
    denom = 1 + 10**(loser_minus_winner_elo / 400) 

    prob_p1_win = 1/denom 

    prob_p2_win = 1 - prob_p1_win

    return prob_p1_win

#I should take the logarithm here. The difference between the final and semi is larger 
#than between the first and second rounds. 
#THIS CANNOT HANDLE QUALIFYING MATCHES. TO DO SO, I WILL CODE IN THE DIFFERENT 
#QUALIFYING ROUNDS
def rounds(df):
    df.reset_index(inplace= True, drop= True)
    r_map = {'F': 0, 'SF': 1, 'QF': 2, 'R16': 3, 'R32': 4, 'R64': 5, 'R128': 6, 'RR': 7}
    r = []

    for i in df.index:
        r.append(r_map[df.iloc[i]['round']])

    df['round'] = r

    return df 

def tourney_win_percentage(df):
    df.reset_index(inplace= True, drop = True)
    w_tourney_wp = []
    l_tourney_wp = []

    player_dict = {} 

    for i in df.index:

        w_name = df.iloc[i]['winner_name'] 
        l_name = df.iloc[i]['loser_name']
        tournament = df.iloc[i]['tourney_name']

        #I want to see if either player has played the tournament before. If they haven't, 
        #I'll add an entry
        if w_name + tournament not in player_dict.keys():
            w_tourney_wp.append(0)
            player_dict[w_name + tournament] = []
        else:
            w_tourney_wp.append(mean(player_dict[w_name + tournament]))

        if l_name + tournament not in player_dict.keys():
            l_tourney_wp.append(0)
            player_dict[l_name + tournament] = [] 
        else:
            l_tourney_wp.append(mean(player_dict[l_name + tournament]))

        #if a player wins, I'll add a 1 to their list. If they don't win, I'll 
        #add a 0
        #winner:
        player_dict[w_name + tournament].append(1)

        #loser
        player_dict[l_name + tournament].append(0)

    df['w_tourney_wp'] = w_tourney_wp
    df['l_tourney_wp'] = l_tourney_wp 
    
    return df, player_dict

#NEEDS TO BE TESTED AND INCORPORATED
def peak_elo(df):
    #TO BE RUN AFTER COMPUTE_ELO
    #calculates the peak elo of a player and adds it as a feature 
    #NEEDS TO BE TESTED 
    #TODO optimize this, and related functions. They're not fast. 

    df.reset_index(inplace= True, drop = True)

    peak_elo_dict = {} 
    w_peak_elo = []
    l_peak_elo = []

    for i in df.index:
        #if there's no peak elo rating, add the current elo: 
        if df.iloc[i]['winner_name'] not in peak_elo_dict.keys():
            peak_elo_dict[df.iloc[i]['winner_name']] = df.iloc[i]['winner_elo']
            
        if df.iloc[i]['loser_name'] not in peak_elo_dict.keys():
            peak_elo_dict[df.iloc[i]['loser_name']] = df.iloc[i]['loser_elo'] 

        if df.iloc[i]['winner_elo'] > peak_elo_dict[df.iloc[i]['winner_name']]:
            uw = {df.iloc[i]['winner_name']: df.iloc[i]['winner_elo']}
            peak_elo_dict.update(uw) 
        
        if df.iloc[i]['loser_elo'] > peak_elo_dict[df.iloc[i]['loser_name']]:
            ul = {df.iloc[i]['loser_name']: df.iloc[i]['loser_elo']}
            peak_elo_dict.update(ul) 

        #adding the peak elos to the columns 
        w_peak_elo.append(peak_elo_dict[df.iloc[i]['winner_name']])
        l_peak_elo.append(peak_elo_dict[df.iloc[i]['loser+name']])

    #creating the columns 
    df['w_peak_elo'] = w_peak_elo
    df['l_peak_elo'] = l_peak_elo

    return df 

#THE FOLLOWING TWO FUNCTIONS QUANTIFY COURT SPEEDS. YOU RUN 
#tournament_speeds first and then pass the resulting dataframe as 
#'a' into the court_speed_index function
def tournament_speeds(df):
    #returns a dataframe mulitindexed by tournament and year. 
    #the "observed_over_expected" column contains how many aces 
    #were observed that tournament over how many we would have 
    #expected given the entrants. 

    
    df = df.dropna(subset = ['w_ace', 'l_ace'], axis = 0)
    #we'll tally up all of a player's aces and the matches she's played. 
    #then we'll take the ratio and return that as a dictionary. 

    #resetting index 
    df.reset_index(inplace = True, drop = True)

    w_avg_ace_rate = []
    w_matches_played = []
    
    l_avg_ace_rate = []
    l_matches_played = [] 

    #creating player ace dictionary. Each dictionary will hold a list with two numbers. The first is a player's 
    #career aces. The second is her career match count. 

    player_dict = {} 

    for i in df.index:
        #if a player doesn't have an entry, we create one 

        if df.iloc[i]['winner_name'] not in player_dict.keys():
            player_dict[df.iloc[i]['winner_name']] = [0,0] 

        if df.iloc[i]['loser_name'] not in player_dict.keys():
            player_dict[df.iloc[i]['loser_name']] = [0,0] 

        #putting in her to-date ace rate:
        #winner
        if player_dict[df.iloc[i]['winner_name']][1] == 0:
            w_avg_ace_rate.append(0)
        else:
            w_avg_ace_rate.append(player_dict[df.iloc[i]['winner_name']][0] / player_dict[df.iloc[i]['winner_name']][1])

        w_matches_played.append(player_dict[df.iloc[i]['winner_name']][1]) 

        #loser
        if player_dict[df.iloc[i]['loser_name']][1] == 0:
            l_avg_ace_rate.append(0)
        else:
            l_avg_ace_rate.append(player_dict[df.iloc[i]['loser_name']][0] / player_dict[df.iloc[i]['loser_name']][1])

        l_matches_played.append(player_dict[df.iloc[i]['loser_name']][1]) 

        #now we increment the career match counter and the ace one. 

        #for the winner
        player_dict[df.iloc[i]['winner_name']][0] = player_dict[df.iloc[i]['winner_name']][0] + df.iloc[i]['w_ace']

        player_dict[df.iloc[i]['winner_name']][1] += 1 

        #for the loser 
        player_dict[df.iloc[i]['loser_name']][0] = player_dict[df.iloc[i]['loser_name']][0] + df.iloc[i]['l_ace']

        player_dict[df.iloc[i]['loser_name']][1] += 1 

    #now we add the rolling ace rates to the dataframe. 

    df['w_avg_ace'] = w_avg_ace_rate
    df['w_matches_played'] = w_matches_played

    df['l_avg_ace'] = l_avg_ace_rate
    df['l_matches_played'] = l_matches_played 

    #now I'm creating the dataframe which goes into the court speed index function 

    a = df.groupby(['tourney_name', 'year']).sum()[['w_avg_ace', 'w_ace', 'l_avg_ace', 'l_ace']]
    a['total_expected_ace'] = a['w_avg_ace'] + a['l_avg_ace'] 
    a['total_observed_ace'] = a['w_ace'] + a['l_ace'] 

    a['observed_over_expected'] = a['total_observed_ace'] / a['total_expected_ace']

    return a  

def court_speed_index(df, a):
    #df is a dataframe of match data. "a" is the dataframe containing the ratio 
    #of observed to expected aces for each tournament by year. "a" should be the output of 
    #"tournament speeds."
    #'a' is a dataframe with a multindex which houses the tournament on the first level and 
    #its year on the second. 

    df.reset_index(drop =True, inplace = True) 
    court_indices = []

    for i in df.index:
        #we'll try to take the average of the three latest iterations of the tournament. 
        #otherwise, we'll resort to inferring the court speed based on surface. 

        tourney_name = df.iloc[i]['tourney_name'] 
        year = df.iloc[i]['year'] 

        #a list to hold the speed index values:
        i_values = [] 

        #calculating the average:
        #If it can't find a year the tournament was held in the for loop, then 
        #I want it to just look for the year before that. 
        # DESIDERATA: TO ACCOUNT FOR CHANGES IN COURT SURFACE FROM YEAR TO YEAR
        try:
            for j in [1,2]:
                index_loc = a.loc[tourney_name].index.get_loc(year)

                #throw an error if index_loc - j goes negative
                if index_loc - j < 0:
                    x = 1/0
                
                h = a.loc[tourney_name].iloc[index_loc-j]['observed_over_expected']

                #accounting for a nan value on a tournament. If it's a nan or inf, I 
                #just impute a value for the court speed. 
                if np.isnan(h) == True or h == np.inf:
                    if df.iloc[i]['surface'] == 0:
                        i_values.append(.9)
                    elif df.iloc[i]['surface'] == 1:
                        i_values.append(1)
                    elif df.iloc[i]['surface'] == 2:
                        i_values.append(1.1)
                    else:
                        print("SOMETHING HAS GONE WRONG")
                else:
                    i_values.append(h)

                
        except Exception:
            #putting in my estimates of court speed
            #resetting the list in case a couple of the loops trigger
            i_values  = [] 
            if df.iloc[i]['surface'] == 0:
                i_values.append(.9)
            elif df.iloc[i]['surface'] == 1:
                i_values.append(1)
            elif df.iloc[i]['surface'] == 2:
                i_values.append(1.1)
            else:
                print('SOMETHING HAS GONE WRONG!')
        #print('these are the i values', i_values)
        court_indices.append(sum(i_values) / len(i_values)) 

    df['court_speed_index'] = court_indices

    return df 

def career_matches(df):
    df.reset_index(inplace = True, drop = True)
    w_career_matches = [] 
    l_career_matches = []

    matches_dict = {}

    for i in df.index:
        #seeing if a player is already in the dictionary

        if df.iloc[i]['winner_name'] not in matches_dict.keys():
            matches_dict[df.iloc[i]['winner_name']] = 0 

        if df.iloc[i]['loser_name'] not in matches_dict.keys():
            matches_dict[df.iloc[i]['loser_name']] = 0 

        #adding a player's career matches to the list
        w_career_matches.append(matches_dict[df.iloc[i]['winner_name']])
        l_career_matches.append(matches_dict[df.iloc[i]['loser_name']]) 

        #updating the career matches count 
        matches_dict[df.iloc[i]['winner_name']] += 1  
        matches_dict[df.iloc[i]['loser_name']] += 1

    #creating a column in the dataframe 
    df['w_career_matches'] = w_career_matches
    df['l_career_matches'] = l_career_matches 

    return df, matches_dict

def three_set(df):
    #indicator feature for whether a match was a three-setter
    df.reset_index(inplace = True, drop = True)

    l = []

    for i in df.index:
        if len(str(df.iloc[i]['score'])) > 4:
            l.append(1)
        else:
            l.append(0)

    df['three_set'] = l
    return df

def career_three_set(df):
    #Tells us what proportion of matches were three-setters in a player's career
    # TO BE RUN AFTER CAREER MATCHES
    df.reset_index(inplace = True, drop = True)

    #creating the dictionary 
    three_setters = {} 

    three_setters_won = {}

    w_three_set = []
    l_three_set = []

    w_three_set_won_pct = []
    l_three_set_won_pct = [] 

    for i in df.index:
        #the loop below does two things. First, it records the proportion of matches a player has played 
        #that are three setters. It also calculates a player's three-set win percentage. 

        #if a player hasn't been recorded, we add them to the dictionary
        
        #for absolute number of three setters
        if df.iloc[i]['winner_name'] not in three_setters.keys():
            three_setters[df.iloc[i]['winner_name']] = 0

        if df.iloc[i]['loser_name'] not in three_setters.keys():
            three_setters[df.iloc[i]['loser_name']] = 0

        #for number of three setters won 
        if df.iloc[i]['winner_name'] not in three_setters_won.keys():
            three_setters_won[df.iloc[i]['winner_name']] = 0

        if df.iloc[i]['loser_name'] not in three_setters_won.keys():
            three_setters_won[df.iloc[i]['loser_name']] = 0 



        #adding three set win pct to the lists
        if three_setters[df.iloc[i]['winner_name']] != 0:
            w_three_set_won_pct.append(three_setters_won[df.iloc[i]['winner_name']]/three_setters[df.iloc[i]['winner_name']])
            #print(three_setters[df.iloc[i]['winner_name']])
        else:
            w_three_set_won_pct.append(0) 

        if three_setters[df.iloc[i]['loser_name']] != 0:
            l_three_set_won_pct.append(three_setters_won[df.iloc[i]['loser_name']]/three_setters[df.iloc[i]['loser_name']])
            #print(three_setters[df.iloc[i]['winner_name']])
        else:
            l_three_set_won_pct.append(0) 



        #adding proportion of three setters to the lists 
        if df.iloc[i]['w_career_matches'] != 0:
            w_three_set.append(three_setters[df.iloc[i]['winner_name']]/df.iloc[i]['w_career_matches'])
            #print(three_setters[df.iloc[i]['winner_name']])
        else:
            w_three_set.append(0) 

        if df.iloc[i]['l_career_matches'] != 0:
            l_three_set.append(three_setters[df.iloc[i]['loser_name']]/df.iloc[i]['l_career_matches'])
        else:
            l_three_set.append(0) 

        #updating both dictionaries if the current match was, indeed, a three setter 
        if df.iloc[i]['three_set'] == 1:
            #print('trigger')
            three_setters[df.iloc[i]['winner_name']] += 1
            three_setters[df.iloc[i]['loser_name']] +=1

            three_setters_won[df.iloc[i]['winner_name']] += 1
        


    df['w_career_3set_pct'] = w_three_set
    df['l_career_3set_pct'] = l_three_set

    df['w_3set_win_pct'] = w_three_set_won_pct
    df['l_3set_win_pct'] = l_three_set_won_pct

    return df

#NEED TO MODIFY FOR:
#NEW FEATURES
def winner_loser_swap(df):

    #setting the random state 
    np.random.RandomState(615)

    #there has to be a better way to do this. I only want to switch 
    #some columns. 
    p1_name = []
    p1_age = []
    p1_elo = []
    p1_days_since_last_match = []
    p1_rolling_win_pct =[]
    p1_rolling_mov = []
    p1_h2h = []
    p1_tournament_wp = []
    p1_hard_elo = []
    p1_clay_elo = []
    p1_grass_elo = []
    p1_career_matches = []
    p1_career_3set_pct = []
    p1_3set_win_pct = []

    p2_name = []
    p2_age = []
    p2_elo = []
    p2_days_since_last_match = []
    p2_rolling_win_pct = []
    p2_rolling_mov = []
    p2_h2h = []
    p2_tournament_wp = []
    p2_hard_elo = []
    p2_clay_elo = []
    p2_grass_elo = []
    p2_career_matches = []
    p2_career_3set_pct = []
    p2_3set_win_pct = [] 

    p1_win = []

    #going row by row 
    for i in df.index:
        if np.random.uniform(0,1) < .5:
            p1_name.append(df.iloc[i]['winner_name'])
            p1_age.append(df.iloc[i]['winner_age'])
            #for debugging 
            #print(df.iloc[i]['winner_age'])
            p1_elo.append(df.iloc[i]['winner_elo'])
            #p1_days_since_last_match.append(df.iloc[1]['w_last_match'])
            p1_rolling_win_pct.append(df.iloc[i]['w_pct_pre'])
            p1_rolling_mov.append(df.iloc[i]['w_mov_rolling'])
            p1_h2h.append(df.iloc[i]['w_h2h'])
            p1_tournament_wp.append(df.iloc[i]['w_tourney_wp'])
            p1_hard_elo.append(df.iloc[i]['winner_hard_elo'])
            p1_clay_elo.append(df.iloc[i]['winner_clay_elo'])
            p1_grass_elo.append(df.iloc[i]['winner_grass_elo'])
            p1_career_matches.append(df.iloc[i]['w_career_matches'])
            p1_career_3set_pct.append(df.iloc[i]['w_career_3set_pct'])
            p1_3set_win_pct.append(df.iloc[i]['w_3set_win_pct'])

            p2_name.append(df.iloc[i]['loser_name'])
            p2_age.append(df.iloc[i]['loser_age'])
            p2_elo.append(df.iloc[i]['loser_elo'])
            #p2_days_since_last_match.append(df.iloc[i]['l_last_match'])
            p2_rolling_win_pct.append(df.iloc[i]['l_pct_pre'])
            p2_rolling_mov.append(df.iloc[i]['l_mov_rolling'])
            p2_h2h.append(df.iloc[i]['l_h2h'])
            p2_tournament_wp.append(df.iloc[i]['l_tourney_wp'])
            p2_hard_elo.append(df.iloc[i]['loser_hard_elo'])
            p2_clay_elo.append(df.iloc[i]['loser_clay_elo'])
            p2_grass_elo.append(df.iloc[i]['loser_grass_elo'])
            p2_career_matches.append(df.iloc[i]['l_career_matches'])
            p2_career_3set_pct.append(df.iloc[i]['l_career_3set_pct'])
            p2_3set_win_pct.append(df.iloc[i]['l_3set_win_pct'])

            p1_win.append(1)
        else:
            p1_name.append(df.iloc[i]['loser_name'])
            #for debugging 
            #print(df.iloc[i]['loser_age'])
            p1_age.append(df.iloc[i]['loser_age'])
            p1_elo.append(df.iloc[i]['loser_elo'])
            #p1_days_since_last_match.append(df.iloc[i]['l_last_match'])
            p1_rolling_win_pct.append(df.iloc[i]['l_pct_pre'])
            p1_rolling_mov.append(df.iloc[i]['l_mov_rolling'])
            p1_h2h.append(df.iloc[i]['l_h2h'])
            p1_tournament_wp.append(df.iloc[i]['l_tourney_wp'])
            p1_hard_elo.append(df.iloc[i]['loser_hard_elo'])
            p1_clay_elo.append(df.iloc[i]['loser_clay_elo'])
            p1_grass_elo.append(df.iloc[i]['loser_grass_elo'])
            p1_career_matches.append(df.iloc[i]['l_career_matches'])
            p1_career_3set_pct.append(df.iloc[i]['l_career_3set_pct'])
            p1_3set_win_pct.append(df.iloc[i]['l_3set_win_pct'])

            p2_name.append(df.iloc[i]['winner_name'])
            p2_age.append(df.iloc[i]['winner_age'])
            p2_elo.append(df.iloc[i]['winner_elo'])
            #p2_days_since_last_match.append(df.iloc[i]['w_last_match'])
            p2_rolling_win_pct.append(df.iloc[i]['w_pct_pre'])
            p2_rolling_mov.append(df.iloc[i]['w_mov_rolling'])
            p2_h2h.append(df.iloc[i]['w_h2h'])
            p2_tournament_wp.append(df.iloc[i]['w_tourney_wp'])
            p2_hard_elo.append(df.iloc[i]['winner_hard_elo'])
            p2_clay_elo.append(df.iloc[i]['winner_clay_elo'])
            p2_grass_elo.append(df.iloc[i]['winner_grass_elo'])
            p2_career_matches.append(df.iloc[i]['w_career_matches'])
            p2_career_3set_pct.append(df.iloc[i]['w_career_3set_pct'])
            p2_3set_win_pct.append(df.iloc[i]['w_3set_win_pct'])

            p1_win.append(0)

        
    columns_names = ['p1_name', 'p1_age', 'p1_elo', 'p1_hard_elo', 'p1_clay_elo', 'p1_grass_elo', 'p1_rolling_win_pct', 'p1_rolling_mov', 'p1_h2h', 'p1_tournament_wp', 'p1_career_matches', 'p1_career_3set_pct', 'p1_3set_win_pct', 'p2_name', 'p2_age', 'p2_elo', 'p2_hard_elo', 'p2_clay_elo', 'p2_grass_elo', 'p2_rolling_win_pct', 'p2_rolling_mov', 'p2_h2h', 'p2_tournament_wp', 'p2_career_matches', 'p2_career_3set_pct', 'p2_3set_win_pct', 'p1_win']
    
    frame = pd.DataFrame(list(zip(p1_name, p1_age, p1_elo, p1_hard_elo, p1_clay_elo, p1_grass_elo, p1_rolling_win_pct, p1_rolling_mov, p1_h2h, p1_tournament_wp, p1_career_matches, p1_career_3set_pct, p1_3set_win_pct, p2_name, p2_age, p2_elo, p2_hard_elo, p2_clay_elo, p2_grass_elo, p2_rolling_win_pct, p2_rolling_mov, p2_h2h, p2_tournament_wp, p2_career_matches, p2_career_3set_pct, p2_3set_win_pct, p1_win)), columns= columns_names)
    
    frame['date'] = df['tourney_date']
    frame['surface'] = df['surface']
    frame['round'] = df['round']
    frame['court_speed_index'] = df['court_speed_index'] 
    frame['three_set'] = df['three_set']
    
    return frame

#function for reading a list of two players and then populating up to date statistics 
##############################
#IT WOULD BE SO MUCH BETTER IF I COULD JUST PASS IN THE DICTIONARIES. 
#THEN I WOULDN'T HAVE TO RECALCULATE GOING BACK TO 2000 EVERY TIME! LET'S JUST DO THAT!
def matchup_info(matchups, df):

    df, win_pct_dict = win_pct_last_n(df, 15)
    df, mov_dict = game_mov_last_n(df, 15) 
    df, h2h_dict = h2h(df)
    df, elo_dict = compute_elo(df, 32)
    df, hard_elo_dict, clay_elo_dict, grass_elo_dict = surface_elos(df, 32) 
    df, holder = tourney_win_percentage(df)

    #the lists we'll use
    p1_win_pct = []
    p1_mov = []
    p1_h2h = []
    p1_elo = []
    p1_hard_elo = []
    p1_clay_elo = []
    p1_grass_elo = []

    p2_win_pct = []
    p2_mov = []
    p2_h2h = []
    p2_elo = []
    p2_hard_elo = []
    p2_clay_elo = []
    p2_grass_elo = [] 

    matchups.reset_index(inplace = True, drop = True)

    for i in matchups.index:
        # I need to account for one of the players being new. If 
        # it throws an error I'll manually input the correct values. 

        #p1 
        try:
            p1_win_pct.append(mean(win_pct_dict[matchups.iloc[i]['p1']]))
        except Exception:
            p1_win_pct.append(-1)

        try:
            p1_mov.append(mean(mov_dict[matchups.iloc[i]['p1']]))
        except Exception:
            p1_mov.append(0)

        try:
            p1_h2h.append(h2h_dict[matchups.iloc[i]['p1'] + '_' + matchups.iloc[i]['p2']])
        except Exception:
            p1_h2h.append(0)

        try:
            p1_elo.append(elo_dict[matchups.iloc[i]['p1']])
        except Exception:
            p1_elo.append(1500)

        try:
            p1_hard_elo.append(hard_elo_dict[matchups.iloc[i]['p1']])
        except:
            p1_hard_elo.append(1500) 

        try:
            p1_clay_elo.append(clay_elo_dict[matchups.iloc[i]['p1']])
        except:
            p1_clay_elo.append(1500) 

        try:
            p1_grass_elo.append(grass_elo_dict[matchups.iloc[i]['p1']])
        except:
            p1_grass_elo.append(1500) 


        #p2
        try:
            p2_win_pct.append(mean(win_pct_dict[matchups.iloc[i]['p2']]))
        except Exception:
            p2_win_pct.append(-1)

        try:
            p2_mov.append(mean(mov_dict[matchups.iloc[i]['p2']]))
        except Exception:
            p2_mov.append(0)

        try:
            p2_h2h.append(h2h_dict[matchups.iloc[i]['p2'] + '_' + matchups.iloc[i]['p1']])
        except Exception:
            p2_h2h.append(0)

        try:
            p2_elo.append(elo_dict[matchups.iloc[i]['p2']])
        except Exception:
            p2_elo.append(1500)

        try:
            p2_hard_elo.append(hard_elo_dict[matchups.iloc[i]['p2']])
        except:
            p2_hard_elo.append(1500) 

        try:
            p2_clay_elo.append(clay_elo_dict[matchups.iloc[i]['p2']])
        except:
            p2_clay_elo.append(1500) 

        try:
            p2_grass_elo.append(grass_elo_dict[matchups.iloc[i]['p2']])
        except:
            p2_grass_elo.append(1500)
        

    #putting everything in the dataframe I'll return 
    matchups['p1_elo'] = p1_elo
    matchups['p1_hard_elo'] = p1_hard_elo
    matchups['p1_clay_elo'] = p1_clay_elo
    matchups['p1_grass_elo'] = p1_grass_elo
    matchups['p1_rolling_win_pct'] = p1_win_pct 
    matchups['p1_rolling_mov'] = p1_mov 
    matchups['p1_h2h'] = p1_h2h 


    matchups['p2_elo'] = p2_elo 
    matchups['p2_hard_elo'] = p2_hard_elo
    matchups['p2_clay_elo'] = p2_clay_elo
    matchups['p2_grass_elo'] = p2_grass_elo
    matchups['p2_rolling_mov'] = p2_mov
    matchups['p2_rolling_win_pct'] = p2_win_pct 
    matchups['p2_h2h'] = p2_h2h 

    return matchups


#THIS IS THE FUNCTION THAT
#-Takes player names, ages, and matchup surfaces and 
#pulls their data from the relevant dictionaries. 
#In the end, it spits out a prediction. 
def training_model(df, features, matchups):
    #takes the path to the csv of matchups, historical match data, and the list of features to train on. 
    #returns a new csv with calculated stats and predicted probabilities 

    df, _win_pct_dict = win_pct_last_n(df, 15)
    df, _mov_dict = game_mov_last_n(df, 15) 
    df, _h2h_dict = h2h(df)
    df, _elo_dict = compute_elo(df, 32)
    df, _hard_elo_dict, _clay_elo_dict, _grass_elo_dict = surface_elos(df, 32) 
    df, holder = tourney_win_percentage(df)

    swapped = winner_loser_swap(df)

    #training the model on all the data beyond 10000 records 
    training = swapped.iloc[10000:]

    X_train, y_train = np.array(training[features]), np.array(training['p1_win'])
    model = XGBClassifier(random_state = 615) 
    model.fit(X_train, y_train)

    #now I need to bring the data into the matchups dataframe. 

    preds = model.predict_proba(matchups[features]) 
    holder = pd.DataFrame(preds)

    matchups['p1_win'] = holder[1]
    matchups['p2_win'] = holder[0]

    return matchups 


    














