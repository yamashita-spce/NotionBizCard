import uuid, os, paramiko
import configparser

config = configparser.ConfigParser()
config.read("../config.ini", encoding="utf-8")

KEY_PATH = config["HOST_WIN"]["SCP_KEY_PATH"]
UPLORD_PATH = config["HOST_WIN"]["UPLOAD_PATH"]
SERVER = config["HOST_WIN"]["SERVER"]
USERNAME = config["HOST_WIN"]["USER"]


def scp_upload_via_key(card_path, hearing_paths):
    unique_id = uuid.uuid4().hex
    remote_base = UPLORD_PATH + "/" + unique_id
    remote_card_dir = remote_base + "/card"
    remote_hearing_dir = remote_base + "/hearing"

    key = load_private_key(KEY_PATH)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=SERVER, username=USERNAME, pkey=key)

    sftp = ssh.open_sftp()
    for d in (remote_base, remote_card_dir, remote_hearing_dir):
        try:
            sftp.mkdir(d)
        except IOError:
            pass

    sftp.put(card_path, f"{remote_card_dir}/{os.path.basename(card_path)}")
    for local in hearing_paths:
        sftp.put(local, f"{remote_hearing_dir}/{os.path.basename(local)}")

    sftp.close()
    ssh.close()
    

    return unique_id, remote_base



def delete_remote_folder(unique_id: str):
    """
    リモートのフォルダを削除する
    """

    remote_base = UPLORD_PATH + unique_id
    key = load_private_key(KEY_PATH)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=SERVER, username=USERNAME, pkey=key)

    stdin, stdout, stderr = ssh.exec_command(f"rm -rf {remote_base}")
    exit_status = stdout.channel.recv_exit_status()
    ssh.close()

    if exit_status != 0:
        err = stderr.read().decode().strip()
        raise RuntimeError(f"リモート削除失敗 (exit {exit_status}): {err}")
    

def load_private_key(path):
    path = os.path.expanduser(path)
    for KeyClass in (paramiko.ECDSAKey, paramiko.RSAKey):
        try:
            return KeyClass.from_private_key_file(path)
        except paramiko.SSHException:
            continue