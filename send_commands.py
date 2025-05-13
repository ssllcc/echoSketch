import subprocess

def send_copy_command(mac_user, mac_ip):
    ssh_command = (
        f'ssh {mac_user}@{mac_ip} '
        '"osascript -e \'tell application \\"Notes\\" to activate\' -e \'tell application \\"System Events\\" to keystroke \\"c\\" using {command down}\'"'
    )
    try:
        subprocess.run(ssh_command, shell=True, check=True)
        print("Copy command sent successfully.")
    except subprocess.CalledProcessError as e:
        print("Failed to send copy command.", e)

def send_paste_command(mac_user, mac_ip):
    ssh_command = (
        f'ssh {mac_user}@{mac_ip} '
        '"osascript -e \'tell application \\"Notes\\" to activate\' -e \'tell application \\"System Events\\" to keystroke \\"v\\" using {command down}\'"'
    )
    try:
        subprocess.run(ssh_command, shell=True, check=True)
        print("Paste command sent successfully.")
    except subprocess.CalledProcessError as e:
        print("Failed to send paste command.", e)

def send_youtube_command(mac_user, mac_ip):
    ssh_command = (
        f'ssh {mac_user}@{mac_ip} '
        '"osascript -e \'tell application \\"Google Chrome\\" to open location \\"https://www.youtube.com\\"\' "'
    )

    try:
        subprocess.run(ssh_command, shell=True, check=True)
        print("Direct YouTube command sent successfully.")
    except subprocess.CalledProcessError as e:
        print("Failed to send Direct YouTube command.", e)

def send_volume_up_command(mac_user, mac_ip):
    ssh_command = (
        f'ssh {mac_user}@{mac_ip} '
        # '"osascript -e \'tell application \\"Notes\\" to activate\' -e \'tell application \\"System Events\\" to keystroke \\"v\\" using {command down}\'"'
        '"osascript -e \'tell applicatoin \\"Notes\\" to activate\' -e \'tell application \\"System Events\\" to set volume output volume (output volume of (get volume settings) - 5)"'
    )
    try:
        subprocess.run(ssh_command, shell=True, check=True)
        print("Volume up command sent successfully.")
    except subprocess.CalledProcessError as e:
        print("Failed to send volume up command.", e)

def send_volume_down_command(mac_user, mac_ip):
    ssh_command = (
        f'ssh {mac_user}@{mac_ip} '
        # '"osascript -e \'tell application \\"Notes\\" to activate\' -e \'tell application \\"System Events\\" to keystroke \\"v\\" using {command down}\'"'
        '"osascript -e \'tell applicatoin \\"Notes\\" to activate\' -e \'tell application \\"System Events\\" to set volume output volume (output volume of (get volume settings) + 5)"'
    )
    try:
        subprocess.run(ssh_command, shell=True, check=True)
        print("Volume down command sent successfully.")
    except subprocess.CalledProcessError as e:
        print("Failed to send volume down command.", e)
