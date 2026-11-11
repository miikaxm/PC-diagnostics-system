import psutil

def run_cpu_test():
  cores = psutil.cpu_count(logical=False)
  threads = psutil.cpu_count(logical=True)

  if cores is None or threads is None:
    status = "UNKNOWN"
    message = "Prosessorin tietoja ei saatu luettua"
  elif cores > 0 and threads >= cores:
    status = "PASS"
    message = "Prosessorin perustiedot luettu onnistuneesti"
  else:
    status = "WARNING"
    messge = "Prosessorin tiedoissa havaittiin poikkeama"

  return {
        "test_id": "cpu_info",
        "test_name": "CPU Information",
        "status": status,
        "message": message,
        "details": {
            "cores": cores,
            "threads": threads
        }
  }