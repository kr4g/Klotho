import requests
from klotho.chronos.temporal_units.ut import TemporalUnit as UT
from klotho.topos.graphs.trees.algorithms import rotate_children

def visualize(uts):
    """Send visualization data to the server."""
    if not isinstance(uts, list):
        uts = [uts]
    data = {"status": "success", "data": [ut.to_dict() for ut in uts]}
    
    try:
        requests.post('http://localhost:8000/data', json=data)
    except requests.exceptions.RequestException as e:
        print("Error: Server not running. Start server first with: python server.py")
        raise e

if __name__ == "__main__":
    # Example usage
    S = ((2, (5, (4, (5, 3, 2)))), (3, (5, (4, (7, 5, 1)), 3, 2)), (7, (5, (7, (9, 5, 2)), 6, 4)))
    ut1 = UT(
        span=8,
        tempus='4/4',
        prolatio=rotate_children(S, 0),
        tempo=60,
        beat='1/4'
    )
    ut2 = UT(
        span=8,
        tempus='4/4',
        prolatio=rotate_children(S, 1),
        tempo=60,
        beat='1/4'
    )
    visualize(ut1)
    # visualize(ut2)
