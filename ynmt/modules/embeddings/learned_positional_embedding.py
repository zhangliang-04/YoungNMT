#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) Jason Young (杨郑鑫).
#
# E-Mail: <AI.Jason.Young@outlook.com>
# 2020-06-28 11:50
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


import math
import torch


class LearnedPositionalEmbedding(torch.nn.Module):
    def __init__(self, embedding_number, dimension):
        super(LearnedPositionalEmbedding, self).__init__()
        self.weight = torch.nn.Parameter(torch.Tensor(embedding_number, dimension))
        torch.nn.init.normal_(self.weight)

    def forward(self, position):
        torch.index_select(self.weight, 0, position)
