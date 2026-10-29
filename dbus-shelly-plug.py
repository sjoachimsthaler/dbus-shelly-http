#!/usr/bin/env python

# vim: ts=2 sw=2 et


# import normal packages
import platform
import logging
import logging.handlers
import sys
import os
import time

import requests # for http GET
import configparser # for config/ini file


# our own packages from victron
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '/opt/victronenergy/dbus-systemcalc-py/ext/velib_python'))


def parsePlugStatus(status, voltage):
  """Maps the /status response of a Shelly Plug S (Gen1) to pvinverter values.

  Gen1 reports only power (W) and a total counter (Wh), so voltage is a fixed
  value and current is calculated."""
  meter = status['meters'][0]

  if not meter.get('is_valid', True):
    raise ValueError("Meter of the plug reports invalid data")

  power = float(meter['power'])

  return {
    'serial': status['mac'],
    'power': power,
    'voltage': voltage,
    'current': power / voltage,
    'energy': float(meter['total']) / 1000, # Wh -> kWh
  }


class DbusShellyPlugService:
  def __init__(self, paths, productname='Shelly Plug S PV', connection='Shelly Plug S Gen1 HTTP'):
    from vedbus import VeDbusService

    config = self._getConfig()

    deviceinstance = int(config['DEFAULT']['DeviceInstance'])
    customname = config['DEFAULT']['CustomName']
    role = config['DEFAULT']['Role']
    self._phase = int(config['DEFAULT']['Phase'])

    if role != 'pvinverter':
      logging.error("Configured Role: %s is not in the allowed list", role)
      sys.exit(1)

    if self._phase not in (1, 2, 3):
      logging.error("Configured Phase: %s must be 1, 2 or 3", self._phase)
      sys.exit(1)

    servicename = 'com.victronenergy.' + role

    self._dbusservice = VeDbusService("{}.http_{:02d}".format(servicename, deviceinstance))
    self._paths = paths

    logging.debug("%s /DeviceInstance = %d" % (servicename, deviceinstance))

    # Create the management objects, as specified in the ccgx dbus-api document
    self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
    self._dbusservice.add_path('/Mgmt/ProcessVersion', 'Unkown version, and running on Python ' + platform.python_version())
    self._dbusservice.add_path('/Mgmt/Connection', connection)

    # Create the mandatory objects
    self._dbusservice.add_path('/DeviceInstance', deviceinstance)
    self._dbusservice.add_path('/ProductId', 0xA144)
    self._dbusservice.add_path('/DeviceType', 345)
    self._dbusservice.add_path('/ProductName', productname)
    self._dbusservice.add_path('/CustomName', customname)
    self._dbusservice.add_path('/Latency', None)
    self._dbusservice.add_path('/FirmwareVersion', 0.1)
    self._dbusservice.add_path('/HardwareVersion', 0)
    self._dbusservice.add_path('/Connected', 1)
    self._dbusservice.add_path('/Role', role)
    self._dbusservice.add_path('/Position', int(config['DEFAULT']['Position'] or 0))
    self._dbusservice.add_path('/Serial', self._getPlugSerial())
    self._dbusservice.add_path('/UpdateIndex', 0)

    # add path values to dbus
    for path, settings in self._paths.items():
      self._dbusservice.add_path(
        path, settings['initial'], gettextcallback=settings['textformat'], writeable=True, onchangecallback=self._handlechangedvalue)

    # last update
    self._lastUpdate = 0

    gobject.timeout_add(2500, self._update)

    # add _signOfLife 'timer' to get feedback in log
    gobject.timeout_add(self._getSignOfLifeInterval()*60*1000, self._signOfLife)


  def _getConfig(self):
    config = configparser.ConfigParser()
    config.read("%s/config.ini" % (os.path.dirname(os.path.realpath(__file__))))
    return config


  def _getSignOfLifeInterval(self):
    value = self._getConfig()['DEFAULT']['SignOfLifeLog']

    if not value:
      value = 0

    return int(value)


  def _getPlugStatus(self):
    config = self._getConfig()

    URL = "http://%s/status" % (config['ONPREMISE']['Host'])

    auth = None
    if config['ONPREMISE']['Username']:
      auth = (config['ONPREMISE']['Username'], config['ONPREMISE']['Password'])

    plug_r = requests.get(url = URL, auth = auth, timeout=5)

    # check for response
    if not plug_r:
      raise ConnectionError("No response from Shelly Plug - %s" % (URL))

    try:
      return parsePlugStatus(plug_r.json(), float(config['ONPREMISE']['Voltage']))
    except (KeyError, IndexError, TypeError):
      raise ValueError("Unexpected response from Shelly Plug - %s" % (URL))


  def _getPlugSerial(self):
    return self._getPlugStatus()['serial']


  def _signOfLife(self):
    logging.info("--- Start: sign of life ---")
    logging.info("Last _update() call: %s" % (self._lastUpdate))
    logging.info("Last '/Ac/Power': %s" % (self._dbusservice['/Ac/Power']))
    logging.info("--- End: sign of life ---")
    return True


  def _update(self):
    try:
      data = self._getPlugStatus()

      prefix = '/Ac/L%d' % (self._phase)

      self._dbusservice[prefix + '/Voltage'] = data['voltage']
      self._dbusservice[prefix + '/Current'] = data['current']
      self._dbusservice[prefix + '/Power'] = data['power']
      self._dbusservice[prefix + '/Energy/Forward'] = data['energy']
      self._dbusservice['/Ac/Power'] = data['power']
      self._dbusservice['/Ac/Energy/Forward'] = data['energy']
      self._dbusservice['/Connected'] = 1

      # increment UpdateIndex - to show that new data is available an wrap
      self._dbusservice['/UpdateIndex'] = (self._dbusservice['/UpdateIndex'] + 1 ) % 256

      self._lastUpdate = time.time()

    except (ValueError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, ConnectionError) as e:
      logging.critical('Error getting data from Shelly Plug - check network or plug status. Setting power values to 0. Details: %s', e, exc_info=e)

      # no stale values (e.g. plug offline), energy keeps its last value
      for path in ('/Ac/Power', '/Ac/L%d/Power' % (self._phase), '/Ac/L%d/Current' % (self._phase)):
        self._dbusservice[path] = 0
      self._dbusservice['/Connected'] = 0
      self._dbusservice['/UpdateIndex'] = (self._dbusservice['/UpdateIndex'] + 1 ) % 256

    except Exception as e:
      logging.critical('Error at %s', '_update', exc_info=e)

    # return true, otherwise add_timeout will be removed from GObject
    return True


  def _handlechangedvalue(self, path, value):
    logging.debug("someone else updated %s to %s" % (path, value))
    return True # accept the change


def getLogLevel():
  config = configparser.ConfigParser()
  config.read("%s/config.ini" % (os.path.dirname(os.path.realpath(__file__))))

  logLevelString = config['DEFAULT']['LogLevel']

  if logLevelString:
    level = logging.getLevelName(logLevelString)
  else:
    level = logging.INFO

  return level


def main():
  global gobject

  #configure logging
  logging.basicConfig(      format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            level=getLogLevel(),
                            handlers=[
                                logging.FileHandler("%s/current.log" % (os.path.dirname(os.path.realpath(__file__)))),
                                logging.StreamHandler()
                            ])

  try:
      logging.info("Start");

      from gi.repository import GLib as gobject
      from dbus.mainloop.glib import DBusGMainLoop

      # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
      DBusGMainLoop(set_as_default=True)

      #formatting
      _kwh = lambda p, v: (str(round(v, 2)) + ' kWh')
      _a = lambda p, v: (str(round(v, 1)) + ' A')
      _w = lambda p, v: (str(round(v, 1)) + ' W')
      _v = lambda p, v: (str(round(v, 1)) + ' V')

      #start our main-service
      DbusShellyPlugService(
        paths={
          '/Ac/Energy/Forward': {'initial': 0, 'textformat': _kwh},
          '/Ac/Power': {'initial': 0, 'textformat': _w},
          '/Ac/L1/Voltage': {'initial': 0, 'textformat': _v},
          '/Ac/L2/Voltage': {'initial': 0, 'textformat': _v},
          '/Ac/L3/Voltage': {'initial': 0, 'textformat': _v},
          '/Ac/L1/Current': {'initial': 0, 'textformat': _a},
          '/Ac/L2/Current': {'initial': 0, 'textformat': _a},
          '/Ac/L3/Current': {'initial': 0, 'textformat': _a},
          '/Ac/L1/Power': {'initial': 0, 'textformat': _w},
          '/Ac/L2/Power': {'initial': 0, 'textformat': _w},
          '/Ac/L3/Power': {'initial': 0, 'textformat': _w},
          '/Ac/L1/Energy/Forward': {'initial': 0, 'textformat': _kwh},
          '/Ac/L2/Energy/Forward': {'initial': 0, 'textformat': _kwh},
          '/Ac/L3/Energy/Forward': {'initial': 0, 'textformat': _kwh},
        })

      logging.info('Connected to dbus, and switching over to gobject.MainLoop() (= event based)')

      mainloop = gobject.MainLoop()
      mainloop.run()

  except (ValueError, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
    logging.critical('Error in main type %s', str(e))
  except Exception as e:
    logging.critical('Error at %s', 'main', exc_info=e)

if __name__ == "__main__":
  main()
