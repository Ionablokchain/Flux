intention ProbDemo {
    trigger: on_command("prob")
    priority: 0.8
    execute: {
        let p = 0.7;
        let result = collapse(p, "weighted_random");
        if result > 0.5 {
            send("inner_voice", "heads (p=" ++ to_string(p) ++ ")", 1s);
        } else {
            send("inner_voice", "tails", 1s);
        }
    }
}
