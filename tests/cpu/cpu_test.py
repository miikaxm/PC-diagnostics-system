# Tämän on vain väliaikainen "testi" tiedosto
# Ei mitään oikeaa testausta CPU corejen ja threadsien hakua vain

import psutil

def run_cpu_test():
  # Haetaan coret ja threadsit
  cores = psutil.cpu_count(logical=False)
  threads = psutil.cpu_count(logical=True)

  # Jos cores ei ole tai threadseja ei ole niin oletetaan että tuloksia ei saatu
  if cores is None or threads is None:
    status = "UNKNOWN"
    message = "Prosessorin tietoja ei saatu luettua"
  # Jos niitä on enemmän kuin 0 niin testi onnistuu
  elif cores > 0 and threads >= cores:
    status = "PASS"
    message = "Prosessorin perustiedot luettu onnistuneesti"
  # Muulloin testissa jotain muuta pielessä
  else:
    status = "WARNING"
    messge = "Prosessorin tiedoissa havaittiin poikkeama"

  # Palautetaan infot
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