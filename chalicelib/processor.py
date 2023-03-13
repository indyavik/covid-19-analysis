
import pandas as pd
import requests
import datetime 
import logging
logging.basicConfig(level=logging.INFO)

# to do: move to a config file
URL = "https://healthdata.gov/resource/j8mb-icvb.json"
END_DATE = None
NUM_DAYS = 40

def analyze():
    # get the datafarame and call analyze_health_data
    error, response = None, None
    try:
        df = get_json_data(end_date=END_DATE, num_days=NUM_DAYS, url=URL)
        if len(df) > 0:
            response = analyze_health_data(df)
        else:
            error = "No data found."
        
    except Exception as e:
        logging.error(f"Error occurred while fetching data: {e}")
        error =e 
    
    return {"error": error , "metrics": response }
    

def get_json_data(end_date=None, num_days=None, url = URL):
    """
    Paginate and return a pandas DF. 
    num_days = number of days to fetch data for. 40 days for 7 day average + some buffer in case most recent data is not available.
    """
    results_per_page = 5000 # to do: move to a config file
    offset=0
    date_format = '%Y-%m-%dT%H:%M:%S.%f'

    # calculate the start and end dates for the query
    if not end_date:
        end_date = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0).strftime(date_format)

    start_date = (datetime.datetime.today() - datetime.timedelta(days=num_days)).replace(hour=0, minute=0, second=0, microsecond=0).strftime(date_format)

    # loop through the pages of the API endpoint until we have fetched data for num_days
    all_data = []
    logging.info(f"Fetching data from {start_date} to {end_date} ..")

    try:
        while True:

            # construct the query to filter by date and set the pagination parameters
            query = f"?$where=date between '{start_date}' and '{end_date}'&$limit={results_per_page}&$offset={offset}&$order=:id"
            logging.info(f"offset = {offset} query = {query} ")
            # make the request
            response = requests.get(url + query)
            response.raise_for_status()

            data = response.json()
            all_data.extend(data)

            # break out of the loop. 
            if len(data) ==0:
                logging.info("No more data to fetch.")
                break

            # move to the next page of data
            offset += results_per_page

    except Exception as e:
        logging.error(f"Error occurred while fetching data: {e}")
        return None

    df = pd.DataFrame(all_data)
    return df

def analyze_health_data(df):

    # convert columns to appropriate data types
    df['date'] = pd.to_datetime(df['date'])
    df['new_results_reported'] = df['new_results_reported'].astype('int')
    df['total_results_reported'] = df['total_results_reported'].astype('int')

    # sort dataframe by date
    df = df.sort_values(by=['date'])
    most_recent_date = df['date'].max()

    # keep only 37 days of data from most recent date. discard the rest. 
    date_37_days_ago = most_recent_date - datetime.timedelta(days=37)
    df = df.loc[df['date'] >= date_37_days_ago] # inclusive. 

    try:

        # calculate the total pcr tests for yesterday.
        yesterday_date = most_recent_date - pd.DateOffset(days=1)
        data_for_pcr = df[df['date'] == yesterday_date]
        total_pcr_cumulative = data_for_pcr['total_results_reported'].sum().tolist() # convert to make it serializable by chalice
        logging.info(f"cumulative pcr: {total_pcr_cumulative}")

        # get rolling 7 day average. 
        daily_new_df = df.groupby('date')['new_results_reported'].sum().reset_index()
        daily_new_df['rolling_7_avg'] = daily_new_df['new_results_reported'].rolling(window=7).mean().round(2)
        df_subset = daily_new_df[['date', 'rolling_7_avg']].tail(30)
        df_subset['date'] = df_subset['date'].dt.strftime('%Y-%m-%d')

        # create dictionary with column 1 as keys and column 2 as values
        return_dict = df_subset.set_index('date')['rolling_7_avg'].to_dict()

        # Calculate the positivity rate for each state for 30 days. 
        date_30_days_ago = most_recent_date - datetime.timedelta(days=30)
        df = df.loc[df['date'] >= date_30_days_ago] 
        state_positivity = (df.loc[df['overall_outcome'] == 'Positive'].groupby('state')['new_results_reported'].sum() /
                df.groupby('state')['new_results_reported'].sum())

        # Get the 10 states with the highest positivity rates
        top_10_states = state_positivity.sort_values(ascending=False).head(10).to_dict() 
        logging.info(f"Top 10 states with highest positivity rates: {top_10_states}")
    
    except Exception as e:
        logging.error(f"Error occurred while analyzing data: {e}")
        total_pcr_cumulative = None
        return_dict = None
        top_10_states = None


    return {
        "total_pcr_cumulative": total_pcr_cumulative, 
        "seven_day_rolling_mean": return_dict,
        "top_10_states": top_10_states
    }


if __name__ == "__main__":
    metrics = analyze()
    print(metrics)