import app
import chalicelib.processor as processor
from chalice.test import Client
import pandas as pd
from datetime import datetime


def test_process_baseline():
    with Client(app.app) as client:
        response = client.http.get('/')
        assert response.status_code == 200

def test_analyze_health_data():
    # create a sample dataframe to test the function
    df = pd.DataFrame({
        'date': [datetime(2022, 1, 1), datetime(2022, 1, 2), datetime(2022, 1, 3)],
        'new_results_reported': [100, 200, 300],
        'total_results_reported': [1000, 1200, 1500],
        'overall_outcome': ['Positive', 'Negative', 'Positive'],
        'state': ['CA', 'CA', 'NY']
    })


    result = processor.analyze_health_data(df)

    # to do: check for other values as well. construct more test fixtures.
    assert result['total_pcr_cumulative'] == 1200
