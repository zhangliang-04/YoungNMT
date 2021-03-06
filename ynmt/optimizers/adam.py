#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) Jason Young (杨郑鑫).
#
# E-Mail: <AI.Jason.Young@outlook.com>
# 2020-06-29 18:54
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


import torch

from ynmt.optimizers import register_optimizer, Optimizer


@register_optimizer('adam')
class Adam(Optimizer):
    def __init__(self, parameters, learning_rate=0.001, betas=(0.9, 0.999), epsilon=1e-08):
        adam_optimizer = torch.optim.Adam(
            parameters,
            lr=learning_rate,
            betas=betas,
            eps=epsilon
        )
        super(Adam, self).__init__(adam_optimizer)

    @classmethod
    def setup(cls, args, model):
        parameters = (parameter for parameter in model.parameters() if parameter.requires_grad and parameter.is_leaf)
        adam = cls(
            parameters,
            learning_rate=args.learning_rate,
            betas=(args.beta1, args.beta2),
            epsilon=args.epsilon
        )

        return adam
