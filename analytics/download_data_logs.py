import requests
import boto3 
from uuid import uuid4
import pandas as pd
import time

def create_query(client):
    

    query_id = str(uuid4())

    query_string = (
            "SELECT key, requestdatetime, remoteip, bytessent, useragent, objectsize FROM "
            "cellxgene_portal_dataset_download_logs_db.dataset_download_logs WHERE operation like "
            "'REST.GET.OBJECT';"
    )

    response = client.start_query_execution(
        QueryString=query_string,
        ClientRequestToken=query_id,
        QueryExecutionContext={"Database": "cellxgene_portal_dataset_download_logs_db", "Catalog": "AwsDataCatalog"},
        ResultConfiguration={
        "OutputLocation": "s3://corpora-data-prod-logs-queries",
        },
     )

    query_id = response.get("QueryExecutionId")

    
    return query_id


def run_query(query_id, client):
    results_have_not_been_calculated = True
    while results_have_not_been_calculated:
        try:
            response = client.get_query_execution(QueryExecutionId=query_id)
            status = response.get("QueryExecution").get("Status").get("State")
            if status == "SUCCEEDED":
                results_have_not_been_calculated = False
        except:
            print(f"Wasn't able to get query information for query ID {query_id} yet. Please be patient!")
            time.sleep(1)

def get_query_output(query_id, client, nextToken = None):
    if nextToken is not None:
        response = client.get_query_results(QueryExecutionId=query_id, NextToken=nextToken)
    else:
        response = client.get_query_results(QueryExecutionId=query_id)
    return response

def download_data(client):
    output = []

    query_id = create_query(client)
    print('Collected query id')
    
    run_query(query_id, client)
    print('Ran query')

    response = get_query_output(query_id, client)
    data = response.get("ResultSet").get("Rows")[1:]
    output = output + data
    
    while 'NextToken' in response.keys():
        response = get_query_output(query_id, client, response['NextToken'])
        data = response.get("ResultSet").get("Rows")
        output = output + data

    return output

def create_df(output):
    key = []
    requestdatetime = []
    remoteip = []
    bytessent = []
    useragent = []
    objectsize = []


    for row in output:
        key.append(row['Data'][0]['VarCharValue'])
        requestdatetime.append(row['Data'][1]['VarCharValue'])
        remoteip.append(row['Data'][2]['VarCharValue'])
        bytessent.append(row['Data'][3]['VarCharValue'])
        useragent.append(row['Data'][4]['VarCharValue'])
        if 'VarCharValue' in row['Data'][5].keys():
            objectsize.append(row['Data'][5]['VarCharValue'])
        else:
            objectsize.append(None)


    df = pd.DataFrame({'key': key, 'requestdatetime': requestdatetime, 'remoteip': remoteip, 'bytessent': bytessent, 'useragent': useragent, 'objectsize': objectsize})
    return df

def process_data(df):
    # extract filetype from key
    df['filetype'] = None
    df.loc[df['key'].str.contains('.h5ad'), 'filetype'] = 'h5ad'
    df.loc[df['key'].str.contains('.loom'), 'filetype'] = 'loom'
    df.loc[df['key'].str.contains('.rds'), 'filetype'] = 'rds'
    df.loc[df['key'].str.contains('.tar'), 'filetype'] = 'tar'
    df.loc[df['key'].str.contains('.ico'), 'filetype'] = 'ico'
    
    # extract download method 
    df['download_agent'] = None
    df.loc[df['useragent'].str.contains('curl'), 'download_agent'] = 'curl'
    df.loc[df['useragent'].str.contains('Mac OS'), 'download_agent'] = 'macOS'
    df.loc[df['useragent'].str.contains('Win64'), 'download_agent'] = 'Win64'
    df.loc[df['useragent'].str.contains('WOW64'), 'download_agent'] = 'WOW64'
    df.loc[(df['useragent'].str.contains('Windows NT')) & (~df['useragent'].str.contains('Win64')) & (~df['useragent'].str.contains('WOW64')), 'download_agent'] = 'Windows'
    df.loc[df['useragent'].str.contains('python-requests'), 'download_agent'] = 'requests-python'
    df.loc[df['useragent'].str.contains('Ubuntu'), 'download_agent'] = 'Ubuntu'
    df.loc[df['useragent'].str.contains('Boto'), 'download_agent'] = 'boto-python'
    df.loc[df['download_agent'].isnull(), 'download_agent'] = 'other'

    df = df.rename(columns={'requestdatetime':'download_datetime'})
    return df

if __name__ == "__main__":
    client = boto3.client("athena", region_name="us-west-2")

    output = download_data(client)
    print('Collected all results')

    df = create_df(output)
    print('Created dataframe')

    processed_df = process_data(df)
    print('Processed dataframe')

    processed_df.to_csv('download_data.csv', index = False)
    print('Saved output')

