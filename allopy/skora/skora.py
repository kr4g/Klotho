# ------------------------------------------------------------------------------------
# SCORE TOOLS
# ------------------------------------------------------------------------------------
'''
--------------------------------------------------------------------------------------
HELP
--------------------------------------------------------------------------------------
'''

import numpy as np
import pandas as pd
import regex as re
import matplotlib.pyplot as plt
from matplotlib import cm

import os
from pathlib import Path

def set_score_path(synth_name: str = 'Integrated'):
    current_path = Path(os.getcwd())
    if current_path.name != 'AlloPy':
        raise EnvironmentError("This script must be run from within the 'AlloPy/' directory.")

    while current_path.name != 'allolib_playground' and current_path.parent != current_path:
        current_path = current_path.parent

    if current_path.name != 'allolib_playground':
        raise FileNotFoundError("allolib_playground directory not found in the path hierarchy.")

    return current_path / f'tutorials/audiovisual/bin/{synth_name}-data'
  
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
