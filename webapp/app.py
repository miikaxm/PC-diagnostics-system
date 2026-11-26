import threading
from datetime import datetime
from uuid import uuid4

from flask import Flask, jsonify, render_template, request

from engine.test_manager import (
  TESTS,
  run_tests,
  save_test_results
)

from engine.storage_devices import (
  list_smart_disks,
  get_selected_disk
)

app = Flask(__name__)

# Käyttöliittymässä näytettävät testien nimet
TEST_NAMES = {
  "cpu": "Prosessorin perustiedot",
  "memory": "RAM-muistin perustiedot",
  "smart": "Tallennuslevyn SMART-tarkistus",
  "cpu_stress": "CPU-kuormitustesti",
  "memory_stress": "RAM-muistitesti",
  "temperature": "Lämpötilojen tarkistus",
  "gpu_stress": "GPU-kuormitustesti"
}

# Yhdentesti ajon tila
test_state = {
  "status": "idle",
  "selected_tests": [],
  "current_test": None,
  "completed": 0,
  "total": 0,
  "results": [],
  "run_id": None,
  "saved_file": None,
  "error": None
}

# Estää sen että testejä ei voida ajaa samaan aikaan
state_lock = threading.Lock()


def execute_tests(selected_tests, run_id, timestamp, smart_device):
  # Lista testien tuloksille
  results = []

  try:
    # Käydään käyttäjän valitsemat testit läpi
    for test_name in selected_tests:

      # Päivitetään parhaillaan suoritettava testi
      with state_lock:
        test_state["current_test"] = test_name

      # Suoritetaan testi lukituksen ulkopuolella
      test_run = run_tests([test_name], smart_device=smart_device)
      results.extend(test_run["results"])

      # Päivitetään valmistuneiden testien määrä
      with state_lock:
        test_state["results"] = list(results)
        test_state["completed"] += 1

    # Yhdistetään kaikkien testien tulokset
    combined_run = {
      "run_id": run_id,
      "timestamp": timestamp,
      "results": results
    }

    # Tallennetaan tulokset yhteen JSON-tiedostoon
    filename = save_test_results(combined_run)

    # Merkitään koko testiajo valmistuneeksi
    with state_lock:
      test_state["status"] = "finished"
      test_state["current_test"] = None
      test_state["saved_file"] = str(filename)

  except Exception as error:
    # Jos testiajo epäonnistuu, tallennetaan virhe
    with state_lock:
      test_state["status"] = "error"
      test_state["current_test"] = None
      test_state["error"] = str(error)

@app.route("/")
def index():
  # Näyttää kotisivun
  tests = [
    {
      "id": test_id,
      "name": TEST_NAMES.get(test_id, test_id)
    }
    for test_id in TESTS
  ]

  return render_template("index.html", tests=tests)

@app.route("/api/start", methods=["POST"])
def start_tests():
  # Käynnistää testit jotka käyttjä valitsee
  data = request.get_json(silent=True)

  if not isinstance(data, dict):
    return jsonify({
      "error": "Virheellinen pyyntö"
    }), 400

  selected = data.get("selected_tests")

  if not isinstance(selected, list) or not selected:
    return jsonify({
      "error": "Valitse vähintääb yksi testi."
    }), 400

  # Hyväkhsytään vain testien oikeat nimet
  if any(
    not isinstance(name, str) or name not in TESTS
    for name in selected
  ):
    return jsonify({
      "error": "Tuntematon testi valinassa"
    }), 400

  # Poistetaan mahdolliset kaksoisvalinnat
  selected = list(dict.fromkeys(selected))

  run_id = str(uuid4())
  timestamp = datetime.now().astimezone().isoformat()
  smart_device = None

  if "smart" in selected:
    try:
      selected_disk = get_selected_disk(data.get("smart_device"))

      smart_device = selected_disk["id"]

    except ValueError as error:
      return jsonify({
        "error": str(error)
      }), 400

    except Exception as error:
      return jsonify({
        "error": f"Levyjen tunnistus epäonnistui: {error}"
      })

  with state_lock:
    if test_state["status"] == "running":
      return jsonify({
        "error": "Testisarja on jo käynnissä"
      }), 409

    # Alustetaan uuden testiajon tiedot
    test_state.update({
      "status": "running",
      "selected_tests": selected,
      "current_test": None,
      "completed": 0,
      "total": len(selected),
      "results": [],
      "run_id": run_id,
      "saved_file": None,
      "error": None
    })

    # suoritetaan testi erillisessä säikeessä
    worker = threading.Thread(
      target=execute_tests,
      args=(selected, run_id, timestamp, smart_device),
      daemon=True
    )

    worker.start()

  return jsonify({
    "message": "Testit käynnistetty",
    "run_id": run_id
  }), 202

@app.route("/api/status")
def get_status():
  # Palauttaa testien tilan selaimessa
  with state_lock:
    current_state = {
      "status": test_state["status"],
      "selected_tests": list(test_state["selected_tests"]),
      "current_test": test_state["current_test"],
      "completed": test_state["completed"],
      "total": test_state["total"],
      "results": list(test_state["results"]),
      "run_id": test_state["run_id"],
      "saved_file": test_state["saved_file"],
      "error": test_state["error"]
    }

  return jsonify(current_state)

# Laitteen tietojen haku
@app.route("/api/hardware")
def get_hardware():
  try:
    # Haetaan haku funktio enginestä
    from engine.inventory import collect_hardware_info

    # Tallennetaan ja palautetaan tiedot
    information = collect_hardware_info()
    return jsonify(information)

  # Jos virhe niin ilmoitetaan
  except Exception as error:
    return jsonify({
      "error": f"Laitteistotietoja ei saatu: {error}"
    }), 503

# käytettävissä olevien levyjen haku
@app.route("/api/disks")
def get_disks():
  # haetaan valittavissa olevat levyt ensin
  try:
    disks = list_smart_disks()

    return jsonify({
      "disks": disks
    })

  except Exception as error:
    return jsonify({
      "error": f"Levyjä ei saatu tunnistettua: {error}"
    }), 503

if __name__ == "__main__":
  app.run(
    host="127.0.0.1",
    port=5000,
    debug=False,
    use_reloader=False
  )



  
