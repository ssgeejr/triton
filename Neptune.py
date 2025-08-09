#!/usr/bin/env python3
import time

class Neptune:
    def __init__(self):
        print("Neptune irrigation controller initialized.")

    def timer_controller(self):
        try:
            while True:
                time.sleep(20)
                print("I'm watering the garden mom!")
                print("all done, sleeping")
        except KeyboardInterrupt:
            print("\nStopping Neptune irrigation system.")

if __name__ == "__main__":
    neptune = Neptune()
    neptune.timer_controller()
