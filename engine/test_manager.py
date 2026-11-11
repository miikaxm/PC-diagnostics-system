import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from tests.cpu.cpu_test import run_cpu_test
from tests.memory.memory_test import run_memory_test

TESTS = {
  "cpu": run_cpu_test,
  "memory": run_memory_test
}

def run_tests(selected_tests=None):
  if selected_tests is None:
    selected_tests = list(TESTS.keys())

  results = []

  for test_name in selected_tests:
    test_function = TESTS.get(test_name)

    if test_function is None:
      results.append({
        "test_id": test_name,
        "test_name": test_name,
        "status": "UNKNOWN",
        "message": "Tuntematon testi",
        "details": {}
      })
      continue

    try:
      result = test_function()
      results.append(result)
    except Exception as error:
      results.append({
        "test_id": test_name,
        "test_name": test_name,
        "status": "UNKNOWN",
        "message": f"Testin suorittaminen epäonnistui: {error}",
        "details": {}
      })

  return {
    "run_id": str(uuid4()),
    "timestamp": datetime.now().astimezone().isoformat(),
    "results": results
  }


def save_test_results(test_run):
  project_folder = Path(__file__).resolve().parent.parent
  data_folder = project_folder / "data"
  data_folder.mkdir(parents=True, exist_ok=True)

  filename = (
    data_folder / f"test_results_{test_run['run_id']}.json"
  )

  with filename.open("w", encoding="utf-8") as file:
    json.dump(
      test_run,
      file,
      indent=4,
      ensure_ascii=False
    )

  return filename