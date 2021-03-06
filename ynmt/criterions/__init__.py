#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) Jason Young (杨郑鑫).
#
# E-Mail: <AI.Jason.Young@outlook.com>
# 2020-06-30 09:38
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


import os

from ynmt.criterions.criterion import Criterion

from ynmt.utilities.registration import Registration, import_modules


criterion_registration = Registration(Criterion)


def build_criterion(args, task):
    return criterion_registration[args.name].setup(args, task)


def register_criterion(registration_name):
    return criterion_registration.register(registration_name)

import_modules('ynmt.criterions', os.path.dirname(__file__))
