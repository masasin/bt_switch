import shlex

class BtSwitchError(Exception):
    pass

class ExecutionError(BtSwitchError):
    def __init__(self, cmd: list[str], stderr: str):
        self.cmd = cmd
        self.stderr = stderr
        super().__init__(f"Command failed: {shlex.join(cmd)}\nError: {stderr}")

class ConfigurationError(BtSwitchError):
    pass
