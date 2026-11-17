import json
import math
import platform
import re
import shutil
import subprocess
import time

def run_temperature_test():
  # Testin tulokset alustetaan UNKNOWN-tilaan
  result = {
    "test_id": "temperature",
    "test_name": "Temperature Monitoring",
    "status": "UNKNOWN",
    "message": "",
    "details": {}
  }

  # Lämpötilatietojen lukeminen sensors-ohjelmalla vaatii Linuxin
  if platform.system() != "Linux":
    result["message"] = "Lämpötilatesti vaatii linuxin"
    return result

  # Tarkistetaan, löytyykö lm-sensorsin sensors-ohjelma
  sensors = shutil.which("sensors")

  # Jos ohjelmaa ei löydy, testiä ei voida suorittaa
  if sensors is None:
    result["message"] = "lm-sensors ei ole asennettu"
    return result

  # Otetaan viisi mittausta kahden sekunnin välein
  sample_count = 5
  sample_interval = 2

  # readings kerää anturikohtaiset mittaukset ja errors epäonnistumiset
  readings = {}
  errors = []
  # Aloitusaikaa käytetään testin kokonaiskeston laskemiseen
  started = time.monotonic()

  # Luetaan antureiden tiedot useamman kerran lämpötilamuutosten havaitsemiseksi
  for sample_number in range(sample_count):
    try:
      # sensors tuottaa mittaustiedot JSON-muodossa
      completed = subprocess.run(
        [sensors, "-j"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False
      )

      # Epäonnistuneen mittauksen virhe lisätään tuloksiin
      if completed.returncode != 0:
        errors.append(
          f"Mittaus {sample_number + 1} epäonnistui: "
          f"{completed.stderr.strip()}"
        )
        continue

      # Muunnetaan ohjelman tuloste käsiteltäväksi Python-dataksi
      data = json.loads(completed.stdout)

      # Käydään läpi kaikki ohjelman ilmoittamat sirut ja niiden anturit
      for chip_name, chip_data in data.items():
        if not isinstance(chip_data, dict):
          continue

        for sensor_name, sensor_data in chip_data.items():
          if not isinstance(sensor_data, dict):
            continue

          # Poimitaan kustakin anturista lämpötilan mittausarvot
          for field, value in sensor_data.items():
            match = re.fullmatch(
              r"(temp\d+)_input", field
            )

            # Ohitetaan kentät, jotka eivät ole lämpötilan mittausarvoja
            if match is None:
              continue

            # Vain äärelliset numeeriset arvot kelpaavat lämpötiloiksi
            if (
              not isinstance(value, (int, float))
              or isinstance(value, bool)
              or not math.isfinite(value)
            ):
              continue

            prefix = match.group(1)

            # Sama tunniste yhdistää saman anturin mittaukset
            sensor_id = (
              f"{chip_name}/{sensor_name}/{prefix}"
            )

            # Haetaan anturin ilmoittamat varoitus- ja kriittiset rajat
            max_value = sensor_data.get(
              f"{prefix}_max"
            )

            critical_value = sensor_data.get(
              f"{prefix}_crit"
            )

            # Uudelle anturille alustetaan mittausarvot ja rajat
            if sensor_id not in readings:
              readings[sensor_id] = {
                "chip": chip_name,
                "sensor": sensor_name,
                "min_c": value,
                "max_c": value,
                "latest_c": value,
                "limit_c": None,
                "critical_c": None,
                "samples": 0
              }

            # Päivitetään anturin alin, ylin ja viimeisin mittaus
            item = readings[sensor_id]

            item["min_c"] = min(
              item["min_c"], value
            )
            item["max_c"] = max(
              item["max_c"], value
            )
            item["latest_c"] = value
            item["samples"] += 1

            # Tallennetaan anturin ilmoittamat rajat, jos ne ovat kelvollisia
            if (
                isinstance(max_value, (int, float))
                and not isinstance(max_value, bool)
                and math.isfinite(max_value)
            ):
                item["limit_c"] = max_value

            if (
                isinstance(critical_value, (int, float))
                and not isinstance(critical_value, bool)
                and math.isfinite(critical_value)
            ):
                item["critical_c"] = critical_value
    # Virheellinen tuloste, aikakatkaisu tai komennon suoritusvirhe kirjataan
    except(
      OSError,
      subprocess.TimeoutExpired,
      json.JSONDecodeError
    ) as error:
      errors.append(
        f"Mittaus {sample_number + 1}: {error}"
      )

    # Odotetaan mittausten välissä, paitsi viimeisen mittauksen jälkeen
    if sample_number < sample_count -1:
      time.sleep(sample_interval)

  # Verrataan antureiden korkeimpia mittaustuloksia ilmoitettuihin rajoihin
  warnings = []
  critical = []
  # Lasketaan anturit, joille löytyi vähintään yksi tarkistettava raja
  checked_limits = 0

  for sensor_id, item in readings.items():
    peak = item["max_c"]
    critical_limit = item["critical_c"]
    max_limit = item["limit_c"]

    # Kriittisen rajan ylitys merkitsee vakavampaa virhettä
    if critical_limit is not None:
      checked_limits += 1

      if peak >= critical_limit:
        critical.append(sensor_id)
        continue

    # Muutoin tarkistetaan anturin ilmoittama yläraja
    if max_limit is not None:
      if critical_limit is None:
        checked_limits += 1

      if peak >= max_limit:
        warnings.append(sensor_id)

  # Pyöristetään lämpötilat raportointia varten
  for item in readings.values():
    for field in ("min_c", "max_c", "latest_c"):
      item[field] = round(item[field], 2)

  # Lisätään tuloksiin mittaukset, rajahavainnot ja kesto
  result["details"] = {
    "duration_seconds": round(
      time.monotonic() - started, 2
    ),
    "requested_samples": sample_count,
    "sensors": readings,
    "warning_sensors": warnings,
    "critical_sensors": critical,
    "errors": errors
  }

  # Määritetään testin tila vakavimman havaitun tilanteen perusteella
  if critical:
    result["status"] = "FAIL"
    result["message"] = (
      "Anturin ilmoittama kriittinen lämpötilaraja ylittyi"
    )

  elif warnings:
    result["status"] = "WARNING"
    result["message"] = (
      "Yhden tai useamman anturin lämpötilaraja ylittyi"
    )

  elif not readings:
    result["status"] = "UNKNOWN"
    result["message"] = (
      "Lämpötila-antureiden tietoja ei saatu luettua"
    )

  elif errors:
    result["status"] = "WARNING"
    result["message"] = (
      "Osa lämpötilamittauksista epäonnistui"
    )

  elif checked_limits == 0:
    result["status"] = "UNKNOWN"
    result["message"] = (
      "Lämpötilat luettiin, mutta anturien raja-arvoja "
      "ei ollut saatavilla"
    )

  else:
    result["status"] = "PASS"
    result["message"] = (
      "Saatavilla olevat lämpötilarajat eivät ylittyneet "
      "mittauksen aikana"
    )

  return result


      