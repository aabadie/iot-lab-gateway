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

""" Open Docker Node experiment implementation """

import logging
import shlex
import subprocess

from gateway_code.common import logger_call
from gateway_code.board_config import board_config as board_config
from gateway_code.utils.docker import Docker
from gateway_code.open_nodes.common.node_no import NodeNoBase

LOGGER = logging.getLogger('gateway_code')

DOCKER_IMAGE = "fitiotlab/iot-lab/iot-lab-jupyterlab"
DOCKER_RUN_CMD = "docker run -ti --rm -d --name node-docker -h {host} {image} bash"
DOCKER_KILL_CMD = "docker kill node-docker"


class NodeDocker(NodeNoBase):
    """ Open Docker node implementation """

    TYPE = 'docker'

    def __init__(self):
        board_cfg = board_config.BoardConfig()
        self.docker_cmd = DOCKER_RUN_CMD.format(host=board_cfg.hostname,
                                                image=DOCKER_IMAGE)
        self.docker = Docker()

    @logger_call("Node Docker: Setup node")
    def setup(self, firmware_path=None):
        """Launch the docker container."""
        ret = subprocess.call(shlex.split(self.docker_cmd))
        ret += self.docker.start()
        return ret

    @logger_call("Node Docker: teardown node")
    def teardown(self):
        """Stop the docker container."""
        return subprocess.call(shlex.split(DOCKER_KILL_CMD))
