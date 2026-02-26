try:
    from .midi_player import play_midi
except ImportError:
    pass

try:
    from .player import play
except ImportError:
    pass
