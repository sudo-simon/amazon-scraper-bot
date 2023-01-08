from AWSDatabase import AWSDatabase
from jsonDatabase import JsonDatabase
from typing import Union
from random import choice,random,randint
from string import ascii_letters
from time import time
from sys import argv

def randomString(length:int) -> str:
    return ''.join(choice(ascii_letters) for _ in range(length))

def randomFloat(maximum:int) -> float:
    return random()*randint(0,maximum)

def randomUserId() -> int:
    numbers = [str(n) for n in range(1,10)]
    return int(''.join(choice(numbers) for _ in range(10)))


def runTests(n_tests:int, database:Union[AWSDatabase,JsonDatabase], multiple_users:bool) -> float:
    e = 0
    user_ids = [randomUserId() for _ in range(n_tests)]
    wl_names = [randomString(15) for _ in range(n_tests)]
    single_userid = randomUserId()

    elapsed:float

    if (multiple_users):
        start = time()
        for i in range(n_tests):
            database.addWatchlist(user_ids[i],wl_names[i],randomFloat(3000))
        for i in range(n_tests):
            if (database.removeWatchlist(user_ids[i],wl_names[i]) == -1):
                e += 1
                print(f"Error in removeWatchlist (#{e})")
        elapsed = time() - start
    
    else:
        start = time()
        for name in wl_names:
            database.addWatchlist(single_userid,name,randomFloat(3000))
        for name in wl_names:
            if (database.removeWatchlist(single_userid,name) == -1):
                e += 1
                print(f"Error in removeWatchlist (#{e})")
        elapsed = time() - start

    return elapsed







if (__name__ == "__main__"):

    n_tests = 1000
    multiple_users = False
    db_json = JsonDatabase("./tests/pyson_database.json")
    db_aws = AWSDatabase("./tests/aws_database.json")
    db_type = "aws"

    try:
        if (argv[1] in ["--aws","--pyson"]): db_type = argv[1][2:]
    except:
        print("Pass the db to test as the first argument (\"--aws\" or \"--pyson\")")
        exit(0)

    if (len(argv) > 2):
        try:
            n_tests = int(argv[2])
        except:
            print("Pass the total number of tests as the second argument (integer)")
            exit(0)
    if (len(argv) > 3 and argv[3] in ["--multiple_users","-m"]): multiple_users = True

    print(f"Running {n_tests} tests on the {db_type} database{' (multiple users insertions)' if multiple_users else ''}...\n")
    if (db_type == "aws"): run_time = runTests(n_tests,db_aws,multiple_users)
    if (db_type == "pyson"): run_time = runTests(n_tests,db_json,multiple_users)

    print(
        f"Total time: {run_time:.3f}\n"
        f"Avg time per test: {(run_time/n_tests):.3f}\n"
    )

    