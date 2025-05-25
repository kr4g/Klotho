from pythonosc import udp_client, osc_message_builder, dispatcher, osc_server
from uuid import uuid4
import threading
import time
from tqdm import tqdm
import heapq
import json
import os
from typing import Union

class StreamBuilder:
    def __init__(self, scheduler: 'Streamer', event_type: str, uid: str, synth_name: str, start: float, params: dict):
        self.scheduler = scheduler
        self.event_type = event_type
        self.uid = str(uuid4()).replace('-', '') if uid is None else uid
        self.synth_name = synth_name
        self.start = start
        self.params = params
        self._add_event()
            
    def _add_event(self):
        args = [self.uid, self.synth_name, self.start] + [item for sublist in self.params.items() for item in sublist]
        event_type = self.event_type
        heapq.heappush(self.scheduler.events, (self.start, (event_type, args)))
        self.scheduler.total_events += 1
    
    def __str__(self):
        return self.uid
        
    def __repr__(self):
        return self.uid


class Streamer:
    def __init__(self, ip:str='127.0.0.1', send_port:int=57121, receive_port:int=9000):
        self.client = udp_client.SimpleUDPClient(ip, send_port)
        self.events = []
        self.paused = True
        self.events_processed = 0
        self.total_events = 0
        self.events_sent = 0
        self.batch_size = 25

        self.dispatcher = dispatcher.Dispatcher()
        self.dispatcher.map("/pause", self.pause_handler)
        self.dispatcher.map("/resume", self.resume_handler)
        self.dispatcher.map("/event_processed", self.event_processed_handler)
        self.dispatcher.map("/reset", self.reset_handler)
        self.dispatcher.map("/start", self.start)
        self.dispatcher.map("/new_synth", self.new_synth_handler)
        self.dispatcher.map("/set_synth", self.set_synth_handler)
        self.dispatcher.map("/clear_events", self.clear_events)
        
        self.server = osc_server.ThreadingOSCUDPServer((ip, receive_port), self.dispatcher)
        self.server_thread = None
        self.running = False
        self.send_progress = None
        self.process_progress = None
        
    def init_progress_bars(self):
        if self.send_progress:
            self.send_progress.close()
        if self.process_progress:
            self.process_progress.close()
            
        self.send_progress = tqdm(total=self.total_events, 
                                desc="Ready to send", 
                                unit="events",
                                position=0,
                                leave=True)
        
        self.process_progress = tqdm(total=self.total_events,
                                   desc="Ready to process",
                                   unit="events",
                                   position=1,
                                   leave=True)
    
    def reset_progress_bars(self):
        if self.send_progress:
            self.send_progress.clear()
            self.send_progress.reset(total=self.total_events)
            self.send_progress.set_description("Ready to send")
        if self.process_progress:
            self.process_progress.clear()
            self.process_progress.reset(total=self.total_events)
            self.process_progress.set_description("Ready to process")
        
    def pause_handler(self, address, *args):
        if not self.paused:
            self.paused = True
            if self.send_progress:
                self.send_progress.set_description("Paused sending")

    def resume_handler(self, address, *args):
        self.paused = False
        if self.send_progress:
            self.send_progress.set_description("Sending")

    def event_processed_handler(self, address, *args):
        self.events_processed += 1
        if self.process_progress:
            self.process_progress.update(1)
        if self.events_sent == self.total_events:
            if self.send_progress:
                self.send_progress.set_description("All Events Sent")
        if self.events_processed == self.total_events:
            if self.process_progress:
                self.process_progress.set_description("All Events Processed")

    def reset_handler(self, address, *args):
        self.events_processed = 0
        self.events_sent = 0
        self.paused = True
        self.reset_progress_bars()

    def new_synth(self, synth_name:str = None, start:float = 0, **params):
        return StreamBuilder(self, 'new', None, synth_name, start, params).uid

    def set_synth(self, uid:str, start:float, **params):
        StreamBuilder(self, 'set', uid, None, start, params)

    def new_synth_handler(self, address, uid, synth_name, start, *params):
        param_dict = {params[i]: params[i+1] for i in range(0, len(params), 2)}
        StreamBuilder(self, 'new', uid, synth_name, float(start), param_dict)
        self.reset_progress_bars()
        
    def set_synth_handler(self, address, uid, start, *params):
        param_dict = {params[i]: params[i+1] for i in range(0, len(params), 2)}
        StreamBuilder(self, 'set', uid, None, float(start), param_dict)
        self.reset_progress_bars()
        
    def start(self, address, *args):
        if self.events_sent == self.total_events:
            self.events_processed = 0
            self.events_sent = 0
            self.reset_progress_bars()
        self.paused = False
        self.send_progress.set_description("Sending")
        self.process_progress.set_description("Processing")
        self.send_events()

    def send_events(self):
        events = self.events.copy()
        while events:
            while self.paused:
                time.sleep(0.01)
            _, (event_type, content) = heapq.heappop(events)
            
            msg = osc_message_builder.OscMessageBuilder(address='/storeEvent')
            msg.add_arg(event_type)
            for item in content:
                msg.add_arg(item)
            self.client.send(msg.build())
            self.events_sent += 1
            self.send_progress.update(1)
            self.process_progress.total = self.events_sent
            self.process_progress.refresh()
            time.sleep(0.01)

        eot_msg = osc_message_builder.OscMessageBuilder(address='/storeEvent')
        eot_msg.add_arg('end_of_transmission')
        self.client.send(eot_msg.build())
        self.send_progress.set_description("All Events Sent")
        # print("All events sent.")

    def clear_events(self, address=None, *args):
        self.events = []
        self.total_events = 0
        self.events_processed = 0
        self.events_sent = 0
        self.paused = True
        if self.send_progress:
            self.send_progress.reset()
        if self.process_progress:
            self.process_progress.reset()

    def stop_server(self):
        if self.running:
            self.server.shutdown()
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join()
            self.server_thread = None
            self.running = False
            if self.send_progress:
                self.send_progress.close()
            if self.process_progress:
                self.process_progress.close()

    def run(self):
        if not self.running:
            self.running = True
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.start()
            self.init_progress_bars()
            # print("Server is running.")
        else:
            print("Server is already running.")


class Scheduler:
    def __init__(self):
        self.events = []
        self.total_events = 0
        self.event_counter = 0  # sorting for final tiebreaker
        
    def new_node(self, synth_name: str, start: float = 0, dur: Union[float, None] = None, group: str = None, **pfields):
        uid = str(uuid4()).replace('-', '')
        
        event = {
            "type": "new",
            "id": uid,
            "synthName": synth_name,
            "start": start,
            "pfields": pfields
        }
        
        if group:
            event["group"] = group
        else:
            event["group"] = "default"
            
        priority = 0 # higher priority
        heapq.heappush(self.events, (start, priority, uid, self.event_counter, event))
        self.event_counter += 1
        self.total_events += 1
        
        if dur:
            self.set_node(uid, start = start + dur, gate = 0)
        
        return uid

    def set_node(self, uid: str, start: float, **pfields):
        event = {
            "type": "set",
            "id": uid,
            "start": start,
            "pfields": pfields
        }
        
        priority = 1 # lower priority
        heapq.heappush(self.events, (start, priority, uid, self.event_counter, event))
        self.event_counter += 1
        self.total_events += 1
    
    def free_node(self, uid: str):
        event = {
            "type": "free",
            "id": uid
        }
        heapq.heappush(self.events, (0, 0, uid, self.event_counter, event))
        self.event_counter += 1
        self.total_events += 1
        
    def clear_events(self):
        self.events = []
        self.total_events = 0
        self.event_counter = 0
        
    def write(self, filepath, start_time: Union[float, None] = None, time_scale: float = 1.0):
        sorted_events = []
        events_copy = self.events.copy()
        
        if events_copy:
            if start_time is not None:
                min_start = min(start for start, _, _, _, _ in events_copy)
                time_shift = start_time - min_start
            else:
                time_shift = 0
            
            while events_copy:
                start, _, _, _, event = heapq.heappop(events_copy)
                new_start = (start + time_shift) * time_scale
                event["start"] = new_start
                sorted_events.append(event)
            
        try:
            with open(filepath, 'w') as f:
                json.dump(sorted_events, f, indent=2)
            print(f"Successfully wrote {self.total_events} events to {os.path.abspath(filepath)}")
        except Exception as e:
            print(f"Error writing to {filepath}: {e}")
