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
like flash memory. A firmware that has data at their address enables the
access port protection (no more debugger, so no more flashing) or the erase
protection (no more ERASEALL to recover). These firmwares are refused.
"""

import logging
from typing import List

import elftools.common.exceptions
from elftools.elf.elffile import ELFFile
from intelhex import IntelHex

LOGGER = logging.getLogger("gateway_code")

UICR_APPROTECT = 0x10001208
UICR_ERASEPROTECT = 0x1000120C
UICR_REGISTER_SIZE = 4

PROTECT_REGISTERS = {
    "APPROTECT": UICR_APPROTECT,
    "ERASEPROTECT": UICR_ERASEPROTECT,
}


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


def written_protect_registers(ihex: IntelHex) -> List[str]:
    """Names of the protection registers the memory image writes to."""
    written = []
    for name, address in PROTECT_REGISTERS.items():
        segment = ihex[address : address + UICR_REGISTER_SIZE]
        if len(segment) > 0:
            written.append(name)
    return written


def check_firmware(firmware_path: str, binary: bool = False, address: int = 0) -> bool:
    """Return False if the firmware writes the APPROTECT or ERASEPROTECT registers.

    :param firmware_path: elf firmware, or binary firmware if `binary`
    :param binary: the firmware is a binary file
    :param address: flash address of a binary firmware
    """
    try:
        ihex = firmware_to_ihex(firmware_path, binary, address)
    except (OSError, ValueError) as err:
        LOGGER.error("Invalid firmware: %s", err)
        return False

    written = written_protect_registers(ihex)
    if written:
        LOGGER.error(
            "Firmware writes the nRF52 UICR %s register(s), refused: it would lock the node",
            " and ".join(written),
        )
        return False
    return True
