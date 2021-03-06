#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) Jason Young (杨郑鑫).
#
# E-Mail: <AI.Jason.Young@outlook.com>
# 2020-06-29 21:56
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


import os

from ynmt.schedulers.scheduler import Scheduler

from ynmt.utilities.registration import Registration, import_modules


scheduler_registration = Registration(Scheduler)


def build_scheduler(args, model):
    return scheduler_registration[args.name].setup(args, model)

def register_scheduler(registration_name):
    return scheduler_registration.register(registration_name)


import_modules('ynmt.schedulers', os.path.dirname(__file__))
