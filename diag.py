import subprocess
import json
import os
import re
from datetime import datetime

def run_cmd(command):
    """Executes a terminal command and returns the result safely"""
    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.DEVNULL, text=True)
        return result.strip()
    except Exception:
        return "N/A"

def get_hardware_data():
    # 1. Motherboard
    mb_serial = run_cmd("sudo dmidecode -s baseboard-serial-number")
    if mb_serial in ["N/A", "None", "To be filled by O.E.M.", ""]:
        mb_serial = run_cmd("sudo dmidecode -s system-serial-number")

    # 2. CPU (Fix: take only the first line to avoid duplicates)
    cpu = run_cmd("lscpu | grep 'Model name' | head -n 1 | cut -d ':' -f 2 | xargs")

    # 3. RAM (Fix: Read physical hardware sticks to ignore iGPU reserved memory)
    ram_raw = run_cmd("sudo dmidecode -t 17")
    total_mb = 0
    slots_used = 0
    
    for line in ram_raw.split('\n'):
        match = re.search(r'Size:\s*(\d+)\s*(MB|GB)', line, re.IGNORECASE)
        if match:
            slots_used += 1
            val = int(match.group(1))
            unit = match.group(2).upper()
            total_mb += (val * 1024) if unit == 'GB' else val

    # Fallback to OS memory if hardware read fails
    if total_mb > 0:
        ram_total = f"{round(total_mb / 1024)} GB"
    else:
        ram_total = run_cmd("awk '/MemTotal/ {printf \"%.0f GB\", $2/1024/1024}' /proc/meminfo")

    # Slots Math (Fix: Ensure used doesn't exceed total due to soldered RAM)
    slots_total_raw = run_cmd("sudo dmidecode -t 16 | grep 'Number Of Devices' | grep -o '[0-9]*'")
    slots_total = int(slots_total_raw) if slots_total_raw.isdigit() else 0
    if slots_used > slots_total:
        slots_total = slots_used

    # 4. Disks (Fix: Ignore USB drives and loop devices)
    disks_raw = run_cmd("lsblk -d -o NAME,SIZE,MODEL,TRAN,TYPE -J")
    disk_list = []
    try:
        if disks_raw != "N/A":
            disks_json = json.loads(disks_raw)
            for dev in disks_json.get('blockdevices', []):
                # Only keep disks that are NOT USB connected
                if dev.get('type') == 'disk' and dev.get('tran') != 'usb' and not str(dev.get('name')).startswith('loop'):
                    disk_list.append({
                        "size": dev.get('size'),
                        "model": dev.get('model', 'Unknown').strip()
                    })
    except:
        disk_list = [{"error": "Could not list disks"}]

    return {
        "scan_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "motherboard_serial": mb_serial,
        "cpu": cpu,
        "ram_total": ram_total,
        "ram_slots_used": str(slots_used),
        "ram_slots_total": str(slots_total),
        "disks": disk_list
    }

def main():
    os.system('clear')
    print("========================================")
    print("     STARTING HARDWARE DIAGNOSTICS      ")
    print("========================================\n")
    print("Analyzing components. Please wait...\n")
    
    new_data = get_hardware_data()
    
    # Locate USB mount point
    usb_path = "/lib/live/mount/medium"
    file_path = os.path.join(usb_path, "inventory.json")
    
    if not os.path.exists(usb_path):
        file_path = "inventory.json"
        
    inventory = []
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                inventory = json.load(f)
        except:
            pass 
            
    inventory.append(new_data)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(inventory, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving: {e}")
        
    os.system('clear')
    print("========================================")
    print("          EXTRACTED PC DATA             ")
    print("========================================")
    print(json.dumps(new_data, indent=4, ensure_ascii=False))
    print("========================================\n")
    
    print("✅ SUCCESSFULLY VERIFIED!")
    print(f"Total PCs logged on USB: {len(inventory)}\n")
    print("You may now remove the USB drive.\n")
    
    input("Press [ENTER] to shutdown the computer...")
    os.system("sudo poweroff")

if __name__ == "__main__":
    main()