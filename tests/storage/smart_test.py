import json
import os
import platform
import stat
import subprocess

def run_smart_test():
  result = {
    "test_id": "storage_smart",
    "test_name": "Storage SMART Health",
    "status": "UNKNOWN",
    "message": "",
    "details": {}
  }

  if platform.system() != "Linux":
    result["message"] = "SMART-testi vaatii Linuxin"
    return result

  device = os.environ.get("PC_DIAGNOSTICS_SMART_DEVICE")

  if not device:
    result["message"] = "Testattavaa levyä ei ole valittu"
    return result

  try:
    device_path = os.path.realpath(device)
    device_info = os.stat(device_path)

    if not device_path.startswith("/dev/"):
      raise ValueError("Virheellinen laitepolku")

    if not stat.S_ISBLK(device_info.st_mode):
      raise ValueError("Kohde ei ole lohkolaite")

  except (OSError, ValueError):
    result["message"] = "Testattavaa levyä ei löytynyt"
    return result

  try:
    completed = subprocess.run(
      ["smartctl", "--all", "--json", device_path],
      capture_output=True,
      text=True,
      timeout=60,
      check=False
    )

    data = json.loads(completed.stdout)

    exit_code = completed.returncode

    smart_status = data.get("smart_status", {})
    passed = smart_status.get("passed")

    nvme_health = data.get(
      "nvme_smart_helath_information_log", {}
    )

    critical_warning = nvme_health.get("critical_warning")

    result["details"] = {
      "device": device_path,
      "model": data.get("model_name"),
      "serial_number": data.get("serial_number"),
      "smart_passed": passed,
      "nvme_critical_warning": critical_warning,
      "smartctl_exit_code": exit_code,
    }

    if exit_code >= 0 and exit_code & (8 | 16):
      result["status"] = "FAIL"
      result["message"] = "Levy ilmoittaa SMART-viasta"

    elif passed is False:
      result["status"] = "FAIL"
      result["message"] = "SMART-terveystarkistus epäonnistui"

    elif exit_code < 0 or exit_code & (1 | 2 | 4):
      result["message"] = (
        "SMART-tietoja ei saatu luettua luotettavasti"
      )

    elif exit_code & (32 | 64 | 128):
      result["status"] = "WARNING"
      result["message"] = ("SMART-historiassa havaittiin varoituksia")

    elif isinstance(critical_warning, int) and critical_warning != 0:
      result["status"] = "WARNING",
      result["message"] = "NVMe-levy ilmoittaa varoituksesta"

    elif passed is True:
      result["status"] = "PASS"
      result["message"] = "SMART-terveystila on hyväksytty"

    else:
      result["message"] = "SMART-terveystilaa ei voitu määrittää"

  except FileNotFoundError:
    result["message"] = "smartctl-ohjelmaa ei löytynyt"

  except subprocess.TimeoutExpired:
    result["message"] = "SMART-testi aikakatkaistiin"

  except json.JSONDecodeError:
    result["message"] = "SMART-tulos ei ollut kelvollista JSONia"

  return result
