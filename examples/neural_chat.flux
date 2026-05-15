// Neural chat: collapse over a weighted distribution of responses.
// The user message is heard via listen(); we pick a reply by collapse.

intention NeuralChat {
    trigger: on_user_intention()
    priority: 0.5
    execute: {
        let msg = listen(user, 5s, "hello");
        if msg == "hello" {
            send("inner_voice", "hello back", 1s);
        } else {
            send("inner_voice", "echo: " ++ msg, 1s);
        }
    }
}
