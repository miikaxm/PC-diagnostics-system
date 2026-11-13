import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

# Testien importit
from tests.cpu.cpu_test import run_cpu_test
from tests.memory.memory_test import run_memory_test
from tests.storage.smart_test import run_smart_test
from tests.cpu.cpu_stress_test import run_cpu_stress_test

# Ajettavat testit (tällä hetkellä kaikki voidaan myöhemmin muokata käyttöliittymästä)
TESTS = {
  "cpu": run_cpu_test,
  "memory": run_memory_test,
  "smart": run_smart_test,
  "cpu_stress": run_cpu_stress_test
}

# Testien ajo
def run_tests(selected_tests=None):
  #Valitaan kaikki testit jos niitä ei ole erikseen määritelty (myöhemmin käyttöliittymästä)
  if selected_tests is None:
    selected_tests = list(TESTS.keys())

  # Lista tuloksille
  results = []

  # Käydään testi nimet läpi ja suoritetaan ne yksitellen
  for test_name in selected_tests:
    # Haetaan testin nimeä vastaava funktio
    test_function = TESTS.get(test_name)

    # Jos testiä ei löydy, niin kirjataan virheilmoitus tuloksiin siitä
    if test_function is None:
      results.append({
        "test_id": test_name,
        "test_name": test_name,
        "status": "UNKNOWN",
        "message": "Tuntematon testi",
        "details": {}
      })
      continue

    # Suoritetaan testi
    try:
      result = test_function()
      results.append(result)
    except Exception as error:
      # Jos testi esim. kaatuu niin tallennetaan virheen tiedot
      results.append({
        "test_id": test_name,
        "test_name": test_name,
        "status": "UNKNOWN",
        "message": f"Testin suorittaminen epäonnistui: {error}",
        "details": {}
      })

  # Palautetaan testiajon yhteenveto yksilöllisellä id:llä ja testi suoritus kellonajalla
  return {
    "run_id": str(uuid4()),
    "timestamp": datetime.now().astimezone().isoformat(),
    "results": results
  }

# Testien tulosten tallennus tiedostoon JSON muodossa
def save_test_results(test_run):
  # Selvitetään juurikansio ja polku data kansiolle
  project_folder = Path(__file__).resolve().parent.parent
  data_folder = project_folder / "data"

  # Jos data kansiota ei ole luodaan se
  data_folder.mkdir(parents=True, exist_ok=True)

  # TEhdään tiedosto nimi käyttäen testiajon id:tä
  filename = (
    data_folder / f"test_results_{test_run['run_id']}.json"
  )

  # Kirjoitetaan JSON tiedostoon tulokset
  with filename.open("w", encoding="utf-8") as file:
    json.dump(
      test_run,
      file,
      indent=4,
      ensure_ascii=False
    )

  # aplautetaan tiedoston polku
  return filename