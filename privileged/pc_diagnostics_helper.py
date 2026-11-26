import json
import os
import stat
import subprocess
import sys

def run_command(command, timeout):
  try:
    completed = subprocess.run(
      command,
      capture_output=True,
      text=True,
      timeout=timeout,
      check=False,
      env={
        "PATH": "/usr/sbin:/usr/bin:/sbin/bin",
        "LANG": "C",
        "LC_ALL": "C"
      }
    )

    sys.stdout.write(completed.stdout)
    sys.stderr.write(completed.stderr)

    return completed.returncode

  except subprocess.TimeoutExpired:
    print("Diagnostiikkatesti aikakatkaistiin", file=sys.stderr)
    return 124

  except OSError as error:
    print(str(error), file=sys.stderr)
    return 125

def get_mounts(device):
  mounts = device.get("mountpoints") or []

  if isinstance(mounts, str):
    mounts = [mounts]

  for child in device.get("children") or []:
    mounts.extend(get_mounts(child))

  return mounts

def get_allowed_disks():
  completed = subprocess.run(
    [
      "/usr/bin/lsblk",
      "--json",
      "--paths",
      "--tree",
      "--output",
      "NAME,TYPE,TRAN,MOUNTPOINTS"
    ],
    capture_output=True,
    text=True,
    check=True,
    timeout=10
  )

  devices = json.loads(completed.stdout).get("blockdevices", [])

  disks_with_root = [
    device
    for device in devices
    if "/" in get_mounts(device)
  ]

  if not disks_with_root:
    raise RuntimeError(
      "Debianin käynnistyslevyä ei voitu tunnistaa"
    )

  allowed = set()

  for device in devices:
    if device.get("type") != "disk":
      continue

    if device.get("tran") == "usb":
      continue

    mounts = get_mounts(device)

    if any(
      mount in {"/", "/boot", "/boot/efi", "[SWAP]"}
      for mount in mounts
    ):
      continue

    name = device.get("name")

    if not name:
      continue

    allowed.add(os.path.realpath(name))

  return allowed

def run_smart(device_id):
  device_path = os.path.realpath(device_id)

  if not device_path.startswith("/dev/"):
    raise ValueError("Virheellinen laitepolku")

  if device_path not in get_allowed_disks():
    raise ValueError("Levy ei ole sallittujen levyjen listalla")

  device_info = os.stat(device_path)

  if not stat.S_ISBLK(device_info.st_mode):
    raise ValueError("Kohde ei ole lohkolaite")

  return run_command(
    [
      "/usr/sbin/smartctl",
      "--all",
      "--json",
      device_path
    ],
    timeout=60
  )

def run_memory():
  with open("/proc/meminfo", encoding="utf-8") as file:
    memory_info = file.read()

    available_kib = None

    for line in memory_info.splitlines():
      if line.startswith("MemAvailable"):
        available_kib = int(line.split()[1])
        break

    if available_kib is None or available_kib < 512 * 1024:
      raise RuntimeError(
        "RAM-testiä varten ei ole riittävästi vapaata muistia"
      )

    available_mib = available_kib // 1024
    test_mib = min(4096, int(available_mib * 0.4))

    if test_mib < 128:
      raise RuntimeError(
        "RAM-testille ei voida varata riittävästi muistia"
      )

    print(
      f"RAM-testin koko: {test_mib} Mib, kierroksia: 2",
      flush=True
    )

    return run_command(
      [
        "/usr/bin/memtester",
        f"{test_mib}M",
        "2"
      ],
      timeout=3600
    )

def main():
  if os.geteuid() != 0:
    print("Apuohjelma vaatii root-oikeudet", file=sys.stderr)
    return 126

  try:
    if len(sys.argv) == 3 and sys.argv[1] == "smart":
      return run_smart(sys.argv[2])

    if len(sys.argv) == 2 and sys.argv[1] == "memory":
      return run_memory()

    print("Tuntematon diagnostiikkatoiminto", file=sys.stderr)
    return 64

  except (
    OSError,
    ValueError,
    RuntimeError,
    subprocess.SubprocessError,
    json.JSONDecodeError
  ) as error:
    print(str(error), file=sys.stderr)
    return 125


if __name__ == "__main__":
  sys.exit(main())