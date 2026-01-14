import abc
import os
import shlex
import subprocess
from .exceptions import ExecutionError
from .models import Host

class Executor(abc.ABC):
    @abc.abstractmethod
    def run(self, cmd: list[str], timeout: int = 10) -> str:
        pass

class LocalExecutor(Executor):
    def run(self, cmd: list[str], timeout: int = 10) -> str:
        env = os.environ.copy()
        env["LC_ALL"] = "C"
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=timeout,
                env=env
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise ExecutionError(cmd, f"Timed out after {timeout}s")
        except subprocess.CalledProcessError as e:
            raise ExecutionError(cmd, e.stderr.strip())

class SshExecutor(Executor):
    def __init__(self, host: Host):
        self.host = host

    def run(self, cmd: list[str], timeout: int = 10) -> str:
        ssh_cmd = [
            "ssh",
            "-o", "ConnectTimeout=5",
            "-o", "StrictHostKeyChecking=no",
            "-o", "LogLevel=ERROR",
            f"{self.host.user}@{self.host.address}",
            "--",
            shlex.join(cmd)
        ]
        
        env = os.environ.copy()
        env["LC_ALL"] = "C"
        
        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=timeout,
                env=env
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise ExecutionError(ssh_cmd, f"SSH Timed out after {timeout}s")
        except subprocess.CalledProcessError as e:
            raise ExecutionError(ssh_cmd, e.stderr.strip())
