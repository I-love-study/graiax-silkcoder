import json
from pathlib import Path

import pytest
from filelock import FileLock

resource_path = Path("tests/data/")
tmp_path = resource_path / "tmp"

def startup():
    tmp_path.mkdir(exist_ok=True)

def teardown():
    for file in tmp_path.iterdir():
        file.unlink(missing_ok=True)
    tmp_path.rmdir()

def _load_worker_list(fn: Path) -> list[str]:
    return json.loads(fn.read_text())["workers"]


def _write_worker_list(fn: Path, workers: list[str]) -> None:
    fn.write_text(json.dumps({"workers": workers}))

@pytest.fixture(scope='package', autouse=True)
def start_and_teardown(
    tmp_path_factory: pytest.TempPathFactory, worker_id: str
):
    if worker_id == "master":
        startup()
        yield 
        teardown()
        return

    root_tmp_dir: Path = tmp_path_factory.getbasetemp().parent

    wfile: Path = root_tmp_dir / "minio.workers"
    fn = root_tmp_dir / "minio_run.lock"
    with FileLock(str(fn)):
        start: bool = False
        if wfile.is_file():
            worker_list = _load_worker_list(wfile)
            if len(worker_list) == 0:
                start = True
            worker_list.append(worker_id)
            _write_worker_list(wfile, worker_list)
        else:
            _write_worker_list(wfile, [worker_id])
            start = True
        if start:
            startup()

    yield

    with FileLock(str(fn)):
        workers = _load_worker_list(wfile)
        workers.remove(worker_id)
        _write_worker_list(wfile, workers)
        if len(workers) == 0:
            teardown()
