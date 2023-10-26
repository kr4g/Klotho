import os
import shutil
import pandas as pd
import numpy as np
import regex as re
from fractions import Fraction
import itertools
import matplotlib.pyplot as plt
from matplotlib import cm
import ipywidgets as widgets
from IPython.display import display, clear_output, HTML


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


def seconds_to_hmsms(seconds):
    '''seconds to h:m:s:ms format.'''
    h = int(seconds // 3600)
    seconds %= 3600
    m = int(seconds // 60)
    seconds %= 60
    s = int(seconds)
    ms = int((seconds - s) * 1000)
    return f'{h}:{m:02}:{s:02}:{ms:03}'


def get_duration(df):
  '''
  total duration of the score
  '''
  duration = 0.0
  for _, event in df.iterrows():
    d = float(event['start']) + float(event['dur'])
    if d > duration:
      duration = d
  return duration


def beat_duration(ratio, bpm, beat_ratio='1/4'):
  '''
  Calculate the duration of a beat (in seconds) based on the given ratio and tempo (BPM).
  '''
  tempo_factor = 60 / bpm
  if isinstance(ratio, str):
    ratio_numerator, ratio_denominator = map(int, ratio.split('/'))
    ratio_value = ratio_numerator / ratio_denominator
  else:
    ratio_value = float(ratio)
  beat_numerator, beat_denominator = map(int, beat_ratio.split('/'))
  return tempo_factor * ratio_value * (beat_denominator / beat_numerator)


def freq_to_midicents(frequency):
  return 100 * (12 * np.log2(frequency / 440.0) + 69)


def midicents_to_freq(midicents):
  return 440.0 * (2 ** ((midicents - 6900) / 1200.0))


def ratio_to_cents(ratio):
  if isinstance(ratio, str):
    numerator, denominator = map(float, ratio.split('/'))
  else:  # assuming ratio is already a float
    numerator, denominator = ratio, 1.0
  return 1200 * np.log2(numerator / denominator)

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
    end_time = start_time + float(row['dur']) + float(row['releaseTime'])
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

  plt.show()
