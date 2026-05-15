intention Hello {
    trigger: on_boot()
    priority: 0.9
    condition: causal_void.exists()
    execute: {
        send("mental_image", "Hello from Flux", 2s);
    }
}
