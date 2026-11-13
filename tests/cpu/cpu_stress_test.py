import os
import platform
import shutil
import signal
import subprocess
import time

def run_cpu_stress_test():
  # lyhyt alustava rasitus testi

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

  # Asetetaan testin kesto (sek), työprosessit sekä cpu:n kuorma (alustavasti nyt 50%) 
  duration = 10
  workers = 1
  cpu_load = 50

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


  try:
    # Käynnistetään testi ohjelma
    process = subprocess.Popen(
      command,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      text=True,
      start_new_session=True
    )

    # Odotetaan max 20sec testin valmistumiseksi ja sen jälkeen tallennetaan tulosteet stdout, stderr muuttujiin
    stdout, stderr = process.communicate(timeout=20)
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
    # Jos koodi on jokin muu niin testissä ilmeni jotain häikkää
    else:
      result["status"] = "WARNING"
      result["message"] = (
        "CPU-rasitustesti ei valmistunut normaalisti "
        "Tarkista stress-ng:n tuloste."
      )

  except subprocess.TimeoutExpired:
    # pysäytä kaikki prosessit jos prosessissa menee liian pitkään
    if process is not None:
      os.killpg(process.pid, signal.SIGKILL)
      process.communicate()

    # Ilmoitetaan tulokseen että testissä meni liian pitkään
    result["status"] = "WARNING"
    result["message"] = "CPU-testi ylitti aikarajan"

  # OSError checkkaus jos tässä häikkää ilmoitetaan tuloksen viestiin
  except OSError as error:
    result["message"] = f"CPU-testin käynnistys epäonnistui: {error}"

  # Palautetaan tulokset
  return result