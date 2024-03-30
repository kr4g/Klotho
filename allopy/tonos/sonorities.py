def chord_mult(sonority1, sonority2):
  '''
  Given two sonorities as lists, return a list of lists where each pitch of
  the first sonority acts as the fundamental for the entire second sonority.
  
  see: https://en.wikipedia.org/wiki/Multiplication_(music)#Pitch_multiplication

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
