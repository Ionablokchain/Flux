// A mosaic is a sparse temporal store: keys map to weighted value branches.
// The default read policy returns the most probable (highest-weight) value.

causal_mosaic store = sparse_temporal_matrix();

intention Save {
    trigger: on_command("save")
    priority: 0.8
    execute: {
        let key = listen(user, 5s, "default_key");
        let val = listen(user, 5s, "default_value");
        store.accept(key).write(val, 1.0);
        send("tactile", "saved", 300ms);
    }
}

intention Load {
    trigger: on_command("load")
    priority: 0.7
    execute: {
        let key = listen(user, 5s, "default_key");
        let val = store.accept(key).read();
        send("inner_voice", "loaded: " ++ to_string(val), 1s);
    }
}
