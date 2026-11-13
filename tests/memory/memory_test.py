# Väliaikainen "testi" tiedosto jossa testataan vain pystytäänkö ram tiedot lukemaan
import psutil

def run_memory_test():
  # Haetaan psutil avulla ramit
  memory = psutil.virtual_memory()

  # Haetaan muistin määrä ja mitä siitä on käytettävissä
  total_gb = round(memory.total / (1024 ** 3), 2)
  available_gb = round(memory.available / (1024 ** 3), 2)

  # Jos muistin määrä on yli 0 niin oletetaan että tiedot saatiin luettua
  if memory.total <= 0:
    status = "UNKNOWN"
    message = "RAM-muistin tietoja ei saatu luettua"
  # Muulloin ilmoitetaan ettei niitä saatu luettua
  else:
    status = "PASS"
    message = "RAM-muistin perustiedot luettu onnistuneesti"

  # Palautetaan tulokset
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