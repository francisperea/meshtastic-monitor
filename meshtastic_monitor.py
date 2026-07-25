#!/home/francis/meshtastic/bin/python

import subprocess
import time
import csv
import re
import logging
from pathlib import Path
from datetime import datetime

# ----------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------

HOST = "192.168.1.50"
NODE = "!9a8b7cf4"

MESHTASTIC = "/home/francis/meshtastic/bin/meshtastic"

RESET_HOUR = 4
RESET_MINUTE = 0

BASE = Path("/home/francis/meshtastic")

LOGDIR = BASE / "logs"
CSVFILE = LOGDIR / "battery.csv"
LOGFILE = LOGDIR / "monitor.log"

LOGDIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOGFILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

# ----------------------------------------------------

last_hour = None
last_reset_day = None


def run_command(args):

    cmd = [MESHTASTIC,
           "--host", HOST,
           "--dest", NODE] + args

    try:

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        return result.stdout

    except Exception as e:

        logging.error(str(e))
        return ""


def request_telemetry():

    output = run_command(["--request-telemetry"])

    battery = None
    voltage = None
    uptime = None

    m = re.search(r'Battery level:\s+([0-9.]+)', output)
    if m:
        battery = float(m.group(1))

    m = re.search(r'Voltage:\s+([0-9.]+)', output)
    if m:
        voltage = float(m.group(1))

    m = re.search(r'Uptime:\s+([0-9]+)', output)
    if m:
        uptime = int(m.group(1))

    if uptime is None:
        logging.error("No se ha recibido telemetría")
        return

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
            datetime.now().isoformat(sep=" "),
            battery,
            voltage,
            uptime
        ])

    logging.info(
        f"Battery={battery}% Voltage={voltage}V Uptime={uptime}s"
    )


def reset_node():

    logging.info("Reseteando NodeDB")

    output = run_command(["--reset-nodedb"])

    if "ACK" not in output:
        logging.warning("No se recibió ACK")

    time.sleep(25)

    request_telemetry()


logging.info("Monitor iniciado")

while True:

    now = datetime.now()

    #
    # Cada hora
    #

    if now.hour != last_hour:

        request_telemetry()
        last_hour = now.hour

    #
    # Reset diario
    #

    if (now.hour == RESET_HOUR and
        now.minute == RESET_MINUTE and
        last_reset_day != now.date()):

        reset_node()
        last_reset_day = now.date()

    time.sleep(60)
