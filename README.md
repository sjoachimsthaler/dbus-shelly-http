# dbus-shelly-plug
Integrate a PV micro inverter (e.g. Growatt NEO 2000M-X2) into [Victron Energies Venus OS](https://github.com/victronenergy/venus) by reading its output through a Shelly Plug S (Gen1) via HTTP.

The service polls `http://<plug>/status` every 2.5 s and publishes `com.victronenergy.pvinverter.http_<DeviceInstance>` on the DBus (power, energy, L1-L3). Based on [dbus-kostal](../dbus-kostal).

## Install
Log in to the GX device via SSH as root and run:

```
wget https://github.com/sjoachimsthaler/dbus-shelly-http/archive/refs/heads/main.zip
unzip main.zip "dbus-shelly-http-main/*" -d /data
mv /data/dbus-shelly-http-main /data/dbus-shelly-plug
rm main.zip
```

The folder must be named `dbus-shelly-plug` because the service name is derived from it. Then set the plug IP in the config and run the installer:

```
nano /data/dbus-shelly-plug/config.ini
chmod a+x /data/dbus-shelly-plug/install.sh
/data/dbus-shelly-plug/install.sh
```

The installer links the service into `/service` and adds itself to `/data/rc.local`, so it survives firmware updates.

To update, run `/data/dbus-shelly-plug/uninstall.sh`, remove the folder (keep a copy of your `config.ini`) and repeat the steps above.

Alternatively, copy the folder manually to `/data/dbus-shelly-plug`.

## Config
| Section | Value | Explanation |
| --- | --- | --- |
| DEFAULT | CustomName | Name shown on the GX |
| DEFAULT | DeviceInstance | Unique per device, default 41 (Kostal service uses 40) |
| DEFAULT | Position | 0 = AC input 1, 1 = AC output, 2 = AC input 2 |
| DEFAULT | Phase | Phase the inverter feeds in (1, 2, 3) |
| ONPREMISE | Host | IP or hostname of the plug |
| ONPREMISE | Username / Password | Only if the plug has a restricted login |
| ONPREMISE | Voltage | Gen1 reports no voltage; fixed value, current = power / voltage |

## Limitations
The plug only measures active power and energy at the socket (including the inverter's own consumption). No MPPT, error or grid data.

When the plug is unreachable, power is set to 0 and `/Connected` to 0.

## Test
`python3 -I testdata/test.py` checks the status parsing against `testdata/shelly-plug-status.json`.
