# EC551-Program2

## Description
This project implements a simplified high-level synthesis (HLS) tool that converts arithmetic equations into synthesizable Verilog hardware. The program reads a text file containing arithmetic expressions, converts them into Static Single Assignment (SSA) form, and constructs a Directed Acyclic Graph (DAG) representing dependencies between operations. It then schedules the operations using one of five available scheduling algorithms, allocates the required arithmetic functional units and registers, and generates a composite Verilog datapath with an FSM controller.

The generated hardware supports addition, subtraction, and multiplication using 16-bit functional units. Each operation completes in one scheduled execution cycle, and intermediate results are stored in registers for use by subsequent operations. The design supports resource sharing across execution cycles, allowing multiple arithmetic operations to reuse the same physical functional unit. A generated testbench verifies the hardware against expected results, while the FPGA wrapper supports manual execution stepping and observation of intermediate and final results. All arithmetic results are truncated to 16 bits. 

## Files
- `main.py` - command line tool: parse -> SSA -> DAG -> schedules -> Verilog
- `parser.py` - equation parsing, SSA conversion, SSA export
- `dag.py` - DAG construction
- `scheduler.py` - ASAP, ALAP, constrained ASAP/ALAP, custom schedules
- `rtl_gen.py` - writes `synth_top.v` (FSM controller + muxes + registers + functional units)
- `tb_gen.py` - writes `testbench.v` (self-checking simulation)
- `wrapper_gen.py` - writes `composite_system.v` and `generated_config.vh` for the board
- `functional_units.v` - adder, subtracter, multiplier (16 bit)
- `top.v` - FPGA top module (debounced buttons, display select, 7-segment)
- `seven_seg.v` - 8 digit hex display driver
- `Nexys4DDR_Master.xdc` - pin constraints
- `build.tcl` - one-command synthesize + program
- `examples/` - test equation files

## Run
The scheduler CLI accepts a required input file and optional scheduling/resource/export flags:

```bash
python main.py example.txt [--schedule ALGORITHM] [--add N] [--sub N] [--mul N] [--export-ssa FILE]
```

| Argument | Meaning | Default |
|---|---|---|
| `input` | Required path to arithmetic-equation text file | Required |
| `--schedule` | `asap`, `alap`, `constrained-asap`, `constrained-alap`, or `custom` | `custom` |
| `--add N` | Available adders for resource-constrained scheduling | `1` |
| `--sub N` | Available subtracters for resource-constrained scheduling | `1` |
| `--mul N` | Available multipliers for resource-constrained scheduling | `1` |
| `--export-ssa FILE` | Write SSA equations to a separate file | Disabled |

### Scheduling algorithms

| CLI value | Algorithm | Description |
|---|---|---|
| `asap` | As Soon As Possible | Earliest legal cycles; no resource limit |
| `alap` | As Late As Possible | Latest legal cycles within minimum unconstrained latency |
| `constrained-asap` | Resource-Constrained ASAP | Forward scheduling under FU limits |
| `constrained-alap` | Resource-Constrained ALAP | Backward scheduling under FU limits |
| `custom` | Hardware-aware scheduling | Searches FU configurations using a weighted latency/area cost |


The custom scheduler evaluates candidate configurations using a cost of `3 × latency + adders + subtracters + 5 × multipliers`. The `--add`, `--sub`, and `--mul` limits apply to the constrained algorithms; the custom algorithm explores configurations independently.

Example command: 
python main.py examples/test3.txt --schedule constrained-asap --add 2 --sub 1 --mul 1 --export-ssa output_ssa.txt

simulation: testbench.v + synth_top.v + functional_units.v + generated_config.vh (sim top: testbench), should print PASS

board: vivado -mode batch -source build.tcl
(or add top.v, composite_system.v, synth_top.v, functional_units.v, seven_seg.v, generated_config.vh + the xdc in the Vivado GUI)

## Board controls
- sw[3:0], sw[7:4], sw[11:8], sw[15:12] - first 4 inputs (others hardcoded to 2)
- BTNL - step one cycle (first press loads switches)
- BTNR - next display item (outputs, then each functional unit)
- BTNC - reset
- 7-segment: [state][display index][value in hex], LEDs: value in binary

## Demo plan
The demo plan will consist of explaining the core functionalities of each component, executing the program on several test cases and examining the results, and showcasing functionality on the FPGA. 

Demo tests:
1. python main.py examples/test1.txt --schedule constrained-asap --add 1 --sub 1 --mul 1 --export-ssa output_ssa.txt
2. python main.py examples/test2.txt --schedule asap --add 2 --sub 1 --mul 2 --export-ssa output_ssa.txt
3. python main.py examples/test3.txt --schedule constrained-alap --add 1 --sub 1 --mul 1 --export-ssa output_ssa.txt
4. python main.py examples/test4.txt --schedule custom --export-ssa output_ssa.txt
