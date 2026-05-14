import pandas as pd
import os

def find_lab_files(directory):
    valid_extensions = ('.txt', '.tsv', '.asc', '.csv')
    return [os.path.join(directory, f) for f in os.listdir(directory) 
            if f.lower().endswith(valid_extensions)]

def load_data(file_path):
    start_line = -1
    with open(file_path, 'r', encoding='latin1') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if "Temperature" in line:
                start_line = i
    
    if start_line == -1:
        return None
    
    df = pd.read_csv(file_path, skiprows=start_line + 1, nrows=8, sep='\t', header=None, encoding='latin1')
    return df.apply(pd.to_numeric, errors='coerce').dropna(axis=1, how='all')