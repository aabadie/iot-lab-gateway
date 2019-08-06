import os

from gateway_code.utils.cc2650_fw_verifier import Cc2650FirmwareVerifier

VERIFIER = Cc2650FirmwareVerifier()

VERIFIER.has_valid_ccfg(os.path.join('gateway_code', 'static', 'cc2650-launchpad_autotest.elf'))
