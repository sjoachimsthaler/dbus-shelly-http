import importlib.util
import json
import os

here = os.path.dirname(os.path.abspath(__file__))

spec = importlib.util.spec_from_file_location("plug", os.path.join(here, "..", "dbus-shelly-plug.py"))
plug = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plug)

with open(os.path.join(here, "shelly-plug-status.json")) as f:
  data = plug.parsePlugStatus(json.load(f), 230.0)

assert data['serial'] == 'AABBCC112233'
assert data['power'] == 412.35
assert data['voltage'] == 230.0
assert abs(data['current'] - 412.35 / 230.0) < 1e-9
assert data['energy'] == 98.765

try:
  plug.parsePlugStatus({'mac': 'x', 'meters': [{'power': 1, 'total': 1, 'is_valid': False}]}, 230.0)
  raise SystemExit("invalid meter must raise")
except ValueError:
  pass

gen2 = plug.parsePlugStatus({
  'sys': {'mac': 'AABBCC445566'},
  'switch:0': {'id': 0, 'output': True, 'apower': 300.5, 'voltage': 231.2, 'current': 1.3, 'aenergy': {'total': 5000.0}},
}, 230.0)
assert gen2 == {'serial': 'AABBCC445566', 'power': 300.5, 'voltage': 231.2, 'current': 1.3, 'energy': 5.0}

print("ok", data)
