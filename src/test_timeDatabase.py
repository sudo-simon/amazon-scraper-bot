from database import Database
from random import choice,random,randint
from string import ascii_letters
from time import time
from sys import argv

def randomString(length:int) -> str:
    return ''.join(choice(ascii_letters) for _ in range(length))

def randomFloat(maximum:int) -> float:
    return random()*randint(0,maximum)


def runTests(n_tests:int, database:Database) -> float:
    e = 0
    wl_names = [randomString(15) for _ in range(n_tests)]

    start = time()
    for name in wl_names:
        database.addWatchlist(name,randomFloat(3000))
        database.write("./tests/database.json")
    for name in wl_names:
        if (database.removeWatchlist(name) == -1):
            e += 1
            print(f"Error in removeWatchlist (#{e})")
        database.write("./tests/database.json")
    elapsed = time() - start

    return elapsed







if (__name__ == "__main__"):

    n_tests = 1000
    db = Database()

    if (len(argv) == 2):
        try:
            n_tests = int(argv[1])
        except:
            print("Pass the total number of tests as an argument (integer)")
            exit(0)

    print(f"Running {n_tests} tests...\n")
    run_time = runTests(n_tests,db)

    print(
        f"Total time: {run_time:.3f}\n"
        f"Avg time per test: {(run_time/n_tests):.3f}\n"
    )

    