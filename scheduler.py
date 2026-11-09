
# unconstrained ASAP scheduling
# returns a dictionary where each key is a clock cycle and each value is a 
# list of operations scheduled for that cycle
def schedule_asap(dag):
    nodes = dag["nodes"]

    # maps node IDs to their assigned execution cycles
    node_cycles = {}

    # maps cycles to lists of scheduled operations
    schedule = {}

    # nodes are already in topological order
    for node_id, node in nodes.items():

        # operations with no dependencies execute in cycle 1
        if not node["predecessors"]:
            cycle = 1
        else:
            # wait until all predecessors have completed
            cycle = 1 + max(
                node_cycles[pred]
                for pred in node["predecessors"]
            )

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


# unconstrained ALAP scheduling
# returns a dictionary where each key is a clock cycle and each value is a 
# list of operations scheduled for that cycle
def schedule_alap(dag, latency):
    nodes = dag["nodes"]

    # maps node IDs to their assigned execution cycles
    node_cycles = {}

    # maps cycles to lists of scheduled operations
    schedule = {}

    if latency < 1:
        raise ValueError("Latency must be at least 1")

    # process nodes in reverse topological order
    for node_id in reversed(nodes):
        node = nodes[node_id]

        # operations with no successors execute in the final allowed cycle
        if not node["successors"]:
            cycle = latency
        else:
            # execute before the earliest successor
            cycle = min(
                node_cycles[succ]
                for succ in node["successors"]
            ) - 1

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



















OP_TYPES = {
    "+": "add",
    "-": "sub",
    "*": "mul"
}

UNIT_PREFIXES = {
    "add": "ADD",
    "sub": "SUB",
    "mul": "MUL"
}

# count the number of functional units needed by the schedule
def count_resources(schedule):
    resources = {"add": 0, "sub": 0, "mul": 0}

    for operations in schedule.values():
        counts = {"add": 0, "sub": 0, "mul": 0}

        for op in operations:
            op_type = OP_TYPES[op["op"]]
            counts[op_type] += 1

        for op_type in resources:
            resources[op_type] = max(
                resources[op_type],
                counts[op_type]
            )

    return resources


# assign physical functional units to operations
def allocate_units(schedule):
    allocated = {}

    for cycle, operations in sorted(schedule.items()):
        unit_counts = {"add": 0, "sub": 0, "mul": 0}
        allocated[cycle] = []

        for op in operations:
            op_type = OP_TYPES[op["op"]]

            unit_id = unit_counts[op_type]
            unit_counts[op_type] += 1

            unit_name = (
                f"{UNIT_PREFIXES[op_type]}_{unit_id}"
            )

            allocated[cycle].append({
                **op,
                "unit": unit_name
            })

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
        formatted_schedule.append({
            "cycle": cycle,
            "operations": operations
        })

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
