#!/usr/bin/python
# -*- coding: utf-8 -*-

# Job Céspedes <jobcespedes@gmail.com>
# MIT License (see licenses/MIT-license.txt or https://opensource.org/licenses/MIT)

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = r'''
---
author: Job Céspedes (@jobcespedes)
module: pxeboot_hpilo
version_added: "2.8"
short_description: Boot once into pxe(network) mode using hp ilo
description:
    - This module boot once a host into pxe(network) mode using hp ilo. It boots the server when off. This module requires the hpilo python module.
options:
    host:
        description:
            - The HP iLO hostname/address that is linked to the physical system.
        required: true
    login:
        description:
            - The login name to authenticate to the HP iLO interface.
        default: Administrator
    password:
        description:
            - The password to authenticate to the HP iLO interface.
        default: admin
    ssl_version:
        description:
            - Change the ssl_version used.
        default: TLSv1
        choices: [ "SSLv3", "SSLv23", "TLSv1", "TLSv1_1", "TLSv1_2" ]
    device:
        description:
            - Whether to boot into pxe(network) or not(normal)
        default: network
        choices: [ "network", "normal" ]
requirements:
    - python-hpilo
notes:
    - This module ought to be run from a system that can access the HP iLO
      interface directly. It could be either by using local_action or using delegate_to
'''

EXAMPLES = r'''
- name: Boot once into pxe mode using hp ilo
  pxeboot_hpilo:
    host: YOUR_ILO_ADDRESS
    login: YOUR_ILO_LOGIN
    password: YOUR_ILO_PASSWORD
  delegate_to: localhost
'''

RETURN = r'''
power_status:
    description: The current power state of the machine.
    returned: success
    type: str
    sample: 'ON', 'OFF', 'BOOTING'
one_time_boot_status:
    description: the one time boot state of the host
    returned: success
    type: str
    sample: network
'''

import time
import traceback
import warnings

HPILO_IMP_ERR = None
try:
    import hpilo
    HAS_HPILO = True
except ImportError:
    HPILO_IMP_ERR = traceback.format_exc()
    HAS_HPILO = False


from ansible.module_utils.basic import AnsibleModule, missing_required_lib

# Suppress warnings from hpilo
warnings.simplefilter('ignore')

def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        host=dict(type='str', required=True),
        login=dict(type='str', default='Administrator'),
        password=dict(type='str', default='admin', no_log=True),
        ssl_version=dict(type='str', default='TLSv1', choices=['SSLv3', 'SSLv23', 'TLSv1', 'TLSv1_1', 'TLSv1_2']),
        device=dict(type='str', default='network', choices=['network', 'normal'])
    )

    # seed the result dict in the object
    result = dict(
        changed=False,
        power_status='UNKNOWN',
        one_time_boot_status='UNKNOWN'
    )

    # AnsibleModule object
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # missing python requirement
    if not HAS_HPILO:
        module.fail_json(msg=missing_required_lib('python-hpilo'), exception=HPILO_IMP_ERR)

    # vars
    host = module.params['host']
    login = module.params['login']
    password = module.params['password']
    ssl_version = getattr(hpilo.ssl, 'PROTOCOL_' + module.params.get('ssl_version').upper().replace('V', 'v'))
    device = module.params['device']
    changed = False

    # ilo operation
    try:
        # ilo interface
        ilo = hpilo.Ilo(host, login=login, password=password, ssl_version=ssl_version)

        # get power status
        power_status = ilo.get_host_power_status()
        # get one time boot status
        one_time_boot_status = ilo.get_one_time_boot()

        # operate if not check mode
        if not module.check_mode:
            if device != one_time_boot_status:
                # try boot once
                try:
                    ilo.set_one_time_boot(device)
                    changed = True
                except hpilo.IloError:
                    time.sleep(60)
                    ilo.set_one_time_boot(device)
                    changed = True
            if changed:
                # set one time boot status
                one_time_boot_status = device
                if power_status == 'OFF':
                    # boot
                    ilo.press_pwr_btn()
                    # set power status
                    power_status = 'BOOTING'

        result['changed'] = changed
        result['power_status'] = power_status
        result['one_time_boot_status'] = one_time_boot_status

        # return
        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=str(e), **result)

def main():
    run_module()

if __name__ == '__main__':
    main()
