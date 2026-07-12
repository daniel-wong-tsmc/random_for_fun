import threading
from concurrent.futures import ProcessPoolExecutor
from gpu_agent.wiki.log import WikiLog


def _proc_worker(args):
    path, n, tag = args
    log = WikiLog(path)
    for i in range(n):
        log.append(asOf="2026-07-12", kind="append-observation", pageId="p",
                   findingId=f"f-{tag}-{i}")
    return n


def test_two_writers_processes_no_duplicate_seq(tmp_path):
    path = str(tmp_path / "log.jsonl")
    K, M = 4, 25
    with ProcessPoolExecutor(max_workers=K) as ex:
        list(ex.map(_proc_worker, [(path, M, k) for k in range(K)]))
    seqs = sorted(e.seq for e in WikiLog(path).read())
    assert len(seqs) == K * M
    assert seqs == list(range(K * M))       # unique AND contiguous


def test_many_threads_no_duplicate_seq(tmp_path):
    log = WikiLog(tmp_path / "log.jsonl")
    T, M = 8, 30

    def work(tag):
        for i in range(M):
            log.append(asOf="2026-07-12", kind="append-observation", pageId="p",
                       findingId=f"f-{tag}-{i}")

    threads = [threading.Thread(target=work, args=(t,)) for t in range(T)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    seqs = sorted(e.seq for e in log.read())
    assert seqs == list(range(T * M))
