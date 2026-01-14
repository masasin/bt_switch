import subprocess
import pytest
from bt_switch.exceptions import ExecutionError
from bt_switch.executor import LocalExecutor, SshExecutor
from bt_switch.models import Host

def test_local_executor_success(mock_subprocess):
    mock_subprocess.return_value.stdout = "output\n"
    executor = LocalExecutor()
    result = executor.run(["echo", "hello"])
    assert result == "output"
    
    # Verify environment variable setup
    call_args = mock_subprocess.call_args
    assert call_args.kwargs["env"]["LC_ALL"] == "C"

def test_local_executor_timeout(mock_subprocess):
    mock_subprocess.side_effect = subprocess.TimeoutExpired(["cmd"], 10)
    executor = LocalExecutor()
    with pytest.raises(ExecutionError, match="Timed out"):
        executor.run(["sleep", "100"])

def test_local_executor_error(mock_subprocess):
    error = subprocess.CalledProcessError(1, ["cmd"], stderr="some error")
    mock_subprocess.side_effect = error
    executor = LocalExecutor()
    with pytest.raises(ExecutionError, match="some error"):
        executor.run(["fail"])

def test_ssh_executor_success(mock_subprocess):
    mock_subprocess.return_value.stdout = "remote output"
    host = Host(address="1.2.3.4", user="user")
    executor = SshExecutor(host)
    
    result = executor.run(["ls", "-la"])
    assert result == "remote output"
    
    # Verify SSH command construction
    cmd_arg = mock_subprocess.call_args.args[0]
    assert cmd_arg[0] == "ssh"
    assert "user@1.2.3.4" in cmd_arg
    assert "--" in cmd_arg
    # The command at the end should be shell-joined
    assert cmd_arg[-1] == "ls -la"

def test_ssh_executor_timeout(mock_subprocess):
    mock_subprocess.side_effect = subprocess.TimeoutExpired(["ssh"], 5)
    host = Host(address="1.2.3.4", user="user")
    executor = SshExecutor(host)
    with pytest.raises(ExecutionError, match="SSH Timed out"):
        executor.run(["ls"])
