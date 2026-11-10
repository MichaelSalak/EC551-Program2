
OP_TYPES = {"+": "add", "-": "sub", "*": "mul"}
UNIT_PREFIXES = {"add": "ADD", "sub": "SUB", "mul": "MUL"}

# place each operation at its earliest dependency-valid cycle
# no resource limits: independent operations can execute simultaneously
# returns a dictionary where each key is a clock cycle and each value is a 
# list of operations scheduled for that cycle
def schedule_asap(dag):
    nodes = dag["nodes"]

    # maps node IDs to their assigned execution cycles
    node_cycles = {}

    # maps cycles to lists of scheduled operations for that cycle
    schedule = {}

    # SSA statements appear in topological order: every producer is visited
    # before an operation that consumes its result
    for node_id, node in nodes.items():
        # operations with no dependencies execute in cycle 1
        if not node["predecessors"]:
            cycle = 1
        else:
            # wait until all predecessors have completed
            cycle = 1 + max(node_cycles[pred] for pred in node["predecessors"])

        node_cycles[node_id] = cycle

        # create cycle entry if necessary
        if cycle not in schedule:
            schedule[cycle] = []

        # add operation to its scheduled cycle
        schedule[cycle].append({
            "id": node_id,
            "dest": node["dest"],
            "src1": node["src1"],
            "src2": node["src2"],
            "op": node["op"]
        })

    return schedule


# return the longest dependency path (integer) in 1 cycle operations
# this is the minimum latency when functional units are unlimited
def calculate_min_latency(dag):
    nodes = dag["nodes"]
    depths = {}

    for node_id, node in nodes.items():
        if not node["predecessors"]:
            depths[node_id] = 1
        else:
            # a node cannot finish until the longest preceding chain finishes
            depths[node_id] = 1 + max(depths[pred] for pred in node["predecessors"])

    return max(depths.values(), default=0)


# place operations as late as possible within minimum latency
# works backward so all successors have known cycle assignments
# returns a dictionary where each key is a clock cycle and each value is a 
# list of operations scheduled for that cycle
def schedule_alap(dag):
    nodes = dag["nodes"]

    latency = calculate_min_latency(dag)

    # maps node IDs to their assigned execution cycles
    node_cycles = {}

    # maps cycles to lists of scheduled operations
    schedule = {}

    # process nodes in reverse topological order
    for node_id in reversed(nodes):
        node = nodes[node_id]

        # operations with no successors execute in the final allowed cycle
        if not node["successors"]:
            cycle = latency
        else:
            # execute before the earliest successor
            cycle = min(node_cycles[succ] for succ in node["successors"]) - 1

        # check if the latency bound is feasible
        if cycle < 1:
            raise ValueError(f"Latency bound {latency} is too small")

        node_cycles[node_id] = cycle

        if cycle not in schedule:
            schedule[cycle] = []

        schedule[cycle].append({
            "id": node_id,
            "dest": node["dest"],
            "src1": node["src1"],
            "src2": node["src2"],
            "op": node["op"]
        })

    return schedule


# validate functional-unit limits: require nonnegative resource counts and at least one of each used type
def validate_limits(dag, limits):
    for op_type in ("add", "sub", "mul"):
        limit = limits.get(op_type, 0)

        # must be present
        if not isinstance(limit, int) or limit < 0:
            raise ValueError(f"Invalid resource limit for {op_type}")

    for node in dag["nodes"].values():
        op_type = OP_TYPES[node["op"]]

        # ensure there are enough resources for the dag
        if limits.get(op_type, 0) == 0:
            raise ValueError(f"No {op_type} units available")


# convert a DAG node into a scheduled operation
def make_operation(node):
    return {
        "id": node["id"],
        "dest": node["dest"],
        "src1": node["src1"],
        "src2": node["src2"],
        "op": node["op"]
    }


# finds the longest path from each node to any terminal operation
# higher values identify operations that have more work remaining
# constrained ASAP uses these as scheduling priorities: longer path = high priority
def calculate_successor_depths(dag):
    nodes = dag["nodes"]
    depths = {}

    for node_id in reversed(nodes):
        successors = nodes[node_id]["successors"]

        if not successors:
            depths[node_id] = 1
        else:
            depths[node_id] = 1 + max(depths[succ] for succ in successors)

    return depths


# finds the longest path from any starting operation to each node
# higher values identify operations with longer preceding chains
# constrained ALAP uses these as backward-scheduling priorities
def calculate_predecessor_depths(dag):
    nodes = dag["nodes"]
    depths = {}

    for node_id, node in nodes.items():
        predecessors = node["predecessors"]

        if not predecessors:
            depths[node_id] = 1
        else:
            depths[node_id] = 1 + max(depths[pred] for pred in predecessors)

    return depths


# resource-constrained ASAP scheduling
# greedy heuristic: nodes with longer successor critical paths are prioritized
def schedule_constrained_asap(dag, limits):
    validate_limits(dag, limits)

    nodes = dag["nodes"]
    unscheduled = set(nodes)
    node_cycles = {}
    schedule = {}

    depths = calculate_successor_depths(dag)

    cycle = 1

    while unscheduled:
        # find operations whose predecessors finished in previous cycles
        ready = [
            node_id for node_id in unscheduled
            if all(
                pred in node_cycles
                and node_cycles[pred] < cycle
                for pred in nodes[node_id]["predecessors"]
            )
        ]

        # prefer operations on longer remaining paths. break ties by node ID
        ready.sort(key=lambda n: (-depths[n], n))

        # reset available resources for current cycle
        available = {op_type: limits.get(op_type, 0) for op_type in ("add", "sub", "mul")}

        operations = []

        # schedule as many ready operations as possible, starting with longest path node
        for node_id in ready:
            node = nodes[node_id]
            op_type = OP_TYPES[node["op"]]

            # subtract available resource from current cycle resource pool
            if available[op_type] > 0:
                operations.append(make_operation(node))
                available[op_type] -= 1
                node_cycles[node_id] = cycle
                unscheduled.remove(node_id)

        if not operations:
            raise ValueError("Unable to schedule remaining operations")

        schedule[cycle] = operations
        cycle += 1

    return schedule


# resource-constrained ALAP scheduling
# greedy backward list scheduling using relative cycles
# starts at cycle 0, grows backward (-1, -2, ...), then renumbers the earliest occupied cycle as 1
def schedule_constrained_alap(dag, limits):
    validate_limits(dag, limits)

    nodes = dag["nodes"]
    unscheduled = set(nodes)
    node_cycles = {}
    schedule = {}

    depths = calculate_predecessor_depths(dag)

    # start at the final cycle and work backward
    cycle = 0

    while unscheduled:
        # find operations whose successors have already been scheduled in later cycles
        ready = [
            node_id for node_id in unscheduled
            if all(
                succ in node_cycles
                and node_cycles[succ] > cycle
                for succ in nodes[node_id]["successors"]
            )
        ]

        # prioritize longer predecessor paths. break ties by node ID
        ready.sort(key=lambda n: (-depths[n], n))

        # reset available resources for current cycle
        available = {op_type: limits.get(op_type, 0) for op_type in ("add", "sub", "mul")}

        operations = []

        # schedule as many ready operations as possible, starting with longest path node
        for node_id in ready:
            node = nodes[node_id]
            op_type = OP_TYPES[node["op"]]

            # subtract available resource from current cycle resource pool
            if available[op_type] > 0:
                operations.append(make_operation(node))
                available[op_type] -= 1
                node_cycles[node_id] = cycle
                unscheduled.remove(node_id)

        if not operations: 
            raise ValueError("Unable to schedule remaining operations")

        schedule[cycle] = operations

        # move backward one cycle
        cycle -= 1

    # normalize cycles so earliest cycle is 1
    first_cycle = min(schedule)
    offset = 1 - first_cycle

    normalized = {}

    # create list with corrected cycle assignments
    for cycle, operations in sorted(schedule.items()):
        normalized[cycle + offset] = operations

    return normalized


# custom schedule: hardware-aware scheduling
# the maximum number of resources needed for unconstrained ASAP is aquired,
# then all possible hardware configurations are exhaustively tested to find an optimal balance
# between latency and resource utilization
# *** operates under the following assumptions:
#    - 1 unit of latency = weight of 3
#    - 1 additional resource = weight of 5
def schedule_custom(dag):
    asap = schedule_asap(dag)
    max_resources = count_resources(asap)

    best_schedule = None
    best_cost = float("inf")

    # explore possible hardware configurations
    for add in range(1, max(1, max_resources["add"]) + 1):
        for sub in range(1, max(1, max_resources["sub"]) + 1):
            for mul in range(1, max(1, max_resources["mul"]) + 1):

                limits = {"add": add, "sub": sub, "mul": mul}

                # test current configuration as constrained alap
                schedule = schedule_constrained_asap(dag, limits)

                latency = max(schedule, default=0)
                resources = count_resources(schedule)

                # weighted cost (arbitrary values)
                cost = (
                    3 * latency
                    + resources["add"]
                    + resources["sub"]
                    + 5 * resources["mul"]
                )

                # save the lowest cost schedule across all combinations
                if cost < best_cost:
                    best_cost = cost
                    best_schedule = schedule

    return best_schedule


# count the minimum number of functional units needed by the schedule
def count_resources(schedule):
    resources = {"add": 0, "sub": 0, "mul": 0}

    for operations in schedule.values():
        counts = {"add": 0, "sub": 0, "mul": 0}

        for op in operations:
            op_type = OP_TYPES[op["op"]]
            counts[op_type] += 1

        for op_type in resources:
            resources[op_type] = max(resources[op_type], counts[op_type])

    return resources


# assign physical functional units to operations
# number units from zero up independently for each type each cycle
# reusing "ADD0" in a later cycle means sharing the same physical adder over time
def allocate_units(schedule):
    allocated = {}

    for cycle, operations in sorted(schedule.items()):
        unit_counts = {"add": 0, "sub": 0, "mul": 0}
        allocated[cycle] = []

        for op in operations:
            op_type = OP_TYPES[op["op"]]

            unit_id = unit_counts[op_type]
            unit_counts[op_type] += 1

            unit_name = (f"{UNIT_PREFIXES[op_type]}{unit_id}")
            allocated[cycle].append({**op, "unit": unit_name})

    return allocated


# convert any schedule into the standard JSON structure
# JSON structured as follows:
# {
#   "algorithm": ...,
#   "resources": {
#     "add": ...,
#     "sub": ...,
#     "mul": ...
#   },
#   "inputs": [...],
#   "outputs": [...],
#   "schedule": [
#     {
#       "cycle": ...,
#       "operations": [
#         {
#           "id": ...,
#           "dest": ...,
#           "src1": ...,
#           "src2": ...,
#           "op": ...,
#           "unit": ...
#         }
#       ]
#     },
#     {
#       "cycle": ...,
#       "operations": [
#         {
#           "id": ...,
#           "dest": ...,
#           "src1": ...,
#           "src2": ...,
#           "op": ...,
#           "unit": ...
#         },
#         {
#           "id": ...,
#           "dest": ...,
#           "src1": ...,
#           "src2": ...,
#           "op": ...,
#           "unit": ..."
#         }
#       ]
#     },
#   ]
# }
def format_schedule_json(schedule, dag, algorithm):
    resources = count_resources(schedule)
    allocated = allocate_units(schedule)

    formatted_schedule = []

    for cycle, operations in sorted(allocated.items()):
        formatted_schedule.append({"cycle": cycle, "operations": operations})

    return {
        "algorithm": algorithm,
        "resources": resources,
        "inputs": dag["inputs"],
        "outputs": dag["outputs"],
        "schedule": formatted_schedule
    }


# print the scheduled operations
def print_schedule(schedule, algorithm):
    print(f"\n{algorithm} Schedule:")

    for cycle, operations in sorted(schedule.items()):
        print(f"\nCycle {cycle}:")

        for op in operations:
            print(
                f"    Node {op['id']}: "
                f"{op['dest']} = "
                f"{op['src1']} {op['op']} {op['src2']}"
            )
