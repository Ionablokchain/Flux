intention BenchSwitch {
    trigger: on_boot()
    priority: 1.0
    execute: {
        let start = now();
        for i in [1, 1000] {
            let tl = create_timeline();
            set_current_timeline(tl);
        }
        let end = now();
        send("inner_voice", "1000 switches: " ++ to_string(end - start), 2s);
    }
}
