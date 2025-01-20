#!/usr/bin/env python3

import os
import re
import configparser
import subprocess
import time
import atexit
import signal
import sys

# ANSI colour codes
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
RESET = "\033[0m"

CONFIG_FILE = "config.cfg"

# Load configuration
config = configparser.ConfigParser()
config.read(CONFIG_FILE)

# Parse thresholds and fan duties
try:
    low_temp_1 = int(config["FanControl"]["low_temp_1"])
    low_temp_2 = int(config["FanControl"]["low_temp_2"])
    low_temp_3 = int(config["FanControl"]["low_temp_3"])
    low_temp_4 = int(config["FanControl"]["low_temp_4"])
    high_temp = int(config["FanControl"]["high_temp"])

    duty_1 = int(config["FanControl"]["duty_1"])
    duty_2 = int(config["FanControl"]["duty_2"])
    duty_3 = int(config["FanControl"]["duty_3"])
    duty_4 = int(config["FanControl"]["duty_4"])

    update_interval = float(config["FanControl"].get("update_interval", 0.5))
    cooldown_cycles = int(config["FanControl"].get("cooldown_cycles", 5))
except KeyError as e:
    print(f"{RED}[ERROR] Missing configuration key: {e}{RESET}")
    exit(1)

last_set_duty = duty_1
cooldown_counter = 0

def signal_handler(signum, frame):
    """Handle termination signals."""
    print(f"{YELLOW}[INFO] Caught signal {signum}. Resetting fan to auto mode...{RESET}")
    set_fan_to_auto()
    sys.exit(0)  # Graceful exit after resetting the fan

# Handle various termination signals
signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
signal.signal(signal.SIGINT, signal_handler)   # Interrupt signal (Ctrl+C)
signal.signal(signal.SIGHUP, signal_handler)   # Hangup signal

def set_fan_to_auto():
    """Set fan control to auto."""
    global last_set_duty
    try:
        subprocess.run(["sudo", "./ectool", "autofanctrl"], check=True)
        last_set_duty = None
        print(f"{GREEN}[INFO] Fan set to auto mode.{RESET}")
    except subprocess.CalledProcessError as e:
        print(f"{RED}[ERROR] Failed to set fan to auto: {e}{RESET}")

atexit.register(set_fan_to_auto)

def get_cpu_temperatures():
    """Extract CPU temperatures."""
    try:
        sensors_output = subprocess.check_output(["sensors"], text=True)
        cpu_temp_pattern = r"(Core|Package id)\s+\d*:.*?\+(\d+\.\d)°C"
        matches = re.findall(cpu_temp_pattern, sensors_output)
        temps = [float(temp) for _, temp in matches]
        if not temps:
            print(f"{YELLOW}[WARN] No CPU temperature data found.{RESET}")
        return temps
    except subprocess.CalledProcessError as e:
        print(f"{RED}[ERROR] Failed to execute 'sensors': {e}{RESET}")
        return []

def calculate_gradual_fan_duty_with_cooldown(temperature):
    """Determine fan duty based on temperature and cooldown."""
    global cooldown_counter, last_set_duty

    try:
        if temperature < low_temp_1:
            desired_duty = duty_1
        elif low_temp_1 <= temperature < low_temp_2:
            desired_duty = duty_1 + (duty_2 - duty_1) * (temperature - low_temp_1) / (low_temp_2 - low_temp_1)
        elif low_temp_2 <= temperature < low_temp_3:
            desired_duty = duty_2 + (duty_3 - duty_2) * (temperature - low_temp_2) / (low_temp_3 - low_temp_2)
        elif low_temp_3 <= temperature < low_temp_4:
            desired_duty = duty_3 + (duty_4 - duty_3) * (temperature - low_temp_3) / (low_temp_4 - low_temp_3)
        else:
            desired_duty = duty_4

        desired_duty = round(desired_duty)

        # Ensure last_set_duty is always a valid numeric value
        if last_set_duty is None or desired_duty < last_set_duty:
            cooldown_counter += 1
            if cooldown_counter >= cooldown_cycles:
                cooldown_counter = 0
                return desired_duty
            else:
                print(f"{YELLOW}[INFO] Cooling down: cycle {cooldown_counter}/{cooldown_cycles}.{RESET}")
                return last_set_duty
        else:
            cooldown_counter = 0
            return desired_duty
    except Exception as e:
        print(f"{RED}[ERROR] Error in duty calculation: {e}{RESET}")
        return last_set_duty  # Return the last known valid duty
        
def set_fan_control(duty):
    """Set fan duty."""
    global last_set_duty
    if last_set_duty == duty:
        print(f"{GREEN}[INFO] Fan duty already set to {duty}%.{RESET}")
        return

    try:
        subprocess.run(["sudo", "./ectool", "fanduty", str(int(duty))], check=True)
        last_set_duty = duty
        print(f"{GREEN}[INFO] Fan duty set to {duty}%.{RESET}")
    except subprocess.CalledProcessError as e:
        print(f"{RED}[ERROR] Failed to set fan duty: {e}{RESET}")


def get_fan_rpm():
    """Get fan RPM."""
    try:
        rpm_output = subprocess.check_output(["sudo", "./ectool", "pwmgetfanrpm", "0"], text=True)
        rpm_match = re.search(r"Fan\s+\d+\s+RPM:\s+(\d+)", rpm_output)
        return int(rpm_match.group(1)) if rpm_match else None
    except subprocess.CalledProcessError as e:
        print(f"{RED}[ERROR] Failed to retrieve fan RPM: {e}{RESET}")
        return None


def display_summary(temperatures):
    """Display system status."""
    if not temperatures:
        print(f"{YELLOW}[INFO] No valid CPU temperature data available.{RESET}")
        return

    lowest_temp = min(temperatures)
    highest_temp = max(temperatures)
    avg_temp = sum(temperatures) / len(temperatures)

    colour = RESET if highest_temp < low_temp_2 else YELLOW if highest_temp < low_temp_4 else RED
    fan_rpm = get_fan_rpm()

    print(f"{colour}Lowest Temperature: {lowest_temp:.1f}°C{RESET}")
    print(f"{colour}Highest Temperature: {highest_temp:.1f}°C{RESET}")
    print(f"{colour}Average Temperature: {avg_temp:.1f}°C{RESET}\n")
    
    if fan_rpm is not None:
        print(f"{CYAN}[INFO] Current Fan RPM: {fan_rpm}{RESET}")
    else:
        print(f"{YELLOW}[WARN] Unable to retrieve fan RPM.{RESET}")

    if last_set_duty is None:
        print(f"{CYAN}[INFO] Fan is in auto mode.{RESET}")
    else:
        print(f"{CYAN}[INFO] Fan duty last set to: {last_set_duty}%.{RESET}")


def main():
    """Main function."""
    print(f"{GREEN}[INFO] Starting fan control script...{RESET}")
    set_fan_to_auto()
    time.sleep(1)

    try:
        while True:
            os.system("clear")
            print(f"{YELLOW}[INFO] Monitoring CPU temperatures...\n{RESET}")
            temperatures = get_cpu_temperatures()
            display_summary(temperatures)

            if temperatures:
                max_temp = max(temperatures)
                required_duty = calculate_gradual_fan_duty_with_cooldown(max_temp)
                if last_set_duty is None or required_duty != last_set_duty:
                    set_fan_control(required_duty)
            else:
                print(f"{YELLOW}[WARN] No valid temperature data. Fan remains in current state.{RESET}")

            time.sleep(update_interval)
    except KeyboardInterrupt:
        print(f"{GREEN}[INFO] Exiting fan control script...{RESET}")


if __name__ == "__main__":
    main()

