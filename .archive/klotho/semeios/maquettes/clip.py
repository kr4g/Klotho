import uuid


class Clip:
    """
    A timeline clip representing a time-bounded event with a label.
    
    Used in maquettes (musical sketches) to represent sections, phrases,
    or other musical elements that occur within specific time bounds.
    """
    
    def __init__(self, start, end, label='Untitled', id=None, height=0.1, color='#4a9eff'):
        """
        Initialize a timeline clip.
        
        Parameters
        ----------
        start : float
            Start time of the clip
        end : float
            End time of the clip
        label : str, optional
            Human-readable label for the clip, by default 'Untitled'
        id : str, optional
            Unique identifier for the clip, by default None (auto-generated)
        height : float, optional
            Visual height of the clip, by default 0.1
        color : str, optional
            Default color of the clip, by default '#4a9eff'
        """
        self._id = id or str(uuid.uuid4())
        self._start = start
        self._end = end
        self._label = label
        self._height = height
        self._color = color
    
    @property
    def id(self):
        return self._id
    
    @property
    def start(self):
        return self._start
    
    @start.setter
    def start(self, value):
        self._start = value
    
    @property
    def end(self):
        return self._end
    
    @end.setter
    def end(self, value):
        self._end = value
    
    @property
    def label(self):
        return self._label
    
    @label.setter
    def label(self, value):
        self._label = value
    
    @property
    def height(self):
        return self._height
    
    @property
    def color(self):
        return self._color
    
    @property
    def center_x(self):
        return (self._start + self._end) / 2
    
    @property
    def width(self):
        return self._end - self._start

    def __repr__(self):
        return f"<Clip id={self.id[:6]} label={self.label} start={self.start} end={self.end}>" 