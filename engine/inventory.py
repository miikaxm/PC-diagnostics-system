import json
import platform
import socket
import subprocess
from datetime import datetime
from pathlib import Path

import cpuinfo
import psutil

PROJECT_FOLDER = Path(__file__).resolve().parent.parent

def bytes_to_gb(value):
  if value is None:
    return None
  return round(int(value) / (1024 ** 3), 2)

def run_command(command):
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

    if result.returncode != 0:
      return None

    return result.stdout.strip()

  except(OSError, subprocess.TimeoutExpired):
    return None

def read_linux_file(filename):
  try:
    value = Path(filename).read_text(
      encoding="utf-8"
    ).strip()

    return value or None

  except(OSError, UnicodeError):
    return None

def windows_cim(class_name, properties):
  script = (
    "[Console]::OutputEncoding = "
    "[System.Text.UTF8Encoding]::new($false); "
    f"Get-CimInstance -ClassName {class_name} | "
    f"Select-Object {','.join(properties)} | "
    "ConvertTo-Json -Depth 4 -Compress"
  )

  output = run_command([
    "powershell.exe",
    "-NoProfile",
    "-NonInteractive",
    "-Command",
    script
  ])

  if not output:
    return []

  try:
    data = json.loads(output)

    if isinstance(data, dict):
      return [data]

    if isinstance(data, list):
      return data

  except json.JSONDecodeError:
    pass

  return []

def get_basic_info():
  return {
    "hostname": socket.gethostname(),
    "architecture": platform.machine(),
    "running_os": platform.system(),
    "os_version": platform.platform()
  }

def get_cpu_info():
  processor = cpuinfo.get_cpu_info()

  return {
    "model": processor.get("brand_raw"),
    "manufacturer": processor.get("vendor_id_raw"),
    "physical_cores": psutil.cpu_count(logical=False),
    "logical_threads": psutil.cpu_count(logical=True)
  }

def get_memory_info():
  memory = psutil.virtual_memory()

  return {
    "total_gb": bytes_to_gb(memory.total),
    "modules": []
  }

def get_network_info():
  return list(psutil.net_if_addrs().keys())

def get_battery_info():
  battery = psutil.sensors_battery()

  return {
    "detected": True if battery else None
  }

def get_windows_hardware():
  computer = windows_cim(
    "Win32_ComputerSystem",
    ["Manufacturer", "Model"]
  )

  board = windows_cim(
    "Win32_BaseBoard",
    ["Manufacturer", "Product"]
  )

  bios = windows_cim(
    "Win32_BIOS",
    ["Manufacturer", "SMBIOSBIOSVersion"]
  )

  memory_modules = windows_cim(
    "Win32_PhysicalMemory",
    ["Manufacturer", "PartNumber", "Capacity", "Speed"]
  )

  graphics = windows_cim(
    "Win32_VideoController",
    ["Name"]
  )

  disks = windows_cim(
    "Win32_DiskDrive",
    ["Model", "Size", "InterfaceType"]
  )

  return {
    "computer": {
      "manufacturer": (
        computer[0].get("Manufacturer")
        if computer else None
      ),
      "model": (
        computer[0].get("Model")
        if computer else None
      )
    },

    "motherboard": {
      "manufacturer": (
        board[0].get("Manufacturer")
        if board else None
      ),
      "model": (
        board[0].get("Product")
        if board else None
      )
    },

    "bios": {
      "manufacturer": (
        bios[0].get("Manufacturer")
        if bios else None
      ),
      "version": (
        bios[0].get("SMBIOSBIOSVersion")
        if bios else None
      )
    },

    "memory_modules": [
      {
        "manufacturer": module.get("Manufacturer"),
        "model": module.get("PartNumber"),
        "size_gb": bytes_to_gb(
          module.get("Capacity")
        ),
        "speed_mt_s": module.get("Speed")
      }
      for module in memory_modules
    ],

    "graphics_cards": [
      {"model": card.get("Name")}
      for card in graphics
    ],

    "storage_devices": [
      {
        "model": disk.get("Model"),
        "size_gb": bytes_to_gb(disk.get("Size")),
        "interface": disk.get("InterfaceType")
      }
      for disk in disks
    ]
  }

def get_linux_hardware():
  base = "/sys/class/dmi/id"

  computer = {
    "manufacturer": read_linux_file(
      f"{base}/sys_vendor"
    ),
    "model": read_linux_file(
      f"{base}/product_name"
    )
  }

  motherboard = {
    "manufacturer": read_linux_file(
      f"{base}/board_vendor"
    ),
    "model": read_linux_file(
      f"{base}/board_name"
    )
  }

  bios = {
    "manufacturer": read_linux_file(
      f"{base}/bios_vendor"
    ),
    "version": read_linux_file(
      f"{base}/bios_version"
    )
  }

  storage_devices = []

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
      devices = json.loads(output).get(
        "blockdevices", []
      )

      for device in devices:
        if device.get("type") != "disk":
          continue

        storage_devices.append({
          "name": device.get("name"),
          "model": device.get("model"),
          "size_gb": bytes_to_gb(
            device.get("size")
          ),
          "interface": device.get("tran")
        })

    except (ValueError, TypeError):
      pass

  graphics_cards = []

  pci_output = run_command(["lspci"])

  if pci_output:
    for line in pci_output.splitlines():
      if any(
        label in line
        for label in (
          "VGA compatible controller",
          "3D controller",
          "Display controller"
        )
      ):
        graphics_cards.append({
          "model": line
        })

  return {
    "computer": computer,
    "motherboard": motherboard,
    "bios": bios,
    "memory_modules": [],
    "graphics_cards": graphics_cards,
    "storage_devices": storage_devices
  }

def collect_hardware_info():
  system = platform.system()

  information = {
    "timestamp": datetime.now().astimezone().isoformat(),
    "basic": get_basic_info(),
    "cpu": get_cpu_info(),
    "memory": get_memory_info(),
    "network_interfaces": get_network_info(),
    "battery": get_battery_info()
  }

  if system == "Windows":
    hardware = get_windows_hardware()

  elif system == "Linux":
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

  information["computer"] = hardware["computer"]
  information["motherboard"] = hardware["motherboard"]
  information["bios"] = hardware["bios"]

  information["memory"]["modules"] = hardware["memory_modules"]
  information["graphics_cards"] = hardware["graphics_cards"]
  information["storage_devices"] = hardware["storage_devices"]

  return information

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