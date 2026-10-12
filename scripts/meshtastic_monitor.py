#!/home/francis/meshtastic/bin/python3

import csv
import logging
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

# ==========================================================
# CONFIGURACIÓN
# ==========================================================

HOST = "radiopi.francisperea.org"
NODE = "!9a8b7cf4"

MESHTASTIC = "/home/francis/meshtastic/bin/meshtastic"

# Intervalos (segundos)

BATTERY_INTERVAL = 7200      # Producción: 3600
RESET_INTERVAL = 43200       # Producción: 86400
RESET_WAIT = 25             # Espera tras reset
LOOP_INTERVAL = 5           # Frecuencia del bucle principal

BASE = Path("/home/francis/meshtastic")

LOGDIR = BASE / "logs"
#CSVFILE = LOGDIR / "EA7LDWGS_telemetry.csv"
CSVFILE =  Path("/mnt/PiBacks/EA7LDWGS_telemetry.csv")
LOGFILE = LOGDIR / "monitor.log"

LOGDIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOGFILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

# ==========================================================


def run_command(args):

    cmd = [
        MESHTASTIC,
        "--host", HOST,
        "--dest", NODE,
    ] + args

    try:

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            logging.error(result.stderr.strip())

        return result.stdout

    except Exception as e:

        logging.exception(e)
        return ""


def request_telemetry():

    output = run_command(["--request-telemetry"])

    if not output:
        return False

    battery = None
    voltage = None
    uptime = None

    m = re.search(r"Battery level:\s+([0-9.]+)", output)
    if m:
        battery = float(m.group(1))

    m = re.search(r"Voltage:\s+([0-9.]+)", output)
    if m:
        voltage = float(m.group(1))

    m = re.search(r"Uptime:\s+([0-9]+)", output)
    if m:
        uptime = int(m.group(1))

    if uptime is None:
        logging.error("No se pudo obtener la telemetría.")
        logging.error(output)
        return False

    newfile = not CSVFILE.exists()

    with open(CSVFILE, "a", newline="") as f:

        writer = csv.writer(f)

        if newfile:
            writer.writerow([
                "timestamp",
                "battery",
                "voltage",
                "uptime"
            ])

        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            battery,
            voltage,
            uptime
        ])

    logging.info(
        f"Battery={battery:.1f}%  Voltage={voltage:.2f}V  Uptime={uptime}s"
    )

    return True


def reset_node():

    logging.info("Ejecutando reset de NodeDB")

    output = run_command(["--reset-nodedb"])

    if "ACK" in output:
        logging.info("ACK recibido")
    else:
        logging.warning("No se recibió ACK")
        logging.warning(output)

    time.sleep(RESET_WAIT)

    request_telemetry()


# ==========================================================

logging.info("==========================================")
logging.info("Monitor iniciado")
last_battery = 0
# last_battery = time.time()
last_reset = time.time()

while True:

    now = time.time()

    if now - last_battery >= BATTERY_INTERVAL:

        request_telemetry()
        last_battery = now

    #if now - last_reset >= RESET_INTERVAL:

        #reset_node()
        #last_reset = now

    time.sleep(LOOP_INTERVAL)
