import salt.client
import time
import timeit

# avg = 23 ms


def get_local_client():
    return salt.client.LocalClient(c_path=None, mopts=__opts__, auto_reconnect=True)


def run_cmd(salt_client):
    return salt_client.cmd_async(tgt='*', fun='test.ping')


def test():
    cli = get_local_client()
    ret = run_cmd(cli)
    print(f'>>> RET {ret} {type(__opts__)}')


def start():
    time.sleep(3)

    cli = get_local_client()
    while True:
        print('>>>')
        average_time = timeit.timeit(test, number=5) / 5
        print(f'Лёха застрял: {average_time:.4f} секунд')
        time.sleep(1)
