function authenticate() -> bool {
    let p = generate_paradox(type: "prime_interval_sequence", interval: [now(), now()+10s]);
    let code = resolve_paradox(p, "extract_sequence");
    send_sensation("inner_voice", "Enter paradox code:", 2s);
    let input = listen_intention(user, 10s, "");
    return input == code;
}

intention Secret {
    trigger: on_command("secret")
    execute: {
        if authenticate() then {
            send_sensation("mental_image", "🔓 Access granted.", 2s);
        } else {
            send_sensation("tactile", "access denied – timeline reset", 1s);
            reset_timeline(current_user());
        }
    }
}