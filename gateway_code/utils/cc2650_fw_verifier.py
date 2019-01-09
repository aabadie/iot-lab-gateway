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
""" CC2650 boards firmware verifier """

# pylint: disable=too-few-public-methods
import logging
import os
import shlex
import tempfile
from array import array

from intelhex import IntelHex

from gateway_code.utils import subprocess_timeout


LOGGER = logging.getLogger('gateway_code')


class Cc2650FirmwareVerifier(object):
    """ Firmware verifier for CC2650 Launchpad """
    DEVNULL = open(os.devnull, 'w')

    TIMEOUT = 100

    def __init__(self, verb=False, timeout=TIMEOUT):
        self.timeout = timeout

        self.out = None if verb else self.DEVNULL

        self._debug = None

    def _call_cmd(self, command_str):
        """ Run the given command_str"""

        kwargs = self._args(command_str)

        try:
            return subprocess_timeout.call(**kwargs)
        except subprocess_timeout.TimeoutExpired:
            return 1

    def _args(self, command_str):
        """ Get subprocess arguments for command_str """
        # Generate full command arguments
        args = shlex.split(command_str)
        return {'args': args, 'stdout': self.out, 'stderr': self.out}

    def has_valid_ccfg(self, firmware_path):
        """
        Verifies that the intelhex has
        the correct Bootloader configuration in .ccfg (last page of Flash)
        """
        hex_file = tempfile.NamedTemporaryFile(suffix='.hex')
        hex_path = hex_file.name

        to_hex_command = 'objcopy -I elf32-big -O ihex {elf} {hex}'
        cmd = to_hex_command.format(elf=firmware_path, hex=hex_path)
        LOGGER.debug(' to intelhex CMD %s' % cmd)
        ret_value = self._call_cmd(cmd)

        LOGGER.debug(' to intelhex ret_value %s' % ret_value)

        if ret_value == 0:
            ihex = IntelHex(hex_path)

            ccfg = ihex.tobinarray(start=0x0001FFA8, size=88)

            LOGGER.debug(' to intelhex ccfg %s' % ccfg)
            if ccfg[48:52] == array('B', [0xFF, 0xFF, 0xFF, 0xFF]):
                # filled gap
                return True
            if ccfg[48:52] == array('B', [0xC5, 0x0B, 0xFE, 0xC5]):
                return True
            return False
        return False
