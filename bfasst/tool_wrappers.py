""" Wrappers around various tools.
Only import as needed to minimize dependencies to the tools being used."""

# pylint: disable=import-outside-toplevel
from pathlib import Path
from bfasst.config import VIVADO_BIN_PATH
from bfasst.locks import conformal_lock, onespin_lock
from bfasst.status import BfasstException
from bfasst.tool import ToolProduct
from bfasst.types import ToolType, Vendor


def ic2_lse_synth(design, build_dir, flow_args):
    """Run Icecube2 LSE synthesis"""
    from bfasst.synth.ic2_lse import Ic2LseSynthesisTool

    synth_tool = Ic2LseSynthesisTool(build_dir, flow_args[ToolType.SYNTH])
    return synth_tool.create_netlist(design)


def ic2_synplify_synth(design, build_dir, flow_args):
    """Run Icecube2 Synplify synthesis"""
    from bfasst.synth.ic2_synplify import Ic2SynplifySynthesisTool

    synth_tool = Ic2SynplifySynthesisTool(build_dir, flow_args[ToolType.SYNTH])
    return synth_tool.create_netlist(design)


def ic2_impl(design, build_dir, flow_args):
    """Run Icecube2 implementation"""
    from bfasst.impl.ic2 import Ic2ImplementationTool

    impl_tool = Ic2ImplementationTool(build_dir, flow_args[ToolType.IMPL])
    return impl_tool.implement_bitstream(design)


def icestorm_rev_bit(design, build_dir, flow_args):
    """Reverse bitstream using icestorm"""
    from bfasst.reverse_bit.icestorm import Icestorm_ReverseBitTool

    reverse_bit_tool = Icestorm_ReverseBitTool(build_dir, flow_args[ToolType.REVERSE])
    return reverse_bit_tool.reverse_bitstream(design)


def conformal_cmp(design, build_dir, flow_args, vendor=Vendor.XILINX):
    """Compare netlists using Conformal"""
    from bfasst.compare.conformal import ConformalCompareTool

    compare_tool = ConformalCompareTool(
        build_dir, flow_args[ToolType.CMP], vendor
    )  # TODO vendor should be flow arg
    with conformal_lock:
        return compare_tool.compare_netlists(design)


def structural_cmp(design, build_dir, flow_args):
    """Structural compare and map"""
    from bfasst.compare.structural import StructuralCompareTool

    struct_cmp = StructuralCompareTool(build_dir, flow_args[ToolType.CMP])
    return struct_cmp.compare_netlists(design)


def vivado_synth(design, build_dir, flow_args):
    """Synthesize using Vivado"""
    from bfasst.synth.vivado import VivadoSynthesisTool

    synth_tool = VivadoSynthesisTool(build_dir, flow_args[ToolType.SYNTH])
    return synth_tool.create_netlist(design)


def vivado_impl(design, build_dir, flow_args):
    """Implement using Vivado"""
    from bfasst.impl.vivado import VivadoImplementationTool

    impl_tool = VivadoImplementationTool(build_dir, flow_args[ToolType.IMPL])
    return impl_tool.implement_bitstream(design)


def yosys_synth(design, build_dir, flow_args):
    """Synthesize using Yosys"""
    from bfasst.synth.yosys import YosysTechSynthTool

    synth_tool = YosysTechSynthTool(build_dir, flow_args[ToolType.SYNTH])
    return synth_tool.create_netlist(design)


def yosys_cmp(design, build_dir, flow_args):
    """Compare netlists using yosys"""
    from bfasst.compare.yosys import Yosys_CompareTool

    compare_tool = Yosys_CompareTool(build_dir, flow_args[ToolType.CMP])
    return compare_tool.compare_netlists(design)


def wave_cmp(design, build_dir, flow_args):
    """Compare netlists via waveforms"""
    from bfasst.compare.waveform import WaveformCompareTool

    tool = WaveformCompareTool(build_dir, flow_args[ToolType.CMP])
    return tool.compare_netlists(design)


def onespin_cmp(design, build_dir, flow_args):
    """Compare netlists using Onespin"""
    from bfasst.compare.onespin import OneSpin_CompareTool

    compare_tool = OneSpin_CompareTool(build_dir, flow_args[ToolType.CMP])
    with onespin_lock:
        return compare_tool.compare_netlists(design)


def ic2_lse_opt(design, build_dir, flow_args, in_files, lib_files=None):
    """Optimize design using IceCube2 LSE"""
    from bfasst.opt.ic2_lse import Ic2LseOptTool

    lse_opt_tool = Ic2LseOptTool(build_dir, flow_args)
    status = lse_opt_tool.create_netlist(design, in_files, lib_files)
    # Try fixing the netlist LUT inits (there's some issue with how LSE
    #   generates them)
    lse_opt_tool.fix_lut_inits(design)
    return status


def ic2_synplify_opt(design, build_dir, flow_args, in_files, lib_files=None):
    """Optimize design using Icecube2 Synplify"""
    from bfasst.opt.ic2_synplify import Ic2SynplifyOptTool

    synp_opt_tool = Ic2SynplifyOptTool(build_dir, flow_args)
    return synp_opt_tool.create_netlist(design, in_files, lib_files)


def xray_rev(design, build_dir, flow_args):
    """Reverse bitstream using Xray"""
    from bfasst.reverse_bit.xray import XRayReverseBitTool

    reverse_bit_tool = XRayReverseBitTool(build_dir, flow_args[ToolType.REVERSE])
    return reverse_bit_tool.reverse_bitstream(design)


def xilinx_phys_netlist(design, build_dir):
    """Run the xilinx physical netlist transformation"""
    from bfasst.transform.xilinx_phys_netlist import XilinxPhysNetlist

    phy_netlist_tool = XilinxPhysNetlist(build_dir)
    status = phy_netlist_tool.run(design)
    return status


def vivado_ooc(design, build_dir, flow_args):
    """Run Vivado Synthesis and Implementation for out-of-context designs"""
    from bfasst.impl.vivado import VivadoImplementationTool
    from bfasst.synth.vivado import VivadoSynthesisTool
    from bfasst.status import ImplStatus

    synth_tool = VivadoSynthesisTool(build_dir, flow_args[ToolType.SYNTH])
    impl_tool = VivadoImplementationTool(build_dir, flow_args[ToolType.IMPL])

    synth_tool.args.out_of_context = True
    impl_tool.args.out_of_context = True

    synth_status = synth_tool.check_runs(design)

    if synth_status is not None:
        impl_tool.init_design(design)
        try:
            impl_status = impl_tool.get_prev_run_status(
                tool_products=[
                    ToolProduct(
                        design.bitstream_path,
                        impl_tool.log_path,
                        impl_tool.check_impl_status,
                    )
                ],
                dependency_modified_time=max(
                    Path(__file__).stat().st_mtime, design.netlist_path.stat().st_mtime
                ),
            )
        except FileNotFoundError:
            impl_status = None
        if impl_status is not None:
            synth_tool.print_skipping_synth()
            impl_tool.print_skipping_impl()
            return impl_status

    synth_tool.print_running_synth()
    impl_tool.print_running_impl()
    synth_tool.open_new_log()
    impl_tool.open_new_log()
    tcl_path = synth_tool.cwd / "run.tcl"
    report_io_path = synth_tool.work_dir / "report_io.txt"
    impl_tool.init_design(design)
    with open(tcl_path, "w") as fp:
        synth_tool.write_header(fp)
        synth_tool.write_hdl(design, fp)
        synth_tool.write_synth(design, fp)
        synth_tool.write_products(design, report_io_path, fp)
        # need to add constraints logic, but this is determined post-synthesis
        impl_tool.write_impl(fp)
        impl_tool.write_outputs(design, fp)
        synth_tool.write_footer(fp)

    cmd = [str(VIVADO_BIN_PATH), "-mode", "tcl", "-source", str(tcl_path)]
    proc = synth_tool.exec_and_log(cmd)
    if proc.returncode:
        raise BfasstException(ImplStatus.ERROR, "Vivado ooc synth/impl flow failed")

    return impl_tool.success_status
