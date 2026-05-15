intention HelloTest {
    trigger: on_boot()
    priority: 1.0
    execute: {
        send("inner_voice", "integration test passed", 1s);
    }
}
