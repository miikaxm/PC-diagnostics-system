import json
import platform
import socket
import subprocess
from datetime import datetime
from pathlib import Path

import cpuinfo
import psutil

# Tallennetaan projekti tiedoston polku eli tämä PC-Diagnostics kansio muuttujaan
PROJECT_FOLDER = Path(__file__).resolve().parent.parent

# Apufunktio megatavujen muutoksessa gigatavuihin
def bytes_to_gb(value):
  if value is None:
    return None
  return round(int(value) / (1024 ** 3), 2)

# Apufunktio komennon ajamiselle
def run_command(command):
  # Suorittaa komennon 15 sekunnin aikakatkaisulla ja palauttaa komennon tulosteen merkkijonona tai None arvona, jos komento epäonnistuu tai aikakatkaistaan
  try:
    result = subprocess.run(
      command,
      capture_output=True,
      text=True,
      encoding="utf-8",
      errors="replace",
      timeout=15,
      check=False
    )

    # Jos koodi ei ole 0 niin palautetaan None koska komento epäonnistui tässä tapauksessa
    if result.returncode != 0:
      return None

    # Ylimääräiset rivinvaihdot pois
    return result.stdout.strip()

  # Varaudutaan mahdollisiin virheisiin OSError, subprocess.TimeoutExpired esim. komentoa ei löytynyt, oikeudet puuttuu tai 15 sek aikaraja ylittyi
  except(OSError, subprocess.TimeoutExpired):
    return None

# Linux tiedoston luku apufunktio
def read_linux_file(filename):
  try:
    value = Path(filename).read_text(
      encoding="utf-8"
    ).strip()

    return value or None

  except(OSError, UnicodeError):
    return None

# Perustietojen haku: koneen nimi, suoritinperhe esim: AMD64, käyttöjärjestelmä, ja tarkempi versio käyttöjärjestelmästä
def get_basic_info():
  return {
    "hostname": socket.gethostname(),
    "architecture": platform.machine(),
    "running_os": platform.system(),
    "os_version": platform.platform()
  }

# Cpu info:n haku
def get_cpu_info():
  # Haetaan cpu tiedot
  processor = cpuinfo.get_cpu_info()

  # Palautetaan cpu:n malli, valmistaja, ytimien ja säikeiden määrä
  return {
    "model": processor.get("brand_raw"),
    "manufacturer": processor.get("vendor_id_raw"),
    "physical_cores": psutil.cpu_count(logical=False),
    "logical_threads": psutil.cpu_count(logical=True)
  }

# RAM muistin tiedot
def get_memory_info():
  # haetaan koneesta ram muistit
  memory = psutil.virtual_memory()

  # Palautetaan ram muistin määrä gigatavuissa sekä moduulit (vielä tässä vaiheessa tyhjä lista)
  return {
    "total_gb": bytes_to_gb(memory.total),
    "modules": []
  }

# Netti tiedot
def get_network_info():
  # Palauttaa listan verrkosovittimista
  return list(psutil.net_if_addrs().keys())

# Akun tiedot esim. läppäreissä (Ei vielä testattu)
def get_battery_info():
  battery = psutil.sensors_battery()

  # Jos akkua ei havaittua palautetaan arvoksi None
  return {
    "detected": True if battery else None
  }

# Tarkemmat laitetiedot linux komentojen avulla
def get_linux_hardware():
  base = "/sys/class/dmi/id"

  # Tietokoneen valmistaja ja malli
  computer = {
    "manufacturer": read_linux_file(
      f"{base}/sys_vendor"
    ),
    "model": read_linux_file(
      f"{base}/product_name"
    )
  }

  # Emolevyn valmistaja ja malli
  motherboard = {
    "manufacturer": read_linux_file(
      f"{base}/board_vendor"
    ),
    "model": read_linux_file(
      f"{base}/board_name"
    )
  }

  # bioksen valmistaja ja versio
  bios = {
    "manufacturer": read_linux_file(
      f"{base}/bios_vendor"
    ),
    "version": read_linux_file(
      f"{base}/bios_version"
    )
  }

  # Tallennus laitteet (tässä vaiheessa vielä tyhjä lista)
  storage_devices = []

  # Ajetaan linux komento joka hakee tallennuslaitteet json muodossa
  output = run_command([
    "lsblk",
    "--json",
    "--bytes",
    "--nodeps",
    "--output",
    "NAME,MODEL,SIZE,TRAN,TYPE"
  ])

  if output:
    try:
      # Poimitaan laitelista JSON-datasta
      devices = json.loads(output).get(
        "blockdevices", []
      )

      # Käydään jokainen laite läpi
      for device in devices:
        # Jos laite ei ole tyyppiä "disk" niin mennään seuraavaan laitteesseen
        if device.get("type") != "disk":
          continue

        # Jos laite on tyyppiä disk lisätään se ja sen tiedot "storage_devices" listaan
        storage_devices.append({
          "name": device.get("name"),
          "model": device.get("model"),
          "size_gb": bytes_to_gb(
            device.get("size")
          ),
          "interface": device.get("tran")
        })

    # Oletetaan ValueErroria ja TypeErroria
    except (ValueError, TypeError):
      pass

  # Lista GPu:lle
  graphics_cards = []

  # Haetaan lista PCI- väylän laitteista
  pci_output = run_command(["lspci"])

  # Tarkistetaan palautettiinko mitään
  if pci_output:
    # Käydään läpi rivi kerrallaan
    for line in pci_output.splitlines():
      # Etsitään rivejä jotka viittaa näytönohjaimeen tai johonkin muuhun grafiikka piiriin
      if any(
        label in line
        for label in (
          "VGA compatible controller",
          "3D controller",
          "Display controller"
        )
      ):
      # lisätään graphics_cards listaan malli
        graphics_cards.append({
          "model": line
        })

  # Palautetaan tiedot
  return {
    "computer": computer,
    "motherboard": motherboard,
    "bios": bios,
    "memory_modules": [],
    "graphics_cards": graphics_cards,
    "storage_devices": storage_devices
  }

# Tietojen kasaus yhteen
def collect_hardware_info():
  # Järjestelmä
  system = platform.system()

  # Infot
  information = {
    "timestamp": datetime.now().astimezone().isoformat(),
    "basic": get_basic_info(),
    "cpu": get_cpu_info(),
    "memory": get_memory_info(),
    "network_interfaces": get_network_info(),
    "battery": get_battery_info()
  }

  # Jos käytössä linux niin haetaan funktiolla tarkemmat tiedot muuten jätetään ne hakematta
  if system == "Linux":
    # Tiedot hardware muuttujaan
    hardware = get_linux_hardware()

  else:
    hardware = {
      "computer": {},
      "motherboard": {},
      "bios": {},
      "memory_modules": [],
      "graphics_cards": [],
      "storage_devices": []
    }

  # Asetetaan infoksi linux komennoilla haetut tarkat tiedot
  information["computer"] = hardware["computer"]
  information["motherboard"] = hardware["motherboard"]
  information["bios"] = hardware["bios"]

  information["memory"]["modules"] = hardware["memory_modules"]
  information["graphics_cards"] = hardware["graphics_cards"]
  information["storage_devices"] = hardware["storage_devices"]

  # Palautetaan tiedot
  return information

# Tietojen tallennus JSON tiedostoon
def save_hardware_info(information):
  data_folder = PROJECT_FOLDER / "data"
  data_folder.mkdir(parents=True, exist_ok=True)

  filename = data_folder / "hardware_info.json"

  with filename.open("w", encoding="utf-8") as file:
    json.dump(
      information,
      file,
      indent=4,
      ensure_ascii=False
    )

  return filename