intention ForkDemo {
    trigger: on_command("fork")
    priority: 0.6
    execute: {
        let original = current_timeline();
        let branch = create_timeline();
        set_current_timeline(branch);
        send("inner_voice", "in timeline: " ++ current_timeline(), 1s);
        sleep(2s);
        merge_timelines(branch, original);
        set_current_timeline(original);
        send("inner_voice", "merged back to: " ++ current_timeline(), 1s);
    }
}
