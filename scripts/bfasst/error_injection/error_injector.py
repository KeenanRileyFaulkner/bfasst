import enum
import yaml
import random
import re

import bfasst
from bfasst.error_injection.base import ErrorInjectionTool
from bfasst.status import Status, ErrorInjectionStatus

class ErrorInjector_ErrorInjectionTool (ErrorInjectionTool):
    TOOL_WORK_DIR = "injection"

    # This picks enum and map pick a flow function to run, very similar (i.e.
    #   pretty much identical) to the way flows are selected in flow.py
    @enum.unique
    class Errors(enum.Enum):
        LUT_BIT_FLIP = "LUT_bit_flip"

    # For now these will be lambda functions, but it might be worth having a
    #   separate class system for error injection flows if they end up being
    #   very complicated (which they well could be)
    def __init__(self, build_dir):
        self.flow_fcn_map = {
            self.Errors.LUT_BIT_FLIP : lambda: self.lut_bit_flip_fcn
        }

    def get_flow_fcn_from_name(self, flow_name):
        invalid_flow = False
        
        try:
            flow_enum = self.Errors(flow_name)
        except ValueError:
            invalid_flow = True
        
        if invalid_flow:
            bfasst.utils.error(flow_name, "is not a valid error flow name")

        fcn = self.flow_fcn_map[flow_enum]()
        return fcn

    def run_error_flows(self, design):
        # Open the YAML file (if there is one) and read the flow information
        if design.error_flow_yaml is None:
            return (None, Status(ErrorInjectionStatus.NO_YAML))
        with open(bfasst.ERROR_FLOW_PATH / design.error_flow_yaml) as fp:
            error_flow_info = yaml.safe_load(fp)

        corrupt_netlists = []
        for flow in error_flow_info["error_injection_flows"]:
            corrupt_netlist_path = design.netlist_path.stem + "_" \
                                   + flow["name"] + ".v"
            corrupt_netlist_path = design.netlist_path.parent / corrupt_netlist_path
            for p in flow["passes"]:
                flow_name = p[0]
                num_iterations = p[1]
                flow_fcn = self.get_flow_fcn_from_name(flow_name)
                for itr in range(num_iterations):
                    flow_ret = flow_fcn(design.yosys_netlist_path,
                                        corrupt_netlist_path)
                    if flow_ret == Status(ErrorInjectionStatus.FCN_ERROR):
                        return (None, Status(ErrorInjectionStatus.FCN_ERROR))
            corrupt_netlists.append(corrupt_netlist_path)
        return(Status(ErrorInjectionStatus.SUCCESS), corrupt_netlists)
                    

    def lut_bit_flip_fcn(self, golden_netlist, output_netlist):
        # Go through the golden file. Copy everything to an internal buffer,
        #   and note where LUT inits happen.
        #   Once the whole thing is read, pick a random lut and change 1 bit
        #   Then write the file out to output_netlist
        lines = []
        init_linenos = []
        with open(golden_netlist) as gold_fp:
            for line in gold_fp:
                lines.append(line)
                if line.strip()[:9] == ".LUT_INIT":
                    init_linenos.append(len(lines) - 1)
        # Pick a random LUT to flip
        lut_to_change_idx = random.randint(0, len(init_linenos) - 1)
        lut_to_change = lines[init_linenos[lut_to_change_idx]]
        # Should I change based on the entire init string (i.e. 16 bits) or
        #   just whatever is currently used (which varies w/ input count)
        # Extract the LUT init value (hex)
        match_obj = re.search("'h[0-9A-Fa-f]*\)$", lut_to_change.strip())
        init_value = match_obj.group(0)[2:-1]
        init_int = int(init_value, 16)
        # Pick a bit to flip and flip it
        bit_to_flip = random.randint(0, 15)
        flip_mask = 1 << bit_to_flip
        new_init = init_int ^ flip_mask
        # Replace the old LUT init with this new value
        new_init_hex = hex(new_init)[2:]
        # I'm not going to worry about correct indentation...
        new_init_str = ".LUT_INIT(16'h" + new_init_hex + ")\n"
        lines[init_linenos[lut_to_change_idx]] = new_init_str
        print("Corrupted lut init", lut_to_change.strip(), "to", new_init_str[:-1],
              "on line", init_linenos[lut_to_change_idx] + 1)
        # Now write to the output file
        print(output_netlist)
        with open(output_netlist, 'w') as corrupt_fp:
            for line in lines:
                corrupt_fp.write(line)
        return Status(ErrorInjectionStatus.FCN_SUCCESS)
    