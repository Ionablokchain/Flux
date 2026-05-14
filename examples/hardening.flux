intention HardenDemo {
    trigger: on_command("harden")
    execute: {
        let dur = parse_duration(listen_intention(user, 5s, "5s"));
        let cost = estimate_hardening_cost(interval: [now(), now()+dur]);
        if cost < 0.01 then {
            causal_hardening(interval: [now(), now()+dur], max_cost: cost);
            send_sensation("inner_voice", "Hardened " + to_string(dur) + " of reality.", 2s);
        } else {
            send_sensation("inner_voice", "Not enough quantum vacuum.", 2s);
        }
    }
}