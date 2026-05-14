// Causal clock generator – placeholder
module temporal_clock (
    output reg causal_time
);
    initial causal_time = 0;
    always #10 causal_time = causal_time + 1;
endmodule