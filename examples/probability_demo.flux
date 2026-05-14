intention ProbDemo {
    trigger: on_command("prob")
    execute: {
        let p = 0.7;
        let result = collapse(p, "random");
        if result > 0.5 then {
            send_sensation("inner_voice", "Heads (probability " + to_string(p) + ")", 1s);
        } else {
            send_sensation("inner_voice", "Tails", 1s);
        }
    }
}