`timescale 1ns / 1ps
`include "generated_config.vh"   // defines NUM_OBSERVABLES (written by wrapper_gen.py)

// clock cycles can be stepped through via button press
// functional unit outputs can be cycled through via button press
// 7-segment display: [7:6] FSM state, [5:4] display_sel, [3:0] selected value (hex)
module top #(
    parameter NUM_OBSERVABLES = `NUM_OBSERVABLES,
    parameter SELECT_WIDTH = $clog2(NUM_OBSERVABLES)
)(
    input clk, rst, step_btn, display_btn,
    input [15:0] sw,
    output [15:0] led,
    output [7:0] an,
    output [6:0] seg,
    output dp
);

    // debounced button pulses
    wire step_pulse, display_pulse;

    // display selection register
    reg [SELECT_WIDTH-1:0] display_sel;

    // flattened bus of observable values
    wire [NUM_OBSERVABLES*16-1:0] observables;

    // current FSM state (0 = IDLE, last = DONE)
    wire [7:0] state;

    // selected output value
    reg [15:0] selected_data;

    // step button debouncer
    button_debounce step_debounce(.clk(clk),
                                  .rst(rst),
                                  .btn(step_btn),
                                  .pulse(step_pulse));

    // display button debouncer
    button_debounce display_debounce(.clk(clk),
                                     .rst(rst),
                                     .btn(display_btn),
                                     .pulse(display_pulse));

    // generated datapath and controller
    composite_system dut (
        .clk(clk),
        .rst(rst),
        .step_en(step_pulse),
        .sw(sw),
        .observables(observables),
        .state(state)
    );

    // cycle through observable values
    always @(posedge clk) begin
        if(rst) begin
            display_sel <= 0;
        end else if(display_pulse) begin
            if(display_sel == NUM_OBSERVABLES - 1)
                display_sel <= 0;
            else
                display_sel <= display_sel + 1'b1;
        end
    end

    // select which value appears on LEDs
    always @(*) begin
        selected_data = observables[display_sel*16 +: 16];
    end

    assign led = selected_data;

    // 7-segment display: state, display_sel, value
    wire [7:0] sel_8 = display_sel;
    seven_seg display(.clk(clk),
                      .value({state, sel_8, selected_data}),
                      .an(an),
                      .seg(seg));
    assign dp = 1'b1;   // decimal points off
endmodule


// debounce button signal: one-clock pulse per press
// button must be held ~10 ms (counter fills) before it counts
module button_debounce(input clk, input rst, input btn, output pulse);
    reg [19:0] counter = 0;
    reg clean = 0;
    reg clean_prev = 0;

    always @(posedge clk) begin
        if(rst) begin
            counter <= 0;
            clean <= 0;
        end else begin
            if(btn) begin
                if(!(&counter)) // not max count
                    counter <= counter + 1; // debounce button press
            end else begin
                if(counter != 0)
                    counter <= counter - 1; // debounce button release
            end

            if(&counter)
                clean <= 1;
            else if(counter == 0)
                clean <= 0;
        end
    end

    // detect rising edge of debounced signal
    always @(posedge clk) begin
        clean_prev <= clean;
    end

    // pulse is only high for 1 cycle
    assign pulse = clean & ~clean_prev;
endmodule
