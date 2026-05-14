intention ForkDemo {
    trigger: on_command("fork")
    execute: {
        let original = current_timeline();
        let new_tl = create_timeline(from: original, name: "parallel", weight: 0.8);
        set_current_timeline(new_tl);
        send_sensation("inner_voice", "Now in timeline: " + new_tl, 1s);
        sleep(2s);
        merge_timelines(source: new_tl, target: original, method: "probabilistic_union");
        send_sensation("inner_voice", "Merged back. Welcome to original timeline.", 1s);
    }
}