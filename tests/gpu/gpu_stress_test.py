import os
import platform
import re
import shutil
import signal
import subprocess
import time

def run_gpu_stress_test():
  # Tulokset
  result = {
    "test_id": "gpu_stress",
    "test_name": "GPU Stress Test (glmark2)",
    "status": "UNKNOWN",
    "message": "",
    "details": {}
  }

  # Tarkistetaan ollaanko linuxissa
  if platform.system() != "Linux":
    result["message"] = "GPU-testi vaatii Linuxin"
    return result

  # Tarkistetaanko onko graafista työpöytäistuntoa
  session_type = os.environ.get(
    "XDG_SESSION_TYPE", ""
  ).lower()

  # Valitaa työpöytäistunnolle sopiva glmark2
  if session_type == "wayland":
    candidates = [
      "glmark2-wayland",
      "glmark2-es2-wayland"
    ]
  else:
    candidates = [
      "glmark2",
      "glmark2-x11"
    ]

  glmark2 = None

  for candidate in candidates:
    glmark2 = shutil.which(candidate)
    if glmark2 is not None:
      break

  if glmark2 is None:
    result["message"] = (
      "Graafiselle istunnolle sopivaa "
      "glmark2-ohjelmaa ei löytynyt"
    )
    return result

  # Varmistetaan yhteys graafiseen näyttöpalvelimeen
  if session_type == "wayland":
    if not os.environ.get("WAYLAND_DISPLAY"):
      result["message"] = (
        "Wayland-näyttöyhteyttä ei ole saatavilla"
      )
      return result
  elif not os.environ.get("DISPLAY"):
    result["message"] = (
      "X11-näyttöyhteyttä ei ole saatavilla"
    )
    return result

  # Suoritetaan glmark2 normaali testisarja
  # Ikkunan koko
  window_size = "800x600"
  timeout_seconds = 900

  command = [
    glmark2,
    "--size", window_size
  ]

  result["details"] = {
    "tool": glmark2,
    "session_type": session_type,
    "window_size": window_size,
    "timeout_seconds": timeout_seconds,
    "duration_seconds": None,
    "exit_code": None,
    "renderer": None,
    "opengl_version": None,
    "score": None,
    "output": ""
  }

  process = None
  started = time.monotonic()

  try:
    # Käynnistetään testi
    process = subprocess.Popen(
      command,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      text=True,
      errors="replace",
      start_new_session=True
    )

    # Odotetaan että testi valmistuu
    stdout, stderr = process.communicate(
      timeout=timeout_seconds
    )

    elapsed = round(
      time.monotonic()- started, 2
    )

    output = stdout + "\n" + stderr
    exit_code = process.returncode

    # Haetaan lopullinen pistemäärä testistä
    score_match = re.search(
      r"glmark2 Score:\s*(\d+)",
      output,
      re.IGNORECASE
    )

    # Haetaan mikä grafiikkarenderöijä oli käytössä
    renderer_match = re.search(
      r"GL_RENDERER:\s*(.+)",
      output,
      re.IGNORECASE
    )

    version_match = re.search(
      r"GL_VERSION:\s*(.+)",
      output,
      re.IGNORECASE
    )

    score = (
      int(score_match.group(1))
      if score_match else None
    )

    renderer = (
      renderer_match.group(1).strip()
      if renderer_match else None
    )

    opengl_version = (
      version_match.group(1).strip()
      if version_match else None
    )

    result["details"].update({
      "duration_seconds": elapsed,
      "exit_code": exit_code,
      "renderer": renderer,
      "opengl_version": opengl_version,
      "score": score,
      "output": output[-20000:]
    })

    # ohjelmistorenderöinti ei testaa GPUn laitteistokiihdytystä luotettavasti
    software_renderers = (
      "llvmpipe",
      "softpipe",
      "software rasterizer",
      "swrast"
    )

    is_software_renderer = (
      renderer is not None
      and any(
        name in renderer.lower()
        for name in software_renderers
      )
    )

    if exit_code != 0:
      result["status"] = "WARNING"
      result["message"] = (
        "GPU-renderöintitesti keskeytyi tai "
        "päättyi virheeseen"
      )

    elif score is None:
      result["status"] = "UNKNOWN"
      result["message"] = (
        "glmark2 valmistui, mutta pistemäärää "
        "ei löytynyt tulosteesta"
      )

    elif is_software_renderer:
      result["status"] = "WARNING"
      result["message"] = (
        "Testi valmistui, mutta renderöinti "
        "tehtiin ohjelmistolla eikä GPU:LLA"
      )

    elif renderer is None:
      result["status"] = "UNKNOWN"
      result["message"] = (
        "Testi valmistui, mutta käytettyä "
        "grafiikkarenderöijää ei voitu tunnistaa"
      )

    else:
      result["status"] = "PASS"
      result["message"] = (
        "GPU:n 3D-renderöintitesti valmistui "
        "ilman havaittuja suoritusvirheitä"
      )

  except subprocess.TimeoutExpired:
    # Keskeytetään jos testiin menee liian pitkään
    if process is not None:
      try:
        os.killpg(process.pid, signal.SIGKILL)
      except ProcessLookupError:
        pass

      stdout, stderr = process.communicate()

      result["details"]["output"] = (
        stdout + "\n"+ stderr
      )[-20000:]

      result["details"]["exit_code"] = process.returncode

    result["status"] = "WARNING"
    result["message"] = "GPU-testin aikaraja ylittyi"

    result["details"]["duration_seconds"] = round(
      time.monotonic() - started, 2
    )

  except OSError as error:
    result["status"] = "UNKNOWN"
    result["message"] = (
      f"GPU-testin käynnistäminen epäonnistui: {error}"
    )

  except KeyboardInterrupt:
    # Käyttäjän keskeytys pysäyttää glmark2:n
    if process is not None:
      try:
        os.killpg(process.pid, signal.SIGKILL)
      except ProcessLookupError:
        pass

      process.communicate()

    raise
  
  return result