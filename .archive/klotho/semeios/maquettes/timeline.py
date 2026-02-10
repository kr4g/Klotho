import panel as pn
import bokeh.plotting as bp
from bokeh.models import ColumnDataSource, Range1d, Segment
import threading
from pythonosc import dispatcher, osc_server

try:
    from bokeh.models import CustomJSTickFormatter
    HAS_CUSTOM_FORMATTER = True
except ImportError:
    HAS_CUSTOM_FORMATTER = False

from .clip import Clip


class Timeline:
    """
    An interactive timeline visualization for musical maquettes.
    
    Provides a web-based GUI for visualizing and editing timeline clips,
    with support for OSC communication for real-time highlighting during playback.
    """
    
    def __init__(self, num_tracks=4, time_range=(0, 20)):
        """Initialize the timeline with an empty set of events."""
        self._events = {}
        self._selected_ids = set()
        self._highlighted_by_track = {}  # track_id -> clip_id
        self._osc_server = None
        self._osc_thread = None
        self._osc_port = None
        self._num_tracks = num_tracks
        self._time_range = time_range
        
        pn.extension('bokeh')

        self._source = ColumnDataSource(data=dict(
            id=[], x=[], y=[], width=[], height=[], label=[], color=[], track=[]
        ))

        self._clip_boundaries = ColumnDataSource(data=dict(
            x0=[], y0=[], x1=[], y1=[]
        ))

        track_spacing = 1.0 / num_tracks
        track_height = track_spacing * 0.6
        y_max = 1.0
        
        self._fig = bp.figure(
            height=max(300, 80 * num_tracks),
            x_range=Range1d(time_range[0] - 2, time_range[1], bounds=None),
            y_range=Range1d(0, y_max),
            tools="xpan,xwheel_zoom,reset,tap,box_select",
            active_scroll="xwheel_zoom",
            active_drag="xpan",
            toolbar_location="above",
            sizing_mode="stretch_width",
            background_fill_color="#2c2c2c",
            border_fill_color="#2c2c2c"
        )
        
        self._fig.grid.visible = False
        self._fig.yaxis.visible = False
        
        self._fig.xaxis.axis_line_color = "#666666"
        self._fig.xaxis.major_tick_line_color = "#666666"
        self._fig.xaxis.minor_tick_line_color = "#444444"
        self._fig.xaxis.major_label_text_color = "#cccccc"
        self._fig.xaxis.ticker.desired_num_ticks = max(20, int((time_range[1] - time_range[0]) * 2))
        
        # Hide negative tick labels and format numbers cleanly
        if HAS_CUSTOM_FORMATTER:
            self._fig.xaxis.formatter = CustomJSTickFormatter(code="""
                if (tick < 0) {
                    return "";
                }
                // Format numbers cleanly
                if (Math.abs(tick - Math.round(tick)) < 1e-10) {
                    // It's essentially an integer
                    return Math.round(tick).toString();
                } else {
                    return parseFloat(tick.toFixed(4)).toString();
                }
            """)

        x_indicator = time_range[0] - 0.5
        
        for track in range(num_tracks):
            track_center = (track + 0.5) * track_spacing
            track_bottom = track * track_spacing + 0.1 * track_spacing
            track_top = (track + 1) * track_spacing - 0.1 * track_spacing
            
            self._fig.line([x_indicator, time_range[1] + 100], [track_center, track_center], 
                          line_color="#555555", line_width=1)
            
            self._fig.line([x_indicator, x_indicator], [track_bottom, track_top], 
                          line_color="#888888", line_width=6)
            
            self._fig.text([x_indicator - 0.3], [track_center], [str(track)], 
                          text_color="#cccccc", text_font_size="12pt", text_align="center", text_baseline="middle")
        
        self._track_spacing = track_spacing

        self._rects = self._fig.rect(
            x='x', y='y', width='width', height='height',
            fill_color='color', line_color=None,
            source=self._source
        )

        self._boundaries = self._fig.segment(
            x0='x0', y0='y0', x1='x1', y1='y1',
            line_color="#aaaaaa", line_width=2,
            source=self._clip_boundaries
        )

        self._source.selected.on_change("indices", self._on_select)

        self._label_editor = pn.widgets.TextInput(
            name="Label", placeholder="Edit label...", visible=False,
            styles={'background': '#3c3c3c', 'color': '#cccccc'}
        )
        self._label_editor.param.watch(self._on_label_edit, 'value')

        self._bokeh_pane = pn.pane.Bokeh(self._fig, sizing_mode="stretch_width")
        self._panel = pn.Column(
            self._bokeh_pane, self._label_editor,
            styles={'background': '#2c2c2c'}
        )
    
    @property
    def events(self):
        """Dict of clips in the timeline."""
        return self._events.copy()
    
    @property
    def selected_clips(self):
        """Set of currently selected clip IDs."""
        return self._selected_ids.copy()
    
    @property
    def osc_port(self):
        """Current OSC server port, or None if not running."""
        return self._osc_port
    
    @property
    def num_tracks(self):
        """Number of tracks in the timeline."""
        return self._num_tracks
    
    @property
    def highlighted_clips(self):
        """Dict of currently highlighted clips by track {track_id: clip_id}."""
        return self._highlighted_by_track.copy()
    
    @property
    def highlighted_clip_ids(self):
        """Set of currently highlighted clip IDs."""
        return set(self._highlighted_by_track.values())
    
    def _highlight_event_from_osc(self, event_id):
        """Thread-safe method to trigger highlight from OSC using Bokeh document."""
        try:
            doc = self._fig.document
            if doc is not None:
                def safe_highlight():
                    try:
                        self._do_highlight(event_id)
                    except Exception as e:
                        print(f"Error in document callback: {e}")
                
                doc.add_next_tick_callback(safe_highlight)
                print(f"Added highlight callback to document: {event_id}")
            else:
                print(f"No document available for OSC highlight: {event_id}")
        except Exception as e:
            print(f"Error setting up OSC highlight: {e}")

    def add_to_timeline(self, clip: Clip, track=0):
        """
        Add a clip to the timeline.
        
        Parameters
        ----------
        clip : Clip
            The clip to add to the timeline
        track : int, optional
            Track number (0-based), by default 0
        """
        if track >= self._num_tracks:
            raise ValueError(f"Track {track} exceeds available tracks (0-{self._num_tracks-1})")
        
        event_id = clip.id
        self._events[event_id] = clip
        
        track_center = (track + 0.5) * self._track_spacing
        track_bottom = track * self._track_spacing + 0.1 * self._track_spacing
        track_top = (track + 1) * self._track_spacing - 0.1 * self._track_spacing
        
        self._source.stream(dict(
            id=[event_id],
            x=[clip.center_x],
            y=[track_center],
            width=[clip.width],
            height=[clip.height],
            label=[clip.label],
            color=[clip.color],
            track=[track]
        ))
        
        self._clip_boundaries.stream(dict(
            x0=[clip.start, clip.end],
            y0=[track_bottom, track_bottom],
            x1=[clip.start, clip.end],
            y1=[track_top, track_top]
        ))

    def _highlight_event(self, event_id):
        """Direct highlight method - use only from main thread."""
        self._do_highlight(event_id)
    
    def _get_clip_track(self, event_id):
        """Get the track number for a given clip."""
        if event_id not in self._events:
            return None
        
        # Find track from source data
        ids = list(self._source.data['id'])
        tracks = list(self._source.data['track'])
        try:
            idx = ids.index(event_id)
            return tracks[idx]
        except ValueError:
            return None
    
    def _do_highlight(self, event_id):
        """Internal highlight method that toggles highlighting for an event."""
        if event_id not in self._events:
            print(f"Event ID '{event_id}' not found in timeline")
            return
        
        track = self._get_clip_track(event_id)
        if track is None:
            return
        
        # Check if this clip is already highlighted on its track
        if track in self._highlighted_by_track and self._highlighted_by_track[track] == event_id:
            # Unhighlight this clip
            del self._highlighted_by_track[track]
            print(f"UNHIGHLIGHTED: {event_id} (track {track})")
        else:
            # Highlight this clip (removing any previous highlight on this track)
            if track in self._highlighted_by_track:
                old_clip = self._highlighted_by_track[track]
                print(f"UNHIGHLIGHTED: {old_clip} (track {track})")
            self._highlighted_by_track[track] = event_id
            print(f"HIGHLIGHTED: {event_id} (track {track})")
        
        self._update_colors()
    
    def _highlight_clip(self, event_id):
        """Highlight a specific clip (does not toggle)."""
        if event_id not in self._events:
            print(f"Event ID '{event_id}' not found in timeline")
            return
        
        track = self._get_clip_track(event_id)
        if track is None:
            return
        
        # Remove any existing highlight on this track
        if track in self._highlighted_by_track:
            old_clip = self._highlighted_by_track[track]
            if old_clip != event_id:
                print(f"UNHIGHLIGHTED: {old_clip} (track {track})")
        
        self._highlighted_by_track[track] = event_id
        self._update_colors()
        print(f"HIGHLIGHTED: {event_id} (track {track})")
    
    def _unhighlight_clip(self, event_id):
        """Unhighlight a specific clip."""
        track = self._get_clip_track(event_id)
        if track is not None and track in self._highlighted_by_track and self._highlighted_by_track[track] == event_id:
            del self._highlighted_by_track[track]
            self._update_colors()
            print(f"UNHIGHLIGHTED: {event_id} (track {track})")
    
    def _clear_highlights(self):
        """Clear all highlights."""
        if self._highlighted_by_track:
            self._highlighted_by_track.clear()
            self._update_colors()
            print("CLEARED ALL HIGHLIGHTS")
    
    def _update_colors(self):
        """Update all clip colors based on selection and highlight state."""
        ids = list(self._source.data['id'])
        highlighted_clip_ids = set(self._highlighted_by_track.values())
        new_colors = []
        for eid in ids:
            if eid in self._selected_ids:
                new_colors.append("#6666ff")  # Selected color (blue)
            elif eid in highlighted_clip_ids:
                new_colors.append("#ff4444")  # Highlighted color (red)
            else:
                new_colors.append(self._events[eid].color)  # Default color
        
        self._source.data = dict(self._source.data, color=new_colors)

    def _on_select(self, attr, old, new):
        """Handle selection events in the timeline."""
        self._selected_ids = {self._source.data['id'][i] for i in new}
        self._update_colors()

        if len(new) == 1:
            idx = new[0]
            self._label_editor.visible = True
            self._label_editor.value = self._source.data['label'][idx]
            self._label_editor.name = f"Edit label for {self._source.data['id'][idx][:6]}"
        else:
            self._label_editor.visible = False

    def _on_label_edit(self, event):
        """Handle label editing events."""
        if len(self._source.selected.indices) == 1:
            idx = self._source.selected.indices[0]
            new_label = event.new
            event_id = self._source.data['id'][idx]
            new_labels = list(self._source.data['label'])
            new_labels[idx] = new_label
            self._source.data = dict(self._source.data, label=new_labels)
            self._events[event_id].label = new_label
            print(f"Updated: {self._events[event_id]}")

    def _setup_osc_server(self, ip="127.0.0.1", port=9000, force=True):
        """Setup OSC server for external communication."""
        if self._osc_server is not None:
            if self._osc_port == port:
                print(f"OSC server already running on {ip}:{port}")
                return self._osc_server, self._osc_thread
            else:
                print(f"Stopping existing OSC server on port {self._osc_port} to start on {port}")
                self._stop_osc_server()
            
        def osc_highlight_toggle_handler(addr, args, event_id):
            try:
                self._highlight_event_from_osc(event_id)
                print(f"OSC toggle highlight: {event_id}")
            except Exception as e:
                print(f"Error in OSC highlight toggle: {e}")

        def osc_highlight_on_handler(addr, args, event_id):
            try:
                doc = self._fig.document
                if doc is not None:
                    doc.add_next_tick_callback(lambda: self._highlight_clip(event_id))
                print(f"OSC highlight on: {event_id}")
            except Exception as e:
                print(f"Error in OSC highlight on: {e}")

        def osc_highlight_off_handler(addr, args, event_id):
            try:
                doc = self._fig.document
                if doc is not None:
                    doc.add_next_tick_callback(lambda: self._unhighlight_clip(event_id))
                print(f"OSC highlight off: {event_id}")
            except Exception as e:
                print(f"Error in OSC highlight off: {e}")

        def osc_clear_highlights_handler(addr, args):
            try:
                doc = self._fig.document
                if doc is not None:
                    doc.add_next_tick_callback(lambda: self._clear_highlights())
                print("OSC clear all highlights")
            except Exception as e:
                print(f"Error in OSC clear highlights: {e}")

        disp = dispatcher.Dispatcher()
        disp.map("/highlight", osc_highlight_toggle_handler, "event")
        disp.map("/highlight_on", osc_highlight_on_handler, "event")
        disp.map("/highlight_off", osc_highlight_off_handler, "event")
        disp.map("/clear_highlights", osc_clear_highlights_handler)

        try:
            self._osc_server = osc_server.ThreadingOSCUDPServer((ip, port), disp)
            self._osc_thread = threading.Thread(target=self._osc_server.serve_forever, daemon=True)
            self._osc_thread.start()
            self._osc_port = port
            print(f"OSC server started successfully on {ip}:{port}")
            return self._osc_server, self._osc_thread
        except OSError as e:
            if e.errno == 48:  # Address already in use
                if force:
                    print(f"Port {port} is in use. You may need to:")
                    print(f"1. Kill any existing process using port {port}")
                    print(f"2. Or call timeline.restart_osc_server() to force restart")
                    print("On macOS/Linux, try: lsof -ti:9000 | xargs kill -9")
                else:
                    print(f"Error: Port {port} is already in use")
                return None, None
            else:
                print(f"Error starting OSC server: {e}")
                return None, None
        except Exception as e:
            print(f"Error starting OSC server: {e}")
            return None, None

    def _stop_osc_server(self):
        """Stop the OSC server and clean up resources."""
        if self._osc_server is not None:
            try:
                self._osc_server.shutdown()
                self._osc_server.server_close()
                if self._osc_thread and self._osc_thread.is_alive():
                    self._osc_thread.join(timeout=1)
                print(f"OSC server stopped (was on port {self._osc_port})")
            except Exception as e:
                print(f"Error stopping OSC server: {e}")
            finally:
                self._osc_server = None
                self._osc_thread = None
                self._osc_port = None

    def restart_osc_server(self, ip="127.0.0.1", port=9000, kill_existing=True):
        """
        Restart the OSC server, optionally killing any existing process on the port.
        
        Parameters
        ----------
        ip : str, optional
            OSC server IP address, by default "127.0.0.1"
        port : int, optional
            OSC server port, by default 9000
        kill_existing : bool, optional
            Whether to attempt to kill existing processes on the port, by default True
        """
        self._stop_osc_server()
        
        if kill_existing:
            self._kill_port_processes(port)
            
        return self._setup_osc_server(ip, port)
    
    def _kill_port_processes(self, port):
        """Attempt to kill processes using the specified port."""
        import subprocess
        import platform
        
        try:
            if platform.system() in ["Darwin", "Linux"]:  # macOS or Linux
                # Find processes using the port
                result = subprocess.run(['lsof', '-ti', f':{port}'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        try:
                            subprocess.run(['kill', '-9', pid], timeout=5)
                            print(f"Killed process {pid} using port {port}")
                        except:
                            pass
                    import time
                    time.sleep(0.5)  # Give time for processes to die
            else:
                print(f"Automatic port cleanup not supported on {platform.system()}")
        except Exception as e:
            print(f"Could not automatically kill processes on port {port}: {e}")
            print(f"Manual cleanup: lsof -ti:{port} | xargs kill -9")

    def open(self, start_osc=True, osc_ip="127.0.0.1", osc_port=9000):
        """
        Open the timeline in a browser window.
        
        Parameters
        ----------
        start_osc : bool, optional
            Whether to start OSC server, by default True
        osc_ip : str, optional
            OSC server IP address, by default "127.0.0.1"
        osc_port : int, optional
            OSC server port, by default 9000
        """
        if start_osc and self._osc_server is None:
            server, thread = self._setup_osc_server(osc_ip, osc_port)
            if server is None and osc_port == 9000:
                print("\nTo fix the port 9000 conflict, try:")
                print("timeline.restart_osc_server()  # This will force-kill existing processes")
        self._panel.show() 