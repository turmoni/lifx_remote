#!/usr/bin/env python3
"""Control bulbs like a boss."""
import sys
import asyncio as aio
import argparse

from functools import partial

import yaml
import evdev
from evdev import ecodes

import aiolifx as alix

UDP_BROADCAST_PORT = 56700


class Bulbs():
    """Structure to hold bulbs."""
    def __init__(self):
        self.bulbs = []
        self.current_bulbs = []

    def register(self, bulb):
        """Register a bulb"""
        bulb.get_label()
        bulb.get_location()
        bulb.get_version()
        bulb.get_group()
        bulb.get_wififirmware()
        bulb.get_hostfirmware()
        self.bulbs.append(bulb)
        self.bulbs.sort(key=lambda x: x.label or x.mac_addr)

    def unregister(self, bulb):
        """Unregister a bulb"""
        idx = 0
        for x in list([y.mac_addr for y in self.bulbs]):
            if x == bulb.mac_addr:
                del self.bulbs[idx]
                break
            idx += 1

    def select_bulbs(self, names=None, group=None, location=None,
                     exclude=None):
        """Set our current bulbs based on name, group, and location"""
        self.current_bulbs = []
        for bulb in self.bulbs:
            if exclude and bulb.label in exclude:
                continue
            elif names and bulb.label in names:
                self.current_bulbs.append(bulb)
            elif group and bulb.group == group:
                self.current_bulbs.append(bulb)
            elif location and bulb.location == location:
                self.current_bulbs.append(bulb)


async def input_loop(dev, bulbs, key_mappings):
    """Read inputs from devices and throw them at the control code"""
    async for event in dev.async_read_loop():
        if event.type == ecodes.EV_KEY:
            initial_bulb_requests(evdev.categorize(event), bulbs, key_mappings)


def initial_bulb_requests(event, bulbs, key_mappings):
    """Select and/or fire off initial requests for a bulb"""
    if event.keystate == 1 and event.keycode in key_mappings:
        for step in key_mappings[event.keycode]:
            if 'bulbs' in step:
                bulbs.select_bulbs(**step['bulbs'])
            if 'action' in step:
                for bulb in bulbs.current_bulbs:
                    callback = partial(alter_bulb_state, step['action'])
                    bulb.get_color(callb=callback)


def alter_bulb_state(action, bulb, resp):
    """Deal with the response and alter bulb state as needed"""
    desired_colour = calculate_colour(action, resp.color)
    desired_power = calculate_power(action, resp.power_level)

    if desired_power != resp.power_level:
        bulb.set_power(desired_power)

    if desired_colour != list(resp.color):
        bulb.set_color(desired_colour)


def calculate_colour(action, colour):
    """Given a bulb's current state and desired modifiers, return the desired
       new state"""
    desired_colour = list(colour)
    states = {
        'hue': {
            'idx': 0,
            'increment': 1000,
        },
        'saturation': {
            'idx': 1,
            'increment': 6000,
        },
        'brightness': {
            'idx': 2,
            'increment': 6000,
        },
        'kelvin': {
            'idx': 3,
            'increment': 200,
            'min': 2500,
            'max': 9000,
        },
    }

    for key in action:
        if key not in states:
            continue

        cur = states[key]
        if action[key] == '+':
            desired_colour[cur['idx']] = min(desired_colour[cur['idx']]
                                             + cur['increment'],
                                             cur.get('max', 0xffff))
        elif action[key] == '-':
            desired_colour[cur['idx']] = max(desired_colour[cur['idx']]
                                             - cur['increment'],
                                             cur.get('min', 0))
        elif cur.get('min', 0) <= action[key] <= cur.get('max', 0xffff):
            desired_colour[cur['idx']] = action[key]

    return desired_colour


def calculate_power(action, power):
    """Should the bulb be on or off?"""
    desired_power = power

    if 'power' in action:
        if action['power'] == 'toggle':
            # This could probably be simplified, given it's either 1 or 0
            if power > 0:
                desired_power = 0
            else:
                desired_power = 1
        else:
            desired_power = int(action['power'])

    return desired_power


def main():
    """Do things with stuff."""
    parser = argparse.ArgumentParser(description='Control an LIFX bulb')
    parser.add_argument('config', type=open, nargs='?',
                        help='Config file location')

    args = parser.parse_args()

    if not args.config:
        parser.print_help()
        sys.exit()

    try:
        config = yaml.safe_load(args.config)
    except yaml.YAMLError as exc:
        print('Unable to parse config file: {0}'.format(str(exc)))
        sys.exit(1)

    inputs = []
    devices = [evdev.InputDevice(fn) for fn in evdev.list_devices()]
    for device in devices:
        if device.name == config['device_name']:
            dev = evdev.InputDevice(device.fn)
            dev.grab()
            inputs.append(dev)

    if not inputs:
        print('Unable to find device with a name of "{0}".'.format(
            config['device_name']))
        sys.exit(1)

    bulbs = Bulbs()
    loop = aio.get_event_loop()
    coro = loop.create_datagram_endpoint(
        partial(alix.LifxDiscovery, loop, bulbs),
        local_addr=('0.0.0.0', UDP_BROADCAST_PORT))
    loop.create_task(coro)

    for dev in inputs:
        aio.ensure_future(input_loop(dev, bulbs, config['mappings']))

    loop.run_forever()


if __name__ == '__main__':
    main()
