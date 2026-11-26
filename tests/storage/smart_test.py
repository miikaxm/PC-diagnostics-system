
import json
import os
import platform
import stat
import subprocess

from engine.storage_devices import get_selected_disk

def run_smart_test(device_path=None):
  # Tulokset
  result = {
    "test_id": "smart",
    "test_name": "Storage SMART Health",
    "status": "UNKNOWN",
    "message": "",
    "details": {}
  }

  # Chekataan ollaanko linuxissa
  if platform.system() != "Linux":
    result["message"] = "SMART-testi vaatii Linuxin"
    return result

  if not device_path:
    result["message"] = "SMART-testille ei valittu levyä"
    return result

  try:
    # Varmistetaan että levy on hyvä
    selected_disk = get_selected_disk(device_path)
    device_path = selected_disk["id"]

  except (ValueError, OSError, RuntimeError) as error:
    result["message"] = (
      f"SMART-testin levyvalinta epäonnistui: {error}"
    )
    return result

  try:
    # Haetaan laitteen polku ja infot
    device_path = os.path.realpath(device_path)

    # Jos laitepolku ei ala /dev/ ilmoitetaan siitä
    if not device_path.startswith("/dev/"):
      raise ValueError("Virheellinen laitepolku")

    device_info = os.stat(device_path)

    # Tarkistaa onko laite lohkolaite eli esim. kiintoly, ssd, tai usb
    if not stat.S_ISBLK(device_info.st_mode):
      raise ValueError("Kohde ei ole lohkolaite")

  # Varaudutaan OsErroriin ja ValueErroriin
  # Ilmoitetaan Jos levyä ei löydy
  except (OSError, ValueError):
    result["message"] = "Testattavaa levyä ei löytynyt"
    return result

  try:
    # Ajetaan testi sovellus komenolla
    completed = subprocess.run(
      ["/usr/sbin/smartctl", "--all", "--json", device_path],
      capture_output=True,
      text=True,
      timeout=60,
      check=False
    )

    # Testin lopputuloksen data
    data = json.loads(completed.stdout)

    # Testin lopputuloksen exit_code
    exit_code = completed.returncode

    # Otetaan smart_status ja testin passed tulos talteen
    smart_status = data.get("smart_status") or {}
    passed = smart_status.get("passed")

    # Otetaan nvme terveys data talteen
    nvme_health = data.get(
      "nvme_smart_health_information_log"
    ) or {}

    critical_warning = nvme_health.get("critical_warning")

    # Täydennetään testin datalla tulosten tiedot
    result["details"] = {
      "device": device_path,
      "model": data.get("model_name"),
      "serial_number": data.get("serial_number"),
      "smart_passed": passed,
      "nvme_critical_warning": critical_warning,
      "smartctl_exit_code": exit_code,
    }

    # Exit koodin bitit 8 (SMART vika) ja 16 (prefail varoitus) tarkoittavat levyvikaa ilmoitetaan niistä tulokseen
    if exit_code >= 0 and exit_code & (8 | 16):
      result["status"] = "FAIL"
      result["message"] = "Levy ilmoittaa SMART-viasta"

    # Jos testin antama passed parametri on False ilmoitetaan että testit epäonnistuivat (FAIL)
    elif passed is False:
      result["status"] = "FAIL"
      result["message"] = "SMART-terveystarkistus epäonnistui"

    # Negatiivinen exit koodi meinaa että testin prosessi keskeytyi
    # Exit koodin bittien tarkistus 1 (komentovirhe), 2 (laite ei aukea tai ei ole oikeuksia) ja 4 (SMART komento epäonnistui)
    elif exit_code < 0 or exit_code & (1 | 2 | 4):
      result["status"] = "UNKNOWN"
      result["message"] = (
        "SMART-tietoja ei saatu luettua luotettavasti"
      )

    # bitti 32 (aiemmin ylittynyt raja-arvo), 64 (virhelokimerkintä), 128 (jokin itsetestin virhe)
    elif exit_code & (32 | 64 | 128):
      result["status"] = "WARNING"
      result["message"] = ("SMART-historiassa havaittiin varoituksia")

    # Jos saadaan testin NVMe terveyden tiedoista jokin kriittinen varoitus niin varoitetaan siitä tuloksessa
    elif isinstance(critical_warning, int) and critical_warning != 0:
      result["status"] = "WARNING"
      result["message"] = "NVMe-levy ilmoittaa varoituksesta"

    # Jos testi antaa tuloksissa "passed" parametrin hyväksytyksi niin ilmoitetaan että kaikki OK 
    elif passed is True:
      result["status"] = "PASS"
      result["message"] = "SMART-terveystila on hyväksytty"

    # Muulloin ilmoitetaan että terveydentilaa ei voitu määrittää
    else:
      result["status"] = "UNKNOWN"
      result["message"] = "SMART-terveystilaa ei voitu määrittää"

  # Oletetaan FileNotFoundErroria ilmoitetaan tuloksessa (Ohjelma ei löytynyt)
  except FileNotFoundError:
    result["message"] = "smartctl-ohjelmaa ei löytynyt"

  # Oletetaan TimeoutExpired erroria ilmoitetaan tuloksessa (Testi aikakatkaistiin)
  except subprocess.TimeoutExpired:
    result["message"] = "SMART-testi aikakatkaistiin"

  # Oletetaan JSONDecodeErroria ilmoitetaan tuloksessa (Testin tuloksesta ei saatu kelvollista JSONia)
  except json.JSONDecodeError:
    result["message"] = "SMART-tulos ei ollut kelvollista JSONia"

  # Palautetaan tulokset
  return result