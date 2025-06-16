# ------------------------------------------------------------------------------------
# Klotho/klotho/skora/skora.py
# ------------------------------------------------------------------------------------
'''
--------------------------------------------------------------------------------------
Notation and visualization tools.
--------------------------------------------------------------------------------------
'''
from klotho.thetos.parameters.instruments import PFIELDS
from klotho.utils.data_structures.dictionaries import SafeDict

import numpy as np
import pandas as pd
import regex as re
import json
import matplotlib.pyplot as plt
from matplotlib import cm

import os
from pathlib import Path

def set_score_path(synth_dir: str = 'tutorials/audiovisual', synth_name: str = 'Integrated'):
    current_path = Path(os.getcwd())
    if current_path.name != 'AlloPy':
        raise EnvironmentError("This script must be run from within the 'AlloPy/' directory.")

    while current_path.name != 'allolib_playground' and current_path.parent != current_path:
        current_path = current_path.parent

    if current_path.name != 'allolib_playground':
        raise FileNotFoundError("allolib_playground directory not found in the path hierarchy.")
    score_path = os.path.join(current_path, synth_dir, 'bin', f'{synth_name}-data')
    # return current_path / f'{synth_dir}/bin/{synth_name}-data'
    return score_path

def extract_pfields(filepath):
    with open(filepath, 'r') as file:
        cpp_contents = file.read()

    instruments = {}

    class_start_pattern = re.compile(r'class (\w+) :')
    param_pattern = re.compile(r'createInternalTriggerParameter\(\s*"(\w+)"\s*,\s*([\d.+-]+)')

    class_starts = [m.start() for m in class_start_pattern.finditer(cpp_contents)]
    class_starts.append(len(cpp_contents))

    for i in range(len(class_starts)-1):
        class_block = cpp_contents[class_starts[i]:class_starts[i+1]]
        class_name_match = class_start_pattern.search(class_block)
        if class_name_match:
            class_name = class_name_match.group(1)
            init_start_match = re.search(r'(virtual\s+)?void\s+init\(\)', class_block)
            if init_start_match:
                init_start = init_start_match.start()
                init_end = class_block.find('}', init_start)
                init_block = class_block[init_start:init_end]
                params = {"start": 0, "dur": 1, "synthName": class_name}  # standard pfields
                for param_match in param_pattern.finditer(init_block):
                    param_name, default_value_str = param_match.groups()
                    if param_name != "synthName":
                        default_value = float(default_value_str) if '.' in default_value_str else int(default_value_str)
                    else:
                        default_value = default_value_str
                    params[param_name] = default_value
                instruments[class_name] = params

    instruments_json = json.dumps(instruments, indent=4)
    target_directory = Path('./utils/instruments')
    target_directory.mkdir(parents=True, exist_ok=True)
    output_file_path = target_directory / (Path(filepath).stem + '.json')

    with open(output_file_path, 'w') as json_file:
        json_file.write(instruments_json)
        print(f'New JSON file created at: {output_file_path}')

def get_pfields(instrument_name, instruments_dir='utils/instruments', instrument_file='_instrument_classes.json'):
    # instruments_dir = './utils/instruments'
    base_name = os.path.splitext(os.path.basename(instrument_file))[0] + '.json'
    json_path = os.path.join(instruments_dir, base_name)

    # if not os.path.exists(json_path):
    #     extract_pfields(instrument_file)
    # extract_pfields(instrument_file)

    with open(json_path, 'r') as file:
        instruments_data = json.load(file)

    instrument_pfields = instruments_data.get(instrument_name, {})
    return SafeDict(instrument_pfields)

def make_score_df(pfields=('start', 'dur', 'synthName', 'amplitude', 'frequency')):
  '''
  Creates a DataFrame with the given pfields as columns.
  '''
  return pd.DataFrame(columns=pfields)

def synthSeq_to_df(filepath):
  '''
  Parses a .synthSequence file and returns the score as a Pandas DataFrame
  '''
  with open(filepath, 'r') as f:
      lines = f.readlines()

  params = []
  param_collect = False

  data = []
  # synths = set()
  for line in lines:
      if line.startswith('@'):
          line = line[2:]  # Remove '@ '
          components = line.split()
          data.append(components)
          # synths.add(components[2])
      elif line.startswith('#'):
        # synth parameters
        pattern = re.compile(r'^#\s+([a-zA-Z0-9\s]+(?:\s+[a-zA-Z0-9\s]+)*)\s*$') # pattern: `# {synthName}`
        match = pattern.match(line)
        if match:
          synth_name = components[2]
          params.extend(match.group(1).split()[1:])

  if not params:  # Default parameter names
      params = [f'synth_param_{str(i).zfill(2)}' for i in range(100)]

  df = pd.DataFrame(data)
  df.columns = ['start', 'dur', 'synthName'] + params[:df.shape[1]-3]

  return df

def df_to_synthSeq(df, filepath):
  '''
  Converts a DataFrame to a .synthSequence file
  '''
  with open(filepath, 'w') as f:
    for index, row in df.iterrows():
      f.write('@ ' + ' '.join(map(str, row.values)) + '\n')

def notelist_to_synthSeq(notelist, filepath):
  '''
  Converts a list of dictionaries to a .synthSequence file
  '''
  with open(filepath, 'w') as f:
    for row in notelist:
      f.write('@ ' + ' '.join(map(str, row.values())) + '\n')

def make_notelist(pfields: dict = {}, loop_param: str = 'max'):
  
  # if `pfields` is empty or incomplete, use default values
  if not pfields:
    pfields = getattr(PFIELDS, 'SineEnv', None).value.copy()
  elif 'synthName' not in pfields.keys():
    pfields['synthName'] = ['SineEnv']
  
  if loop_param == 'max':
    seq_len = max(len(value) if isinstance(value, list) else 1 for value in pfields.values())
  elif loop_param == 'min':
    seq_len = min(len(value) if isinstance(value, list) else 1 for value in pfields.values())
  elif loop_param in pfields.keys():
    seq_len = len(pfields[loop_param]) if isinstance(pfields[loop_param], list) else 1
  else:
    seq_len = 8

  pfields['start'] = 0.167 if 'start' not in pfields.keys() else pfields['start']
  pfields['dur']   = [1.0] if 'dur' not in pfields.keys() else pfields['dur'] if isinstance(pfields['dur'], list) else [pfields['dur']]
  pfields['dc']    = [1.0] if 'dc' not in pfields.keys() else pfields['dc'] if isinstance(pfields['dc'], list) else [pfields['dc']]

  note_list = []
  if not isinstance(pfields['synthName'], list):
    pfields['synthName'] = [pfields['synthName']]
  for i_syn, synthName in enumerate(pfields['synthName']):
    start = pfields['start'][0] if isinstance(pfields['start'], list) else pfields['start']
    for i in range(seq_len):
      new_row = getattr(PFIELDS, synthName, None).value.copy()
      new_row['start'] = start
      for key in pfields.keys():
        pfield = pfields[key] if isinstance(pfields[key], list) else [pfields[key]]
        plen = len(pfield)
        pidx = i % len(pfields[key]) if isinstance(pfields[key], list) else 0

        if key in ['start', 'synthName']:  # ignore these keys
          continue

        if key not in new_row.keys():  # check for name variations
          if key == 'amplitude':
            new_row['amp'] = pfields[key][pidx]
          if key == 'amp':
            new_row['amplitude'] = pfields[key][pidx]          
          if key == 'frequency':
            new_row['freq'] = pfields[key][pidx]
          if key == 'freq':
            new_row['frequency'] = pfields[key][pidx]
          continue
        
        # Get the pfield value
        if key == 'dur':
          new_row[key] = pfield[i % plen] * pfields['dc'][i % len(pfields['dc'])]  # apply duty cycle to duration
        else:
          new_row[key] = pfield[i % plen]  # set pfield value
      
      if new_row['dur'] > 0:                                       # negative durations mean rest (skip)
        note_list.append(new_row)                                  # append new row to the notelist
      if isinstance(pfields['start'], list):                       # if start is a list,
        start = pfields['start'][(i + 1) % len(pfields['start'])]  # get the next start time
      else:                                                        # otherwise,
        start += abs(pfields['dur'][i % len(pfields['dur'])])      # increment start time by the current duration

  return note_list

def play(pfields: dict = {}, loop_param: str = 'max', filename: str = 'play.synthSequence', inst: str = 'Integrated'):
  notelist = make_notelist(pfields=pfields, loop_param=loop_param)
  filepath = set_score_path(inst)
  notelist_to_synthSeq(notelist, os.path.join(filepath, filename))
  print(f'created "{filename}" in {filepath}...\n')

def make_row(rows_list: list, new_row: dict):
  '''
  
  '''
  rows_list.append(new_row)

def concat_rows(df, rows_list):
  '''
  Concatenate a list of rows to a DataFrame.
  
  Args:
  df (pd.DataFrame): The DataFrame to which to append the rows.
  rows_list (list): A list of rows to append to the DataFrame.
  
  Returns:
  pd.DataFrame: A new DataFrame with the rows appended.
  '''
  return pd.concat(
    [                 
      pd.DataFrame([row], 
                   columns=df.columns) for row in rows_list
    ],
    ignore_index=True)

def merge_parts_dfs(parts_list: list) -> pd.DataFrame:
  '''
  Merge a list of DataFrames into a single DataFrame.
  
  Args:
  parts_list (list): A list of DataFrames to merge.
  
  Returns:
  pd.DataFrame: A single DataFrame containing all the rows from the input DataFrames.
  '''
  return pd.concat(parts_list, ignore_index=True)

def get_score_duration(df: pd.DataFrame) -> float:
  '''
  Calculate the total duration of a `.synthSequence` file represented as a DataFrame.

  The duration is computed by finding the latest time point at which an event ends,
  which is the sum of its start time and duration.

  Args:
  df (pd.DataFrame): A DataFrame with at least 'start' and 'dur' columns representing the start time and duration of events.

  Returns:
  float: The total duration of the sequence.
  '''
  duration = 0.0
  for _, event in df.iterrows():
    d = float(event['start']) + float(event['dur'])
    if d > duration:
      duration = d
  return duration

def analyze_score(df):
  '''
  for each parameter in the dataframe.
  '''
  if not isinstance(df, pd.DataFrame):
    raise ValueError("Input must be a Pandas DataFrame.")

  # remove 'synthName' column
  param_cols = df.columns[:2].append(df.columns[3:])

  stats = {
      'min': [],
      'max': [],
      'mean': [],
      # etc...
      # continue to add more
  }

  for col in param_cols:
    stats['min'].append(df[col].astype(float).min())
    stats['max'].append(df[col].astype(float).max())
    stats['mean'].append(df[col].astype(float).mean())

  stats_df = pd.DataFrame(stats, index=param_cols)

  return stats_df

def plot_dataframe(df, column_name):
  fig, ax = plt.subplots(figsize=(16, 8))
  ax.set_facecolor('black')
  fig.patch.set_facecolor('black')

  df[column_name] = df[column_name].astype(float)
  # norm = plt.Normalize(vmin=np.log2(df[column_name].min()), vmax=np.log2(df[column_name].max()))
  # colors = cm.jet(norm(np.log2(df[column_name].values)))
  normed_freqs = np.log2(df[column_name].values) % 1
  colors = cm.jet(normed_freqs)

  for i, (idx, row) in enumerate(df.iterrows()):
    start_time = float(row['start'])
    end_time = start_time + float(row['dur'])# + float(row['releaseTime'])
    freq_val = row[column_name]

    ax.plot([start_time, end_time], [freq_val, freq_val], c=colors[i], linewidth=2)

  ax.set_yscale('log')
  min_freq = int(df[column_name].min())
  max_freq = int(df[column_name].max())

  ax.set_yticks([2**x for x in range(int(np.log2(min_freq)), int(np.log2(max_freq))+1)])
  ax.get_yaxis().set_major_formatter(plt.ScalarFormatter())

  ax.set_title(f'Plot of {column_name} over time (seconds)', color='white')
  ax.set_xlabel('time (seconds)', color='white')
  ax.set_ylabel(column_name + ' (Hz)', color='white')
  ax.tick_params(colors='white')
  ax.grid(True, which="both", ls="--", c='gray')
