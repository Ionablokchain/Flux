mosaic store {
    components: sparse_temporal_matrix(),
    policies: { write: "add_branch", read: "most_probable" }
}

intention Save {
    trigger: on_command("save")
    execute: {
        let key = listen_intention(user, 5s, "key");
        let val = listen_intention(user, 5s, "value");
        store.accept(key: key).write(value: val, weight: 1.0);
        send_sensation("tactile", "saved", 0.3s);
    }
}

intention Load {
    trigger: on_command("load")
    execute: {
        let key = listen_intention(user, 5s, "key");
        let val = store.accept(key: key).read() otherwise "<missing>";
        send_sensation("inner_voice", to_string(val), 1s);
    }
}