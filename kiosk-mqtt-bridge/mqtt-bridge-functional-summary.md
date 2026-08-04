### 1. Configuration Management

- **`load_config()`:** Reads `config.toml` from a hardcoded path and parses it into a dictionary.  
- **`update_config_url(new_url)`:** Opens `config.toml`, searches for the `default_url` line, overwrites it with the new URL, and saves the file.  

### 2. D-Bus & System Service Orchestration

- **`run_cogctl(action, arg, retries, delay)`:** Injects the `DBUS_SESSION_BUS_ADDRESS` environment variable and executes `cogctl` commands (like `open`). It includes a crucial retry loop to handle D-Bus startup latency.  
- **`restart_kiosk_service()`:** Executes `sudo systemctl restart kiosk.service`. It then dynamically reads the saved `default_url` and uses `run_cogctl` to restore the page after the service restarts.  

### 3. Zero-Overhead Hardware Diagnostics

- **`get_wifi_rssi()`:** Parses `/proc/net/wireless` to extract the signal strength integer for `wlan0`.  
- **`get_free_mem()`:** Parses `/proc/meminfo` to find `MemAvailable` and converts the value from KB to MB.  
- **`get_cpu_temp()`:** Reads `/sys/class/thermal/thermal_zone0/temp` and mathematically rounds the output to a single decimal place in Celsius.  

### 4. Display Pipeline Control

- **`get_screen_power()`:** Reads `/sys/class/graphics/fb0/blank` and translates `1` to "OFF" and `0` to "ON".  
- **`set_screen_power(state)`:**
  - If "OFF": Stops `kiosk.service`, then writes `1` to the framebuffer blanking interface.  
  - If "ON": Writes `0` to the framebuffer, then triggers `restart_kiosk_service()`.  
- **`get_orientation()`:** Uses regex to parse `/etc/default/kiosk` for `KIOSK_ROTATION` and maps the integer to a string (landscape, portrait, etc.).  
- **`update_rotation(orientation)`:** Maps the string back to an integer, overwrites the `/etc/default/kiosk` file, and triggers `restart_kiosk_service()`.  

### 5. MQTT Orchestration & Discovery

- **`on_connect(...)`:**
  - Subscribes to all `set` topics (url, screen, orientation, refresh, reboot).  
  - Constructs and publishes the Home Assistant MQTT Discovery JSON payloads for the text, switch, select, button, and sensor entities.  
  - Publishes the initial states (screen power, orientation, saved URL) as retained messages.  
  - Executes `run_cogctl` on boot to enforce the saved URL.  
- **`on_message(...)`:** Routes incoming payloads to the correct system function and updates the corresponding state topic upon success. Contains the standalone `sudo reboot` system call.  

### 6. The Execution Loop

- **Main Block:** Connects to the broker, starts the network loop, and enters a `while True` loop that polls and publishes the three hardware diagnostics exactly every 300 seconds.  

### Implementation notes:

There are a few highly specific, hardcoded implementation details in the monolithic script that are worth explicitly calling out to ensure they are properly extracted and decoupled in the new architecture:

- **Device Info Hardcoding:** The `on_connect` function hardcodes `"model": "Pi 1 Model A+"` directly into the Home Assistant discovery payload. In the modular architecture, this should be dynamically provided by the active hardware profile or passed via the configuration file.  
- **MQTT Connection Authentication:** The script explicitly checks for the existence of `MQTT_USER` and `MQTT_PASSWORD` in the TOML dictionary and conditionally applies them using `client.username_pw_set()` before initiating the connection.  
- **Graceful Shutdown:** The main loop utilizes a `try/finally` block to catch `KeyboardInterrupt` and cleanly execute `client.loop_stop()` and `client.disconnect()`. This ensures no orphaned network connections remain if the service is stopped.  
- **Default Fallbacks:** The `get_orientation()` function has a hardcoded fallback to return `"landscape"` if the file read fails or if the regex fails to find a match in `/etc/default/kiosk`.  
- **Topic Structure:** The topics rely entirely on `TOPIC_PREFIX` (defaulting to `kiosk/pi`) combined with a `CLIENT_ID` via f-strings for all subscriptions and state publications.  