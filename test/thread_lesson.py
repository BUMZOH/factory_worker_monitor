import threading
import time


def worker(stop_event):
    """Run in another thread."""
    while not stop_event.wait(2):
        print("Worker thread.")
        time.sleep(2)

stop_event = threading.Event()

thread = threading.Thread(
    target=worker,
    args=(stop_event,),
)

thread.start()


for count in range(10):
    print(f"Main thread: {count}")
    time.sleep(1)

stop_event.set()

thread.join()

print("Finished")

