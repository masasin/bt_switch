from typing import Literal
from pydantic import BaseModel

class Device(BaseModel):
    mac: str
    name: str

class Host(BaseModel):
    address: str
    user: str
    protocol: Literal["ssh", "local"] = "ssh"
    driver_type: Literal["bluez", "macos"] = "bluez"

class DefaultSettings(BaseModel):
    default_device: str
    default_target: str

class AppConfig(BaseModel):
    devices: dict[str, Device]
    hosts: dict[str, Host]
    defaults: dict[str, DefaultSettings]
