# EC551-Program2

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
python main.py examples/test3.txt --schedule constrained-asap --add 2 --sub 1 --mul 1 --export-ssa output_ssa.txt

simulate: testbench.v + synth_top.v + functional_units.v (sim top: testbench), should print PASS

board: vivado -mode batch -source build.tcl
(or add top.v, composite_system.v, synth_top.v, functional_units.v, seven_seg.v, generated_config.vh + the xdc in the Vivado GUI)

## Board controls
- sw[3:0], sw[7:4], sw[11:8], sw[15:12] - first 4 inputs (others hardcoded to 2)
- BTNL - step one cycle (first press loads switches)
- BTNR - next display item (outputs, then each functional unit)
- BTNC - reset
- 7-segment: [state][display index][value in hex], LEDs: value in binary
