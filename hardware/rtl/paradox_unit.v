// Hardware paradox accelerator – placeholder
module paradox_unit (input [7:0] seed, output [31:0] paradox_code);
    assign paradox_code = seed * 1103515245 + 12345;
endmodule