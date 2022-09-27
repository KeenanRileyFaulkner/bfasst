from pathlib import Path
import subprocess


def check_diff(paths):
    """This function will run through all of the differences between the two VCD files and then determine equivalence based upon the number of different lines."""
    is_equivalent = False

    # Finds how many lines are different in the two files.
    dif = subprocess.getoutput(
        [f"diff -c {paths['vcd'][0]} {paths['vcd'][1]}"]
    )
    if paths["diff"].exists():
        paths["diff"].unlink()
    with paths["diff"].open("x") as file:
        for line in dif:
            file.write(line)

    lines = 0
    with paths["diff"].open("r") as file:
        for line in file:
            if len(line) != 0:
                lines = lines + 1

    # If there are more than 32 lines different, the two designs must be unequivalent.
    if lines > 42:
        print(f"NOT EQUIVALENT! SEE {paths['parsed_diff']} for more info")
        parse_diff(paths)
        if paths["parsed_diff"].exists():
            with paths["parsed_diff"].open("r") as file:
                for line in file:
                    print(line)
        else:
            subprocess.run(["diff", "-c", str(paths["vcd"][0]), str(paths["vcd"][1])])

    else:
        paths["diff"].unlink()
        is_equivalent = True
    return is_equivalent


def parse_diff(paths):
    """This function reads through the diff.txt file generated by running a diff function on the two vcd files (text representation of a wave file).
    Since the VCD files represent each signal as a symbol (IE: $, #, !, etc), this script replaces those names with the actual signal names.
    This script also tells you the exact times, in ms, that these differences occur.
    The output of this script is saved in the waveform folder AND is printed out anytime unequivalent waveforms are viewed."""
    newWord = False
    words = []
    symbols = []
    signals = []

    # We gather up all of the signals with this script. They are stored as follows: bit_length, Symbol, Signal_name.
    # Because we don't need the bit_length, it will be discarded. Each symbol and signal are stored in individual arrays and
    # each entry will correspond with each other. (Note: Could be replaced with a map in the future.)
    with paths["vcd"][0].open("r") as file:
        for line in file:
            if "$var wire" in line:
                word = ""
                for i in line:
                    if i == " ":
                        newWord = True
                    if newWord is False:
                        word = word + i
                    else:
                        if word != "$var" & word != "wire":
                            if "[" in word:
                                word = word[0 : word.index("[")]
                            words.append(word)
                            word = ""
                            newWord = False
                        else:
                            word = ""
                            newWord = False
    # J increments through the 3 entries for words (bit_length, symbol, signal_name.) If j==0, the bit_length is discarded.
    # If j==1, the symbol is saved. If j==2, the signal_name is saved and j is set back to 0.
    j = 0
    for i in words:
        if j == 0:
            j = j + 1
        elif j == 1:
            symbols.append(i)
            j = j + 1
        elif j == 2:
            signals.append(i)
            j = 0

    if Path(paths["parsed_diff"]).exists():
        Path(paths["parsed_diff"]).unlink()

    # A lot of logic here. Essentially, all of the excess information is discarded and everything is renamed so that
    # it can be easier to read for a normal individual. A HOW TO READ: section is added for first-time users.
    with paths["diff"].open("r") as file:
        with paths["parsed_diff"].open("x") as output:
            output.write("HOW TO READ: \n")
            output.write(
                "+ indicates this data was added and is not present in the other file.\n"
            )
            output.write(
                "- indicates this data was removed and is present in the other file.\n"
            )
            output.write(
                "All differences are seperated by file. The Implicit and Reversed Files are labeled as such.\n"
            )
            output.write(
                "To better debug, re-open the VCD files using the Compare Waveforms script and use this file to find where to look for differences.\n"
            )
            output.write(
                "For further confirmation, open both testbenches with Vivado and compare the results to this diff file.\n\n"
            )
            firstDif = True
            isDif = False
            for line in file:
                isParsed = False
                for symbol, signal in zip(symbols, signals):
                    if symbol == "#":
                        if "#\n" in line:
                            line = line.replace(f"{symbol} {signal}")
                            isParsed = True
                        elif "#" in line:
                            if line[line.index("#") + 1] != " ":
                                if line[len(line) - 1] == "\n":
                                    num = line[line.index("#") + 1 : line.index("\n")]
                                    num = int(num)
                                    num = int(num / 1000)
                                    line = f" {num} ns\n"
                                    isParsed = True
                                else:
                                    num = line[line.index("#") + 1 :]
                                    num = int(num)
                                    num = int(num / 1000)
                                    line = f" {num} ns\n"
                                    isParsed = True
                    elif symbol == "$":
                        if "$scope" not in line:
                            if "$var wire" not in line:
                                if "$timescale" not in line:
                                    if "$end" not in line:
                                        if isParsed is False:
                                            line = line.replace(symbol, f" {signal}")
                                            isParsed = True
                    elif symbol in line:
                        if line[line.index(symbol) :] == (f"{symbol}\n"):
                            line = line.replace(symbol, f" {signal}")
                            isParsed = True

                if firstDif:
                    if isDif:
                        if "*****" in line:
                            firstDif = False
                        else:
                            line = ""
                    else:
                        if "*****" in line:
                            line = ""
                            isDif = True
                        else:
                            line = ""
                else:
                    if "*****" in line:
                        line = "*******************\n"

                    if "*** " in line:
                        line = f"*** IMPL: P{line[line.index(' ') + 1 :]}"

                    if "--- " in line:
                        line = f"--- REVERSED: {line[line.index(' ') + 1 :]}"

                output.write(line)
