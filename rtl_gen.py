from scheduler import OP_TYPES, allocate_units

# RTL generator: turns a scheduled DAG into one Verilog module
#   1. build_plan()     decides which unit runs each operation, which register stores
#                       each result, and what goes into every mux
#   2. write_verilog()  prints that plan as an FSM (control) + datapath (muxes, units, registers)

WIDTH = 16
UNIT_MODULES = {"add": "adder", "sub": "subtracter", "mul": "multiplier"}


# number of select bits needed for a mux with "count" inputs (at least 1)
# Ex: 1 -> 1, 2 -> 1, 3 -> 2, 5 -> 3
def select_width(count):
    width = 1
    while (1 << width) < count:
        width += 1
    return width


# sort key for register allocation: earliest written value first
def write_cycle_key(entry):
    return (entry["write_cycle"], entry["dest"])


# decide all the hardware for a schedule
# returns:
#   "num_cycles" - number of compute states
#   "units"      - {"add0": {"type": "add", "a": [mux inputs], "b": [mux inputs]}, ...}
#   "registers"  - {"reg0": {"sources": [unit names], "values": [SSA names]}, ...}
#   "states"     - {cycle: [op with its unit, mux selects, and destination register], ...}
#   "outputs"    - [(SSA name, register), ...]
def build_plan(dag, schedule):
    nodes = dag["nodes"]
    allocated = allocate_units(schedule)
    num_cycles = max(schedule)

    # cycle of every operation
    node_cycle = {}
    for cycle in allocated:
        for op in allocated[cycle]:
            node_cycle[op["id"]] = cycle

    # ---- register allocation ----
    # a value is written at the end of its cycle and kept until the last cycle that reads it
    # outputs are kept forever so they can be displayed after the run
    # Ex: A0 written in cycle 1, last read in cycle 3 -> a value written in cycle 3 can reuse its register
    lifetimes = []
    for node_id in nodes:
        node = nodes[node_id]
        last_read = node_cycle[node_id]

        if node["dest"] in dag["outputs"]:
            last_read = num_cycles + 1

        for succ in node["successors"]:
            if node_cycle[succ] > last_read:
                last_read = node_cycle[succ]

        lifetimes.append({"dest": node["dest"], "write_cycle": node_cycle[node_id], "last_read": last_read})

    lifetimes.sort(key=write_cycle_key)

    busy_until = []       # busy_until[i] = last cycle register i is still needed
    value_register = {}   # SSA name -> register name

    for entry in lifetimes:
        chosen = None
        for index in range(len(busy_until)):
            if busy_until[index] <= entry["write_cycle"]:
                chosen = index
                break

        if chosen is None:
            chosen = len(busy_until)
            busy_until.append(0)

        busy_until[chosen] = entry["last_read"]
        value_register[entry["dest"]] = f"reg{chosen}"

    registers = {}
    for index in range(len(busy_until)):
        registers[f"reg{index}"] = {"sources": [], "values": []}

    # Verilog expression for an operand
    # Ex: "5" -> "5",  "A0" -> "reg2" (register holding A0),  "B" -> "in_B_q" (latched input)
    def operand_expression(operand):
        if operand.isdigit():
            return operand
        if operand in value_register:
            return value_register[operand]
        return f"in_{operand}_q"

    # ---- muxes and per-cycle control ----
    units = {}
    states = {}

    for cycle in range(1, num_cycles + 1):
        states[cycle] = []

        if cycle not in allocated:
            continue

        for op in allocated[cycle]:
            unit_name = op["unit"].lower()   # Ex: "ADD0" -> "add0"

            if unit_name not in units:
                units[unit_name] = {"type": OP_TYPES[op["op"]], "a": [], "b": []}
            unit = units[unit_name]

            # add each operand to the unit's input mux if it is not there yet
            a_source = operand_expression(op["src1"])
            b_source = operand_expression(op["src2"])
            if a_source not in unit["a"]:
                unit["a"].append(a_source)
            if b_source not in unit["b"]:
                unit["b"].append(b_source)

            # add the unit to the destination register's input mux
            reg_name = value_register[op["dest"]]
            register = registers[reg_name]
            if unit_name not in register["sources"]:
                register["sources"].append(unit_name)
            register["values"].append(op["dest"])

            states[cycle].append({
                "text": f"{op['dest']} = {op['src1']} {op['op']} {op['src2']}",
                "dest": op["dest"],
                "unit": unit_name,
                "a_sel": unit["a"].index(a_source),
                "b_sel": unit["b"].index(b_source),
                "reg": reg_name,
                "reg_sel": register["sources"].index(unit_name)
            })

    outputs = []
    for name in dag["outputs"]:
        outputs.append((name, value_register[name]))

    return {"num_cycles": num_cycles, "units": units, "registers": registers,
            "states": states, "outputs": outputs}


# write the plan as one Verilog module
def write_verilog(plan, dag, module_name, filename):
    num_cycles = plan["num_cycles"]
    state_bits = select_width(num_cycles + 2)    # IDLE + N cycles + DONE
    unit_names = list(plan["units"])
    lines = []

    # ---- header: schedule summary ----
    lines.append("`timescale 1ns / 1ps")
    lines.append(f"// {module_name}.v - generated by rtl_gen.py")
    lines.append("// FSM states: 0 = IDLE, 1..N = compute cycles, N+1 = DONE")
    for cycle in range(1, num_cycles + 1):
        for op in plan["states"][cycle]:
            lines.append(f"//   cycle {cycle}: {op['text']:<20} on {op['unit']} -> {op['reg']}")
    lines.append(f"// unit_values (lowest bits first): {', '.join(unit_names)}")
    lines.append("")

    # ---- ports ----
    lines.append(f"module {module_name} (")
    lines.append("    input clk, rst,")
    lines.append("    input en,                  // advance one step (debounced button pulse)")
    lines.append("    input start,               // latch inputs and begin a run")
    for name in dag["inputs"]:
        lines.append(f"    input [{WIDTH-1}:0] in_{name},")
    for name, reg_name in plan["outputs"]:
        lines.append(f"    output [{WIDTH-1}:0] out_{name},")
    lines.append(f"    output [{len(unit_names) * WIDTH - 1}:0] unit_values,   // every unit output, unit 0 in the lowest bits")
    lines.append(f"    output reg [{state_bits-1}:0] state,")
    lines.append("    output done")
    lines.append(");")
    lines.append("")

    # ---- FSM state register ----
    lines.append(f"    localparam S_LAST = {num_cycles}, S_DONE = {num_cycles + 1};")
    lines.append("    assign done = (state == S_DONE);")
    lines.append("    wire load = ((state == 0) || done) && start;")
    lines.append("")
    lines.append("    always @(posedge clk) begin")
    lines.append("        if (rst)                 state <= 0;")
    lines.append("        else if (en) begin")
    lines.append("            if (load)            state <= 1;")
    lines.append("            else if (state == S_LAST) state <= S_DONE;")
    lines.append("            else if (state != 0 && !done) state <= state + 1;")
    lines.append("        end")
    lines.append("    end")
    lines.append("")

    # ---- input registers ----
    lines.append("    // input registers: latched when a run starts")
    for name in dag["inputs"]:
        lines.append(f"    reg [{WIDTH-1}:0] in_{name}_q;")
    lines.append("    always @(posedge clk) begin")
    lines.append("        if (en && load) begin")
    for name in dag["inputs"]:
        lines.append(f"            in_{name}_q <= in_{name};")
    lines.append("        end")
    lines.append("    end")
    lines.append("")

    # ---- control signals (FSM outputs) ----
    controls = []   # (signal name, bit width)
    for unit_name in plan["units"]:
        unit = plan["units"][unit_name]
        controls.append((f"{unit_name}_a_sel", select_width(len(unit["a"]))))
        controls.append((f"{unit_name}_b_sel", select_width(len(unit["b"]))))
    for reg_name in plan["registers"]:
        controls.append((f"{reg_name}_we", 1))
        controls.append((f"{reg_name}_sel", select_width(len(plan["registers"][reg_name]["sources"]))))

    lines.append("    // control unit: mux selects and register write-enables for each state")
    for name, bits in controls:
        lines.append(f"    reg [{bits-1}:0] {name};")
    lines.append("    always @(*) begin")
    for name, bits in controls:
        lines.append(f"        {name} = 0;")
    lines.append("        case (state)")
    for cycle in range(1, num_cycles + 1):
        lines.append(f"            {cycle}: begin")
        for op in plan["states"][cycle]:
            unit = op["unit"]
            lines.append(f"                // {op['text']}")
            lines.append(f"                {unit}_a_sel = {op['a_sel']}; {unit}_b_sel = {op['b_sel']};")
            lines.append(f"                {op['reg']}_we = 1; {op['reg']}_sel = {op['reg_sel']};")
        lines.append("            end")
    lines.append("        endcase")
    lines.append("    end")
    lines.append("")

    # ---- value registers ----
    for reg_name in plan["registers"]:
        lines.append(f"    reg [{WIDTH-1}:0] {reg_name};")
    lines.append("")

    # ---- functional units with input muxes ----
    for unit_name in plan["units"]:
        unit = plan["units"][unit_name]
        lines.append(f"    // {unit_name}: {UNIT_MODULES[unit['type']]} with a mux on each input")
        lines.append(f"    reg [{WIDTH-1}:0] {unit_name}_a, {unit_name}_b;")
        lines.append(f"    wire [{WIDTH-1}:0] {unit_name}_y;")
        for port in ("a", "b"):
            lines.append("    always @(*) begin")
            lines.append(f"        case ({unit_name}_{port}_sel)")
            for index in range(len(unit[port])):
                lines.append(f"            {index}: {unit_name}_{port} = {unit[port][index]};")
            lines.append(f"            default: {unit_name}_{port} = 0;")
            lines.append("        endcase")
            lines.append("    end")
        lines.append(f"    {UNIT_MODULES[unit['type']]} u_{unit_name} (.a({unit_name}_a), .b({unit_name}_b), .result({unit_name}_y));")
        lines.append("")

    # ---- register writes ----
    lines.append("    // registers: store the selected unit result when write-enabled")
    for reg_name in plan["registers"]:
        register = plan["registers"][reg_name]
        lines.append(f"    // {reg_name} holds: {', '.join(register['values'])}")
        lines.append("    always @(posedge clk) begin")
        lines.append(f"        if (rst) {reg_name} <= 0;")
        lines.append(f"        else if (en && {reg_name}_we) begin")
        lines.append(f"            case ({reg_name}_sel)")
        for index in range(len(register["sources"])):
            lines.append(f"                {index}: {reg_name} <= {register['sources'][index]}_y;")
        lines.append("            endcase")
        lines.append("        end")
        lines.append("    end")
    lines.append("")

    # ---- outputs ----
    for name, reg_name in plan["outputs"]:
        lines.append(f"    assign out_{name} = {reg_name};")

    # unit outputs packed into one bus for observability
    # Ex: units [add0, mul0] -> assign unit_values = {mul0_y, add0_y};
    packed = []
    for unit_name in reversed(unit_names):
        packed.append(f"{unit_name}_y")
    lines.append(f"    assign unit_values = {{{', '.join(packed)}}};")
    lines.append("")
    lines.append("endmodule")

    with open(filename, "w") as file:
        file.write("\n".join(lines) + "\n")
