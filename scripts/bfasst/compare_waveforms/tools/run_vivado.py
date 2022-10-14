"""A launcher for Vivado to compare gtkwave wavefiles to Vivado's waveform analysis"""
import argparse
from pathlib import Path
import subprocess
import shutil

global ARGS


def parse_args():

    """Creates the argument parser for the Vivado Launcher."""

    parser = argparse.ArgumentParser(description="Launch Vivado.")
    parser.add_argument("base", metavar="Base", help="Base path to files.")
    parser.add_argument("module", metavar="Module", help="Module name.")
    parser.add_argument(
        "temp", metavar="Temp Folder", help="Temporary Location for TCL files."
    )
    parser.add_argument("vivado", metavar="Vivado", help="Location of Vivado Launcher.")

    ARGS = parser.parse_args()


def create_tcl(template, temp_tcl):

    """Creates a temporary TCL file to launch Vivado."""

    if temp_tcl.exists():
        temp_tcl.unlink()

    with template.open("r") as file:
        with temp_tcl.open("x") as output:
            for line in file:
                if "PATH" in line:
                    line = line.replace(
                        line[line.find("PATH") : line.find("PATH") + 4],
                        f"{ARGS.base}/{ARGS.module}.v",
                    )
                if "FILE_T" in line:
                    line = line.replace(
                        line[line.find("FILE_T") : line.find("FILE_T") + 6],
                        f"{ARGS.base}/{ARGS.module}_tb.v",
                    )
                elif "TB" in line:
                    line = line.replace(
                        line[line.find("TB") : line.find("TB") + 2], f"{ARGS.module}_tb"
                    )
                output.write(line)


def main():

    """The main function."""

    parse_args()

    assert ARGS.vivado is not None, "VIVADO_PATH environmental variable was not set!"

    template = Path(ARGS.temp) / ("templates/template.tcl")
    temp_tcl = Path(ARGS.temp) / (f"temp_{ARGS.module}.tcl")

    create_tcl(template, temp_tcl)

    temp_dir = Path(f"{ARGS.module}_vivado_sim")
    if temp_dir.exists():
        shutil.rmtree(str(temp_dir))
    temp_dir.mkdir()
    print(str(temp_dir))

    subprocess.run(
        [
            ARGS.vivado,
            "-nolog",
            "-nojournal",
            "-tempDir",
            str(temp_dir),
            "-source",
            str(temp_tcl),
        ]
    )

    shutil.rmtree(str(temp_dir))
    temp_tcl.unlink()


if __name__ == "__main__":
    main()
