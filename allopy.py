from imports import *

# ------------------------------------------------------------------------------------
# TIME-BASED TOOLS
# ------------------------------------------------------------------------------------

def seconds_to_hmsms(seconds: float) -> str:
  '''
  Convert a duration from seconds to a formatted string in hours, minutes, seconds, and milliseconds.

  Args:
  seconds (float): The duration in seconds.

  Returns:
  str: A string representing the time in 'h:mm:ss:ms' format.
  '''
  h = int(seconds // 3600)
  seconds %= 3600
  m = int(seconds // 60)
  seconds %= 60
  s = int(seconds)
  ms = int((seconds - s) * 1000)
  return f'{h}:{m:02}:{s:02}:{ms:03}'

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

def beat_duration(ratio: str, bpm: float, beat_ratio: str = '1/4') -> float:
  '''
  Calculate the duration in seconds of a musical beat given a ratio and tempo.

  The beat duration is determined by the ratio of the beat to a reference beat duration (beat_ratio),
  multiplied by the tempo factor derived from the beats per minute (BPM).

  Args:
  ratio (str): The ratio of the desired beat duration to a whole note (e.g., '1/4' for a quarter note).
  bpm (float): The tempo in beats per minute.
  beat_ratio (str, optional): The reference beat duration ratio, defaults to a quarter note '1/4'.

  Returns:
  float: The beat duration in seconds.
  '''
  tempo_factor = 60 / bpm
  if isinstance(ratio, str):
    ratio_numerator, ratio_denominator = map(int, ratio.split('/'))
    ratio_value = ratio_numerator / ratio_denominator
  else:
    ratio_value = float(ratio)
  beat_numerator, beat_denominator = map(int, beat_ratio.split('/'))
  return tempo_factor * ratio_value * (beat_denominator / beat_numerator)

def metric_modulation(current_tempo: float, current_beat_value: float, new_beat_value: float) -> float:
  '''
  Determine the new tempo (in BPM) for a metric modulation from one metric value to another.

  Metric modulation is calculated by maintaining the duration of a beat constant while changing
  the note value that represents the beat, effectively changing the tempo.
  
  see:  https://en.wikipedia.org/wiki/Metric_modulation

  Args:
  current_tempo (float): The original tempo in beats per minute.
  current_beat_value (float): The note value (as a fraction of a whole note) representing one beat before modulation.
  new_beat_value (float): The note value (as a fraction of a whole note) representing one beat after modulation.

  Returns:
  float: The new tempo in beats per minute after the metric modulation.
  '''
  current_duration = 60 / current_tempo * current_beat_value
  new_tempo = 60 / current_duration * new_beat_value
  return new_tempo

class RT:
  '''
  A rhythm tree is a list representing a rhythmic structure. This list is organized hierarchically in sub lists, 
  just as time is organized in measures, time signatures, pulses and rhythmic elements in the traditional notation.

  Hence, the expression form of rhythm trees is crucially different from that of onsets and offsets. It can be 
  exacting and not very "ergonomic", from a musician's point of view : rhythm trees can be long, with a great number 
  of parenthesis and sub lists nested within each others.

  see: https://support.ircam.fr/docs/om/om6-manual/co/RT1.html
  '''
  def __init__(self, data):
    self.data = data

  @property
  def duration(self):
    return self.data[0]

  @property
  def time_signature(self):
    return self.data[1][0]

  @property
  def subdivisions(self):
    return self.data[1][1]

  def __getitem__(self, key):
    return self.data[key]

def measure_ratios(tree):
  '''
  Algorithm 1: MeasureRatios
  - **Data**: 'S' is the part of a RT
  - **Result**: Transforms the part '(s)' of a composed UT into fractional proportions.
    ```python
    div = for all 's' elements of 'S' do
      if 's' is a list of the form (DS) then
        return |D of s|;
      else
        return |s|;
      end if
    end for all
    begin
      for all 's' of 'S' do
        if 's' is a list then
          return (|D of s| / div) * MeasureRatios('S' of 's');
        else
          |s|/div;
        end if
      end for all
    end
  '''
  if not tree:
    return []

  if isinstance(tree, RT):
    tree = tree.subdivisions

  # divisor for the current tree level
  div = sum(abs(s[0]) if isinstance(s, tuple) else abs(s) for s in tree)

  result = []
  for s in tree:
    if isinstance(s, tuple):
      D, S = s
      ratio = Fraction(abs(D), div)
      result.extend([ratio * el for el in measure_ratios(S)])
    else:
      result.append(Fraction(s, div))
  return result


# ------------------------------------------------------------------------------------
# PITCH- AND FREQUENCY-BASED TOOLS
# ------------------------------------------------------------------------------------

def freq_to_midicents(frequency: float) -> float:
  '''
  Convert a frequency in Hertz to MIDI cents notation.

  Args:
  frequency: The frequency in Hertz to convert.

  Returns:
  The MIDI cent value as a float.
  '''
  return 100 * (12 * np.log2(frequency / 440.0) + 69)

def midicents_to_freq(midicents: float) -> float:
  '''
  Convert MIDI cents back to a frequency in Hertz.
  
  Args:
    midicents: The MIDI cent value to convert.
    
  Returns:
    The corresponding frequency in Hertz as a float.
  '''
  return 440.0 * (2 ** ((midicents - 6900) / 1200.0))

def ratio_to_cents(ratio: Union[str, float]) -> float:
  '''
  Convert a musical interval ratio to cents, a logarithmic unit of measure.
  
  Args:
    ratio: The musical interval ratio as a string (e.g., '3/2') or float.
    
  Returns:
    The interval in cents as a float.
  '''
  if isinstance(ratio, str):
    numerator, denominator = map(float, ratio.split('/'))
  else:  # assuming ratio is already a float
    numerator, denominator = ratio, 1.0
  return 1200 * np.log2(numerator / denominator)

def octave_reduce(interval: float, octave: int = 1) -> float:
  '''
  Reduce an interval to within the span of a specified octave.
  
  Args:
    interval: The musical interval to be octave-reduced.
    octave: The span of the octave for reduction, default is 1 octave.
    
  Returns:
    The octave-reduced interval as a float.
  '''
  while interval >= 2**octave:
    interval /= 2
  return interval

def hexany(prime_factors: List[int] = [1,3,5,7], r: int = 2) -> Tuple[List[float], List[float]]:
  '''
  Calculate a Hexany scale from a list of prime factors and a rank value.
  
  The Hexany is a six-note scale in just intonation derived from combinations
  of prime factors, as conceptualized by Erv Wilson.
  
  see:  https://en.wikipedia.org/wiki/Hexany
  
  Args:
    prime_factors: List of primes to generate the Hexany.
    r: Rank value indicating the number of primes to combine.
    
  Returns:
    A tuple containing two lists:
    - The first list contains the products of combinations of prime factors.
    - The second list is the sorted Hexany scale after octave reduction.
  '''
  products = [prod(comb) for comb in itertools.combinations(prime_factors, r)]
  scale = sorted([octave_reduce(product) for product in products])
  return products, scale
  
def n_et(interval=2, divisions=12, nth_division=1):
  '''
  Calculate the size of the nth division of an interval in equal temperament.
  
  see:  https://en.wikipedia.org/wiki/Equal_temperament

  :param interval: The interval to divide (default is 2 for an octave)
  :param divisions: The number of equal divisions
  :param nth_division: The nth division to calculate
  :return: The frequency ratio of the nth division
  '''
  return interval ** (nth_division / divisions)

def chord_mult(sonority1, sonority2):
  '''
  Given two sonorities as lists, return a list of lists where each pitch of
  the first sonority acts as the fundamental for the entire second sonority.

  :param sonority1: A list representing the first sonority
  :param sonority2: A list representing the second sonority
  :return: A list of sonorities, each based on pitches of the first sonority
  '''
  multiplied_chords = []
  for pitch in sonority1:
      # Transpose the second sonority by each pitch in the first sonority
      transposed_sonority = [pitch * x for x in sonority2]
      multiplied_chords.append(transposed_sonority)
  return multiplied_chords


# ------------------------------------------------------------------------------------
# SCORE TOOLS
# ------------------------------------------------------------------------------------

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

