
import queue
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from common import Logger, DISHES

log = Logger("a2_1_threads")


class PriceBoard:
    """Shared price table. Both the worker (writes) and main thread (reads) touch it."""
    def __init__(self):
        self._prices = {"tomato": 40.0, "onion": 35.0, "potato": 28.0, "palak": 40.0}
        self._lock = threading.Lock()

    def update(self, item, price):
        with self._lock:                      # without this a reader could see half an update
            old = self._prices[item]
            self._prices[item] = price
            return old

    def snapshot(self):
        with self._lock:
            return dict(self._prices)


class PriceMonitor(threading.Thread):
    def __init__(self, board, alerts, stop_evt, interval=0.6, seed=11):
        super().__init__(name="price-monitor", daemon=True)
        self.board, self.alerts, self.stop_evt = board, alerts, stop_evt
        self.interval, self.rnd = interval, random.Random(seed)
        self.latencies = []                   # seconds per poll, for the performance table

    def run(self):
        poll = 0
        while not self.stop_evt.is_set():
            poll += 1
            t0 = time.perf_counter()
            time.sleep(self.rnd.uniform(0.15, 0.45))        # pretend network round trip
            for item, price in self.board.snapshot().items():
                new = round(price * self.rnd.uniform(0.96, 1.05), 1)
                if poll == 4 and item == "tomato":
                    new = round(price * 1.9, 1)             # forced spike so we can see an alert
                old = self.board.update(item, new)
                if abs(new - old) / old >= 0.15:
                    self.alerts.put(("PRICE_ALERT", item, old, new))
            lat = time.perf_counter() - t0
            self.latencies.append(lat)
            log("MONITOR", "[%s] poll #%d done in %.0f ms" % (self.name, poll, lat * 1000))
            self.stop_evt.wait(self.interval)               # wait() so shutdown is instant


def score_day(day, dish_ids):
    """Stand-in for a slow job (nutrition scoring of one day's menu)."""
    time.sleep(0.5)
    kcal = sum(DISHES[d]["kcal"] for d in dish_ids)
    return day, kcal


def main(run_seconds=4.0, tick=0.1):
    board, alerts, stop = PriceBoard(), queue.Queue(), threading.Event()
    mon = PriceMonitor(board, alerts, stop)
    pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix="scorer")
    log("MAIN", "starting background monitor (daemon=%s)" % mon.daemon)
    mon.start()

    jobs = {"Mon": ["dal_tadka", "curd_rice"], "Tue": ["rajma_chawal", "idli_sambar"],
            "Wed": ["paneer_masala", "veg_upma"]}
    pending, gaps = [], []
    t_start = time.perf_counter()
    last = t_start
    n = 0
    while time.perf_counter() - t_start < run_seconds:
        n += 1
        now = time.perf_counter()
        gaps.append(now - last)               # how long since the last UI tick = freeze detector
        last = now

        if n == 5:                            # user presses "plan the week" -> hand off, dont wait
            log("MAIN", "user clicked 'plan week' -> submitting %d jobs to pool" % len(jobs))
            for day, dishes in jobs.items():
                pending.append(pool.submit(score_day, day, dishes))
        for f in [f for f in pending if f.done()]:
            pending.remove(f)
            day, kcal = f.result()
            log("MAIN", "job finished: %s menu = %d kcal" % (day, kcal))

        try:
            while True:                       # drain alerts without blocking
                kind, item, old, new = alerts.get_nowait()
                log("MAIN", "%s: %s Rs.%.1f -> Rs.%.1f, replanning gravies" % (kind, item, old, new))
        except queue.Empty:
            pass
        time.sleep(tick)

    stop.set()
    mon.join(timeout=2)
    pool.shutdown(wait=True)

    lat = mon.latencies
    log("PERF", "polls=%d  latency min/avg/max = %.0f / %.0f / %.0f ms"
        % (len(lat), min(lat) * 1000, sum(lat) / len(lat) * 1000, max(lat) * 1000))
    log("PERF", "UI ticks=%d  target gap=%.0f ms  avg gap=%.0f ms  worst gap=%.0f ms"
        % (len(gaps), tick * 1000, sum(gaps) / len(gaps) * 1000, max(gaps) * 1000))
    log("PERF", "if polling ran on the main thread the UI would freeze for ~%.0f ms per poll"
        % (sum(lat) / len(lat) * 1000))
    log("MAIN", "final prices: %s" % board.snapshot())
    return lat, gaps


if __name__ == "__main__":
    log.open()
    lat, gaps = main()
    import json
    with open("logs/a2_1_latency.json", "w") as fh:
        json.dump({"latency": lat, "gaps": gaps}, fh)
