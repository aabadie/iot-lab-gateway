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


"""Check that a firmware for nRF54L boards doesn't lock the debug access.

The UICR protection registers of the nRF54L are written like the RRAM. Each
protection has two registers, PROTECT0 and PROTECT1. The access port
protections are off only with the erased value 0xFFFFFFFF, the erase
protection is on with 0x50FA50FA: any other written value is refused.
"""

from typing import Tuple

from gateway_code.utils import nrf52

UICR_BASE = 0x00FFD000
ERASED_VALUE = 0xFFFFFFFF


def _register(offset: int) -> Tuple[int, int, Tuple[int, ...]]:
    """UICR protection register at `offset`, off only when erased"""
    return (UICR_BASE + offset, ERASED_VALUE, (ERASED_VALUE,))


PROTECT_REGISTERS: nrf52.ProtectRegisters = {
    "APPROTECT.PROTECT0": _register(0x000),
    "APPROTECT.PROTECT1": _register(0x01C),
    "SECUREAPPROTECT.PROTECT0": _register(0x020),
    "SECUREAPPROTECT.PROTECT1": _register(0x03C),
    "AUXAPPROTECT.PROTECT0": _register(0x040),
    "AUXAPPROTECT.PROTECT1": _register(0x05C),
    "ERASEPROTECT.PROTECT0": _register(0x060),
    "ERASEPROTECT.PROTECT1": _register(0x07C),
}


def check_firmware(firmware_path: str, binary: bool = False, address: int = 0) -> bool:
    """Return False if the firmware writes one of the UICR protection registers.

    :param firmware_path: elf firmware, or binary firmware if `binary`
    :param binary: the firmware is a binary file
    :param address: flash address of a binary firmware
    """
    return nrf52.check_firmware(firmware_path, binary, address, PROTECT_REGISTERS, "nRF54L")
