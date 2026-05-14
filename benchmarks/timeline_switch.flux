intention BenchSwitch {
    trigger: on_boot()
    execute: {
        let start = now();
        for i in [1, 1000] {
            let tl = create_timeline(from: current_timeline(), name: "t" + to_string(i), weight: 0.5);
            set_current_timeline(tl);
        }
        let end = now();
        send_sensation("inner_voice", "1000 switches in " + to_string(end - start), 2s);
    }
}