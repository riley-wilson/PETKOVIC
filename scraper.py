import time 
from datetime import datetime
import pandas as pd 
import numpy as np 
import re 
import sys 
sys.path.append('path/to/chromedriver')
from selenium import webdriver 
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains


from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By


tournament_name = 'tournament name'
tournament_url = 'https://www.wtatennis.com/tournament/1038/madrid/2023/scores/LS'
draw_size = 128

#The tournament URL should be the url of a matchup page on the WTA website with the last three numbers 
#removed. A matchup page is the WTA page describing match statistics. For instance, here is the matchup page for the 
#2023 WTA Madrid final between Swiatek and Sabalenka: https://www.wtatennis.com/tournament/1038/madrid/2023/scores/LS001


#functions I developed to take a list of scores and put them in p1 or p2's perspective
def scorify_p1(l):
    indices = list(range(0, len(l)))
    score = ""
    for i in indices:
        score = score + str(l[i])

    return score

def scorify_p2(l):
    indices = list(range(0, len(l)))
    score = ""
    for i in indices:
        if i % 2 == 1:
            score = score+ str(l[i])
            score = score + str(l[i-1])
            print(score)
    
    return score 

#scraper function
def scrape(tournament, url, upper, lower):

    #creating a chromedriver instance
    ser = Service('path/to/chromedriver')
    op = webdriver.ChromeOptions() 
    driver = webdriver.Chrome(service = ser, options = op)

    #opening up the WTA website to make sure things work. 
    driver.get("https://www.wtatennis.com")

    driver.implicitly_wait(10)
    driver.maximize_window()

    #creating the dataframe in Sackman's format. 
    df = pd.DataFrame(columns = ['tourney_id', 'tourney_name', 'draw_size', 'tourney_level', 'tourney_date',
                             'match_num', 'winner_seed', 'winner_entry', 'winner_name', 'winner_hand',
                             'winner_ht', 'winner_ioc', 'winner_age', 'loser_id', 
                             'loser_seed', 'loser_entry', 'loser_name', 'loser_hand', 'loser_ht', 
                             'loser_ioc', 'loser_age', 'score', 'best_of', 'round', 'minutes', 
                             'w_ace', 'w_df', 'w_svpt', 'w_1stIn', 'w_1stWon', 'w_2ndWon', 'w_SvGms',
                             'w_bpSaved', 'w_bpFaced', 'l_ace', 'l_df', 'l_svpt', 'l_1stIn', 
                             'l_1stWon', 'l_2ndWon', 'l_SvGms', 'l_bpSaved', 'l_bpFaced', 'winner_rank', 'winner_rank_points', 
                             'loser_rank', 'loser_rank_points'])

    #starting the loop
    for i in list(range(lower, upper +1)):

        #handling url values below 10 or above 100
        if i < 10:
            url_iter = url + '00' + str(i)
        elif i < 100:
            url_iter = url + '0' + str(i)
        else:
            url_iter = url + str(i)

        #going to the url
        driver.get(url_iter)
        

        #if the page is blank, then I'm going to go to the next loop
        try:
            tester = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[1]/div/div[1]/div/div')
        except:
            continue

        #finding player information
        #p1
        #################
        #full name
        p1_page = driver.find_element(By.XPATH, "//main[@id='main-content']/div[1]/div[2]/section[1]/div[1]/div[2]/div[2]/table[1]/tbody[1]/tr[1]/th[1]/div[1]/div[1]/div[1]/a[1]/div[1]/span[1]/span[2]")
        time.sleep(5)
        p1_page.click()
        print('we passed the click')

        #accepting cookies 
        try:
            cookie = driver.find_element(By.XPATH, "//button[contains(@class,'button button--icon-left')]" )
            cookie.click()
        except:
            pass

        p1_fn = driver.find_element(By.XPATH, "//h1[@class='profile-header-info__name']//span").text
        p1_ln = driver.find_element(By.XPATH, "(//h1[@class='profile-header-info__name']//span)[2]").text

        p1_name = p1_fn + ' ' + p1_ln
        print(p1_name)

        #country
        try:
            p1_country = driver.find_element(By.XPATH, '/html/body/section[4]/div/div[2]/div/div[1]/div').text 
            print(p1_country)
        except Exception:
            p1_country = 'U'

        

        #birthday
        try:
            p1_bd = driver.find_element(By.XPATH, '/html/body/section[4]/div/div[2]/div/div[2]/div[2]/div[1]/div[3]').text 
            print(p1_bd)
        except Exception:
            p1_bd = 'Jan 1 2050'

        

        #for safety purposes
        time.sleep(1)

        #height
        try:
            p1_ht = driver.find_element(By.XPATH, '/html/body/section[4]/div/div[2]/div/div[2]/div[1]/div[1]/div[3]').text
            p1_ht = re.sub('[^0-9]', "", p1_ht)
            print(p1_ht)
        except Exception:
            p1_ht = '-1'

        

        #hand
        try:
            p1_hand = driver.find_element(By.XPATH, '/html/body/section[4]/div/div[2]/div/div[2]/div[1]/div[2]/div[2]').text
            print(p1_hand)
        except Exception:
            p1_hand = 'U'

        

        #going back
        driver.back()

        #p2
        ##################

        #full name 
        p2_page = driver.find_element(By.XPATH, "//main[@id='main-content']/div[1]/div[2]/section[1]/div[1]/div[2]/div[2]/table[1]/tbody[1]/tr[2]/th[1]/div[1]/div[1]/div[1]/a[1]/div[1]/span[1]/span[2]")
        time.sleep(5)
        p2_page.click()

        p2_fn = driver.find_element(By.XPATH, "//h1[@class='profile-header-info__name']//span").text
        p2_ln = driver.find_element(By.XPATH, "(//h1[@class='profile-header-info__name']//span)[2]").text
        p2_name = p2_fn + ' ' + p2_ln
        print(p2_name)

        #country 
        try:
            p2_country = driver.find_element(By.XPATH, '/html/body/section[4]/div/div[2]/div/div[1]/div').text 
            print(p2_country)
        except Exception:
            p2_country = "U"
        

        #birthday
        try:
            p2_bd = driver.find_element(By.XPATH, '/html/body/section[4]/div/div[2]/div/div[2]/div[2]/div[1]/div[3]').text 
            print(p2_bd)
        except Exception:
            p2_bd = 'Jan 1 2050'

        #for safety purposes 
        time.sleep(1)

        #height 
        try:
            p2_ht = driver.find_element(By.XPATH, '/html/body/section[4]/div/div[2]/div/div[2]/div[1]/div[1]/div[3]').text
            p2_ht = re.sub('[^0-9]', "", p2_ht)
            print(p2_ht) 
        except Exception:
            p2_ht = '-1'


        #hand
        try:
            p2_hand = driver.find_element(By.XPATH, '/html/body/section[4]/div/div[2]/div/div[2]/div[1]/div[2]/div[2]').text
            print(p1_hand)
        except Exception:
            p2_hand = 'U'

        #going back
        driver.back()

        ##########################################################################################

        #getting scores
        #If anything goes wrong, then I'll hop into the next loop
        try:
            p1_set1 = int(driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[1]/div/div[2]/div[2]/table/tbody/tr[1]/td[1]').text[0])
            p2_set1 = int(driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[1]/div/div[2]/div[2]/table/tbody/tr[2]/td[1]').text[0])

            p1_set2 = int(driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[1]/div/div[2]/div[2]/table/tbody/tr[1]/td[2]').text[0])
            p2_set2 = int(driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[1]/div/div[2]/div[2]/table/tbody/tr[2]/td[2]').text[0])
        except Exception:
            continue
        
        #################################################################
        
       #figuring out who's the winner: 
       #I want whoever won more sets. Let's just count who gets to two sets first. I'll structure it so we 
       #only look for the third set if nobody has gotten to two yet. 

        p1set = 0
        p2set = 0

        score_list = [p1_set1, p2_set1, p1_set2, p2_set2]

        if p1_set1 > p2_set1:
            p1set += 1 
        else:
            p2set +=1 

        if p1_set2 > p2_set2: 
            p1set += 1
        else:
            p2set +=1 

        if p1set != 2 and p2set != 2:
            p1_set3 = int(driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[1]/div/div[2]/div[2]/table/tbody/tr[1]/td[3]').text[0])
            p2_set3 = int(driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[1]/div/div[2]/div[2]/table/tbody/tr[2]/td[3]').text[0])

            score_list.append(p1_set3)
            score_list.append(p2_set3) 

            if p1_set3 > p2_set3:
                p1set += 1 
            else:
                p2set += 1 
    

        #creating the scores when p1 is the winner and when p2 is the winner. 


        if p1set > p2set:
            print(score_list)
            p1_score = scorify_p1(score_list)
        else:
            print(score_list)
            p2_score = scorify_p2(score_list)

        ######################################################################################
        #Match data 

        #Date 
        match_date = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/header/div[1]/div').text 
        print('date ', match_date)

        #Surface 
        match_surface = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/header/div[2]/div').text 
        print('surface', match_surface)

        #Round 
        match_round = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/header/div[1]/h3').text
        print('match round', match_round)


        ########################################################################################


        #Extracting statistics on the match. 
        #creating an instance of the action chains 
        a = ActionChains(driver)

        #Ace counts 
        ###########
        try:
            p1_ace = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[2]/div/div/div/div[2]/section/div/div/div[1]/div[1]/div[1]/div[1]/div[1]/span').text
        except Exception:
            p1_ace = '-1'

        try:
            p2_ace = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[2]/div/div/div/div[2]/section/div/div/div[1]/div[1]/div[1]/div[2]/div[2]/span').text
        except Exception:
            p2_ace = '-1'

        print(p1_ace)

        print(p2_ace)

        #Double faults 
        ##############

        #scrolling to the element 
        try:
            p1_df_elem = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[2]/div/div/div/div[2]/section/div/div/div[1]/div[1]/div[2]/div[1]/div[1]/span')
            a.scroll_to_element(p1_df_elem).perform()
            p1_df = p1_df_elem.text
        except Exception:
            p1_df = '-1'

        try:
             p2_df = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[2]/div/div/div/div[2]/section/div/div/div[1]/div[1]/div[2]/div[2]/div[2]/span').text
        except Exception:
            p2_df = '-1'

        #sleep for safety purposes
        time.sleep(1) 

        #first serve stats 
        ##################

        #first serve in 
        try:
            p1_fs_elem = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[2]/div/div/div/div[2]/section/div/div/div[1]/div[1]/div[3]/div[1]/div[1]/span[2]')
            a.scroll_to_element(p1_fs_elem).perform()
            p1_fs = p1_fs_elem.text
        except Exception:
            p1_fs = '-1'

        try:
            p2_fs = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[2]/div/div/div/div[2]/section/div/div/div[1]/div[1]/div[3]/div[2]/div[2]/span[2]').text 
        except Exception:
            p2_fs = '-1'


        #1st serve points won 
        try:
            p1_fsw_elem = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[2]/div/div/div/div[2]/section/div/div/div[1]/div[1]/div[4]/div[1]/div[1]/span[2]')
            a.scroll_to_element(p1_fsw_elem).perform()
            p1_fsw = p1_fsw_elem.text 
        except Exception:
            p1_fsw = '-1'

        try:
            p2_fsw = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[2]/div/div/div/div[2]/section/div/div/div[1]/div[1]/div[4]/div[2]/div[2]/span[2]').text 
        except Exception:
            p2_fsw = '-1'

        #2nd serve points won 
        try:
            p1_ssw_elem = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[2]/div/div/div/div[2]/section/div/div/div[1]/div[1]/div[5]/div[1]/div[1]/span[2]')
            a.scroll_to_element(p1_ssw_elem).perform()
            p1_ssw = p1_ssw_elem.text 
        except Exception:
            p1_ssw = '-1'

        try:
            p2_ssw = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[2]/div/div/div/div[2]/section/div/div/div[1]/div[1]/div[5]/div[2]/div[2]/span[2]').text 
        except Exception:
            p2_ssw ='-1'

        #sleep for safety purposes
        time.sleep(1)

        #bp saved
        try:
            p1_bps_elem = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[2]/div/div/div/div[2]/section/div/div/div[1]/div[1]/div[6]/div[1]/div[1]/span[2]')
            a.scroll_to_element(p1_bps_elem).perform()
            p1_bps = p1_bps_elem.text
        except Exception:
            p1_bps = '-1'

        try:
            p2_bps = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[2]/div/div/div/div[2]/section/div/div/div[1]/div[1]/div[6]/div[2]/div[2]/span[2]').text
        except Exception:
            p2_bps = '-1'


        #Service games 
        try:
            p1_svg_elem = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[2]/div/div/div/div[2]/section/div/div/div[1]/div[1]/div[7]/div[1]/div[1]/span')
            a.scroll_to_element(p1_svg_elem).perform()
            p1_svg = p1_svg_elem.text 
        except Exception:
            p1_svg = '-1'

        try:
            p2_svg = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[2]/div/div/div/div[2]/section/div/div/div[1]/div[1]/div[7]/div[2]/div[2]/span').text
        except Exception:
            p2_svg = '-1'

        #sleep for safety purposes
        time.sleep(1)

        #Return
        ########

        #first serve return points won 
        try:
            p1_fsr_elem = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[2]/div/div/div/div[2]/section/div/div/div[1]/div[2]/div[1]/div[1]/div[1]/span[2]')
            a.scroll_to_element(p1_fsr_elem).perform()
            p1_fsr = p1_fsr_elem.text 
        except Exception:
            p1_fsr = '-1'

        
        try:
            p2_fsr = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[2]/div/div/div/div[2]/section/div/div/div[1]/div[2]/div[1]/div[2]/div[2]/span[2]').text 
        except Exception:
            p2_fsr = '-1'


        #second serve return points won 
        try:
            p1_ssr_elem = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[2]/div/div/div/div[2]/section/div/div/div[1]/div[2]/div[2]/div[1]/div[1]/span[2]')
            a.scroll_to_element(p1_ssr_elem).perform()
            p1_ssr = p1_ssr_elem.text 
        except Exception:
            p1_ssr = '-1'

        try:
            p2_ssr = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[2]/section[2]/div/div/div/div[2]/section/div/div/div[1]/div[2]/div[2]/div[2]/div[2]/span[2]').text
        except Exception:
            p2_ssr = '-1'


        #####################################################################################################################################
        #I have all the information I can gather. Now I want to put it in the appropriate columns. I'll need to do
        #some transformations on these as well. 

        #calculating the player's ages 
        #############
        p1_bd = datetime.strptime(p1_bd, '%b %d %Y')
        p1_age = round((datetime.today() - p1_bd).days / 365, 1)  

        p2_bd = datetime.strptime(p2_bd, '%b %d %Y')
        p2_age = round((datetime.today() - p2_bd).days / 365, 1)  

        #turning match_date into a string
        ###############
        dt_match = datetime.strptime(match_date, '%B %d')
        #putting it all together in a string
        if dt_match.month < 10:
            match_date = '2023' + '0' + str(dt_match.month) + match_date[-2:]
        else:
            match_date = '2023' + str(dt_match.month) + match_date[-2:]

        #mapping WTA rounds into Sackman's format. 
        rounds_dict = {'128': 'R128', '64': 'R64', '32': 'R32', '16': 'R16',
                       'Quarterfinal': 'QF', 'Semifinal': 'SF', 'Final': 'F'}
        last = match_round.split(' ')[-1]
        match_round = rounds_dict[last]


        #extracting relevant stats from the webpage data. 
        ##################

        #aces
        p1_ace = int(p1_ace)
        p2_ace = int(p2_ace) 

        #double faults 
        p1_df = int(p1_df)
        p2_df = int(p2_df) 

        #svpt (total number of serve points)
        #I'll need to sum the denominators of first serve points won and second serve points won. 

        p1_fs = p1_fs.split("/") 
        p1_ssw = p1_ssw.split('/')

        p1_svpt = int(p1_fs[-1]) + int(p1_ssw[-1])

        p2_fs = p2_fs.split('/') 
        p2_ssw = p2_ssw.split('/')

        p2_svpt = int(p2_fs[-1]) + int(p2_ssw[-1])

        #1stin
        #the number of first serves made 
        p1_1stIn = int(p1_fs[0])

        p2_1stIn = int(p2_fs[0])

        #1stWon
        #the number of first serve points won 
        p1_1stWon = int(p1_fsw.split('/')[0])
        p2_1stWon = int(p2_fsw.split('/')[0])

        #2ndWon
        #the number of second serve points won 
        p1_2ndWon = int(p1_ssw[0])
        p2_2ndWon = int(p2_ssw[0])

        #SvGms
        #total number of serve games 

        p1_SvGms = int(p1_svg)
        p2_SvGms = int(p2_svg) 

        #bpSaved
        #number of break points saved 

        p1_bps = p1_bps.split('/')
        p2_bps = p2_bps.split('/')
        print(p2_bps)


        p1_bpSaved = int(p1_bps[0])
        p2_bpSaved = int(p2_bps[0])

        #bpFaced
        #number of break points faced by the player 
        p1_bpFaced = int(p1_bps[1])
        p2_bpFaced = int(p2_bps[1])

        #putting it in the dataframe
        if p1set > p2set:
            row = {'tourney_id': -1, 'tourney_name': tournament, 'surface': match_surface.split(' ')[0], 
                    'draw_size': 64, 'tourney_level': 'n/a',
                    'tourney_date': match_date, 'match_num': -1,
                    'winner_id': -1, 'winner_seed':-1, 
                    'winner_name': p1_name, 'winner_hand': p1_hand[0],
                    'winner_ht': p1_ht, 'winner_ioc': p1_country, 'winner_age': p1_age, 
                    'loser_id': -1, 'loser_seed': -1, 'loser_entry': -1,
                    'loser_name': p2_name, 'loser_hand': p2_hand[0], 'loser_ht': p2_ht,
                    'loser_ioc': p2_country, 'loser_age': p2_age, 
                    'score': p1_score, 'best_of': -1, 'round': match_round, 'minutes': -1, 
                    'w_ace': p1_ace, 'w_df': p1_df, 'w_svpt': p1_svpt, 'w_1stIn': p1_1stIn, 'w_1stWon': p1_1stWon,
                    'w_2ndWon': p1_2ndWon, 'w_SvGms': p1_SvGms, 'w_bpSaved': p1_bpSaved, 'w_bpFaced': p1_bpFaced,
                    'l_ace': p2_ace, 'l_df': p2_df, 'l_svpt': p2_svpt, 'l_1stIn': p2_1stIn, 'l_1stWon': p2_1stWon,
                    'l_2ndWon': p2_2ndWon, 'l_SvGms': p2_SvGms, 'l_bpSaved': p2_bpSaved, 'l_bpFaced': p2_bpFaced,
                    'winner_rank': -1, 'winner_rank_points': -1, 'loser_rank': -1, 'loser_rank_points': -1}
        else:
            row = {'tourney_id': -1, 'tourney_name': tournament, 'surface': match_surface.split(' ')[0], 
                    'draw_size': 64, 'tourney_level': 'n/a',
                    'tourney_date': match_date, 'match_num': -1,
                    'winner_id': -1, 'winner_seed':-1, 
                    'winner_name': p2_name, 'winner_hand': p2_hand[0],
                    'winner_ht': p2_ht, 'winner_ioc': p2_country, 'winner_age': p2_age, 
                    'loser_id': -1, 'loser_seed': -1, 'loser_entry': -1,
                    'loser_name': p1_name, 'loser_hand': p1_hand[0], 'loser_ht': p1_ht,
                    'loser_ioc': p1_country, 'loser_age': p1_age, 
                    'score': p2_score, 'best_of': -1, 'round': match_round, 'minutes': -1, 
                    'w_ace': p2_ace, 'w_df': p2_df, 'w_svpt': p2_svpt, 'w_1stIn': p2_1stIn, 'w_1stWon': p2_1stWon,
                    'w_2ndWon': p2_2ndWon, 'w_SvGms': p2_SvGms, 'w_bpSaved': p2_bpSaved, 'w_bpFaced': p2_bpFaced,
                    'l_ace': p1_ace, 'l_df': p1_df, 'l_svpt': p1_svpt, 'l_1stIn': p1_1stIn, 'l_1stWon': p1_1stWon,
                    'l_2ndWon': p1_2ndWon, 'l_SvGms': p1_SvGms, 'l_bpSaved': p1_bpSaved, 'l_bpFaced': p1_bpFaced,
                    'winner_rank': -1, 'winner_rank_points': -1, 'loser_rank': -1, 'loser_rank_points': -1}

        df = pd.concat([df, pd.DataFrame([row])], ignore_index = True)

    return df 


t = scrape(tournament_name,tournament_url, draw_size, 1)
t.to_csv(tournament_name)












