import os
import platform
import shutil
import signal
import subprocess
import time

import psutil

# Ram testi
def run_memory_stress_test(memory_mb=None, loops=2, timeout_seconds=1800):
  # Tulokset
  result = {
    "test_id": "memory_stress",
    "test_name": "RAM Memory Test (memtester)",
    "status": "UNKNOWN",
    "message": "",
    "details": {}
  }

  # Checkataan ollaanko linuxissa
  if platform.system() != "Linux":
    result["message"] = "Muistitesti vaatii Linuxin"
    return result

  # Checkataan onko järjestelmänvaljovan oikeudet
  if os.geteuid() != 0:
    result["message"] = "Muistitesti vaatii järjestelmänvaljovan oikeudet"
    return result

  # etsitään ohjelma
  memtester = shutil.which("memtester")

  if not os.path.isfile(memtester):
    result["message"] = "memtester-ohjelmaa ei löytynyt"
    return result

  # Jos memtestiä ei löydy ilmoitetaan siitä
  if memtester is None:
    result["message"] = "memterter ei ole asennettu"
    return result

  #Tarkistetaan asetukset. Testikierrosten määrä
  if type(loops) is not int or not 1 <= loops <= 10:
    result["message"] = "Virheellinen testikierrosten määrä"
    return result

  # Aikaraja
  if type(timeout_seconds) is not int or not 60 <= timeout_seconds <= 7200:
    result["message"] = "Virheellinen aikaraja"
    return result

  # Tarkistetaan paljon ramia on käytettävissä
  memory = psutil.virtual_memory()
  available_mb = int(memory.available / (1024 ** 2))

  # Testiin 50% käytettävästä ramista
  safe_limit_mb = min(
    available_mb // 2,
    available_mb - 1024,
    4096
  )

  if memory_mb is None:
    memory_mb = safe_limit_mb

  # Jos muistia ei ole tarpeeksi tai se ei palauta lukua niin ilmoitetaan.
  if type(memory_mb) is not int or memory_mb < 128:
    result["message"] = "Testiin ei ole riittävästi käytettävissä olevaa RAM-muistia"
    return result

  # Jos muisti ylittää turvarajan ilmoitetaan
  if memory_mb > safe_limit_mb:
    result["message"] = "Valittu muistimäärä ylittää turvallisuusrajan"
    return result

  # Komento memtesterille
  command = [
    memtester,
    f"{memory_mb}M",
    str(loops)
  ]

  # Tulosten tiedot alustavasti
  result["details"]= {
    "memory_mb": memory_mb,
    "available_memory_mb": available_mb,
    "loops": loops,
    "timeout_seconds": timeout_seconds,
    "exit_code": None,
    "duration_seconds": None,
    "output": ""
  }

  # Alustetaan process muuttuja ja aloitus aika
  process = None
  start_time = time.monotonic()

  # Ajetaan komento
  try:
    process = subprocess.Popen(
      command,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      text=True,
      errors="replace",
      start_new_session=True
    )

    # Tallennetaan ohjelman tulosteet ja tarkistetaan jääkö ohjelma jumiin
    stdout, stderr = process.communicate(timeout=timeout_seconds)

    # Tallennetaan ohjelman exit_code
    exit_code = process.returncode
    # Testiin kulunut aika
    elapsed = round(time.monotonic() - start_time, 2)

    # Päivitetään tiedot
    result["details"].update({
      "exit_code": exit_code,
      "duration_seconds": elapsed,
      "output": (stdout + "\n" + stderr)[-20000:]
    })

    # Jos exit_code on 0 niin kaikki OK
    if exit_code == 0:
      result["status"] = "PASS"
      result["message"] = (
        "RAM-muistin testikierrokset valmistuivat "
        "ilman havaittuja virheitä"
      )

    # Jos exit coden bitti 2 tai 4 on asetettu niin testissä havaittiin muistivirheitä
    elif exit_code > 0 and exit_code & (2 | 4):
      result["status"]= "FAIL"
      result["message"] = (
        "Memtester havaitsi muistivirheitä"
      )

    # Jos exit coden bitti 1 on asetettu niin testissä havaittiin muistin varaamiseen tai lukitsemiseen liittyviä ongelmia
    elif exit_code > 0 and exit_code & 1:
      result["status"] = "UNKNOWN"
      result["message"] = (
        "Muistin varaaminen tai lukitseminen "
        "epäonnistui"
      )

    # Muulloin ilmoitetaan että muistitesti päättyi odottamattomasti
    else :
      result["status"] = "UNKNOWN"
      result["message"] = (
        "Muistitesti päättyi odottamattomasti"
      )

  # Jos ylitetään aikaraja keskeytetään prosessi
  except subprocess.TimeoutExpired:
    if process is not None:
      # Lopetetaan memtesterin prosessi
      os.killpg(process.pid, signal.SIGKILL)
      stdout, stderr = process.communicate()

      # Tallennetaan testin tulosteen viimeiset 20000 merkiä
      result["details"]["output"] = (
        stdout + "\n" + stderr
      )[-20000:]

    result["status"] = "WARNING"
    result["message"] = "Muistitestin aikaraja ylittyi"
    # Testiin kulunut aika
    result["details"]["duration_seconds"] = round(
      time.monotonic() - start_time, 2
    )

  # OsError käsittely
  except OSError as error:
    result["status"] = "UNKNOWN"
    result["message"] = (
      f"Muistitestin suoritus epäonnistui: {error}"
    )

  # Palautetaan testin tulokset
  return result



