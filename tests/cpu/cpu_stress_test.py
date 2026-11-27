import os
import platform
import shutil
import signal
import subprocess
import time
import json
import math
import re
import threading
import psutil

# Lukee tietokoneen antureista lämpötiloja
def read_temp():
  # Etsitään sensors ohjelma
  sensors = shutil.which("sensors")

  # Jos ohjelmaa ei löydy niin palautetaan tyhjä sanakirja
  if sensors is None:
    return {}

  # haetaan anturien tiedot json muodossa
  completed = subprocess.run(
    [sensors, "-j"],
    capture_output=True,
    text=True,
    timeout=5,
    check=False
  )

  # Tarkistetaan onnistuiko anturitietojen lukeminen
  if completed.returncode != 0:
    raise RuntimeError(
      completed.stderr.strip()
      or "Lämpötila-antureiden lukeminen epäonnistui"
    )

  # Muutetaan JSON sanakirjaksi
  data = json.loads(completed.stdout)
  temperatures = {}

  # Käydään kaikki anturipiirit läpi
  for chip_name, features in data.items():
    if not isinstance(features, dict):
      continue

    # Piirien anturit läpi
    for feature_name, values in features.items():
      if not isinstance(values, dict):
        continue

      # Ja etsitään antureiden lämpötilat
      for field_name, value in values.items():
        if not re.fullmatch(r"temp\d+_input", field_name):
          continue

        # Hyväksytään vain numeroarvot
        if (
          isinstance(value, bool)
          or not isinstance(value, (int, float))
          or not math.isfinite(value)
        ):
          continue

        # Luodaan jokaiselle anturille tunniste
        sensor_id = (
          f"{chip_name}/{feature_name}/{field_name}"
        )

        # Pyöristetaan kahden desimaalin tarkkuudella lämpötila
        temperatures[sensor_id] = round(value, 2)

  # Palautetaan lämpötilat
  return temperatures

def run_cpu_stress_test():
  
  # Tulokset
  result = {
    "test_id": "cpu_stress",
    "test_name": "CPU Stress Test",
    "status": "UNKNOWN",
    "message": "",
    "details": {}
  }

  # chekataan ollaanko linuxissa
  if platform.system() != "Linux":
    result["message"] = "Testi vaatii Linuxin"
    return result

  # Chekataan löytyykö stress-ng koneelta
  stress_ng = shutil.which("stress-ng")

  # Jos stress-ng ei löydy koneelta ilmoitetaan siitä tuloksissa ja palautetaan tulokset
  if stress_ng is None:
    result["message"] = "stress-ng ei ole asennettu"
    return result

  # Asetetaan testin kesto (sek), työprosessit sekä cpu:n kuorma
  duration = 60
  workers = (
    len(os.sched_getaffinity(0))
    if hasattr(os, "sched_getaffinity")
    else (os.cpu_count() or 1)
  )
  cpu_load = 100

  # Testin käynnistyskomento ja parametrit
  command = [
    stress_ng,
    "--cpu", str(workers),
    "--cpu-load", str(cpu_load),
    "--timeout", f"{duration}s",
    "--verify",
    "--metrics-brief"
  ]

  # Process muuttujan alustus ja aloitus ajan tallentaminen
  process = None
  start_time = time.monotonic()

  # Lista mihin tallennetaan rasitustestin aikana otetut lämpötila mittaukset
  samples = []
  # Lista mahdollisille virheille
  monitoring_errors = []
  # Tapahtuma jolla seurantasäikeen suoritus lopetetaan
  stop_monitoring = threading.Event()
  # Alustetaan cpu:n seurantaan käytettävä säe
  monitor_thread = None

  # Seuraa cpu:n käyttöastetta ja lämpötiloja testin aikana
  def monitor_cpu():
    psutil.cpu_percent(interval=None)

    # Jatketaan kunnes testi on päättynyt
    while not stop_monitoring.wait(2):
      # Lasketaan testiin kulunut aika
      elapsed = round(time.monotonic() - start_time, 2)

      # Haetaan cpu:n käyttöaste
      cpu_usage = psutil.cpu_percent(interval=None)

      try:
        # Luetaan lämpötilat
        temperatures = read_temp()

      except(
        OSError,
        ValueError,
        RuntimeError,
        subprocess.TimeoutExpired
      ) as error:
        # Jos jokin virhe tulee vastaan niin käytetään vain tyhjää sanakirjaa
        temperatures = {}

        # Tallennetaan virhe
        if str(error) not in monitoring_errors:
          monitoring_errors.append(str(error))

      # Tallennetaan mittaus ja siihen kulunut aika
      samples.append({
        "elapsed_seconds": elapsed,
        "cpu_usage_percent": round(cpu_usage, 2),
        "temperature_c": temperatures
      })

  try:
    # Käynnistetään testi ohjelma
    process = subprocess.Popen(
      command,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      text=True,
      start_new_session=True
    )

    # Käynnistetään lämpötilojen ja cpu käyttöasteen seuranta
    monitor_thread = threading.Thread(
      target=monitor_cpu,
      daemon=True
    )

    # Aloitetaan mittausten kerääminen testin rinnalla
    monitor_thread.start()

    # Odotetaan max 90sec testin valmistumiseksi ja sen jälkeen tallennetaan tulosteet stdout, stderr muuttujiin
    stdout, stderr = process.communicate(timeout=90)

    # Testiin kulunut aika
    elapsed = round(time.monotonic() - start_time, 2)

    # Tuloksen tiedot osio
    result["details"] = {
      "duration_seconds": elapsed,
      "workers": workers,
      "target_cpu_load_percent": cpu_load,
      "exit_code": process.returncode,
      "output": (stdout + "\n" + stderr)[-3000:]
    }

    # Testin returncode tarkistukset. Koodi 0 = Hyvä
    if process.returncode == 0:
      result["status"] = "PASS"
      result["message"] = (
        "CPU-rasitustesti valmistui ilman "
        "stress-ng:n ilmoittamia virheitä."
      )
    # Koodi 2 niin j otain häikkää ilmeni
    elif process.returncode == 2:
      result["status"] = "FAIL"
      result["message"] = (
        "stress-ng ilmoitti kuormitustyöprosessin "
        "epäonnistumisesta."
      )
    # Koodi 5/6 niin testi keskeytyi poikkeavasti
    elif process.returncode in (5, 6):
      result["status"] = "WARNING"
      result["message"] = (
        "CPU-rasitustesti keskeytyi poikkeavasti. "
        "Tarkista stress-ng:n tuloste."
      )
    else:
      result["status"] = "UNKNOWN"
      result["message"] = (
        "CPU-rasitustestin tulosta ei voitu "
        "määrittää luotettavasti."
      )

  except subprocess.TimeoutExpired:
    # pysäytä kaikki prosessit jos prosessissa menee liian pitkään
    if process is not None:
      try:
        os.killpg(process.pid, signal.SIGKILL)
      except ProcessLookupError:
        pass

      process.communicate()

    # Ilmoitetaan tulokseen että testissä meni liian pitkään
    result["status"] = "WARNING"
    result["message"] = "CPU-testi ylitti aikarajan"

  # OSError checkkaus jos tässä häikkää ilmoitetaan tuloksen viestiin
  except OSError as error:
    result["message"] = f"CPU-testin käynnistys epäonnistui: {error}"

  finally:
    # Ilmoitetaan seurantasäikeelle että testi on loppunut
    stop_monitoring.set()

    # Odotetaan että lämpöjenseuranta loppuu
    if monitor_thread is not None:
      monitor_thread.join(timeout=7)

    # kerätään kaikki mitatut cpu:n käyttöasteet
    cpu_values = [
      sample["cpu_usage_percent"]
      for sample in samples
      if sample["elapsed_seconds"] >= 1
    ]

    sensors_data = {}

    # Käydään testin aikana kerätyt mittaukset läpi
    for sample in samples:
      # Erotellaan jokaisen anturin lämpötilat omiin listoihinsa
      for sensor_id, temperature in sample[
        "temperature_c"
      ].items():
        if sensor_id not in sensors_data:
          sensors_data[sensor_id] = []

        sensors_data[sensor_id].append(temperature)

    temperature_summary = {}

    for sensor_id, values in sensors_data.items():
      # Tallennetaan ensimmäinen, viimeinen, pienin, suurin ja keskimääräinen lämpötila
      temperature_summary[sensor_id] = {
        "start_c": values[0],
        "end_c": values[-1],
        "min_c": min(values),
        "max_c": max(values),
        "average_c": round(
          sum(values) / len(values),
          2
        ),
        "sample_count": len(values)
      }

    # Lisätään mittaustulokset testin tarkempiin tietoihin
    result["details"].update({
      "cpu_average_percent": (
        round(sum(cpu_values) / len(cpu_values), 2)
        if cpu_values else None
      ),
      "cpu_max_percent": (
        max(cpu_values) if cpu_values else None
      ),
      "temperature_sensors": temperature_summary,
      "monitoring_samples": samples,
      "monitoring_errors": monitoring_errors
    })

  # Palautetaan tulokset
  return result