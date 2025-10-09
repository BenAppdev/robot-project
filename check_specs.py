import subprocess
import shutil

def run_command(command):
    """Runs a shell command and returns its output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return f"Error running command '{command}': {e.stderr or str(e)}"

def print_header(title):
    """Prints a formatted header."""
    print("\n" + "="*20)
    print(f" {title}")
    print("="*20)

def check_os():
    """Checks Operating System details."""
    print_header("Operating System")
    # The lsb_release command may not be available
    if shutil.which("lsb_release"):
        os_info = run_command("lsb_release -a")
    else:
        os_info = run_command("cat /etc/os-release")
    print(os_info)

def check_cpu():
    """Checks CPU details."""
    print_header("CPU Information")
    cpu_info = run_command("lscpu | grep -E 'Model name|Core(s) per socket|Socket(s)|Architecture'")
    print(cpu_info)

def check_ram():
    """Checks RAM details."""
    print_header("RAM Information")
    ram_info = run_command("free -h")
    print(ram_info)

def check_gpu():
    """Checks for an NVIDIA GPU."""
    print_header("GPU Information")
    # nvidia-smi is the standard tool for NVIDIA GPUs
    if not shutil.which("nvidia-smi"):
        print("`nvidia-smi` command not found. No NVIDIA GPU detected or drivers are not installed.")
        return

    gpu_info = run_command("nvidia-smi")
    print(gpu_info)

def check_disk():
    """Checks disk space."""
    print_header("Disk Space")
    disk_info = run_command("df -h /") # Check the root filesystem
    print(disk_info)

if __name__ == "__main__":
    print("Gathering system specifications...")
    check_os()
    check_cpu()
    check_ram()
    check_gpu()
    check_disk()
    print("\n" + "="*20)
    print("Spec check complete.")
    print("="*20)
