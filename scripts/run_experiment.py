#!/usr/bin/python3.6

import argparse
import glob
import sys
import pathlib
from threading import Thread
import time

import bfasst


def main():
    parser = argparse.ArgumentParser()

    # Find all experiments in the experiments/ directory
    experiments = []
    for dir_item in bfasst.EXPERIMENTS_PATH.glob('*'):
        if (bfasst.EXPERIMENTS_PATH / dir_item).is_file() and dir_item.suffix == ".yaml":
            experiments.append(dir_item.stem)

    # Set up command line arguments
    parser.add_argument("experiment_name", choices=experiments,
                        help="Name of folder in experiments directory (with experiment.yaml file).")
    parser.add_argument("--force", action='store_true')
    args = parser.parse_args()

    # Build experiment object
    experiment = bfasst.experiment.Experiment(args.experiment_name)

    # Create temp folder
    build_dir = pathlib.Path.cwd() / "build" / args.experiment_name
    if not build_dir.is_dir():
        build_dir.mkdir(parents = True)
    elif not args.force:
        bfasst.utils.error("Build directory", build_dir, "already exists.  Use --force to overwrite")
    else:
        pass

    # For each design
    ljust = experiment.get_longest_design_name() + 5
    statuses = []
    thread_rets = [None] * len(experiment.designs)
    threads = [None] * len(experiment.designs)

    def flow_fcn_wrapper(design, design_dir, ret_array, ind):
        status = experiment.flow_fcn(design, design_dir)
        ret_array[ind] = (design, status)
    
    for i in range(len(experiment.designs)):

        design = experiment.designs[i]
        # Create a per-design build directory
        design_dir = build_dir / design.top
        try:
            design_dir.mkdir()
        except FileExistsError:
            pass


        #sys.stdout.write(design.design_dir.ljust(ljust))
        #sys.stdout.flush()
        
        # Run the design
        #status = experiment.flow_fcn(design, design_dir)
        #statuses.append(status)
        #sys.stdout.write(str(status))
        #sys.stdout.write("\n")

        threads[i] = Thread(target = flow_fcn_wrapper, args=(design, design_dir, thread_rets, i))
        threads[i].start()

    all_threads_done = False
    done_threads = [False] * len(threads)
    while not all_threads_done:
        all_threads_done = True
        for i in range(len(threads)):
            if threads[i].is_alive():
                all_threads_done = False
            if (not threads[i].is_alive()) and (done_threads[i] == False):
                done_threads[i] = True
                design, status = thread_rets[i]
                sys.stdout.write(design.design_dir.ljust(ljust))
                sys.stdout.flush()
                sys.stdout.write(str(status))
                sys.stdout.write("\n")
                statuses.append(status)
        time.sleep(1)

    print("")
    print("-" * 80)
    print("Status By Type")
    print("-" * 80)

    # types_to_print = [  bfasst.status.SynthStatus,
    #                     bfasst.status.OptStatus,
    #                     bfasst.status.ImplStatus,
    #                     bfasst.status.BitReverseStatus,
    #                     bfasst.status.CompareStatus]
    
    j = 30
    print("Synth Error:".ljust(j), len([s for s in statuses if type(s.status) == bfasst.status.SynthStatus and s.error]))
    print("Opt Error:".ljust(j), len([s for s in statuses if type(s.status) == bfasst.status.OptStatus and s.error]))
    print("Impl Error:".ljust(j), len([s for s in statuses if type(s.status) == bfasst.status.ImplStatus and s.error]))
    print("Bit Reverse Error:".ljust(j), len([s for s in statuses if type(s.status) == bfasst.status.BitReverseStatus and s.error]))
    print("Compare Error:".ljust(j), len([s for s in statuses if type(s.status) == bfasst.status.CompareStatus and s.error and s.status != bfasst.status.CompareStatus.NOT_EQUIVALENT]))
    print("Compare Not Equivalent:".ljust(j), len([s for s in statuses if s.status == bfasst.status.CompareStatus.NOT_EQUIVALENT]))
    print("Compare Equivalent:".ljust(j), len([s for s in statuses if s.status == bfasst.status.CompareStatus.SUCCESS]))


    # print(types)

    print("-" * 80)


if __name__ == "__main__":
    main()
