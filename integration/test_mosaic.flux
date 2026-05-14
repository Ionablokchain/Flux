mosaic test_mosaic {
    components: sparse_temporal_matrix(),
    policies: { write: "add_branch", read: "most_probable" }
}

intention WriteRead {
    trigger: on_boot()
    execute: {
        test_mosaic.accept(key: "x").write(value: 42, weight: 1.0);
        let val = test_mosaic.accept(key: "x").read();
        send_sensation("inner_voice", "Read: " + to_string(val), 1s);
    }
}