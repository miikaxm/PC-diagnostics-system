import psutil

def run_memory_test():
  memory = psutil.virtual_memory()

  total_gb = round(memory.total / (1024 ** 3), 2)
  available_gb = round(memory.available / (1024 ** 3), 2)

  if memory.total <= 0:
    status = "UNKNOWN"
    message = "RAM-muistin tietoja ei saatu luettua"
  else:
    status = "PASS"
    message = "RAM-muistin perustiedot luettu onnistuneesti"

  return {
    "test_id": "memory_info",
    "test_name": "Memory Information",
    "status": status,
    "message": message,
    "details": {
      "total_gb": total_gb,
      "available_gb": available_gb,
      "usage_percent": memory.percent
    }
  }