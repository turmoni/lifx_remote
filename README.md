# lifx_remote
Control LIFX bulbs via a remote control (or anything else) that presents
itself as a keyboard. Ideally use a remote control that sends a single,
distinct keypress per button.

## Requirements

Linux, python >= 3.5, [python-evdev](https://github.com/gvalkov/python-evdev),
[aiolifx](https://github.com/frawau/aiolifx),
[pyyaml](https://github.com/yaml/pyyaml).

## Running

```lifx_remote.py <path to config>```

A unit file has also been provided for you to modify if you like that kind of
thing.

You will need permission to access the device you wish to use, which usually
is only allowed by root. Configuring this is outside of the scope of this
document.

## Configuration

Configuration is all in YAML, and consists of two parts. Firstly, and most
simply, the device name:
```yaml
device_name: Some Device Here
```

This configures the device to use for input. Run `evtest` to get a list of
available devices, or look in dmesg. The script will grab every device with
this name (in my case, two keyboards and a mouse) and have exclusive access to
their input (so your login prompt/desktop session won't be spammed with
keypresses).

Secondly, the list of keypress → action mappings. Each keypress can trigger as
many actions as you wish, with as many combinations of bulbs as you want. The
basic structure is:
```yaml
mappings:
  KEY_NAME:
    - bulbs: <bulb config>
      action: <action config
    - <additional steps>
```

The `KEY_NAME` can be obtained by running `evtest` and pressing relevant
buttons.

Both `bulbs` and `action` can be omitted. If `bulbs` is omitted, the previously
used bulbs will be controlled, whilst if `action` is ommitted, no action will
take place but the currently controlled bulbs will change.

`bulbs` configuration takes the following form:

```yaml
names:
  - Bulb 1
  - Bulb 2
group: Group Name
location: Location Name
exclude:
  - Not This One
```

Any combination of the above can be used and will select all matching bulbs
(except those that have been specifically excluded). If a bulb is covered
by more than one of `names`, `group`, or `location`, it will still only have
operations applied to it once.

`action` configuration is as follows:

```yaml
brightness: (+|-|0-65535)
hue: (+|-|0-65535)
saturation: (+|-|0-65535)
kelvin: (+|-|2500-9000)
power: (toggle|0|1)
```

Any combination of the above can be specified.
