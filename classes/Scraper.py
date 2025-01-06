import os
import pandas as pd
import json
import re
from time import sleep
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

class FlightScraper:
    def __init__(self):
        """
        Initialize the FlightScraper.

        Sets up the Chrome WebDriver with incognito mode.
        """
        # Set up Chrome driver options
        options = webdriver.ChromeOptions()
        options.add_argument('--incognito')

        # Initialize Chrome driver
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def get_times(self, flight, id:int) -> Dict:
        """
        Get the departure time, arrival time, and duration of a flight.

        Args:
            flight: The flight element containing the time information.
            id: The ID of the flight.

        Returns:
            A dictionary with the following keys:
            - 'departure_time': The departure time of the flight.
            - 'arrival_time': The arrival time of the flight.
            - 'duration': The duration of the flight.
            - 'id': The ID of the flight.
        """
        ###################
        # Get hours
        hours = flight.find_elements(
            by=By.XPATH, value='.//span[contains(@class, "HourFlight")]')

        if len(hours) < 2:
            return {}

        ###################
        # Departure time
        departure = hours[0].text

        ###################
        # Arrival time
        arrival = hours[1].text

        ###################
        # Duration
        duration = flight.find_element(
            by=By.XPATH, value='.//div[contains(@class, "flight-duration")]/span[2]').text

        ###################
        # Price
        amount_element = flight.find_element(
            by=By.XPATH, value='.//div[contains(@class, "TextAmount")]'
        )

        amount_text = amount_element.text

        numeric_amount = re.sub(r'[^0-9.,]', '', amount_text)

        ###################
        # Stop or no
        is_direct = flight.find_element(
            by=By.XPATH, value='.//div[contains(@class, "ContainerFooterCard")]/a/span'
        ).text

        flight_info = {
            'departure_time': departure,
            'arrival_time': arrival,
            'duration': duration,
            'numeric_amount': numeric_amount,
            'is_direct': is_direct,
            'id': id,
        }

        return flight_info

    def get_info(self) -> List[Dict]:
        """
        Get flight information for each flight element (prices, times, and stopovers) on the page.

        Returns:
            A list of dictionaries, where each dictionary contains flight information including prices, times, and stopovers.
        """
        flights = self.driver.find_elements(
            by=By.XPATH, value='//ol[@aria-label="Voos disponíveis."]/li')

        info = []
        i = 0

        for flight in flights:
            # Extract the HTML content of the flight element
            flight_html = flight.get_attribute('outerHTML')

            # Parse and prettify the HTML using BeautifulSoup
            soup = BeautifulSoup(flight_html, 'html.parser')
            pretty_html = soup.prettify()

            # Get general flight times
            times = self.get_times(flight, i)

            info.append(times)
            i += 1

        return info

    def scrape_latam(self, urls) -> pd.DataFrame:
        """
        Scrape flight information from LATAM website using the provided URLs.

        Args:
            urls: A list of URLs to scrape.

        Returns:
            A Pandas DataFrame containing the scraped flight information.
        """
        delay = 20

        # If it's a single string, convert it to a list
        if type(urls) == str:
             urls = [urls]

        info = []
        for url in urls:
            print('Scraping URL:', url)
            self.driver.get(url)
            try:
                # Wait for the flight list element to be visible
                flight_list = WebDriverWait(self.driver, delay).until(
                    EC.presence_of_all_elements_located(
                        (By.XPATH, '//ol[@aria-label="Voos disponíveis."]/li')
                    )
                )
                print(f"Page is ready! Found {len(flight_list)} flights.")

                # Extract flight information
                info = self.get_info()
            except TimeoutException:
                print("Loading took too much time!")
            except NoSuchElementException:
                print("Element not found")

        # Quit the Chrome driver
        self.driver.quit()

        return info
