import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from classes.Scraper import FlightScraper
from urllib.parse import urlparse, parse_qs
from utils.save_flight_information import save_flight_information
from utils.save_flight_information import save_aggregated_csv
from utils.get_flight_search_inputs import get_flight_search_inputs

if __name__ == "__main__":
    try:
        # Set up the base URL
        url_base = 'https://www.latamairlines.com/br/pt/oferta-voos?'

        urls, departure_dates, return_dates, origin, destination = get_flight_search_inputs(url_base)

        # Initialize an empty DataFrame for aggregating all flight data
        aggregated_flight_data = pd.DataFrame()

        def scrape_url(index, url):
            scraper = FlightScraper()
            flight_data_df = scraper.scrape_latam(url)

            # Convert list to DataFrame
            flight_data_df = pd.DataFrame(flight_data_df)

            # Parse the URL
            parsed_url = urlparse(url)

            # Extract query parameters
            query_params = parse_qs(parsed_url.query)

            # Get the inbound value
            outbound_datetime = query_params.get("outbound", [None])[0]
            inbound_datetime = query_params.get("inbound", [None])[0]

            # Extract just the date (before 'T')
            departure_date_formatted = outbound_datetime.split("T")[0] if outbound_datetime else None
            return_date_formatted = inbound_datetime.split("T")[0] if inbound_datetime else None
            airport_codes = f"{origin.upper()}_{destination.upper()}"

            # Add metadata columns to the DataFrame
            flight_data_df['departure_date_formatted'] = departure_date_formatted
            flight_data_df['return_date_formatted'] = return_date_formatted
            flight_data_df['airport_codes'] = airport_codes

            return flight_data_df

        # Use ThreadPoolExecutor to scrape multiple URLs concurrently
        with ThreadPoolExecutor(max_workers=6) as executor:
            future_to_url = {
                executor.submit(scrape_url, index, url): url
                for index, url in enumerate(urls)
            }

            for future in as_completed(future_to_url):
                try:
                    # Get the result from the future
                    result_df = future.result()
                    # Append the result to the aggregated DataFrame
                    aggregated_flight_data = pd.concat([aggregated_flight_data, result_df], ignore_index=True)
                except Exception as e:
                    print(f"An error occurred while scraping {future_to_url[future]}: {e}")

        # Replace thousand separators (periods) with an empty string
        aggregated_flight_data['numeric_amount'] = aggregated_flight_data['numeric_amount'].str.replace('.', '', regex=False)

        # Replace decimal separators (commas) with a period
        aggregated_flight_data['numeric_amount'] = aggregated_flight_data['numeric_amount'].str.replace(',', '.')

        # Convert to float after cleaning
        aggregated_flight_data['numeric_amount'] = pd.to_numeric(aggregated_flight_data['numeric_amount'], errors='coerce')

        # Print to verify the output
        print(aggregated_flight_data['numeric_amount'])

        # Sort the dataframe by numeric_amount in ascending order
        aggregated_flight_data_sorted = aggregated_flight_data.sort_values(by='numeric_amount', ascending=True)

        save_aggregated_csv(aggregated_flight_data_sorted, "aggregated_flights")

        print("Flight search completed.")

    except Exception as e:
        print('An error occurred:', str(e))