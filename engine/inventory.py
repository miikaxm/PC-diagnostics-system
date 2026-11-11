import json
import platform
import socket
from datetime import datetime
from pathlib import Path

import cpuinfo
import psutil

# Tietojen keräys koneesta
def collect_hardware_info():
  memory = psutil.virtual_memory()
  processor = cpuinfo.get_cpu_info()

  information = {
    "timestamp": datetime.now().astimezone().isoformat(),
    "hostname": socket.gethostname(),
    "operating_system": platform.system(),
    "os_version": platform.release(),
    "architecture": platform.machine(),
    "processor": processor.get("brand_raw", "Unknown"),
    "cpu_cores": psutil.cpu_count(logical=False),
    "cpu_threads": psutil.cpu_count(logical=True),
    "ram_total_gb": round(memory.total / (1024 ** 3), 2),
  }

  return information

# Tietojen tallennus JSON tiedostoon /data kansioon
def save_hardware_info(information):
  project_folder = Path(__file__).resolve().parent.parent
  data_folder = project_folder / "data"

  data_folder.mkdir(parents=True, exist_ok=True)

  filename = data_folder / "hardware_info.json"

  with filename.open("w", encoding="utf-8") as file:
    json.dump(information, file, indent=4, ensure_ascii=False)

  return filename