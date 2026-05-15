intention BenchCollapse {
    trigger: on_boot()
    priority: 1.0
    execute: {
        let start = now();
        for i in [1, 10000] {
            let _ = collapse(0.5, "weighted_random");
        }
        let end = now();
        send("inner_voice", "10000 collapses: " ++ to_string(end - start), 2s);
    }
}
