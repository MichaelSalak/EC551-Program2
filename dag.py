from collections import deque

# Construct a dependency DAG from SSA equations
# Each arithmetic operation becomes one node
# Edges represent dependencies between operations
# DAG structured as follows:
# {
#   "nodes": {
#       node_id: {
#           "id": ...,
#           "dest": ...,
#           "src1": ...,
#           "src2": ...,
#           "op": ...,
#           "predecessors": [...],
#           "successors": [...]
#       }
#   },
#   "inputs": [...],
#   "outputs": [...]
# }
def construct_dag(ssa_equations):
    nodes = {}
    producers = {}
    inputs = set()
    consumed = set()

    # first pass: create a node for every SSA operation
    for node_id, eq in enumerate(ssa_equations):
        dest = eq["dest"]

        if dest in producers:
            raise ValueError(f"Duplicate SSA assignment: {dest}")

        # left hand side variables are producers
        producers[dest] = node_id

        nodes[node_id] = {
            "id": node_id,
            "dest": dest,
            "src1": eq["src1"],
            "src2": eq["src2"],
            "op": eq["op"],
            "predecessors": [],
            "successors": []
        }

    # second pass: determine dependencies
    for node_id, node in nodes.items():
        dependencies = set()

        for operand in (node["src1"], node["src2"]):
            # numeric constants are not DAG nodes
            if operand.isdigit():
                continue

            # operand is dependent on producer
            if operand in producers:
                producer_id = producers[operand]
                dependencies.add(producer_id)
                consumed.add(operand)
            else:
                # operand has no producer: primary input
                inputs.add(operand)

        node["predecessors"] = sorted(dependencies)

        for pred_id in dependencies:
            nodes[pred_id]["successors"].append(node_id)

    for node in nodes.values():
        node["successors"].sort()

    # terminal operation results are outputs
    outputs = [
        node["dest"]
        for node in nodes.values()
        if node["dest"] not in consumed
    ]

    dag = {
        "nodes": nodes,
        "inputs": sorted(inputs),
        "outputs": outputs
    }

    return dag


# print the DAG in a readable format
def print_dag(dag):
    print("\nDAG Nodes:")

    for node_id, node in dag["nodes"].items():
        node = dag["nodes"][node_id]

        print(
            f"Node {node_id}: "
            f"{node['dest']} = "
            f"{node['src1']} {node['op']} {node['src2']}"
        )
        print(f"    Predecessors: {node['predecessors']}")
        print(f"    Successors:   {node['successors']}")

    print("\nPrimary inputs:", dag["inputs"])
    print("Final outputs:", dag["outputs"])
