# Waveform equivalence checker. Designed by Jake Edvenson.
# Relies on gtkwave, icarus-verilog, spydrnet, and numpy.
# To use this script, use ./scripts/run_design.py (DESIGN_PATH) xilinx_yosys_waveform
# The rest of the script should be self-explanitory. I've included a lot of user-prompts to make it very user-friendly.
# If vivado or F4PGA ever change there netlist-generating style, this file may need to be edited.
# I would check the fix_file function because this file currently alters the netlists so that spydrnet can parse them.

import pathlib
import re
from bfasst.compare_waveforms.Tools import analyze_graph
from bfasst.compare_waveforms.File_Parsing import parse_diff, parse_files
from bfasst.compare_waveforms.File_Generation import testbench_generator, tcl_generator, waveform_generator, file_rewriter
from bfasst.compare_waveforms.Templates import get_paths
from bfasst.compare_waveforms.Interface import waveform_interface
from bfasst.compare.base import CompareTool
from bfasst.status import Status, CompareStatus
from bfasst.tool import ToolProduct

#Data and Paths are structs that contain the parsed data from our design and the paths for all generated files.
data = parse_files.data
paths = get_paths.paths

"""The main class for comparing the waveforms."""

class Waveform_CompareTool(CompareTool):
    TOOL_WORK_DIR = "waveform"
    LOG_FILE_NAME = "log.txt"

    """The function that compares the netlists."""

    def compare_netlists(self, design, print_to_stdout=True):
        self.print_to_stdout = print_to_stdout
        log_path = self.work_dir / self.LOG_FILE_NAME
        generate_comparison = ToolProduct(None, log_path, self.check_compare_status)
        status = self.get_prev_run_status(
            tool_products=(generate_comparison,),
            dependency_modified_time=max(
                pathlib.Path(__file__).stat().st_mtime,
                design.reversed_netlist_path.stat().st_mtime,
            ),
        )

        if status is not None:
            if self.print_to_stdout:
                self.print_skipping_compare()
            return status

        if self.print_to_stdout:
            self.print_running_compare()

        paths = get_paths.get_paths(self, design) #Gets all paths used for file-generation

        multiple_files = waveform_interface.check_multiple_files(design) #Checks if there are multiple verilog files in the design.

        choice = waveform_interface.user_interface(paths) #Runs through the User interface, finds what the user wants to do.

        if choice ==  0: #Previous Status was unequivalent and User doesn't want to do any tests.
            return(Status(CompareStatus.NOT_EQUIVALENT))
        elif choice == 1: #User wants to re-generate files.
            self.generate_files(multiple_files)
            if self.run_test():
                return self.success_status
            else:
                return Status(CompareStatus.NOT_EQUIVALENT)
        elif choice == 2: #User wants to analyze graphs, previous Status was unequivalent
            analyze_graph.analyze_graphs(paths["build_dir"], paths["modules"][0])
            return Status(CompareStatus.NOT_EQUIVALENT)
        elif choice == 3: #Previous Status was equivalent and User doesn't want to do any tests.
            return Status(CompareStatus.SUCCESS)
        elif choice == 4: #User wants to analyze graphs, previous status was equivalent
            analyze_graph.analyze_graphs(paths["build_dir"], paths["modules"][0])
            return Status(CompareStatus.SUCCESS)



    """The main function that generates testbenches and TCL files. It begins by calling the parsers for the input & output names, then
    it calls the testbench generators, finally it calls the TCL generators. It then increments to the next file and clears the data structure."""

    def generate_files(self, multiple_files):
        test_num = 100  # Change this number if you want to run more or less than 100 tests in the testbench.
        file_rewriter.copy_files(paths) #Creates copies of the netlists that will be modified by the file_rewriter
        for i in range(2):
            with open(paths["path"][i]) as file:

                if i==1:
                    file_rewriter.fix_file(paths, i) #Rewrites the files to have correct module names
                    data = parse_files.parse_reversed(paths["file"][i], False, file.name, i, paths) #Finds the IO names and bit sizes

                else:
                    file_rewriter.fix_file(paths, i) #Rewrites the files to have correct module names
                    if multiple_files: #The logic for how to parse the file depends on whether or not there are multiple verilog files involved in a design
                        data = parse_files.parse_reversed(paths["file"][1], multiple_files, file.name, i, paths) #Finds the IO names and bit sizes
                    else:
                        data = parse_files.parse(file.name) #Finds the IO names and bit sizes
                tb_path = (paths["build_dir"] / (paths["modules"][i+1] + "_tb.v"))
                if tb_path.exists(): #Remove old testbench because we're making a new one
                    tb_path.unlink()
                
                if i==0: 
                    compare_path = paths["sample_tb"] #The implicit design will rely on an outline testbench

                else:
                    compare_path = paths["build_dir"] / (paths["modules"][1] + "_tb.v") #Reversed designs will build off of the initial, implicit design

                # Calls both the testbench and the TCL generators.
                with compare_path.open() as sample:
                    with tb_path.open("x") as tb:
                        for line in sample:
                            if i == 0: #Create the initial testbench with randomized inputs for all input ports (based upon bit-size)
                                testbench_generator.generate_first_testbench( 
                                    tb, line, paths["modules"][1], test_num, data
                                )
                            else: #Build off of the old testbench to keep the same randomized values
                                testbench_generator.generate_testbench(
                                    tb, line, i, data, paths
                                )

                if i == 0:
                    tcl_generator.generate_first_TCL(paths, i, data) #The first TCL will be generated based upon the IO port names
                else:
                    tcl_generator.generate_TCL(paths, i) #The second TCL just needs to change module names from the first one

                waveform_generator.generate_VCD( #All previously generated files are ran through Icarus and then GTKwave, creating the files we need.
                    paths,
                    paths["file"][i],
                    tb_path,
                    paths["build_dir"] / (paths["modules"][i+1] + ".tcl"),
                    paths["build_dir"] / (paths["modules"][i+1] + "_temp.vcd"),
                    paths["build_dir"] / (paths["modules"][i+1] + "_temp.vcd.fst"),
                )
                data = parse_files.clear_data(data) #Clears the data struct so future tests don't have old data
        file_rewriter.rewrite_tcl(paths) #TCLs are rewritten to remove VCD generation portions so they can be tested in the future without regenerating VCD files.

    """A function that generates the wavefiles from the testbenches, runs gtkwave w/ the TCLs generated earlier on the wavefiles
    that have just been generated, then checks the difference between gtkwave's two outputs. If there are more than 32 lines that
    are different, the designs must be unequivalent."""

    def run_test(self):
        return parse_diff.check_diff(paths) #Checks the two VCD files against each other. Returns either equivalent or not depending on how many lines are different.

    def check_compare_status(self, log_path):
        with open(log_path) as log:
            log_text = log.read()

        # Check for timeout
        if re.search(r"^Timeout$", log_text, re.M):
            return Status(CompareStatus.TIMEOUT)

        # Regex search for result
        m = re.search(r"Equivalence successfully proven!", log_text, re.M)
        if m:
            return Status(CompareStatus.SUCCESS)

        m = re.search(r"ERROR", log_text, re.M)
        if m:
            return Status(CompareStatus.NOT_EQUIVALENT)
