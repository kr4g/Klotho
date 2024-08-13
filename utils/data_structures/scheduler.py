from pythonosc import udp_client, osc_message_builder
from uuid import uuid4

class Scheduler:
    def __init__(self, ip:str='127.0.0.1', port:int=57120):
        self.client = udp_client.SimpleUDPClient(ip, port)
        self.events = []
    
    def add_new_event(self, synth_name:str, start:float, **params):
        args = [synth_name, start] + [item for sublist in params.items() for item in sublist]
        self.events.append(('new', args))
    
    def add_new_event_with_id(self, synth_name:str, start:float, **params):
        uid = str(uuid4()).replace('-', '')
        args = [uid, synth_name, start] + [item for sublist in params.items() for item in sublist]
        self.events.append(('new_id', args))
        return uid

    def add_set_event(self, uid:str, start:float, **params):
        args = [uid, start] + [item for sublist in params.items() for item in sublist]
        self.events.append(('set', args))
    
    def send_all_events(self):
        for event_type, content in self.events:
            msg = osc_message_builder.OscMessageBuilder(address='/storeEvent')
            msg.add_arg(event_type)
            for item in content:
                msg.add_arg(item)
            self.client.send(msg.build())
        self.events.clear()
        print('Events have been sent.')
