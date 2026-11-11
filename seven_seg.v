`timescale 1ns / 1ps

// seven_seg: shows a 32-bit value as 8 hex digits on the Nexys A7 display
// digits are lit one at a time, fast enough (~95 Hz per digit) to look steady
// anodes and segments are active low; seg = {g, f, e, d, c, b, a}
// Ex: value = 32'h0601_0042 -> display shows "06010042"
module seven_seg (
    input clk,
    input [31:0] value,
    output reg [7:0] an,
    output reg [6:0] seg
);
    reg [19:0] refresh = 0;
    always @(posedge clk) refresh <= refresh + 1;

    wire [2:0] digit = refresh[19:17];   // which digit is lit right now
    wire [3:0] hex = value[digit*4 +: 4];

    always @(*) begin
        an = 8'hFF;
        an[digit] = 1'b0;

        case (hex)
            4'h0: seg = 7'b1000000;
            4'h1: seg = 7'b1111001;
            4'h2: seg = 7'b0100100;
            4'h3: seg = 7'b0110000;
            4'h4: seg = 7'b0011001;
            4'h5: seg = 7'b0010010;
            4'h6: seg = 7'b0000010;
            4'h7: seg = 7'b1111000;
            4'h8: seg = 7'b0000000;
            4'h9: seg = 7'b0010000;
            4'hA: seg = 7'b0001000;
            4'hB: seg = 7'b0000011;
            4'hC: seg = 7'b1000110;
            4'hD: seg = 7'b0100001;
            4'hE: seg = 7'b0000110;
            default: seg = 7'b0001110;   // F
        endcase
    end
endmodule
