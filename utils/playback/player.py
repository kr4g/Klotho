from pythonosc import udp_client

client = udp_client.SimpleUDPClient("127.0.0.1", 57120)

def play(**kwargs):
    processed_params = {}
    
    for name, value in kwargs.items():
        if isinstance(value, list):
            for i, item in enumerate(value):
                processed_params[f"{name}_{i}"] = item
            processed_params[f"{name}_size"] = len(value)
        else:
            processed_params[name] = value
    
    flat_params = []
    for name, value in processed_params.items():
        flat_params.append(name)
        flat_params.append(value)
    
    client.send_message("/play", flat_params)