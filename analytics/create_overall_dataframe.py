import boto3 
import pandas as pd
import requests
import os
import scanpy as sp
import datetime

def get_collection_info(collection_id):
    collection_info_response = requests.get(f"https://api.cellxgene.cziscience.com/dp/v1/collections/{collection_id}")
    collection_info = collection_info_response.json()
    return collection_info

def get_data():
    response = requests.get("https://api.cellxgene.cziscience.com/dp/v1/collections")
    collections = response.json()["collections"]

    data = [get_collection_info(c["id"]) for c in collections]

    return data 

def name_to_collection_id(data):
    collection_ids = [r['id'] for r in data]
    collection_names = [r['name'] for r in data]
    cId = pd.DataFrame({'collection_id': collection_ids, 'collection_name': collection_names})
    return cId

def collection_id_to_dataset_id(data):
    dataset_ids = [d['id'] for r in data for d in r['datasets']]
    dataset_names = [d['name'] for r in data for d in r['datasets']]
    collection_ids = [d['collection_id'] for r in data for d in r['datasets']]
    cId_to_dId = pd.DataFrame({'dataset_id': dataset_ids, 'dataset_name': dataset_names, 'collection_id': collection_ids})
    return cId_to_dId

def create_translation(data):
    cId = name_to_collection_id(data)
    cId_to_dId = collection_id_to_dataset_id(data)
    
    translation = cId.merge(cId_to_dId, how = 'inner', on = 'collection_id')
    return translation

def dataset_id_to_key(data):
    dataset_ids = [a['dataset_id'] for r in data for d in r['datasets'] for a in d['dataset_assets']]
    s3_uri = [a['s3_uri'] for r in data for d in r['datasets'] for a in d['dataset_assets']]
    updated_at = [a['updated_at'] for r in data for d in r['datasets'] for a in d['dataset_assets']]
    dId_to_key = pd.DataFrame({'dataset_id': dataset_ids, 'key': s3_uri, 'updated_at': updated_at})

    dId_to_key = dId_to_key[dId_to_key['key'].str.contains('.h5ad')].reset_index(drop = True)
    dId_to_key['updated_at'] = pd.to_datetime(dId_to_key['updated_at'], unit='s')
    dId_to_key['key'] = dId_to_key['key'].str.replace('s3://corpora-data-prod/', '')
    
    return dId_to_key

def download_file_from_s3(s3_path):
    try:
        s3 = boto3.client("s3", region_name="us-west-2")
        s3.download_file('corpora-data-prod', s3_path, 'dataset.h5ad')
        print("Successful download of file {}".format(s3_path))
        return True
    except FileNotFoundError:
        print("The location to save this file does not exist: {}".format(local_path))
        return False
    except Exception as e:
        print(e)
        return False

def process_file(id):
    file = sp.read_h5ad('dataset.h5ad')
    print('Read in file')

    output = file.obs
    output['dataset_id'] = id
    output['cells'] = 1
    if 'cell_type' in list(output.columns):
        output = output[['dataset_id', 'sex', 'development_stage', 'tissue', 'assay', 'disease', 'cell_type', 'ethnicity', 'cells']]
        output = output.groupby(['dataset_id', 'sex', 'development_stage', 'tissue', 'assay', 'disease', 'cell_type', 'ethnicity']).sum().reset_index()
    elif 'cell_type_original' in list(output.columns):
        output = output[['dataset_id', 'sex', 'development_stage', 'tissue', 'assay', 'disease', 'cell_type', 'ethnicity', 'cells']]
        output = output.groupby(['dataset_id', 'sex', 'development_stage', 'tissue', 'assay', 'disease', 'cell_type', 'ethnicity']).sum().reset_index()
    output = output[output['cells'] > 0].reset_index(drop = True)
    return output

if __name__ == "__main__":
    # determine datasets currently on the cellxgene platform
    data = get_data()
    print('downloaded API data')

    # match s3 file path to dataset id 
    input_df = dataset_id_to_key(data)
    print('created input table')

    # create translation table of collection/dataset names
    translation = create_translation(data)
    print('created translation table')

    # keep track of the number of files being read in
    count = 0 
    
    # loop through the datasets
    for i in range(len(input_df)):
        file = input_df['key'].iloc[i]
        dataset_id = input_df['dataset_id'].iloc[i]
        updated_dt = input_df['updated_at'].iloc[i]

        # check if the dataframe has been started
        if os.path.isfile('cellxgene_df.csv'):
            print('dataframe already started')
            df = pd.read_csv('cellxgene_df.csv')
            datasets = df['dataset_id'].unique().tolist()
            modified_dt = os.path.getmtime('cellxgene_df.csv')
            modified_dt = datetime.datetime.fromtimestamp(modified_dt)

            # check if the dataset is already included or was modified after the date of the dataframe
            if (dataset_id not in datasets) | (updated_dt > modified_dt):
                download_file_from_s3(file)
        
                output = process_file(dataset_id)
                print('processed file')

                if 'collection_id' in df.columns.tolist():
                    output = translation.merge(output, how = 'right', on = 'dataset_id')

                # if dataset has not been added
                if dataset_id not in datasets:
                    combined = df.append(output).reset_index(drop = True)
                    print('Added new dataset {}'.format(dataset_id))
                # if dataset was modified
                elif updated_dt > modified_dt:
                    temp = df[df['dataset_id'] != dataset_id]
                    combined = temp.append(output).reset_index(drop = True)
                    print('Updated {} dataset'.format(dataset_id))
                combined.to_csv('cellxgene_df.csv', index = False)

                os.remove('dataset.h5ad')
                count += 1 
                print('saved dataframe to file')
            else:
                print('{} is already included in the dataframe'.format(dataset_id))
        else:
            download_file_from_s3(file)
        
            output = process_file(dataset_id)
            print('processed file')

            output.to_csv('cellxgene_df.csv', index = False)

            os.remove('dataset.h5ad')
            count += 1 
            print('saved dataframe to file')
        print('Files: {}'.format(count))

    # limit to only datasets still on the platform
    datasets_df = input_df[['dataset_id']]
    combined = datasets_df.merge(combined, how = 'inner', on = 'dataset_id')
    
    if 'collection_id' not in combined.columns.tolist():
        combined = translation.merge(combined, how = 'inner', on = 'dataset_id')
        combined.to_csv('cellxgene_df.csv', index = False)
        print('saved cellxgene overall dataframe')
    else:
        print('updated cellxgene overall dataframe')
        

          
        
    






