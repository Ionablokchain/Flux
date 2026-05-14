intention BenchCollapse {
    trigger: on_boot()
    execute: {
        let start = now();
        for i in [1, 10000] {
            let _ = collapse(0.5, "random");
        }
        let end = now();
        send_sensation("inner_voice", "10000 collapses in " + to_string(end - start), 2s);
    }
}