import time
import random


def get_log(section, status):
    return '127.0.0.1 - user [09/May/2018:16:00:39 +0000] "GET /{}/user/ HTTP/1.0" {} {}\n'.format(section, status, random.randint(1,2000))

starttime = time.time()

SECTION = [
    'api',
    'admin',
    'news',
    'products',
    'promos',
    'locations',
    'users',
    'food',
    'menus',
]

STATUS = [
    200,
    400,
    401,
    404,
    500,
]

while True:

    with open('./access.log', 'a') as f:

        qty = random.randint(1, 30)
        for i in range(qty):
            f.write(get_log(random.choice(SECTION), random.choice(STATUS)))

    interval = 1
    time.sleep(interval - ((time.time() - starttime) % interval))
