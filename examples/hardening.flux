intention HardenDemo {
    trigger: on_command("harden")
    priority: 0.7
    execute: {
        let dur = parse_duration("5s");
        let cost = estimate_hardening_cost();
        if cost < 0.01 {
            causal_hardening(dur, cost);
            send("inner_voice", "hardened " ++ to_string(dur) ++ " of reality", 2s);
        } else {
            send("inner_voice", "not enough causal_void", 2s);
        }
    }
}
