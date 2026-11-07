
// inputs and outputs are 16 bits for each functional unit:
// intermediate results can quickly exceed small input bit widths (ex: sequence of multiplications)
// uses built in vivado functions to implement each: ('+', '-', '*')

module adder(input [15:0] a, b, 
             output [15:0] result);
    assign result = a + b;
endmodule

// assumes negative results do not need to be handled (as stated by assignment)
module subtracter(input [15:0] a, b, 
             output [15:0] result);
    assign result = a - b;
endmodule

module multiplier(input [15:0] a, b, 
             output [7:0] result);
    assign result = a * b;
endmodule