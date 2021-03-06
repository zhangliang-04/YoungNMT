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


class Scheduler(object):
    def __init__(self):
        pass

    @classmethod
    def setup(cls, args, model):
        raise NotImplementedError

    def learning_rate(self, step):
        raise NotImplementedError

    def state_dict(self):
        raise NotImplementedError

    def load_state_dict(self, state_dict):
        raise NotImplementedError
