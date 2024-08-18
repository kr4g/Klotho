import sys
from pathlib import Path

root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))


from klotho.aikous.messaging import scheduler as sch
scheduler = sch.Scheduler()

import numpy as np

start = 0
for i in range(1000):
    scheduler.add_new_event('kick', i*0.125)
    # start += np.random.uniform(0.1, 0.5)

scheduler.run()
