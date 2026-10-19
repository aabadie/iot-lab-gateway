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


"""Test utils.nrf52."""

import logging
import os

import pytest
from intelhex import IntelHex
from testfixtures import LogCapture

from gateway_code.config import static_path
from gateway_code.open_nodes.node_m3 import NodeM3
from gateway_code.open_nodes.node_nrf52dk import NodeNrf52Dk
from gateway_code.open_nodes.node_nrf52840mdk import NodeNrf52840Mdk

from .. import nrf52

FIRMWARES_DIR = os.path.join(os.path.dirname(__file__), "elftarget_firmwares")

# Built with arm-none-eabi-gcc from a vector table and two constants placed
# in the UICR APPROTECT and ERASEPROTECT registers, both set to 0 (enabled).
APPROTECT_ELF = os.path.join(FIRMWARES_DIR, "nrf52_approtect.elf")


@pytest.fixture(name="log")
def fixture_log():
    """Capture the gateway_code logs."""
    log = LogCapture("gateway_code", level=logging.DEBUG)
    yield log
    log.uninstall()


def write_bin(tmp_path, size=16):
    """Write a binary firmware of `size` bytes."""
    path = tmp_path / "firmware.bin"
    path.write_bytes(bytes(range(size)))
    return str(path)


def test_elf_to_ihex():
    """The loadable segments are placed at their load address."""
    ihex = nrf52.elf_to_ihex(APPROTECT_ELF)
    assert ihex.minaddr() == 0x0
    assert ihex.maxaddr() == nrf52.UICR_ERASEPROTECT + 3
    assert ihex.gets(nrf52.UICR_APPROTECT, 4) == b"\x00\x00\x00\x00"

    ihex = nrf52.elf_to_ihex(static_path("nrf52dk_idle.elf"))
    assert ihex.maxaddr() < nrf52.UICR_APPROTECT


def test_elf_to_ihex_invalid(tmp_path):
    """A binary file is not an elf file."""
    with pytest.raises(ValueError, match="Not a valid elf file"):
        nrf52.elf_to_ihex(write_bin(tmp_path))


def test_bin_to_ihex(tmp_path):
    """A binary is placed at its flash address."""
    ihex = nrf52.bin_to_ihex(write_bin(tmp_path), 0x1000)
    assert ihex.minaddr() == 0x1000
    assert ihex.maxaddr() == 0x100F


def put_register(ihex, address, value):
    """Write a 32 bits little endian register value in the image."""
    ihex.puts(address, value.to_bytes(4, "little"))


def test_register_value():
    """Bytes not written stay erased."""
    ihex = IntelHex()
    assert nrf52.register_value(ihex, nrf52.UICR_APPROTECT) == 0xFFFFFFFF
    ihex[nrf52.UICR_APPROTECT] = 0x5A
    assert nrf52.register_value(ihex, nrf52.UICR_APPROTECT) == 0xFFFFFF5A


@pytest.mark.parametrize(
    "approtect,eraseprotect,enabled",
    [
        (None, None, []),
        (0xFFFFFFFF, 0xFFFFFFFF, []),
        (0xFFFFFF5A, None, []),
        (0x0000005A, None, []),
        (0x000000FF, 0x0000FFFF, []),
        (0x00000000, None, ["APPROTECT"]),
        (0xFFFFFF00, None, ["APPROTECT"]),
        (0x12345678, None, ["APPROTECT"]),
        (None, 0x00000000, ["ERASEPROTECT"]),
        (None, 0xFFFF0000, ["ERASEPROTECT"]),
        (0x00000000, 0x00000000, ["APPROTECT", "ERASEPROTECT"]),
    ],
)
def test_enabled_protect_registers(approtect, eraseprotect, enabled):
    """Only the values enabling the protection count."""
    ihex = IntelHex()
    ihex[nrf52.UICR_APPROTECT - 1] = 0x00
    ihex[nrf52.UICR_ERASEPROTECT + 4] = 0x00
    if approtect is not None:
        put_register(ihex, nrf52.UICR_APPROTECT, approtect)
    if eraseprotect is not None:
        put_register(ihex, nrf52.UICR_ERASEPROTECT, eraseprotect)
    assert nrf52.enabled_protect_registers(ihex) == enabled


def test_enabled_protect_registers_partial():
    """A single byte enabling the protection counts."""
    ihex = IntelHex()
    ihex[nrf52.UICR_ERASEPROTECT + 1] = 0x00
    assert nrf52.enabled_protect_registers(ihex) == ["ERASEPROTECT"]


def test_check_firmware_elf(log):
    """Elf firmwares: idle firmwares pass, protecting firmware refused."""
    for firmware in ("nrf52dk_idle.elf", "nrf52840dk_autotest.elf", "dwm3001_idle.elf"):
        assert nrf52.check_firmware(static_path(firmware))
    log.check()

    assert not nrf52.check_firmware(APPROTECT_ELF)
    log.check(
        (
            "gateway_code",
            "ERROR",
            "Firmware enables the nRF52 UICR APPROTECT and ERASEPROTECT protection, "
            "refused: it would lock the node",
        )
    )


def test_check_firmware_bin(tmp_path, log):
    """Binary firmwares are checked at their flash address."""
    firmware = write_bin(tmp_path)
    assert nrf52.check_firmware(firmware, binary=True, address=0x0)
    assert nrf52.check_firmware(firmware, binary=True, address=nrf52.UICR_APPROTECT - 16)
    assert nrf52.check_firmware(firmware, binary=True, address=nrf52.UICR_ERASEPROTECT + 4)
    log.check()

    assert not nrf52.check_firmware(firmware, binary=True, address=nrf52.UICR_APPROTECT - 15)
    assert not nrf52.check_firmware(firmware, binary=True, address=nrf52.UICR_ERASEPROTECT)
    assert [record.levelname for record in log.records] == ["ERROR", "ERROR"]


def test_check_firmware_bin_protection_off(tmp_path, log):
    """A binary writing the UICR with the protection off is accepted."""
    path = tmp_path / "uicr.bin"
    path.write_bytes(bytes([0x5A, 0, 0, 0]) + bytes([0xFF] * 4))
    assert nrf52.check_firmware(str(path), binary=True, address=nrf52.UICR_APPROTECT)
    log.check()


def test_check_firmware_invalid(tmp_path, log):
    """Unreadable or invalid firmwares are refused."""
    assert not nrf52.check_firmware(str(tmp_path / "missing.elf"))
    assert not nrf52.check_firmware(write_bin(tmp_path))
    assert [record.levelname for record in log.records] == ["ERROR", "ERROR"]


def test_node_check_firmware(tmp_path):
    """nRF52 nodes check the firmware, the others accept it."""
    firmware = write_bin(tmp_path)
    for node_class in (NodeNrf52Dk, NodeNrf52840Mdk):
        node = node_class.__new__(node_class)
        assert node.check_firmware(None)
        assert node.check_firmware(node_class.FW_IDLE)
        assert not node.check_firmware(APPROTECT_ELF)
        assert node.check_firmware(firmware, binary=True, offset=0x1000)
        assert not node.check_firmware(firmware, binary=True, offset=nrf52.UICR_APPROTECT)

    node = NodeM3.__new__(NodeM3)
    assert node.check_firmware(APPROTECT_ELF)
