import re

# match equations such as:
# A = B + C
# X1=Y*Z
# result = A - B
PATTERN = re.compile(
    r"^\s*([A-Za-z_]\w*)\s*=\s*"
    r"([A-Za-z_]\w*|\d+)\s*"
    r"([+\-*])\s*"
    r"([A-Za-z_]\w*|\d+)\s*$"
)

# read list of equations from an input .txt file
# return list of dictionaries, each containing:
#    dest - destination variable
#    src1 - source variable one
#    op   - equation operator ('+', '-', '*')
#    src2 - source variable two
def parse_equations(filename):
    equations = []

    with open(filename, "r") as file:
        for line_number, line in enumerate(file, 1):
            # omit blank and comment lines if present
            line = line.split("#", 1)[0].strip()

            if not line:
                continue

            # ensure input format is correct: (letter + '=' + letter + operator + letter)
            match = PATTERN.fullmatch(line)

            if not match:
                raise ValueError(f"Invalid equation on line {line_number}: {line}")

            dest, src1, op, src2 = match.groups()

            equations.append({"dest": dest, "src1": src1, "op": op, "src2": src2})

    return equations

# converts list of regular equations to list of single static assignment (ssa) equations
# tracks number of occurances of a destination variable to ensure new versions are stored properly
def convert_to_ssa(equations):
    versions = {}
    ssa_equations = []

    # get the current version of a variable
    def current_version(variable):
        # constants do not require SSA renaming
        if variable.isdigit():
            return variable

        # variables never assigned are primary inputs
        if variable not in versions:
            return variable

        return f"{variable}{versions[variable]}"

    for eq in equations:
        dest = eq["dest"]

        # resolve operands BEFORE updating destination
        # This is important for expressions like A = A + B
        src1 = current_version(eq["src1"])
        src2 = current_version(eq["src2"])

        # assign a new version to the destination
        if dest not in versions:
            versions[dest] = 0
        else:
            versions[dest] += 1

        # create new destination variable with updated version
        new_dest = f"{dest}{versions[dest]}"

        ssa_equations.append({
            "dest": new_dest,
            "src1": src1,
            "op": eq["op"],
            "src2": src2
        })

    return ssa_equations

# format string from dict values to write to ssa file
def format_equation(eq):
    return f"{eq['dest']} = "f"{eq['src1']} {eq['op']} {eq['src2']}"

# export ssa equations via text file
def export_ssa(equations, filename):
    with open(filename, "w") as file:
        for eq in equations:
            file.write(format_equation(eq) + "\n")

