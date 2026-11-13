import os
import platform
import shutil
import signal
import subprocess
import time

def run_cpu_stress_test():
  # lyhyt alustava rasitus testi

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

  if stress_ng is None:
    result["message"] = "stress-ng ei ole asennettu"
    return result

  duration = 10
  workers = 1
  cpu_load = 50

  command = [
    stress_ng,
    "--cpu", str(workers),
    "--cpu-load", str(cpu_load),
    "--timeout", f"{duration}s",
    "--verify",
    "--metrics-brief"
  ]

  process = None
  start_time = time.monotonic()

  try:
    process = subprocess.Popen(
      command,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      text=True,
      start_new_session=True
    )

    stdout, stderr = process.communicate(timeout=20)
    elapsed = round(time.monotonic() - start_time, 2)

    result["details"] = {
      "duration_seconds": elapsed,
      "workers": workers,
      "target_cpu_load_percent": cpu_load,
      "exit_code": process.returncode,
      "output": (stdout + "\n" + stderr)[-3000:]
    }

    if process.returncode == 0:
      result["status"] = "PASS"
      result["message"] = (
        "CPU-rasitustesti valmistui ilman "
        "stress-ng:n ilmoittamia virheitä."
      )
    else:
      result["status"] = "WARNING"
      result["message"] = (
        "CPU-rasitustesti ei valmistunut normaalisti "
        "Tarkista stress-ng:n tuloste."
      )

  except subprocess.TimeoutExpired:
    # pysäytä kaikki prosessit
    if process is not None:
      os.killpg(process.pid, signal.SIGKILL)
      process.communicate()

    result["status"] = "WARNING"
    result["message"] = "CPU-testi ylitti aikarajan"

  except OSError as error:
    result["message"] = f"CPU-testin käynnistys epäonnistui: {error}"

  return result