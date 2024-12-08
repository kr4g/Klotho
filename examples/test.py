from utils.messaging import Scheduler

scheduler = Scheduler()

for i in range(10):
    start = i
    # event with no uid
    scheduler.new_event('test', start=start + 0.5, freq=880, amp=0.5, attackTime=0.5, releaseTime=0.0)
    # event with uid
    uid = scheduler.new_event('default', start=start, freq=440, amp=0.5)
    # set event using uid
    scheduler.set_event(uid, start=start + 0.25, gate=0)

scheduler.run()