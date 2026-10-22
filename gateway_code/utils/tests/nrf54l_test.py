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


"""Test utils.nrf54l."""

import logging

import mock
import pytest
from intelhex import IntelHex
from testfixtures import LogCapture

from gateway_code.config import static_path
from gateway_code.open_nodes.common.node_jlink import NodeJLinkBase
from gateway_code.open_nodes.common.node_nrf54l import NodeNrf54lBase

from .. import nrf54l

APPROTECT_PROTECT0 = nrf54l.UICR_BASE
ERASEPROTECT_PROTECT1 = nrf54l.UICR_BASE + 0x07C


class NodeNrf54lTest(NodeNrf54lBase, NodeJLinkBase):
    """nRF54L node, as the nRF54L open nodes"""

    TYPE = "nrf54l_test"
    FW_IDLE = static_path("nrf52840dk_idle.elf")


@pytest.fixture(name="log")
def fixture_log():
    """Capture the gateway_code logs."""
    log = LogCapture("gateway_code", level=logging.DEBUG)
    yield log
    log.uninstall()


def write_bin(tmp_path, data):
    """Write a binary firmware."""
    path = tmp_path / "firmware.bin"
    path.write_bytes(data)
    return str(path)


def test_protect_registers():
    """PROTECT0 and PROTECT1 of the four protections, in the UICR."""
    addresses = [address for address, _, _ in nrf54l.PROTECT_REGISTERS.values()]
    assert len(set(addresses)) == 8
    assert min(addresses) == APPROTECT_PROTECT0
    assert max(addresses) == ERASEPROTECT_PROTECT1


@pytest.mark.parametrize(
    "name",
    [
        "APPROTECT.PROTECT0",
        "SECUREAPPROTECT.PROTECT1",
        "AUXAPPROTECT.PROTECT0",
        "ERASEPROTECT.PROTECT1",
    ],
)
@pytest.mark.parametrize("value", [0x00000000, 0x50FA50FA, 0xFFFFFF00])
def test_enabled_protect_registers(name, value):
    """Any value written in a protection register but the erased one counts."""
    address = nrf54l.PROTECT_REGISTERS[name][0]
    ihex = IntelHex()
    ihex.puts(address, value.to_bytes(4, "little"))
    assert nrf54l.nrf52.enabled_protect_registers(ihex, nrf54l.PROTECT_REGISTERS) == [name]


def test_check_firmware_bin(tmp_path, log):
    """Binary firmwares writing the protection registers are refused."""
    erased = write_bin(tmp_path, bytes([0xFF] * 0x80))
    assert nrf54l.check_firmware(erased, binary=True, address=nrf54l.UICR_BASE)
    log.check()

    protected = write_bin(tmp_path, bytes(4))
    assert nrf54l.check_firmware(protected, binary=True, address=0x0)
    assert not nrf54l.check_firmware(protected, binary=True, address=ERASEPROTECT_PROTECT1)
    log.check(
        (
            "gateway_code",
            "ERROR",
            "Firmware enables the nRF54L UICR ERASEPROTECT.PROTECT1 protection, "
            "refused: it would lock the node",
        )
    )


def test_check_firmware_elf(log):
    """Elf firmwares not writing the UICR pass."""
    assert nrf54l.check_firmware(static_path("nrf52840dk_idle.elf"))
    log.check()


def test_node_check_firmware(tmp_path):
    """nRF54L nodes check the firmware with the nRF54L registers."""
    node = NodeNrf54lTest.__new__(NodeNrf54lTest)
    firmware = write_bin(tmp_path, bytes(4))
    assert node.check_firmware(None)
    assert node.check_firmware(NodeNrf54lTest.FW_IDLE)
    assert node.check_firmware(firmware, binary=True, offset=0x1000)
    assert not node.check_firmware(firmware, binary=True, offset=APPROTECT_PROTECT0)


@mock.patch("gateway_code.open_nodes.common.node_openocd.NodeOpenOCDBase.flash")
def test_node_flash(flash, tmp_path):
    """A refused firmware is not flashed."""
    flash.return_value = 0
    node = NodeNrf54lTest.__new__(NodeNrf54lTest)
    firmware = write_bin(tmp_path, bytes(4))

    assert node.flash(firmware, binary=True, offset=APPROTECT_PROTECT0) == 1
    flash.assert_not_called()
    assert node.flash(firmware, binary=True) == 0
    flash.assert_called_with(firmware, True, 0)
