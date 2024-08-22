from pythonosc import udp_client, osc_message_builder, dispatcher, osc_server
from uuid import uuid4
import threading
import time

class Scheduler:
    def __init__(self, ip:str='127.0.0.1', send_port:int=57120, receive_port:int=57121):
        self.client = udp_client.SimpleUDPClient(ip, send_port)
        self.events = []
        self.paused = False
        self.events_processed = 0
        self.total_events = 0
        self.events_sent = 0
        self.batch_size = 10

        self.dispatcher = dispatcher.Dispatcher()
        self.dispatcher.map("/pause", self.pause_handler)
        self.dispatcher.map("/resume", self.resume_handler)
        self.dispatcher.map("/event_processed", self.event_processed_handler)
        self.server = osc_server.ThreadingOSCUDPServer((ip, receive_port), self.dispatcher)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        # self.server_thread.start()
    
    def pause_handler(self, address, *args):
        if not self.paused:
            self.paused = True
            # print("Paused")

    def resume_handler(self, address, *args):
        self.paused = False

    def event_processed_handler(self, address, *args):
        self.events_processed += 1
        if self.events_processed == self.total_events:
            print("All events processed by SuperCollider. Terminating program.")
            self.stop_server()

    def add_event(self, synth_name:str, start:float, **params):
        # uid = str(uuid4()).replace('-', '')
        args = [synth_name, start] + [item for sublist in params.items() for item in sublist]
        self.events.append(('new', args))
        self.total_events += 1
        # return uid
    
    def add_event_with_id(self, synth_name:str, start:float, **params):
        uid = str(uuid4()).replace('-', '')
        args = [uid, synth_name, start] + [item for sublist in params.items() for item in sublist]
        self.events.append(('new_id', args))
        self.total_events += 1
        return uid

    def set_event(self, uid:str, start:float, **params):
        args = [uid, start] + [item for sublist in params.items() for item in sublist]
        self.events.append(('set', args))
        self.total_events += 1
    
    # def free_synth(self, uid:str):
    #     self.events.append(('free', [uid]))
    #     self.total_events += 1
    
    def send_events(self):
        print(f"Started sending events. Total events: {self.total_events}")
        for event_type, content in self.events:
            while self.paused:
                time.sleep(0.01)
            msg = osc_message_builder.OscMessageBuilder(address='/storeEvent')
            msg.add_arg(event_type)
            for item in content:
                msg.add_arg(item)
            self.client.send(msg.build())
            self.events_sent += 1
            # if self.events_sent % self.batch_size == 0:
            #     print(f"Sent {self.events_sent} of {self.total_events} events")
            time.sleep(0.01)
        # Send end of transmission signal
        eot_msg = osc_message_builder.OscMessageBuilder(address='/storeEvent')
        eot_msg.add_arg('end_of_transmission')
        self.client.send(eot_msg.build())
        print('All events have been sent.')

    def stop_server(self):
        self.server.shutdown()
        self.server_thread.join()
        exit(0)

    def run(self):
        self.server_thread.start()
        self.send_events()
        # Wait for SuperCollider to process all events
        # while self.events_processed < self.total_events:
        #     time.sleep(0.1)
