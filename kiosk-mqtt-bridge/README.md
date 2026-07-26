# **Kiosk MQTT Bridge**

A lightweight, headless bridge that exposes System Board Computer (SBC) hardware controls and web kiosk management to MQTT. It provides seamless integration with Home Assistant via MQTT Discovery, allowing remote control of screen power, display orientation, URL navigation, and hardware diagnostics polling.

## **🏗️ Architecture & Design Philosophy**

This project is built around two core principles:

> 1. **Strict Process Isolation:** To prevent blocking the main MQTT event loop, hardware diagnostic polling (Wi-Fi RSSI, CPU temp, memory) is offloaded entirely to a separate process using multiprocessing. **Threading is strictly prohibited in this codebase** to avoid GIL contention and ensure robust isolation of OS-level blocking calls.  
> 2. **Zero-Abstraction Production Hosts:** When troubleshooting an edge device in the field, cognitive load must be zero. The production host runs a completely flat file structure with literal OS commands, completely bypassing dynamic loading, factories, or abstract base classes.

## **📂 Repository Structure**

The repository contains the core logic and a library of hardware-specific profiles:

Plaintext  
kiosk-mqtt-bridge/  
├── config.toml                \# Default configuration template  
├── config.py                  \# TOML parser and writer  
├── discovery.py               \# Home Assistant MQTT discovery payloads  
├── main.py                    \# Core orchestrator and multiprocessing entry point  
└── hardware\_profiles/         \# ⚠️ REPOSITORY ONLY  
    └── rpi1.py                \# Implementation for Raspberry Pi 1 Model A+

## **🚀 Deployment Workflow (Fat Repo ➡️ Lean Host)**

This repository is designed to be consumed by an external **Provisioner Script** during the SD-card imaging or first-boot process.  
The provisioner is responsible for translating this repository into a flat structure on the target host. **The repository itself does not dynamically load hardware at runtime on the production device.**

### **The Provisioner Execution Steps:**

> 1. Clone or download this repository.  
> 2. Copy main.py, config.py, and discovery.py to the target host directory (e.g., /home/kiosk/kiosk-mqtt-bridge/).  
> 3. Identify the target hardware (e.g., Raspberry Pi 1).  
> 4. Copy the specific hardware profile (e.g., hardware\_profiles/rpi1.py) to the target host and **rename it strictly to hardware.py**.  
> 5. Discard the rest of the repository/hardware\_profiles folder.

### **The Resulting Host Structure:**

Plaintext  
/home/kiosk/kiosk-mqtt-bridge/  
├── config.toml  
├── config.py  
├── discovery.py  
├── hardware.py    \<-- The literal, hardware-specific OS commands  
└── main.py

*Because main.py simply executes import hardware, the deployment requires no runtime resolution and leaves a perfectly transparent trace for debugging.*

## **🔌 Home Assistant Integration**

On startup, the bridge publishes standard Home Assistant MQTT Discovery payloads. The following entities will automatically appear in Home Assistant under the configured client\_id:

* **Text:** Kiosk URL (read/write)  
* **Switch:** Screen Power (turns display off/on and toggles kiosk.service)  
* **Select:** Screen Orientation (Landscape, Portrait, etc.)  
* **Button:** Refresh Kiosk, System Reboot  
* **Sensor:** Wi-Fi RSSI, Free Memory, CPU Temperature

## **🤖 LLM / Agent Implementation Notes**

If you are an AI assistant tasked with extending this project, adhere strictly to the following constraints:

> 1. **Adding New Hardware Support:** Do not modify main.py or attempt to introduce an Abstract Base Class. To add support for a new SBC, create a new file in hardware\_profiles/ (e.g., hardware\_profiles/rpi3.py). Ensure it implements the exact same function signatures found in hardware\_profiles/rpi1.py.  
> 2. **Concurrency Rules:** Do not implement threading. Any new long-running or periodic background tasks must be spun up as a separate multiprocessing.Process inside the main() function.  
> 3. **Host Execution Environment:** Assume D-Bus commands (like cogctl) require a properly defined session bus (DBUS\_SESSION\_BUS\_ADDRESS).  
> 4. **Configuration:** Do not write JSON configs. The project strictly uses tomllib for configuration management.