intention Chat {
    trigger: on_user_intention()
    execute: {
        let msg = listen_intention(user, 5s, "");
        if msg != "" then {
            send_sensation("inner_voice", "Echo: " + msg, 1s);
        }
    }
}