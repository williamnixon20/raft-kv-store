import sys
import os


def pytest_configure(config):
    print("Starting pytest!")
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
    )


def pytest_unconfigure(config):
    print("Finishing pytest!")
