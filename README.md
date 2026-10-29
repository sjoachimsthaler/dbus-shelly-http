# dbus-shelly-plug
Integrate a PV micro inverter (e.g. Growatt NEO 2000M-X2) into [Victron Energies Venus OS](https://github.com/victronenergy/venus) by reading its output through a Shelly Plug S (Gen1 or Gen2/Gen3) via HTTP.

The service polls `http://<plug>/status` (Gen2+: `/rpc/Shelly.GetStatus`) every 2.5 s and publishes `com.victronenergy.pvinverter.http_<DeviceInstance>` on the DBus (power, energy, L1-L3). Based on [dbus-kostal](../dbus-kostal).

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

Alternatively, copy the folder manually to `/data/dbus-shelly-plug`.

## Update
Your `config.ini` is kept. Run on the GX device as root:

```
cd /data
wget -O main.zip https://github.com/sjoachimsthaler/dbus-shelly-http/archive/refs/heads/main.zip
unzip -o main.zip "dbus-shelly-http-main/*" -x "dbus-shelly-http-main/config.ini" -d /data/update
cp -r /data/update/dbus-shelly-http-main/. /data/dbus-shelly-plug/
rm -r /data/update main.zip
chmod a+x /data/dbus-shelly-plug/*.sh /data/dbus-shelly-plug/service/run
pkill -f dbus-shelly-plug.py
```

The supervisor restarts the service with the new version. Check the log with `cat /data/dbus-shelly-plug/current.log` (if present) or `ps | grep dbus-shelly-plug`. New options may have been added to `config.ini` (see the Config table below); add them by hand.

## Config
| Section | Value | Explanation |
| --- | --- | --- |
| DEFAULT | CustomName | Name shown on the GX |
| DEFAULT | DeviceInstance | Unique per device, default 41 (Kostal service uses 40) |
| DEFAULT | Position | 0 = AC input 1, 1 = AC output, 2 = AC input 2 |
| DEFAULT | Phase | Phase the inverter feeds in (1, 2, 3) |
| ONPREMISE | Host | IP or hostname of the plug |
| ONPREMISE | Generation | 1 = Plug S Gen1, 2 = Plus Plug S and newer (Gen2/Gen3) |
| ONPREMISE | Username / Password | Only if the plug has a restricted login |
| ONPREMISE | Voltage | Gen1 reports no voltage; fixed value, current = power / voltage |

## Limitations
The plug only measures active power and energy at the socket (including the inverter's own consumption). No MPPT, error or grid data.

When the plug is unreachable, power is set to 0 and `/Connected` to 0.

## Test
`python3 -I testdata/test.py` checks the status parsing against `testdata/shelly-plug-status.json`.
