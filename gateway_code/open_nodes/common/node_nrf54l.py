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


"""Common checks of the open nodes based on a nRF54L microcontroller"""

from gateway_code.open_nodes.common.node_nrf52 import NodeNrf52Base
from gateway_code.utils import nrf54l


class NodeNrf54lBase(NodeNrf52Base):
    # pylint: disable=too-few-public-methods,no-member
    """Mixin of the nRF54L open nodes: refuse firmwares locking the debug access

    A node locked anyway (by a firmware setting the TAMPC signal protectors
    at runtime) is erased and unlocked by its openocd configuration.

    To put before the programmer base class: class Node(NodeNrf54lBase, NodeJLinkBase)
    """

    def check_firmware(self, firmware_path, binary=False, offset=0):
        """Return False if the firmware writes one of the UICR protection registers

        A binary firmware is flashed at ROM_START_ADDR + offset, as in `flash`.
        """
        if firmware_path is None:
            return True
        address = int(self.ROM_START_ADDR) + offset
        return nrf54l.check_firmware(firmware_path, binary, address)
