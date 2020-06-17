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


""" Module managing a docker container """

import shlex

import logging

from .external_process import ExternalProcess

LOGGER = logging.getLogger('gateway_code')


class Docker(ExternalProcess):
    """ Class providing a process that controls a Docker container

    It's implemented as a stoppable thread running docker exec piped via socat
    in a loop
    """
    DOCKER_EXEC_CMD = ("socat -d "
                       "TCP4-LISTEN:20000,reuseaddr-,echo=0,raw "
                       "exec:\"docker exec -ti node-docker bash\",pty")
    NAME = "docker"

    def __init__(self):
        self.process_cmd = shlex.split(self.DOCKER_EXEC_CMD)
        super(Docker, self).__init__()

    def check_error(self, retcode):
        """Print debug message and check error."""
        if retcode and self._run:
            LOGGER.warning('%s error or restarted', self.NAME)
        return retcode
