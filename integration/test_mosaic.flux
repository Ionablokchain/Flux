causal_mosaic test_store = sparse_temporal_matrix();

intention WriteRead {
    trigger: on_boot()
    priority: 1.0
    execute: {
        test_store.accept("x").write(42, 1.0);
        let val = test_store.accept("x").read();
        send("inner_voice", "read: " ++ to_string(val), 1s);
    }
}
