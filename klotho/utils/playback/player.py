from .tonejs import ToneEngine, convert_to_events


class _SyncContext:
    def __init__(self):
        self.in_sync_mode = False
        self.pending_plays = []
    
    def __enter__(self):
        self.in_sync_mode = True
        self.pending_plays = []
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.pending_plays:
            all_events = []
            cumulative_offset = 0.0
            
            for item in self.pending_plays:
                if item[0] == 'pause':
                    cumulative_offset += item[1]
                else:
                    obj, kwargs = item
                    events = convert_to_events(obj, **kwargs)
                    for ev in events:
                        ev['start'] += cumulative_offset
                    all_events.extend(events)
                    if events:
                        max_end = max(e['start'] + e['duration'] for e in events)
                        cumulative_offset = max_end
            
            if all_events:
                engine = ToneEngine(all_events)
                engine.display()
        
        self.in_sync_mode = False
        self.pending_plays = []
    
    def add_play(self, obj, **kwargs):
        self.pending_plays.append((obj, kwargs))
    
    def add_pause(self, duration):
        self.pending_plays.append(('pause', duration))


_sync_context = _SyncContext()


def sync():
    return _sync_context


def pause(duration):
    if not _sync_context.in_sync_mode:
        raise RuntimeError("pause() can only be used within a sync() context manager")
    _sync_context.add_pause(duration)


def stop():
    pass


def play(obj, **kwargs):
    if _sync_context.in_sync_mode:
        _sync_context.add_play(obj, **kwargs)
    else:
        events = convert_to_events(obj, **kwargs)
        engine = ToneEngine(events)
        return engine.display()
