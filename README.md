# E1001 Fixer

**Fix Android ROM Error E1001 – Recovery & Boot Repair Tool**

`E1001 Fixer` is a utility designed to **resolve the E1001 error** encountered when flashing GSI or custom ROMs on Android devices. It helps users:

* Analyze boot and system image structures.
* Reconstruct necessary partitions to make the device bootable.
* Flash GSI ROMs without encountering “device incompatible” or missing partition errors.
* Generate verbose logs for debugging complex recovery issues.

---

## Key Features

* ✅ Analyze and modify `boot.img`.
* ✅ Repack `system.img` for GSI compatibility.
* ✅ Verbose boot logging for easier debugging.
* ✅ Fix symbolic link issues (e.g., `/system/etc/ld.config.txt`).
* ✅ Multi-device and multi-architecture support (ARM / ARM64).

---

## Requirements

* Python 3.8
* WSL (Ubuntu or Debian)

---

## Installation

### 1. Install Python 3.8

Download and install from the official Python page:
[https://www.python.org/downloads/release/python-380/](https://www.python.org/downloads/release/python-380/)

### 2. Install WSL

Run one of the following commands in **PowerShell**:

```powershell
wsl --install -d Ubuntu
```

**or**

```powershell
wsl --install -d Debian
```

> ⚠️ Make sure there is an empty line **before and after `or`** to prevent Markdown from rendering it as inline text.

### 3. Install dependencies

Install `brotli` via pip:

```bash
pip install brotli
```

---

## Usage

### 1. Mount partitions in TWRP

* Mount `system` and `vendor` partitions first.

### 2. Run the GUI

```bash
python gui.py
```

### 3. Check ADB device

* In the GUI, verify that the debug text shows:

```
device id -> recovery
```

* If yes, the device is ready.

### 4. Check system partition space

### 5. Load ROM

* Load your ROM from your directory and build it.
* Input `system.img` size (must be smaller than available free space).

### 6. Copy output files

* Copy `system.img`, `vendor.img`, and `boot.img` from the output folder into the `E1001Fixer` folder.

### 7. Flash images

* Flash `system.img` to the system partition.
* Flash `vendor.img` to the vendor partition.
* Flash `boot.img` to the boot partition.

### 8. Done!

* Reboot your phone.

---

## Notes

* Always **backup your original ROM** before using this tool.
* Intended for users familiar with flashing, rooting, o
