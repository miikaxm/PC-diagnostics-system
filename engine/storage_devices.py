import json
import os
import re
import subprocess
from pathlib import Path

# Debianin omien osioiden liitospisteet (mahdollisesti pitää vielä vaihtaa)
PROTECTED_MOUNTS = {
  "/",
  "/boot/efi",
  "/diagnostics-data"
}

def has_protected_mount(device):
  # Tarkistetaan levyn ja sen osioiden liitospisteet
  mounts = device.get("mountpoints") or []

  if isinstance(mounts, str):
    mounts = [mounts]

  if any(mount in PROTECTED_MOUNTS for mount in mounts):
    return True

  for child in device.get("children", []):
    if has_protected_mount(child):
      return True

  return False

def get_stable_device_path(device_path):
  # Etsitään levylle pysyvämpi /dev/disk/by-id polku
  by_id_folder = Path("/dev/disk/by-id")

  if not by_id_folder.is_dir():
    return device_path

  aliases = []

  for link in by_id_folder.iterdir():
    if not link.is_symlink():
      continue

    # Osion tunnistetta ei käytetä koko levylle:
    if re.search(r"-part\d+$", link.name):
      continue

    if os.path.realpath(link) == os.path.realpath(device_path):
      aliases.append(link)

  # Suositaan levyn yksilöiviä tunnisteita
  prefixes = (
    "wwn-",
    "nvme-eui.",
    "nvme-uuid.",
    "nvme-",
    "ata-",
    "scsi-",
    "usb-"
  )

  for prefix in prefixes:
    matches = sorted(
      link for link in aliases
      if link.name.startswith(prefix)
    )

    if matches:
      return str(matches[0])

  return device_path

def list_smart_disks():
  # Haetaan fyysiset levyt ja niidei osiopuu
  completed = subprocess.run(
    [
      "lsblk",
      "--json",
      "--bytes",
      "--paths",
      "--tree",
      "--output",
      "NAME,TYPE,MODEL,SIZE,TRAN,MOUNTPOINTS"
    ],
    capture_output=True,
    text=True,
    timeout=10,
    check=True
  )

  data = json.loads(completed.stdout)
  devices = data.get("blockdevices", [])

  # jos debian juuriosiota ei tunnisteta niin levyvalinta estetään turvallisuussyistä
  if not any(
    has_root_mount(device)
    for device in devices
  ):
    raise RuntimeError(
      "Debianin käynnistyslevyä ei voitu tunnistaa"
    )

  disks = []

  for device in devices:
    if device.get("type") != "disk":
      continue

    # ohitetaan debianin käynnistyslevy
    if has_protected_mount(device):
      continue

    device_path = device.get("name")

    if not device_path:
      continue

    stable_path = get_stable_device_path(device_path)

    size_bytes = device.get("size")
    size_gib = (round(size_bytes / (1024 ** 3), 2) if isinstance(size_bytes, (int, float)) else None)

    disks.append({
      "id": stable_path,
      "device": device_path,
      "model": device.get("model") or "Tuntematon levy",
      "size_gib": size_gib,
      "interface": device.get("tran") or "tuntematon"
    })

  return disks

def has_root_mount(device):
  mounts = device.get("mountpoints") or []

  if isinstance(mounts, str):
    mounts = [mounts]

  if "/" in mounts:
    return True

  return any(
    has_root_mount(child)
    for child in device.get("children", [])
  )

def get_selected_disk(device_id):
  # Selaimesta saatu tunniste hyväksytään vain jos se löytyy levylistasta
  if not isinstance(device_id, str):
    raise ValueError("Virheellinen levyn tunniste")

  for disk in list_smart_disks():
    if disk["id"] == device_id:
      return disk

  raise ValueError(
    "Valittua levyä ei löytynyt tai sen käyttö on estetty"
  )

