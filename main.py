import argparse
from parser import parse_equations, convert_to_ssa, format_equation, export_ssa
from dag import construct_dag, print_dag
from scheduler import (schedule_asap, schedule_alap, schedule_constrained_asap, 
                       schedule_constrained_alap, schedule_custom, print_schedule)

if __name__ == "__main__":
    # parsing
    parser = argparse.ArgumentParser(
        description="Arithmetic equation parser and hardware scheduler"
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

    # Functional-unit constraints
    parser.add_argument(
        "--add",
        type=int,
        default=1,
        help="Number of available adders (default: 1)"
    )

    parser.add_argument(
        "--sub",
        type=int,
        default=1,
        help="Number of available subtractors (default: 1)"
    )

    parser.add_argument(
        "--mul",
        type=int,
        default=1,
        help="Number of available multipliers (default: 1)"
    )

    # Select which schedule is exported for RTL generation
    parser.add_argument(
        "--schedule",
        choices=[
            "asap",
            "alap",
            "constrained-asap",
            "constrained-alap",
            "custom"
        ],
        default="custom",
        help="Schedule to export for RTL generation (default: custom)"
    )

    args = parser.parse_args()

    limits = {"add": args.add, "sub": args.sub, "mul": args.mul}

    # validate resource limits
    if any(value < 0 for value in limits.values()):
        parser.error("Resource limits cannot be negative")

    # parse equations from file
    equations = parse_equations(args.input)

    if len(equations) > 20:
        raise ValueError("Maximum of 20 equations allowed")

    if not equations:
        raise ValueError("Input file contains no equations")

    # ----------------------------------------------------------------

    # convert equations to ssa form
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
    print("--------------------------------------------------")

    # generate and print dag
    dag = construct_dag(ssa_equations)
    print_dag(dag)
    print("--------------------------------------------------")

    # asap schedule
    asap = schedule_asap(dag)
    print_schedule(asap, "ASAP")
    print("--------------------------------------------------")

    # alap schedule
    alap = schedule_alap(dag)
    print_schedule(alap, "ALAP")
    print("--------------------------------------------------")

    # resource-constrained asap
    constrained_asap = schedule_constrained_asap(dag, limits)
    print_schedule(constrained_asap, "Constrained ASAP")
    print("--------------------------------------------------")

    # resource-constrained alap
    constrained_alap = schedule_constrained_alap(dag, limits)
    print_schedule(constrained_alap, "Constrained ALAP")
    print("--------------------------------------------------")

    # custom hardware-aware scheduling
    custom = schedule_custom(dag)
    print_schedule(custom, "Custom - Hardware-Aware")
    print("--------------------------------------------------")

    # map command line names to generated schedules
    schedules = {
        "asap": asap,
        "alap": alap,
        "constrained-asap": constrained_asap,
        "constrained-alap": constrained_alap,
        "custom": custom
    }

    # select schedule for RTL generation
    selected_schedule = schedules[args.schedule]
