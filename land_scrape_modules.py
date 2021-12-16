# -*- coding: utf-8 -*-
"""
Created on Thu Nov 18 09:00:10 2021

@author: Patty Whack
"""
from selenium import webdriver as wd
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re
import json
import pandas as pd


def launch_browser(test_info_dict):
    """ launch and return a browser  """
    chromedriver_service = Service('./chromedriver.exe')
    new_browser = wd.Chrome(service=chromedriver_service)
    new_browser.get(test_info_dict.get('events_url'))
    new_browser.set_window_rect(x=930, y=0, width=1100, height=1125)
    return new_browser


def wait_for_browser_ready(browser, condition):
    """ called from within functions outside of main """
    # wait until the page is loaded
    waiter = WebDriverWait(browser, 10)
    ready = waiter.until(EC.element_to_be_clickable((By.ID, condition)))
    return ready


def get_test_info(path, file_name):
    """ open the json file and return a dictionary """
    with open(path + './' + file_name, 'r') as t_f:
        json_string = t_f.read()

    test_info_dictionary = json.loads(json_string)
    print(str(test_info_dictionary.keys()))
    return test_info_dictionary


def login(browser, test_info_dictionary):
    """ log in using credentials and locators """
    login_button_locator = test_info_dictionary.get('locators').get('login_submit_button')
    wait_for_browser_ready(browser, login_button_locator)
    user_name_field = browser.find_element(By.ID, test_info_dictionary.get('locators').get('user_name_field'))
    user_name_field.send_keys(test_info_dictionary.get('user_name'))

    user_password_field = browser.find_element(By.ID, test_info_dictionary.get('locators').get('user_pass_field'))
    user_password_field.send_keys(test_info_dictionary.get('user_password'))

    login_button = browser.find_element(By.ID, login_button_locator)
    login_button.click()


def list_events(browser, test_info_dictionary):
    """ navigate to the Upcoming Events page and return a list of all events """
    upcoming_events_locator = test_info_dictionary.get('locators').get('upcoming_events_link')
    wait_for_browser_ready(browser, upcoming_events_locator)

    ''' ensure we are on the Upcoming Events page '''
    upcoming_events_link = browser.find_element(By.ID, upcoming_events_locator)
    upcoming_events_link.click()

    ''' wait until the first rsvp button is ready to be clicked '''
    wait_for_browser_ready(browser, test_info_dictionary.get('locators').get('first_rsvp_button'))

    ''' parse the page source into html '''
    page_soup = BeautifulSoup(browser.page_source, 'html.parser')
    event_title_regex_pattern = test_info_dictionary.get('locators').get('event_title_links_regex')
    evnt_title_links = page_soup.find_all("a", {"id": re.compile(event_title_regex_pattern)})

    return evnt_title_links


def get_required_events(test_info_dictionary):
    tmp_base_path = test_info_dictionary.get('base_path')
    tmp_file_name = test_info_dictionary.get('required_sessions_file')
    req_session_file_path = tmp_base_path + '//' + tmp_file_name
    # slap all required sessions into one string for easy compare
    req_sessions_file = open(req_session_file_path, "r")
    req_sessions_string = req_sessions_file.read()

    return req_sessions_string


def get_event_details(browser, link, test_info_dictionary):
    """
    :param browser: our driven browser
    :param link: the link for the event detail page we are interested in
    :param test_info_dictionary: our secret test information dictionary
    :return: tuple of data we are interested in
    """
    print(link.text)
    click_me = browser.find_element(By.ID, link['id'])
    click_me.click()
    wait_for_browser_ready(browser, test_info_dictionary.get('locators').get('event_rsvp_button'))

    ''' parse the current page into something we can search '''
    tmp_event_soup = BeautifulSoup(browser.page_source, 'html.parser')

    ''' search for the zoom link and get a parent object '''
    zoom_link = tmp_event_soup.find('p', text=re.compile('^https:.*zoom'))
    if zoom_link is not None:
        description_container_element = zoom_link.parent
        zoom_link_text = zoom_link.text
    else:
        # in which case our first attempt fails
        description_container_element = tmp_event_soup.find(class_='column wpc65 left')
        zoom_link_text = description_container_element.text.split('via Zoom:')[1]

    event_start_datetime = description_container_element.find(id='lblDatetime')
    description_text = description_container_element.text.split('Send calendar to email')[1].replace(u'\n', ' ')

    ''' create our tuple to return containing the event details '''
    tmp_tuple = (link.text, event_start_datetime.text.replace('/', '-'),
                 zoom_link_text, description_text.replace(u'\xa0', ' '))
    return tmp_tuple


def return_to_upcoming_events(browser, test_info_dictionary):
    """ simple nav function back to whence we came """
    back_to_calendar_link = browser.find_element(By.ID, test_info_dictionary.get('locators').get('back_calendar_link'))
    back_to_calendar_link.click()
    upcming_events_locator = test_info_dictionary.get('locators').get('upcoming_events_link')
    wait_for_browser_ready(browser, upcming_events_locator)
    tmp_upcoming_events_link = browser.find_element(By.ID, upcming_events_locator)
    tmp_upcoming_events_link.click()
    wait_for_browser_ready(browser, test_info_dictionary.get('locators').get('first_rsvp_button'))


def main():
    local_base_path = r"H:\2021-11-03-HIGHER-LANDING"
    test_info_dict = get_test_info(local_base_path, 'test_info.json')

    # this will take us to the log in page
    browser = launch_browser(test_info_dict)

    # log in using credentials
    login(browser, test_info_dict)
    event_title_links = list_events(browser, test_info_dict)
    required_sessions_string = get_required_events(test_info_dict)

    # the list that will be used to create our dataframe
    events_to_attend_list = []

    for event_title_link in event_title_links:
        if event_title_link.text in required_sessions_string:
            event_details = get_event_details(browser, event_title_link, test_info_dict)
            events_to_attend_list.append(event_details)
            return_to_upcoming_events(browser, test_info_dict)
        else:
            print("skipped {}".format(event_title_link.text))

    ''' use the events to attend list to create a pandas dataframe '''
    events_to_attend_df = pd.DataFrame(events_to_attend_list, columns=["Title", "Start Time", "Link", "Description"])
    events_to_attend_df.to_csv('Required_Events_modules.csv')


if __name__ == '__main__':
    main()
