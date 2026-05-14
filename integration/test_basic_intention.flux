intention HelloTest {
    trigger: on_boot()
    execute: {
        send_sensation("inner_voice", "Integration test passed", 1s);
    }
}