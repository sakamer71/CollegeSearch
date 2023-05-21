#!/usr/bin/env python3
import pandas as pd
from pprint import pprint
#from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import os

college_data_file = 'datafiles/Most-Recent-Cohorts-Institution.csv'
data_dict_file = 'datafiles/institution-data-dictionary.csv'
zipcode_file = 'datafiles/Gaz_zcta_national.txt'

os.system('clear')
zip_codes = pd.read_csv(zipcode_file, sep='\t')
zip_codes['GEOID'] = zip_codes['GEOID'].astype(str)

def zip_to_coord(zip_code):
    row = zip_codes[zip_codes['GEOID'] == zip_code]
    if not row.empty:
        return row.iloc[0]['INTPTLAT'], row.iloc[0]['INTPTLONG']
    else:
        return None
    
def zip_to_coord(zip_code):
    zip_code = int(zip_code)
    for i in range(-2, 3):
        temp_zip_code = zip_code + i
        row = zip_codes[zip_codes['GEOID'] == str(temp_zip_code)]
        if not row.empty:
            return row.iloc[0]['INTPTLAT'], row.iloc[0]['INTPTLONG']
    return None



def distance_between_zips(zip1, zip2):
    coord1 = zip_to_coord(zip1)

    coord2 = zip_to_coord(zip2)
    if coord1 is not None and coord2 is not None:
        return geodesic(coord1, coord2).miles
    else:
        return None

def is_within_radius(base_zip, zip_code, radius):
    distance = distance_between_zips(base_zip, zip_code)
    if distance is not None:
        return distance <= radius
    else:
        return False


pd.set_option('display.max_rows', None)
pd.set_option('display.max_colwidth', None)






def read_data_dict(data_dict_file):
    data_dict = pd.read_csv(data_dict_file)
    friendly_to_variable_map = dict(zip(data_dict['developer-friendly name'].dropna(), data_dict['VARIABLE NAME'].dropna()))

    label_to_value_map = {}
    last_seen_variable_name = None
    last_seen_friendly_name = None
    for _, row in data_dict.iterrows():
        variable_name = row['VARIABLE NAME']
        friendly_name = row['developer-friendly name']

        if pd.isna(variable_name) and last_seen_variable_name is not None:
            variable_name = last_seen_variable_name
        else:
            last_seen_variable_name = variable_name
        
        if pd.isna(friendly_name) and last_seen_friendly_name is not None:
            friendly_name = last_seen_friendly_name
        else:
            last_seen_friendly_name = friendly_name

        if pd.notna(row['LABEL']) and pd.notna(row['VALUE']):
            #if friendly_name not in label_to_value_map:
            #    label_to_value_map[friendly_name] = {}
            if variable_name not in label_to_value_map:
                label_to_value_map[variable_name] = {}
            try:
                # Attempt to convert the value to an integer
                value = int(row['VALUE'])
            except ValueError:
                # If it fails, use the original string value
                value = row['VALUE']
            #label_to_value_map[friendly_name][row['LABEL']] = row['VALUE']
            #label_to_value_map[friendly_name][row['LABEL']] = value
            label_to_value_map[variable_name][row['LABEL']] = value



    return friendly_to_variable_map, label_to_value_map



def read_college_data(college_data_file):
    college_data = pd.read_csv(college_data_file, low_memory=False, dtype={'ZIP': str})
    return college_data


def query_data(filter_dict):
    college_data = read_college_data(college_data_file)
    friendly_to_variable_map, label_to_value_map = read_data_dict(data_dict_file)

    query_str = ''
    for key in filter_dict:
        if key in friendly_to_variable_map:
            variable_name = friendly_to_variable_map[key]
            if isinstance(filter_dict[key], dict):
                op = filter_dict[key].get('op', '==')
                filter_value = filter_dict[key].get('value')
                if filter_value in label_to_value_map.get(variable_name, {}):
                    value = label_to_value_map[variable_name][filter_value]
                else:
                    value = filter_value
            else:
                op = '=='
                if filter_dict[key] in label_to_value_map.get(variable_name, {}):
                    value = label_to_value_map[variable_name][filter_dict[key]]
                else:
                    value = filter_dict[key]
            query_str += f'{variable_name} {op} {value} & '
        elif key == 'zip_radius':
            continue  # We will handle this separately
        else:
            print(f'Warning: "{key}" not found in friendly_to_variable_map')

    query_str = query_str.rstrip(' & ')

    #print("Query string:", query_str)

    if query_str:
        filtered_data = college_data.query(query_str)
    else:
        print('Error: Query string is empty')
        return pd.DataFrame()


    # Now apply the zip_radius filter, if it exists
    # Now apply the zip_radius filter, if it exists
    if 'zip_radius' in filter_dict:
        base_zip = filter_dict['zip_radius']['zip'][:5]
        radius = filter_dict['zip_radius']['radius']
        # Create a copy of filtered_data to avoid SettingWithCopyWarning
        filtered_data = filtered_data.copy()
        # Calculate the distance for each row and store it in a new column
        filtered_data['distance_int'] = filtered_data['ZIP'].str[:5].apply(lambda x: distance_between_zips(base_zip, x))
        # Then filter the rows based on the distance
        filtered_data = filtered_data[filtered_data['distance_int'] <= radius]
        # Round the distance values to the nearest whole number and keep as integer for sorting
        filtered_data['distance_int'] = filtered_data['distance_int'].round().astype(int)
        # Create a display version of the distance column
        filtered_data['distance_display'] = filtered_data['distance_int'].astype(str) + ' miles'
        # Sort by distance
        filtered_data = filtered_data.sort_values('distance_int')
        

    return filtered_data


# Example usage:
#filter_dict = {'ownership': 'Private nonprofit', 'degrees_awarded.predominant': 'Predominantly bachelor\'s-degree granting', 'state_fips': 'California'}
#filter_dict = {'ownership': 'Public', 'degrees_awarded.predominant': 'Predominantly bachelor\'s-degree granting', 'state_fips': 'New York'}
#filter_dict = {'ownership': 'Public', 'degrees_awarded.predominant': 'Predominantly bachelor\'s-degree granting', 'state_fips': 'New York', 'admission_rate.overall':.8101}
#filter_dict = {'ownership': 'Public', 'degrees_awarded.predominant': 'Predominantly bachelor\'s-degree granting', 'state_fips': 'Illinois', 'admission_rate.overall': {'op': '<=', 'value': .6101}, 'sat_scores.average.overall': {'op': '>=', 'value': 1000}}
#filter_dict = {'degrees_awarded.predominant': 'Predominantly bachelor\'s-degree granting', 'admission_rate.overall': {'op': '<=', 'value': .3101}, 'sat_scores.average.overall': {'op': '>=', 'value': 1400}}
filter_dict = {'ownership': 'Public', 'degrees_awarded.predominant': 'Predominantly bachelor\'s-degree granting', 'state_fips': 'New York', 'admission_rate.overall': {'op': '>=', 'value': .8101}, 'zip_radius': {'zip': '10001', 'radius': 300}}
filter_dict = {'degrees_awarded.predominant': 'Predominantly bachelor\'s-degree granting', 'admission_rate.overall': {'op': '>=', 'value': .6101}, 'zip_radius': {'zip': '60564', 'radius': 100}, 'sat_scores.average.overall': {'op': '>=', 'value': 1200}}

filtered_data = query_data(filter_dict)

print('filter:')
pprint(filter_dict)
print(filtered_data[['INSTNM','ADM_RATE','SAT_AVG','distance_int']])

