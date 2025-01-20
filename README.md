# Vero-514-Chrultrabook Sound and Fans and Fixes
Fixes to allow functioning Linux installation on chromebook vero 514

This guide helps you configure sound and fan controls on your device. It includes setting up sound functionality and using the `sensors.py` script to automatically monitor and adjust fan speeds via `ectool`, as well as other fixes I will add as I come across them.

NOTE: This is an Alder-Lake device, the USBC storage seems to only recognised if it is connected at boot. I have not found a proper fix for this yet.

---

## Prerequisites

Ensure you have the following installed and configured:

- **Python 3.6+**
- **ectool** (Embedded Controller tool): required for controlling fan behaviour.
- **lm-sensors**: for temperature readings on Linux systems.
- Appropriate permissions (root or sudo) to interact with system hardware.

---

## Sound Setup

1. **Check Audio Drivers**: Ensure your system drivers are installed and up to date.
   - Install the latest kernel and updates.
   - Verify that `pulseaudio` or `pipewire` is running or install as required.

3. **Test Audio Output**:
   - Run `aplay -l` to list audio devices, and `speaker-test` to check functionality.
  
4. **Install @WeirdTreeThing SOF Drivers**:
   - https://github.com/WeirdTreeThing/chromebook-linux-audio
   - Reboot

6. **Troubleshooting**:
   - Open sound setting and select the correct output device (if only 'dummy audio' is present try the next steps).
   - Open the 'Volume Control' application (Gnome) and ensure the correct sound profile is selected (Pro Audio)
   - Ensure the output channels are not muted in `alsamixer`.
   - Check system logs for any relevant errors related to the sound card.

---

## Fan Control with `sensors.py`

The `sensors.py` script monitors system temperatures and dynamically adjusts fan speeds using `ectool`. Follow the steps below to set it up.

### Installation

1. **Verify ectool and lm-sensors Installation**:
   - Ensure `ectool` is available in your PATH. Test by running:
     ```bash
     ectool version
     ```
   - Ensure `lm-sensors` is installed and configured:
     ```bash
     sudo apt install lm-sensors
     sudo sensors-detect
     sensors
     ```

### Configuration

1. **Edit `config.cfg`**:
   - The script uses a configuration file (`config.cfg`) to define temperature thresholds and corresponding fan duties. Adjust the following parameters:
     ```ini
     [FanControl]
     low_temp_1 = 40
     low_temp_2 = 50
     low_temp_3 = 60
     low_temp_4 = 70
     high_temp = 80

     duty_1 = 20
     duty_2 = 40
     duty_3 = 60
     duty_4 = 80

     update_interval = 0.5
     cooldown_cycles = 5
     ```

2. **Run the Script**:
   - Execute with:
     ```bash
     sudo python3 sensors.py
     ```
   - Use `sudo` to grant access to hardware controls.

3. **Background Execution**:
   - Run the script as a background process or systemd service for continuous monitoring. Example:
     ```bash
     nohup sudo python3 sensors.py &
     ```

### Key Features

- Gradual fan duty adjustments to minimise noise.
- Cooldown cycles to avoid unnecessary speed changes.
- Automatic reset to auto mode on termination or error.
- Detailed real-time summaries of temperatures and fan status.

---

## Troubleshooting

- **Sound Issues**:
  - Confirm the sound card is properly recognised (`dmesg | grep audio` on Linux).
  - Restart the sound server (`pulseaudio -k && pulseaudio --start` for PulseAudio).

- **Fan Issues**:
  - Ensure `ectool` and `lm-sensors` are installed and properly configured.
  - Verify `config.cfg` contains valid temperature and duty values.
  - Check script logs for errors or unusual behaviour.

---

## Contributions

Contributions are welcome. 
