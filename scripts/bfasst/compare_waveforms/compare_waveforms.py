"""The main comparison tool for comparing two netlists."""
import argparse
from pathlib import Path
from bfasst.compare_waveforms.file_parsing import parse_files, parse_diff
from bfasst.compare_waveforms.file_generation import (testbench_generator,
tcl_generator, waveform_generator)
from bfasst.compare_waveforms.templates import get_paths

def generate_files(multiple_files, paths, test_num):
    """The main function that generates testbenches and TCL files. It begins by calling the
    parsers for the input & output names, then
    it calls the testbench generators, finally it calls the TCL generators. It then increments
    to the next file and clears the data structure."""
    # testbench.
    data = {}  # Contains all of the IOs for the design.
    for i in range(2):
        with open(paths["file"][i], "r") as file:

            if i == 1:
                #file_rewriter.fix_file(paths, i)
                # Rewrites the files to have correct module names
                data = parse_files.parse_reversed(paths, i)
                # Finds the IO names and bit sizes
                paths["test"].unlink()  # Gets rid of the test.v file

            else:
                #file_rewriter.fix_file(paths, i)
                # Rewrites the files to have correct module names
                if multiple_files:
                    # The logic for how to parse the file depends on whether or not there are
                    # multiple verilog files involved in a design
                    data = parse_files.parse_reversed(paths, i)
                    # Finds the IO names and bit sizes
                else:
                    data = parse_files.parse(file.name)

            if i == 0:
                # Create the initial testbench with randomized inputs for all input ports
                # (based upon bit-size)
                testbench_generator.generate_first_testbench(
                    paths, test_num, data, i
                )
            else:  # Build off of the old testbench to keep the same randomized values
                testbench_generator.generate_testbench(paths, data, i)

            if i == 0:
                tcl_generator.generate_first_tcl(paths, data, i)
                # The first TCL will be generated based upon the IO port names
            else:
                tcl_generator.generate_tcl(paths, i)
                # The second TCL just needs to change module names from the first one

            waveform_generator.generate_vcd(paths, i)
            # All previously generated files are ran through Icarus and then GTKwave, creating
            # the files we need.

def run_test(paths):
    """A function that generates the wavefiles from the testbenches, runs gtkwave w/ the TCLs
    generated earlier on the wavefiles
    that have just been generated, then checks the difference between gtkwave's two outputs. If
    there are more than 32 lines that
    are different, the designs must be unequivalent."""
    return parse_diff.check_diff(paths)
    # Checks the two VCD files against each other. Returns either equivalent or not depending
    # on how many lines are different.

def parse_args():

    """Creates the argument parser for the Vivado Launcher."""

    if __file__ != "compare_waveforms.py":
        package_path = Path(Path().absolute()/__file__[0:len(__file__)-20])
    else:
        package_path = Path().absolute()

    parser = argparse.ArgumentParser(description="Launch Vivado.")

    parser.add_argument("-b", "--base", metavar="BasePath", action='store',
    help="Base path to store files (defaults to the out folder).",
    default=str(package_path/"out"))

    parser.add_argument("-t", "--tech", metavar="TechLib", action='store',
    help="Path to tech library (defaults to cells_sim.v in templates).",
    default=str(package_path/"templates/cells_sim.v"))

    parser.add_argument(
        "-v", "--verilog", metavar="VerilogTB", action='store',
        help="Location of the testbench template file (defaults to sample_tb.v in templates).",
        default=str(package_path/"templates/sample_tb.v"))

    parser.add_argument("fileA", metavar="File1", help="Path to file 1.")
    parser.add_argument("fileB", metavar="File2", help="Path to file 2.")

    args = parser.parse_args()

    return get_paths.get_paths(args.base, args.tech, args.template, args.fileA, args.fileB)

if __name__ == "__main__":
    tests = input("Input number of tests to run")
    generate_files(False, parse_args(), 10)
