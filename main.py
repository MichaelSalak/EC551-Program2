import argparse
from parser import parse_equations, convert_to_ssa, format_equation, export_ssa

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Arithmetic equation parser and SSA converter"
    )

    parser.add_argument(
        "input",
        help="Input text file containing equations"
    )

    parser.add_argument(
        "--export-ssa",
        metavar="FILE",
        help="Export SSA equations to a text file"
    )

    args = parser.parse_args()

    equations = parse_equations(args.input)

    if len(equations) > 20:
        raise ValueError("Maximum of 20 equations allowed")

    ssa_equations = convert_to_ssa(equations)

    print("\nOriginal equations:")
    for eq in equations:
        print(format_equation(eq))

    print("\nSSA equations:")
    for eq in ssa_equations:
        print(format_equation(eq))

    if args.export_ssa:
        export_ssa(ssa_equations, args.export_ssa)
        print(f"\nSSA exported to {args.export_ssa}")