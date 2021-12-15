# -*- coding: utf-8 -*-
"""
Created on Thu Nov 18 09:00:10 2021
Outputs a list of events that a student must attend
@author: Patty Whack - video here - https://www.youtube.com/watch?v=hKT7jWbkxmc
"""
from selenium import webdriver as wd
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re
import pandas as pd
import json

''' open a new chrome browser using the webdriver service '''
chromedriver_service = Service('./chromedriver.exe')
browser = wd.Chrome(service=chromedriver_service)

''' get secret test information from a json file '''
base_path = r"H:\2021-11-03-HIGHER-LANDING\\"
test_info_file_name = 'secret_test_info.json'
with open(base_path + './' + test_info_file_name, 'r') as t_f:
    json_string = t_f.read()
test_info_dict = json.loads(json_string)

''' open the browser to the events page of the course '''
url = test_info_dict.get('events_url')
browser.get(url)
browser.set_window_rect(x=930, y=0, width=1200, height=1125)
''' wait until we can click on the log in button'''
waiter = WebDriverWait(browser, 10)
ready_for_input = waiter.until(EC.element_to_be_clickable((
    By.ID, test_info_dict.get('locators').get('login_submit_button'))))

''' enter the user name and password by using locators, all data is stored in test_info_dict '''
user_name_field = browser.find_element(By.ID, test_info_dict.get('locators').get('user_name_field'))
user_name_field.send_keys(test_info_dict.get('user_name'))
user_password_field = browser.find_element(By.ID, test_info_dict.get('locators').get('user_pass_field'))
user_password_field.send_keys(test_info_dict.get('user_password'))
login_button = browser.find_element(By.ID, test_info_dict.get('locators').get('login_submit_button'))
login_button.click()

''' wait until the Upcoming Events link is ready to be clicked '''
upcoming_events_locator = test_info_dict.get('locators').get('upcoming_events_link')
calendar_ready = waiter.until(EC.element_to_be_clickable((By.ID, upcoming_events_locator)))
upcoming_events_link = browser.find_element(By.ID, upcoming_events_locator)
upcoming_events_link.click()

''' wait until the first rsvp button is ready to be clicked '''
first_rsvp_button_locator = test_info_dict.get('locators').get('first_rsvp_button')
upcoming_events_page_ready = waiter.until(EC.element_to_be_clickable((By.ID, first_rsvp_button_locator)))

''' use the html parser from BeautifulSoup to find all the links matching a specific pattern  '''
page_soup = BeautifulSoup(browser.page_source, 'html.parser')
event_title_regex_pattern = test_info_dict.get('locators').get('event_title_links_regex')
event_title_links = page_soup.find_all("a", {"id": re.compile(event_title_regex_pattern)})

''' read the contents of the required sessions file into string for easy comparison '''
required_sessions_file = open(r"H:\2021-11-03-HIGHER-LANDING\schedule.txt", "r")
required_sessions_string = required_sessions_file.read()
# todo: should go line by line split at (must take November 4) and then check date

''' an empty list which will be populated in the for loop below '''
events_to_attend_list = []
''' go through all the events on the page and gather the event start time as well as the zoom link  '''
for link in event_title_links:
    if link.text in required_sessions_string:
        '''link.text, event_time, zoom_link, description  '''
        print(link.text)
        ''' use the id property from the current link to enter the event details page '''
        click_me = browser.find_element(By.ID, link['id'])
        click_me.click()
        rsvp_page_ready = waiter.until(EC.element_to_be_clickable((
            By.ID, test_info_dict.get('locators').get('event_rsvp_button'))))
        ''' parse the current page and search for the zoom link '''
        tmp_event_soup = BeautifulSoup(browser.page_source, 'html.parser')

        zoom_link = tmp_event_soup.find('p', text=re.compile('^https:.*zoom'))
        # get the parent/containing element
        if zoom_link is not None:
            description_container_element = zoom_link.parent
            zoom_link_text = zoom_link.text
        else:
            # in which case there is a \xa0 that is stopping our first attempt
            description_container_element = tmp_event_soup.find(class_='column wpc65 left')
            zoom_link_text = description_container_element.text.split('via Zoom:')[1]

        ''' this is not perfect currently pulling out too many spaces '''
        description_text = description_container_element.text.split('Send calendar to email')[1].replace(u'\n', ' ')

        ''' collect the start time, date, and full event description '''
        event_start_datetime_locator = test_info_dict.get('locators').get('event_start_datetime')
        event_start_datetime = description_container_element.find(id=event_start_datetime_locator)
        event_start_datetime_formatted = event_start_datetime.text.replace('/', '-')
        # todo: attending_span = description_container_element.find(id='description_container_element')
        ''' create a tuple to add to the events to attend list '''
        tmp_tuple = (link.text, event_start_datetime_formatted, zoom_link_text, description_text.replace(u'\xa0', ' '))
        print(str(tmp_tuple))
        events_to_attend_list.append(tmp_tuple)
        ''' navigate back to previous page '''
        back_to_calendar_link = browser.find_element(By.ID, test_info_dict.get('locators').get('back_calendar_link'))
        back_to_calendar_link.click()
        tmp_calendar_ready = waiter.until(EC.element_to_be_clickable((By.ID, upcoming_events_locator)))
        tmp_upcoming_events_link = browser.find_element(By.ID, upcoming_events_locator)
        tmp_upcoming_events_link.click()
        tmp_upcoming_events_page_ready = waiter.until(EC.element_to_be_clickable((By.ID, first_rsvp_button_locator)))
    else:
        print("skipped {}".format(link.text))
''' use the events to attend list to create a pandas dataframe '''
events_to_attend_df = pd.DataFrame(events_to_attend_list, columns=["Title", "Start Time", "Link", "Description"])
events_to_attend_df.to_csv("{}-Required_Events.csv".format(base_path))
