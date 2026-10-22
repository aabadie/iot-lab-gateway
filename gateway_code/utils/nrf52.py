# -*- coding:utf-8 -*-

# This file is a part of IoT-LAB gateway_code
# Copyright (C) 2015 INRIA (Contact: admin@iot-lab.info)
# Contributor(s) : see AUTHORS file
#
# This software is governed by the CeCILL license under French law
# and abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL
# license as circulated by CEA, CNRS and INRIA at the following URL
# http://www.cecill.info.
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL license and that you accept its terms.


"""Check that a firmware for nRF52 boards doesn't lock the debug access.

The UICR registers APPROTECT and ERASEPROTECT of the nRF52 are written
like flash memory. A firmware that writes a value enabling the access port
protection (no more debugger, so no more flashing) or the erase protection
(no more ERASEALL to recover) could brick the board: it is refused. Values
keeping the protection off are accepted.
"""

import logging
from typing import Dict, List, Optional, Tuple

import elftools.common.exceptions
from elftools.elf.elffile import ELFFile
from intelhex import IntelHex

LOGGER = logging.getLogger("gateway_code")

UICR_APPROTECT = 0x10001208
UICR_ERASEPROTECT = 0x1000120C
UICR_REGISTER_SIZE = 4

# Protection registers by name: (address, mask, values keeping the protection off)
ProtectRegisters = Dict[str, Tuple[int, int, Tuple[int, ...]]]

# Field PALL of each register: (mask, values keeping the protection off).
# APPROTECT: 0xFF Disabled, 0x5A HwDisabled (newer revisions), else enabled.
# ERASEPROTECT: 0xFFFF Disabled, else enabled.
PROTECT_REGISTERS: ProtectRegisters = {
    "APPROTECT": (UICR_APPROTECT, 0xFF, (0xFF, 0x5A)),
    "ERASEPROTECT": (UICR_ERASEPROTECT, 0xFFFF, (0xFFFF,)),
}

ERASED_BYTE = 0xFF


def elf_to_ihex(firmware_path: str) -> IntelHex:
    """Memory image of an elf firmware, as written by a programmer.

    The loadable segments are placed at their physical (load) address, as
    `objcopy -O ihex` does.

    :raises: ValueError if the file is not a valid elf file.
    """
    ihex = IntelHex()
    try:
        with open(firmware_path, "rb") as _file:
            elffile = ELFFile(_file)
            for segment in elffile.iter_segments():
                if segment["p_type"] != "PT_LOAD" or segment["p_filesz"] == 0:
                    continue
                ihex.puts(segment["p_paddr"], segment.data())
    except elftools.common.exceptions.ELFError:
        raise ValueError("Not a valid elf file")
    return ihex


def bin_to_ihex(firmware_path: str, address: int) -> IntelHex:
    """Memory image of a binary firmware flashed at `address`."""
    ihex = IntelHex()
    ihex.loadbin(firmware_path, offset=address)
    return ihex


def firmware_to_ihex(firmware_path: str, binary: bool = False, address: int = 0) -> IntelHex:
    """Memory image of an elf firmware, or of a binary flashed at `address`."""
    if binary:
        return bin_to_ihex(firmware_path, address)
    return elf_to_ihex(firmware_path)


def register_value(ihex: IntelHex, address: int) -> int:
    """Little endian 32 bits value written at `address`.

    Bytes not written by the image stay erased (0xFF).
    """
    ihex.padding = ERASED_BYTE
    data = bytes(ihex[addr] for addr in range(address, address + UICR_REGISTER_SIZE))
    return int.from_bytes(data, "little")


def enabled_protect_registers(
    ihex: IntelHex, registers: Optional[ProtectRegisters] = None
) -> List[str]:
    """Names of the protection registers the memory image enables.

    :param registers: protection registers, as PROTECT_REGISTERS (default)
    """
    if registers is None:
        registers = PROTECT_REGISTERS
    enabled = []
    for name, (address, mask, off_values) in registers.items():
        value = register_value(ihex, address)
        if value & mask not in off_values:
            enabled.append(name)
    return enabled


def check_firmware(
    firmware_path: str,
    binary: bool = False,
    address: int = 0,
    registers: Optional[ProtectRegisters] = None,
    chip: str = "nRF52",
) -> bool:
    """Return False if the firmware enables one of the protection registers.

    :param firmware_path: elf firmware, or binary firmware if `binary`
    :param binary: the firmware is a binary file
    :param address: flash address of a binary firmware
    :param registers: protection registers, as PROTECT_REGISTERS (default)
    :param chip: chip name in the error message
    """
    try:
        ihex = firmware_to_ihex(firmware_path, binary, address)
    except (OSError, ValueError) as err:
        LOGGER.error("Invalid firmware: %s", err)
        return False

    enabled = enabled_protect_registers(ihex, registers)
    if enabled:
        LOGGER.error(
            "Firmware enables the %s UICR %s protection, refused: it would lock the node",
            chip,
            " and ".join(enabled),
        )
        return False
    return True
