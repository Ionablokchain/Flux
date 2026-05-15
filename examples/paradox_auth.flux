function authenticate() -> bool {
    let p = generate_paradox();
    let input = listen(user, 10s, p);
    return input == p;
}

intention Secret {
    trigger: on_command("secret")
    priority: 0.9
    execute: {
        if authenticate() {
            send("mental_image", "access granted", 2s);
        } else {
            send("tactile", "access denied", 1s);
        }
    }
}
