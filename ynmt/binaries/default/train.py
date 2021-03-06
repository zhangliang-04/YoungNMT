#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) Jason Young (杨郑鑫).
#
# E-Mail: <AI.Jason.Young@outlook.com>
# 2020-04-02 08:23
#
# This source code is licensed under the Apache-2.0 license found in the
# LICENSE file in the root directory of this source tree.


import torch

import ynmt.hocon.arguments as harg

from ynmt.utilities.apex import mix_precision
from ynmt.utilities.random import fix_random_procedure
from ynmt.utilities.logging import setup_logger, logging_level
from ynmt.utilities.checkpoint import load_checkpoint
from ynmt.utilities.visualizing import setup_visualizer
from ynmt.utilities.extractor import get_model_parameters_number
from ynmt.utilities.distributed import DistributedManager, distributed_main, distributed_data_sender, distributed_data_receiver, get_device_descriptor

from ynmt.tasks import build_task
from ynmt.models import build_model
from ynmt.schedulers import build_scheduler
from ynmt.optimizers import build_optimizer
from ynmt.trainers import build_trainer


def process_main(args, batch_queue, device_descriptor, workshop_semaphore, rank):
    logger = setup_logger(args.logger.name, logging_path=args.logger.path, logging_level=logging_level['INFO'])
    fix_random_procedure(args.random_seed)

    visualizer = setup_visualizer(
        args.visualizer.name, args.visualizer.server, args.visualizer.port,
        username=args.visualizer.username,
        password=args.visualizer.password,
        logging_path=args.visualizer.path,
        offline=args.visualizer.offline,
        overwrite=args.visualizer.overwrite,
    )
    is_station = rank == 0
    if is_station:
        logger.disabled = False | args.logger.off
        visualizer.disabled = False | args.visualizer.off
    else:
        logger.disabled = True
        visualizer.disabled = True

    validation_batches = distributed_data_receiver('list', batch_queue, workshop_semaphore)
    training_batches = distributed_data_receiver('generator', batch_queue, workshop_semaphore)

    ## Building Something
    
    # Build Task
    logger.info(f' * Building Task: \'{args.task.name}\' ...')
    task = build_task(args.task, logger)
    logger.info(f'   The construction of Task is complete.')

    # Load Ancillary Datasets
    logger.info(f' * Loading Ancillary Datasets ...')
    task.load_ancillary_datasets(args.task)
    logger.info(f'   Ancillary Datasets has been loaded.')

    # Build Model
    logger.info(f' * Building Model ...')
    model = build_model(args.model, task)
    parameters_number = get_model_parameters_number(model)
    parameters_number_str = str()
    for name, number in parameters_number.items():
        parameters_number_str += f'{name}: {number} Elements ;\n'
    parameters_number_str += f'Total: {sum(parameters_number.values())} Elements .\n'
    logger.info(
        f'\n ~ Model Architecture:'
        f'\n{model}'
        f'\n ~ Number of Parameters:'
        f'\n{parameters_number_str}'
    )

    logger.info(f' * Moving model to device of Trainer ...')
    model.to(device_descriptor)
    logger.info(f'   Completed.')

    # Loading Checkpoint
    checkpoint = load_checkpoint(args.checkpoint)
    if checkpoint is None:
        logger.info(f' * Training from scratch.')
    else:
        logger.info(f' * Training from checkpoint \'{args.checkpoint}\' at {checkpoint["step"]} steps.')

    # Build Scheduler
    logger.info(f' * Building Learning Rate Scheduler \'{args.scheduler.name}\' ...')
    scheduler = build_scheduler(args.scheduler, model)
    logger.info(f'   Completed.')

    # Build Optimizer
    logger.info(f' * Building Optimizer \'{args.optimizer.name}\' ...')
    optimizer = build_optimizer(args.optimizer, model)
    logger.info(f'   Completed.')

    model, optimizer = mix_precision(model, optimizer, mix_precision=args.mix_precision.on, optimization_level=args.mix_precision.optimization_level)
    if args.mix_precision.on:
        logger.info(f'Training in mix precision mode, optimization level is {args.mix_precision.optimization_level}')

    if checkpoint is not None:
        if not args.reset_scheduler:
            scheduler.load_state_dict(checkpoint['scheduler'])
            logger.info(f' | Reset Scheduler.')

        if not args.reset_optimizer:
            optimizer.load_state_dict(checkpoint['optimizer'])
            logger.info(f' | Reset Optimizer.')

        logger.info(f' | Loading Parameters ...')
        model.load_state_dict(checkpoint['model'], strict=False)
        logger.info(f' - Completed.')

    # Build Trainer
    logger.info(f' * Building Trainer \'{args.trainer.name}\' ...')
    trainer = build_trainer(args.trainer, task, model, scheduler, optimizer, device_descriptor, logger, visualizer)
    logger.info(f'   The construction of trainer is complete.')

    if checkpoint is not None and not args.reset_trainer:
        trainer.step = checkpoint['step']

    if visualizer.disabled:
        logger.info(f' * Visualizer Disabled.')
    else:
        # Open Visualizer
        logger.info(f' * Visualizer On.')
        visualizer.open()
        if visualizer.offline:
            logger.info(f'   Visualizer in Offline mode')
        else:
            logger.info(f'   Visualizer connection established between {visualizer.server}:{visualizer.port}')
        logger.info(f'   Visualizer logging to \'{visualizer.logging_path}\' .')

    # Launch Trainer
    logger.info(f' * Launch Trainer ...')
    logger.info(f'   Trainer Life Cycle: {trainer.life_cycle} update steps!')
    logger.info(f'   Saving checkpoint every {args.trainer.training_period} steps;')
    logger.info(f'   Validate every {args.trainer.validation_period} steps.')

    trainer.launch(training_batches, validation_batches)

    visualizer.close()


def build_batches(args, batch_queues, workshop_semaphore, world_size, ranks):
    logger = setup_logger(args.logger.name, logging_path=args.logger.path, logging_level=logging_level['INFO'])
    fix_random_procedure(args.random_seed)

    task = build_task(args.task, logger)

    distributed_data_sender(task.validation_batches(args.task), batch_queues, workshop_semaphore, world_size, ranks)

    distributed_data_sender(task.training_batches(args.task), batch_queues, workshop_semaphore, world_size, ranks)


def train(args):
    logger = setup_logger(args.logger.name, logging_path=args.logger.path, logging_level=logging_level['INFO'])

    device = args.distribution.device
    master_ip = args.distribution.master_ip
    master_port = args.distribution.master_port
    world_size = args.distribution.world_size
    ranks = args.distribution.ranks
    workshop_capacity = args.distribution.workshop_capacity
    number_process = len(ranks)

    if device == 'CPU':
        logger.info(' * Distribution on CPU ...')
    if device == 'GPU':
        logger.info(' * Distribution on GPU ...')
        assert torch.cuda.device_count() >= number_process, f'Insufficient GPU!'
    logger.info(f'   Master - tcp://{master_ip}:{master_port}')
    logger.info(f'   Ranks({ranks}) in World({world_size})')

    torch.multiprocessing.set_start_method('spawn')
    distributed_manager = DistributedManager()
    workshop_semaphore = torch.multiprocessing.Semaphore(world_size * workshop_capacity)

    consumers = list()
    batch_queues = list()
    for process_index in range(number_process):
        device_descriptor = get_device_descriptor(device, process_index)
        batch_queue = torch.multiprocessing.Queue(workshop_capacity)

        main_args = [args, batch_queue, device_descriptor, workshop_semaphore, ranks[process_index]]
        init_args = [device, master_ip, master_port, world_size, ranks[process_index]]
        consumer = torch.multiprocessing.Process(
            target=distributed_main,
            args=(
                process_main,
                main_args,
                init_args,
                distributed_manager.exception_queue,
            ),
            daemon=True
        )
        distributed_manager.manage(consumer)
        consumer.start()
        logger.info(f' * No.{process_index} Training Process start ...')
        logger.info(f'   PID: {consumer.pid};')
        logger.info(f'   Rank: {ranks[process_index]}/{world_size};')
        logger.info(f'   Device: {device_descriptor}.')

        consumers.append(consumer)
        batch_queues.append(batch_queue)

    producer = torch.multiprocessing.Process(
        target=build_batches,
        args=(
            args,
            batch_queues,
            workshop_semaphore,
            world_size,
            ranks,
        ),
        daemon=True
    )
    distributed_manager.manage(producer)
    producer.start()
    logger.info(f' = [Producer] = Batch Producer Process start (PID: {producer.pid}).')

    for consumer in consumers:
        consumer.join()
    producer.terminate()

    logger.info(' $ Finished !')


def main():
    args = harg.get_arguments()
    train_args = harg.get_partial_arguments(args, 'binaries.train')
    train_args.task = harg.get_partial_arguments(args, f'tasks.{train_args.task}')
    train_args.model = harg.get_partial_arguments(args, f'models.{train_args.model}')
    train_args.trainer = harg.get_partial_arguments(args, f'trainers.{train_args.trainer}')
    train(train_args)


if __name__ == '__main__':
    main()
